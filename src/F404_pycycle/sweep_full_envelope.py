"""
Full-envelope cycle deck builder for the F404 mixed-flow turbofan.

Runs two separate sweeps — dry (mil power and below) and wet (afterburning) —
using two independent om.Problem instances, one per mode.

Dry sweep
---------
  - afterburn=False: no FAR_ab balance; afterburner is a zero-FAR pass-through
  - 'power' in sweep points = Tt4 target (degR)

Wet sweep
---------
  - afterburn=True: FAR_ab balance drives T7 to target
  - 'power' in sweep points = T7 (Tt7) target (degR)
  - Tt4 is fixed at mil power (mil_Tt4) for the entire wet sweep
  - DESIGN anchor: Tt7=3800 degR (max AB), Fn=17,700 lbf — correct sizing point
  - Sweep covers partial-AB range (3200–3800 degR); thrust is an output, not a target

Usage:
    python sweep_full_envelope.py                   # both dry and wet (default)
    python sweep_full_envelope.py --mode dry        # dry sweep only
    python sweep_full_envelope.py --mode wet        # wet sweep only
"""
import argparse
import logging
import time
import warnings

import numpy as np
import openmdao.api as om
import pandas as pd

from F404_pycycle.mp_cycle import MPMixedFlowTurbofan
from F404_pycycle.printer import page_viewer
from F404_pycycle.sweep_utils import build_snake_sweep, SweepRunner

warnings.filterwarnings('ignore', category=RuntimeWarning)
try:
    from openmdao.utils.om_warnings import SolverWarning
    warnings.filterwarnings('ignore', category=SolverWarning)
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ── Shared design geometry ────────────────────────────────────────────────────
# TODO: Unify dry and wet under a single sized engine.
# Currently setup_dry_problem() and setup_wet_problem() each create their own
# om.Problem with an independent DESIGN solve — sizing two different engines
# (~1–2% different W, BPR, map scalars, station areas) rather than one F404.
# Path forward: anchor sizing at wet max-AB conditions and reuse those scalars
# for dry OD. See docs/single_engine_mode.md for design options and tradeoffs.
MIL_Tt4    = 3100.   # degR — core burner exit at mil power (throttle wall)
DSN_Tt7    = 3800.   # degR — afterburner exit at DESIGN point (wet only; max AB)
DRY_DSN_FN = 11000.  # lbf  — SLS mil power (no afterburner)
WET_DSN_FN = 17700.  # lbf  — SLS max afterburner

# Columns serialized with 4 decimals rather than the 2-decimal default: rates,
# ratios, bypass ratio, spool speeds and Mach — the continuous quantities a
# downstream tool or optimizer would ingest, where extra resolution is cheap and
# useful. Thrust, temperatures and flight conditions stay at 2 decimals.
DECK_HI_PRECISION_COLS = {
    'MN', 'TSFC', 'W', 'BPR',
    'OPR', 'fan_PR', 'hpc_PR', 'hpt_PR', 'lpt_PR',
    'LP_Nmech', 'HP_Nmech',
}

# Fuel-air ratios sit around 0.03–0.04, so a fixed-decimal format wastes its
# shown digits on the leading zeros: at %.4f the small dTs-driven variation in
# augmentor/core fueling (5th–6th decimal) flattens to a constant. Scientific
# notation spends every shown digit on significant figures instead, so the
# point-to-point change stays visible.
DECK_SCI_COLS = {'FAR_core', 'FAR_ab'}


def write_deck_csv(df, path):
    """Write a cycle-deck DataFrame to CSV at capped precision.

    The single writer for every deck (dry, wet, combined). The raw float64 repr
    (15+ significant figures) is meaningless for engine performance data — no
    model input or sensor is accurate to that precision — and bloats the deck as
    sweeps scale up. pandas' float_format is global, so per-column precision is
    applied here before writing: scientific %.4e for DECK_SCI_COLS, 4 decimals
    for DECK_HI_PRECISION_COLS, 2 decimals otherwise.
    """
    out = df.copy()
    for col in out.select_dtypes('number'):
        if col in DECK_SCI_COLS:
            fmt = '%.4e'
        elif col in DECK_HI_PRECISION_COLS:
            fmt = '%.4f'
        else:
            fmt = '%.2f'
        out[col] = out[col].map(fmt.__mod__)
    out.to_csv(path, index=False)


