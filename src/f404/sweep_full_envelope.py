"""
Off-design runs of a sized engine: one point, one mode, or the full deck.

The engine is sized once (DESIGN at SLS dry mil, ``problems.design()``) and
every OD run below starts from its SLS max-AB anchor on the one OD point.

Dry mode
--------
  - afterburner dry (Tt7 command 0); ``throttle`` is the Tt4 target (degR)

Wet mode
--------
  - FAR_ab balance drives T7 to target; ``throttle`` is Tt7 (degR)
  - Tt4 is held at the engine's mil_Tt4
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

import pandas as pd
from openmdao.utils.om_warnings import SolverWarning

from f404.config import DesignInputs, axis
from f404.problems import MAX_Tt7, MIL_Tt4, design
from f404.sweep_utils import build_snake_sweep, STATIC_MN, SweepRunner

# ── Default sweep grid (shared by both modes) ────────────────────────────────
# Static to high subsonic; the inlet's fixed ram recovery is subsonic only.
DEFAULT_MACHS = [STATIC_MN, 0.2, 0.4, 0.6, 0.8, 0.95]
# Crawl-walk-run scope: low altitudes.
DEFAULT_ALTS = [0., 2500., 5000.]              # ft — 3 pts
# dTs ordering: anchor at 0 (matches OD verification), walk hot first
# (+10..+50), then jump to cold side (-10..-50). Bridge logic handles
# the +50 → -10 jump within each alt level.
DEFAULT_DTS = [0., 10., 20., 30., 40., 50.,
               -10., -20., -30., -40., -50.]   # 11 pts, hot-first



def default_throttle(top):
    """Four levels down from ``top`` (mil Tt4 or max-AB Tt7), 200 R apart."""
    return [top - 200. * k for k in range(4)]


# The default engine's grids: Tt4 3100 -> 2500 R, Tt7 3607.68 -> 3007.68 R.
DEFAULT_DRY_POWERS = default_throttle(MIL_Tt4)   # Tt4, degR
DEFAULT_WET_POWERS = default_throttle(MAX_Tt7)   # Tt7, degR

# MN 0.25 bridges only the jump back to static at each new power level.
BRIDGE_THRESHOLD = {'alt': 2000, 'dTs': 30, 'power': 100, 'MN': 0.25}
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
    warnings.filterwarnings('ignore', category=SolverWarning)

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def sweep(engine, *, mode, mach=DEFAULT_MACHS, alt=DEFAULT_ALTS, dts=DEFAULT_DTS,
          throttle=None, out_dir=None, verbose=False):
    """Sweep one mode of a sized engine and return its deck.

    Parameters
    ----------
    engine : Engine
        From ``design()``. Restored to its SLS max-AB anchor first, so earlier
        calls don't steer the result (up to solver-internal state, #59). Afterwards ``engine.prob`` is
        solved at the last point only if that point converged.
    mode : {'dry', 'wet'}
    mach, alt, dts, throttle : list of float, float, or range string
        The axes, validated as for the CLI and YAML (``config.axis``):
        Mach ascending, alt ascending, dts hot then cold, throttle descending.
        ``throttle`` is Tt4 dry and Tt7 wet, degR; by default four levels
        200 R apart down from the engine's ``mil_Tt4`` or ``max_Tt7``.
    out_dir : path-like, optional
        Write ``cycle_deck_<mode>.csv`` here; nothing is written if None.
    verbose : bool
        Print a line per point.

    Returns
    -------
    pandas.DataFrame
        One row per point, failed ones included: ``INPUT_COLUMNS``, then
        ``DECK_COLUMNS`` (blank where the point failed), then ``failure``.
    """
    return _sweep(engine, mode, mach, alt, dts, throttle, out_dir, verbose,
                  MAX_BRIDGE_STEPS)


def _sweep(engine, mode, mach, alt, dts, throttle, out_dir, verbose, bridge_steps):
    if mode not in ('dry', 'wet'):
        raise ValueError(f"mode must be 'dry' or 'wet', got {mode!r}")
    inputs = engine.inputs
    top = inputs.mil_Tt4 if mode == 'dry' else inputs.max_Tt7
    points = build_snake_sweep(
        axis(alt, 'alt'), axis(dts, 'dts'),
        axis(default_throttle(top) if throttle is None else throttle, 'throttle'),
        axis(mach, 'mach'))
    if verbose:
        print(f"\n{mode.capitalize()} sweep matrix: {len(points)} points")

    engine.restore_anchor()
    prob = engine.prob
    prob.set_solver_print(level=-1)
    runner = SweepRunner(prob, od_pt=prob.model.od_pt, afterburn=(mode == 'wet'),
                         mil_Tt4=inputs.mil_Tt4, verbose=verbose)
    # The anchor's condition, at this mode's top power. The default grids
    # start here, so their first point needs no bridge.
    home = {'MN': STATIC_MN, 'alt': 0., 'dTs': 0., 'power': top}
    df = runner.run_sweep(points, bridge_threshold=BRIDGE_THRESHOLD,
                          max_bridge_steps=bridge_steps, start=home)
    if out_dir is not None:
        write_deck_csv(df, Path(out_dir) / f'cycle_deck_{mode}.csv')
    return df


def run_point(engine, *, mode, alt, mach, dts, throttle, verbose=False):
    """Solve one OD condition of a sized engine and return its deck row.

    The point is reached from the engine's SLS max-AB anchor through bridge
    points, as a sweep reaches its first point, so the result doesn't depend
    on earlier calls. Arguments are as for ``sweep()``, one value each;
    ``mach`` 0 is flown at 0.001.

    Returns
    -------
    dict
        ``INPUT_COLUMNS`` + ``DECK_COLUMNS`` + ``failure``. A point that
        fails is returned with ``converged`` False and NaN outputs, not
        raised. When it converged, ``engine.prob`` is left solved at it,
        so it can be read or differentiated; when it failed, it is not.
    """
    df = _sweep(engine, mode, [mach], [alt], [dts], [throttle], None, verbose,
                MAX_BRIDGE_STEPS)
    return df.to_dict('records')[0]


def run_sweeps(mode, alts=DEFAULT_ALTS, dTs_vals=DEFAULT_DTS,
               dry_powers=None, wet_powers=None,
               machs=DEFAULT_MACHS, out_dir='.', inputs=DesignInputs()):
    """Size the engine from ``inputs``, run the dry sweep, the wet sweep, or
    both, and write the decks: the driver behind ``f404 sweep`` and YAML runs.

    ``mode`` is 'dry', 'wet' or 'both'; 'both' also writes the combined
    ``cycle_deck_full_envelope.csv``. Throttles left as None run down from
    the sized engine's ``mil_Tt4`` and ``max_Tt7``, as in ``sweep()``. Returns ``{mode: DataFrame}`` for the
    modes that ran.
    """
    if mode not in ('dry', 'wet', 'both'):
        raise ValueError(f"mode must be 'dry', 'wet' or 'both', got {mode!r}")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    st_total = time.time()
    engine = design(inputs, verbose=True)
    results = {}
    for m, powers in (('dry', dry_powers), ('wet', wet_powers)):
        if mode in (m, 'both'):
            results[m] = sweep(engine, mode=m, mach=machs, alt=alts, dts=dTs_vals,
                               throttle=powers, out_dir=out_dir, verbose=True)

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
