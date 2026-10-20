"""
Full-envelope cycle deck builder for the F404 mixed-flow turbofan.

Sizes one engine (DESIGN at SLS dry mil) and sweeps it in two modes on the
one off-design point of the same om.Problem.

Dry sweep
---------
  - afterburner dry (Tt7 command 0); 'power' in sweep points = Tt4 target (degR)

Wet sweep
---------
  - FAR_ab balance drives T7 to target; 'power' in sweep points = Tt7 (degR)
  - Tt4 is fixed at mil power (mil_Tt4) for the entire wet sweep
  - A8 is set by the nozzle schedule (gas generator held where dry put it)
  - Thrust is an output, not a target

Usage (see f404.cli for the full flag set):
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

from f404.problems import build_problem, MAX_Tt7
from f404.sweep_utils import build_snake_sweep, SweepRunner, _scalar

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
# Wet: sweep T7 from the calibrated max AB down to min AB, 200 R steps
DEFAULT_WET_POWERS = [MAX_Tt7 - 200. * k for k in range(4)]   # Tt7, degR

BRIDGE_THRESHOLD = {'alt': 2000, 'dTs': 30, 'power': 100}
MAX_BRIDGE_STEPS = 5

def write_deck_csv(df, path):
    """Write a cycle-deck DataFrame to CSV at full float64 precision.

    The single writer for every deck (dry, wet, combined). Every float is
    written as its shortest round-trip repr, so a re-read deck is bit-identical
    to the solve. Deck-to-deck comparisons (spikes, PR proof) then measure the
    model rather than the rounding.
    """
    df.to_csv(path, index=False, float_format=None)


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
    pandas.DataFrame
        One row per attempted point; ``converged`` marks the ones that solved.
    """
    if mode not in ('dry', 'wet'):
        raise ValueError(f"mode must be 'dry' or 'wet', got {mode!r}")
    prob, mp = built if built is not None else build_problem()
    prob.set_solver_print(level=-1)
    # Wet holds Tt4 at the mil value this engine was built with, which may
    # not be problems.MIL_Tt4 if the caller passed custom targets.
    mil_Tt4 = _scalar(prob.get_val('DESIGN.balance.rhs:FAR_core', units='degR'))

    sweep_pts = build_snake_sweep(alts, dTs_vals, powers)
    print(f"\n{mode.capitalize()} sweep matrix: {len(sweep_pts)} points")

    runner = SweepRunner(prob, od_pt=mp.od_pt, mach=MACH,
                         afterburn=(mode == 'wet'), mil_Tt4=mil_Tt4)
    df = runner.run_sweep(
        sweep_pts,
        bridge_threshold=BRIDGE_THRESHOLD,
        max_bridge_steps=MAX_BRIDGE_STEPS,
    )
    write_deck_csv(df, Path(out_dir) / f'cycle_deck_{mode}.csv')
    return df


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
    prob, mp = built
    # Both modes run on the one OD point, so each starts from the SLS max-AB
    # solution build_problem() left, not from where the previous sweep ended.
    od_states = prob.model._get_subsystem(mp.od_pt)._outputs.asarray()
    anchor = od_states.copy()
    results = {}
    for m, powers in (('dry', dry_powers), ('wet', wet_powers)):
        if mode in (m, 'both'):
            od_states[:] = anchor
            results[m] = run_mode_sweep(
                m, alts, dTs_vals, powers, out_dir, built)

    if mode == 'both':
        df_all = pd.concat([results['dry'], results['wet']], ignore_index=True)
        write_deck_csv(df_all, out_dir / 'cycle_deck_full_envelope.csv')

    print(f"\nSweep complete in {time.time() - st_total:.1f}s")
    for m, df in results.items():
        print(f"  {m.capitalize()}: {df['converged'].sum()} / {len(df)} converged "
              f"→ {out_dir / f'cycle_deck_{m}.csv'}")
    if mode == 'both':
        print(f"  Combined: {len(df_all)} rows "
              f"→ {out_dir / 'cycle_deck_full_envelope.csv'}")
    return results


if __name__ == "__main__":
    # Kept so `python -m f404.sweep_full_envelope [--mode ...]` still
    # works; it is the same as `f404 sweep`.
    import sys
    from f404.cli import main
    sys.exit(main(['sweep', *sys.argv[1:]]))