def _apply_design_inputs(prob, fn_target):
    """Set design-point values and initial guesses (shared by both modes).

    fn_target : float
        SLS thrust target in lbf. Use DRY_DSN_FN (11,000) for dry mode and
        WET_DSN_FN (17,700) for wet (max-AB) mode — sizing the engine for
        the wrong thrust pins the W balance at its upper bound and corrupts
        all subsequent OD points.
    """
    prob.set_val('DESIGN.fc.alt', 0.0, units='ft')
    prob.set_val('DESIGN.fc.MN', 0.01)
    prob.set_val('DESIGN.balance.rhs:W', fn_target, units='lbf')
    prob.set_val('DESIGN.balance.rhs:FAR_core', MIL_Tt4, units='degR')

    prob.set_val('DESIGN.fan.PR', 4.1)
    prob.set_val('DESIGN.fan.eff', 0.8948)
    prob.set_val('DESIGN.hpc.PR', 6.5)
    prob.set_val('DESIGN.hpc.eff', 0.8707)
    prob.set_val('DESIGN.hpt.eff', 0.8888)
    prob.set_val('DESIGN.lpt.eff', 0.8996)

    # Design initial guesses
    prob['DESIGN.fc.balance.Pt']   = 5.3
    prob['DESIGN.fc.balance.Tt']   = 450.
    prob['DESIGN.balance.W']       = 120.0
    prob['DESIGN.balance.BPR']     = 0.65
    prob['DESIGN.balance.FAR_core'] = 0.025
    prob['DESIGN.balance.hpt_PR']  = 2.5506
    prob['DESIGN.balance.lpt_PR']  = 2.5
    prob['DESIGN.mixer.balance.P_tot'] = 55.


def _apply_od_guesses(prob, pt):
    """Set OD initial guesses (shared starting point for both modes)."""
    prob[pt + '.fc.balance.Pt']    = 14.7
    prob[pt + '.fc.balance.Tt']    = 519.
    prob[pt + '.balance.FAR_core'] = 0.025
    prob[pt + '.balance.BPR']      = 0.35
    prob[pt + '.balance.W']        = 100.
    prob[pt + '.balance.HP_Nmech'] = 15000.
    prob[pt + '.balance.LP_Nmech'] = 10000.
    prob[pt + '.mixer.balance.P_tot'] = 55.
    prob[pt + '.hpt.PR']           = 2.523
    prob[pt + '.lpt.PR']           = 2.401
    prob[pt + '.fan.map.RlineMap'] = 2.0
    prob[pt + '.hpc.map.RlineMap'] = 2.0


def setup_dry_problem():
    """Build and return a converged dry (no afterburner) MPCycle problem."""
    prob = om.Problem()
    prob.model = mp = MPMixedFlowTurbofan(afterburn=False)
    prob.setup()

    _apply_design_inputs(prob, DRY_DSN_FN)

    # Dry mode: afterburner is a pyc.Duct (no fuel addition), so there is
    # no Fl_I:FAR balance/input to override here. FAR propagates through
    # from the upstream mixer_duct flow as-is.

    pt = mp.od_pt
    _apply_od_guesses(prob, pt)

    # Pre-set OD flight conditions before first run_model() (runs DESIGN + OD together)
    prob.set_val(pt + '.fc.alt', 0.0, units='ft')
    prob.set_val(pt + '.fc.MN', 0.01)
    prob.set_val(pt + '.fc.dTs', 0.0, units='degR')
    prob.set_val(pt + '.balance.rhs:FAR_core', MIL_Tt4, units='degR')

    prob.set_solver_print(level=-1)
    prob.set_solver_print(level=2, depth=1)

    print("=" * 60)
    print("DRY — Running DESIGN point...")
    print("=" * 60)
    prob.run_model()
    page_viewer(prob, 'DESIGN')

    # Verify OD at design conditions
    print("\n" + "=" * 60)
    print("DRY — Verifying OD at design conditions...")
    print("=" * 60)
    prob.set_val(pt + '.fc.alt', 0.0, units='ft')
    prob.set_val(pt + '.fc.MN', 0.01)
    prob.set_val(pt + '.fc.dTs', 0.0, units='degR')
    prob.set_val(pt + '.balance.rhs:FAR_core', MIL_Tt4, units='degR')
    prob.run_model()
    page_viewer(prob, pt)

    return prob, mp


