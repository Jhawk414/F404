"""
Full-envelope cycle deck builder for the F404 mixed-flow turbofan.

Sizes one engine (DESIGN at SLS dry mil) and sweeps it in two modes, each on
its own off-design point of the same om.Problem.

Dry sweep (OD_dry)
------------------
  - afterburner is a Duct; 'power' in sweep points = Tt4 target (degR)

Wet sweep (OD_wet)
------------------
  - FAR_ab balance drives T7 to target; 'power' in sweep points = Tt7 (degR)
  - Tt4 is fixed at mil power (mil_Tt4) for the entire wet sweep
  - A8 is set by the nozzle control law (fan held on its design operating line)
  - Thrust is an output, not a target

Usage (see F404_pycycle.cli for the full flag set):
    f404 sweep                       # both modes, default grid
    f404 sweep --mode dry            # dry sweep only
    f404 sweep --mode wet --alt 0,10000,1000 --out decks/run1
"""
import logging
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from F404_pycycle.problems import build_problem, MIL_Tt4
from F404_pycycle.sweep_utils import build_snake_sweep, SweepRunner

# ── Default sweep grid (shared by both modes) ────────────────────────────────
# Crawl-walk-run scope: low altitudes, static conditions on the runway.
DEFAULT_ALTS = np.arange(0, 5001, 2500)        # [0, 2500, 5000] ft — 3 pts
# dTs ordering: anchor at 0 (matches OD verification), walk hot first
# (+10..+50), then jump to cold side (-10..-50). Bridge logic handles
# the +50 → -10 jump within each alt level.
DEFAULT_DTS = [0., 10., 20., 30., 40., 50.,
               -10., -20., -30., -40., -50.]   # 11 pts, hot-first
MACH = 0.001                                   # static (runway) conditions

# Dry: sweep Tt4 from mil (3100) down to part-power (2500)
DEFAULT_DRY_POWERS = [3100., 2900., 2700., 2500.]   # Tt4, degR
# Wet: sweep T7 from max (problems.MAX_Tt7) down to min AB
DEFAULT_WET_POWERS = [3608., 3408., 3208., 3008.]   # Tt7, degR

BRIDGE_THRESHOLD = {'alt': 2000, 'dTs': 30, 'power': 100}
MAX_BRIDGE_STEPS = 5

# Columns serialized with 4 decimals rather than the 2-decimal default: rates,
# ratios, bypass ratio, spool speeds and Mach — the continuous quantities a
# downstream tool or optimizer would ingest, where extra resolution is cheap and
# useful. Thrust, temperatures and flight conditions stay at 2 decimals.
DECK_HI_PRECISION_COLS = {
    'MN', 'TSFC', 'W', 'BPR',
    'OPR', 'fan_PR', 'hpc_PR', 'hpt_PR', 'lpt_PR',
    'LP_Nmech', 'HP_Nmech', 'Wf_core', 'Wf_ab',
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


def configure_runtime():
    """Quiet the expected solver noise and set up logging.

    Called from main() rather than at import so that importing this module
    (tests, other drivers) doesn't reconfigure the host's logging or warnings.
    """
    warnings.filterwarnings('ignore', category=RuntimeWarning)
    try:
        from openmdao.utils.om_warnings import SolverWarning
        warnings.filterwarnings('ignore', category=SolverWarning)
    except ImportError:
        pass

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def run_mode_sweep(mode, alts, dTs_vals, powers, out_dir='.', built=None):
    """Sweep one mode of the sized engine and write its deck.

    Parameters
    ----------
    mode : {'dry', 'wet'}
    alts, dTs_vals, powers : sequence of float
        The sweep axes, already in traversal order. ``powers`` is Tt4 (degR)
        in dry mode and Tt7 (degR) in wet mode.
    out_dir : path-like
        Directory the ``cycle_deck_<mode>.csv`` is written to.
    built : (Problem, MPMixedFlowTurbofan), optional
        A problem from ``build_problem()`` to sweep; built here if omitted.

    Returns
    -------
    (pandas.DataFrame, int)
        The converged rows (with a ``mode`` column) and the number of points
        the sweep attempted.
    """
    if mode == 'dry':
        runner_kwargs = dict(afterburn=False)
    elif mode == 'wet':
        runner_kwargs = dict(afterburn=True, mil_Tt4=MIL_Tt4)
    else:
        raise ValueError(f"mode must be 'dry' or 'wet', got {mode!r}")
    prob, mp = built if built is not None else build_problem()
    prob.set_solver_print(level=-1)

    sweep_pts = build_snake_sweep(alts, dTs_vals, powers)
    print(f"\n{mode.capitalize()} sweep matrix: {len(sweep_pts)} points")

    frozen = [pt for m, pt in mp.od_pts.items() if m != mode]
    runner = SweepRunner(prob, od_pt=mp.od_pts[mode], mach=MACH,
                         frozen_pts=frozen, **runner_kwargs)
    df = runner.run_sweep(
        sweep_pts,
        bridge_threshold=BRIDGE_THRESHOLD,
        max_bridge_steps=MAX_BRIDGE_STEPS,
    )
    df['mode'] = mode
    write_deck_csv(df, Path(out_dir) / f'cycle_deck_{mode}.csv')
    return df, len(sweep_pts)


def run_sweeps(mode, alts=DEFAULT_ALTS, dTs_vals=DEFAULT_DTS,
               dry_powers=DEFAULT_DRY_POWERS, wet_powers=DEFAULT_WET_POWERS,
               out_dir='.'):
    """Run the dry sweep, the wet sweep, or both, and write the decks.

    ``mode`` is 'dry', 'wet' or 'both'; 'both' also writes the combined
    ``cycle_deck_full_envelope.csv``. The engine is sized once and both modes
    sweep it. Returns ``{mode: DataFrame}`` for the modes that ran.
    """
    if mode not in ('dry', 'wet', 'both'):
        raise ValueError(f"mode must be 'dry', 'wet' or 'both', got {mode!r}")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    st_total = time.time()
    built = build_problem()
    results, attempted = {}, {}
    for m, powers in (('dry', dry_powers), ('wet', wet_powers)):
        if mode in (m, 'both'):
            results[m], attempted[m] = run_mode_sweep(
                m, alts, dTs_vals, powers, out_dir, built)

    if mode == 'both':
        df_all = pd.concat([results['dry'], results['wet']], ignore_index=True)
        write_deck_csv(df_all, out_dir / 'cycle_deck_full_envelope.csv')

    print(f"\nSweep complete in {time.time() - st_total:.1f}s")
    for m, df in results.items():
        print(f"  {m.capitalize()}: {len(df)} / {attempted[m]} converged "
              f"→ {out_dir / f'cycle_deck_{m}.csv'}")
    if mode == 'both':
        print(f"  Combined: {len(df_all)} rows "
              f"→ {out_dir / 'cycle_deck_full_envelope.csv'}")
    return results


if __name__ == "__main__":
    # Kept so `python -m F404_pycycle.sweep_full_envelope [--mode ...]` still
    # works; it is the same as `f404 sweep`.
    import sys
    from F404_pycycle.cli import main
    sys.exit(main(['sweep', *sys.argv[1:]]))