def setup_wet_problem():
    """Build and return a converged wet (afterburning) MPCycle problem."""
    prob = om.Problem()
    prob.model = mp = MPMixedFlowTurbofan(afterburn=True)
    prob.setup()

    _apply_design_inputs(prob, WET_DSN_FN)

    # Wet DESIGN: set T7 target and FAR_ab initial guess
    prob.set_val('DESIGN.balance.rhs:FAR_ab', DSN_Tt7, units='degR')
    prob['DESIGN.balance.FAR_ab'] = 0.0375

    pt = mp.od_pt
    _apply_od_guesses(prob, pt)
    prob[pt + '.balance.FAR_ab'] = 0.025

    # Pre-set OD flight conditions and targets before first run_model()
    prob.set_val(pt + '.fc.alt', 0.0, units='ft')
    prob.set_val(pt + '.fc.MN', 0.01)
    prob.set_val(pt + '.fc.dTs', 0.0, units='degR')
    prob.set_val(pt + '.balance.rhs:FAR_core', MIL_Tt4, units='degR')
    # OD T7 target — will be overridden per-iteration during sweep
    prob.set_val(pt + '.balance.rhs:FAR_ab', DSN_Tt7, units='degR')

    prob.set_solver_print(level=-1)
    prob.set_solver_print(level=2, depth=1)

    print("=" * 60)
    print("WET — Running DESIGN point...")
    print("=" * 60)
    prob.run_model()
    page_viewer(prob, 'DESIGN')

    # Verify OD at design conditions
    print("\n" + "=" * 60)
    print("WET — Verifying OD at design conditions...")
    print("=" * 60)
    prob.set_val(pt + '.fc.alt', 0.0, units='ft')
    prob.set_val(pt + '.fc.MN', 0.01)
    prob.set_val(pt + '.fc.dTs', 0.0, units='degR')
    prob.set_val(pt + '.balance.rhs:FAR_core', MIL_Tt4, units='degR')
    prob.set_val(pt + '.balance.rhs:FAR_ab', DSN_Tt7, units='degR')
    prob.run_model()
    page_viewer(prob, pt)

    return prob, mp


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    parser.add_argument('--mode', choices=['dry', 'wet', 'both'], default='both',
                        help="Sweep mode (default: both). Use 'dry' or 'wet' "
                             "to run only one mode without re-running the other.")
    args = parser.parse_args()

    # ── Sweep grid (shared by both modes) ────────────────────────────────────
    # Crawl-walk-run scope: low altitudes, static conditions on the runway.
    alts      = np.arange(0, 5001, 2500)       # [0, 2500, 5000] ft — 3 pts
    # dTs ordering: anchor at 0 (matches OD verification), walk hot first
    # (+10..+50), then jump to cold side (-10..-50). Bridge logic handles
    # the +50 → -10 jump within each alt level.
    dTs_vals  = [0., 10., 20., 30., 40., 50.,
                 -10., -20., -30., -40., -50.]   # 11 pts, hot-first
    MACH      = 0.001                           # static (runway) conditions

    # Dry: sweep Tt4 from mil (3100) down to part-power (2500)
    dry_powers = [3100., 2900., 2700., 2500.]   # Tt4, degR

    # Wet: sweep T7 from min AB (3200) up to max (3800)
    wet_powers = [3800., 3600., 3400., 3200.]   # Tt7, degR

    st_total = time.time()
    df_dry = df_wet = None
    n_dry = n_wet = 0

    # ── DRY SWEEP ────────────────────────────────────────────────────────────
    if args.mode in ('dry', 'both'):
        prob_dry, mp_dry = setup_dry_problem()
        prob_dry.set_solver_print(level=-1)

        dry_sweep_pts = build_snake_sweep(alts, dTs_vals, dry_powers)
        n_dry = len(dry_sweep_pts)
        print(f"\nDry sweep matrix: {n_dry} points")

        runner_dry = SweepRunner(
            prob_dry, od_pt=mp_dry.od_pt, mach=MACH,
            afterburn=False,
        )
        df_dry = runner_dry.run_sweep(
            dry_sweep_pts,
            bridge_threshold={'alt': 2000, 'dTs': 30, 'power': 100},
            max_bridge_steps=5,
        )
        df_dry['mode'] = 'dry'
        write_deck_csv(df_dry, 'cycle_deck_dry.csv')

    # ── WET SWEEP ────────────────────────────────────────────────────────────
    if args.mode in ('wet', 'both'):
        prob_wet, mp_wet = setup_wet_problem()
        prob_wet.set_solver_print(level=-1)

        wet_sweep_pts = build_snake_sweep(alts, dTs_vals, wet_powers)
        n_wet = len(wet_sweep_pts)
        print(f"\nWet sweep matrix: {n_wet} points")

        runner_wet = SweepRunner(
            prob_wet, od_pt=mp_wet.od_pt, mach=MACH,
            afterburn=True, mil_Tt4=MIL_Tt4,
        )
        df_wet = runner_wet.run_sweep(
            wet_sweep_pts,
            bridge_threshold={'alt': 2000, 'dTs': 30, 'power': 100},
            max_bridge_steps=5,
        )
        df_wet['mode'] = 'wet'
        write_deck_csv(df_wet, 'cycle_deck_wet.csv')

    # ── Combined CSV (only when both modes ran) ──────────────────────────────
    if df_dry is not None and df_wet is not None:
        df_all = pd.concat([df_dry, df_wet], ignore_index=True)
        write_deck_csv(df_all, 'cycle_deck_full_envelope.csv')

    elapsed = time.time() - st_total
    print(f"\nSweep complete in {elapsed:.1f}s")
    if df_dry is not None:
        print(f"  Dry: {len(df_dry)} / {n_dry} converged → cycle_deck_dry.csv")
    if df_wet is not None:
        print(f"  Wet: {len(df_wet)} / {n_wet} converged → cycle_deck_wet.csv")
    if df_dry is not None and df_wet is not None:
        print(f"  Combined: {len(df_dry) + len(df_wet)} rows → cycle_deck_full_envelope.csv")
