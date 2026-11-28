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

from f404.config import DesignInputs, PlaSchedule, axis
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


def _pla_bridge_threshold(schedules, inputs):
    """Bridge threshold for PLA sweeps, keeping Tt4 and Tt7 jumps within
    ``BRIDGE_THRESHOLD['power']`` (100 R) at the schedule's steepest slope."""
    dry_slope = (inputs.mil_Tt4 - schedules.idle_Tt4) / (schedules.mil_pla - schedules.idle_pla)
    wet_slope = (inputs.max_Tt7 - schedules.min_ab_Tt7) / (schedules.max_ab_pla - schedules.min_ab_pla)
    return {**BRIDGE_THRESHOLD, 'power': BRIDGE_THRESHOLD['power'] / max(dry_slope, wet_slope)}

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


def sweep(engine, *, mode=None, mach=DEFAULT_MACHS, alt=DEFAULT_ALTS, dts=DEFAULT_DTS,
          throttle=None, pla=None, out_dir=None, verbose=False):
    """Sweep a sized engine over flight conditions and throttle or PLA.

    Parameters
    ----------
    engine : Engine
        From ``design()``. Restored to its SLS max-AB anchor first, so earlier
        calls don't steer the result. Afterwards ``engine.prob`` is solved at
        the last point only if that point converged.
    mode : {'dry', 'wet'}, optional
        Required when sweeping temperature ``throttle``; must be None when
        sweeping ``pla`` (PLA selects dry/wet per point via ``engine.schedules``).
    mach, alt, dts, throttle, pla : list of float, float, or range string
        The axes, validated as for the CLI and YAML (``config.axis``):
        Mach ascending, alt ascending, dts hot then cold, throttle/pla descending.
        ``throttle`` and ``pla`` are mutually exclusive. ``throttle`` is Tt4 dry
        and Tt7 wet, degR; by default four levels 200 R apart down from the
        engine's ``mil_Tt4`` or ``max_Tt7``. ``pla`` is GE engine-level PLA in
        deg (ADR-0006), spanning dry and wet in one descending pass.
    out_dir : path-like, optional
        Write ``cycle_deck_<mode>.csv`` (or ``cycle_deck_pla.csv`` for PLA)
        here; nothing is written if None.
    verbose : bool
        Print a line per point.

    Returns
    -------
    pandas.DataFrame
        One row per point, failed ones included: ``INPUT_COLUMNS`` (or
        ``PLA_INPUT_COLUMNS`` for PLA), then ``DECK_COLUMNS`` (blank where the
        point failed), then ``failure``.
    """
    if pla is not None:
        if throttle is not None:
            raise ValueError("throttle and pla are mutually exclusive")
        if mode is not None:
            raise ValueError("mode cannot be combined with pla; pla selects dry/wet automatically")
        pla_vals = axis(pla, 'pla')
        for angle in pla_vals:
            engine.schedules.resolve(angle, engine.inputs)
        home = engine.home('pla')
        points = build_snake_sweep(
            axis(alt, 'alt'), axis(dts, 'dts'), pla_vals, axis(mach, 'mach'))
        label, deck_name = 'PLA', 'cycle_deck_pla.csv'
        threshold = _pla_bridge_threshold(engine.schedules, engine.inputs)
        runner_kw = {
            'command': lambda p: engine.schedules.resolve(p, engine.inputs),
            'power_label': 'PLA', 'power_unit': 'deg', 'pla_column': True,
        }
    else:
        if mode not in ('dry', 'wet'):
            raise ValueError(f"mode must be 'dry' or 'wet', got {mode!r}")
        # The anchor's condition at this mode's top power. The default grids
        # start here, so their first point needs no bridge.
        home = engine.home(mode)
        points = build_snake_sweep(
            axis(alt, 'alt'), axis(dts, 'dts'),
            axis(default_throttle(home['power']) if throttle is None else throttle,
                 'throttle'),
            axis(mach, 'mach'))
        label, deck_name = mode.capitalize(), f'cycle_deck_{mode}.csv'
        threshold = BRIDGE_THRESHOLD
        runner_kw = {'afterburn': (mode == 'wet'), 'mil_Tt4': engine.inputs.mil_Tt4}

    if verbose:
        print(f"\n{label} sweep matrix: {len(points)} points")

    engine.restore_anchor()
    prob = engine.prob
    prob.set_solver_print(level=-1)
    runner = SweepRunner(prob, od_pt=prob.model.od_pt, verbose=verbose, **runner_kw)
    df = runner.run_sweep(points, bridge_threshold=threshold,
                          max_bridge_steps=MAX_BRIDGE_STEPS, start=home)
    if out_dir is not None:
        write_deck_csv(df, Path(out_dir) / deck_name)
    return df


def run_point(engine, *, mode=None, alt, mach, dts, throttle=None, pla=None, verbose=False):
    """Solve one OD condition of a sized engine and return its deck row.

    The point is reached from the engine's SLS max-AB anchor through bridge
    points, as a sweep reaches its first point, so the result doesn't depend
    on earlier calls. Pass either ``throttle`` (with ``mode='dry'`` or
    ``'wet'``) or ``pla`` (mode inferred from ``engine.schedules``); ``mach`` 0
    is flown at 0.001.

    Returns
    -------
    dict
        ``INPUT_COLUMNS`` (or ``PLA_INPUT_COLUMNS``) + ``DECK_COLUMNS`` +
        ``failure``. A point that fails is returned with ``converged`` False
        and NaN outputs, not raised. When it converged, ``engine.prob`` is left
        solved at it, so it can be read or differentiated; when it failed, it
        is not.
    """
    if (throttle is None) == (pla is None):
        raise ValueError("pass exactly one of throttle or pla")
    df = sweep(engine, mode=mode, mach=[mach], alt=[alt], dts=[dts],
               throttle=None if throttle is None else [throttle],
               pla=None if pla is None else [pla], verbose=verbose)
    return df.to_dict('records')[0]


def run_sweeps(mode=None, alts=DEFAULT_ALTS, dTs_vals=DEFAULT_DTS,
               dry_powers=None, wet_powers=None,
               machs=DEFAULT_MACHS, out_dir='.', inputs=DesignInputs(),
               pla=None, schedules=PlaSchedule()):
    """Size the engine from ``inputs``, run dry/wet or PLA sweeps, and write
    the decks: the driver behind ``f404 sweep`` and YAML runs.

    With ``pla`` set (mutually exclusive with ``mode``), runs one unified PLA
    sweep and writes ``cycle_deck_pla.csv``. Otherwise ``mode`` is ``'dry'``,
    ``'wet'`` or ``'both'``; ``'both'`` also writes ``cycle_deck_full_envelope.csv``.
    Returns ``{name: DataFrame}`` for the sweeps that ran.
    """
    if pla is not None:
        if mode is not None:
            raise ValueError("mode cannot be combined with pla; pla selects dry/wet automatically")
        if dry_powers is not None or wet_powers is not None:
            raise ValueError("dry_powers/wet_powers cannot be combined with pla")
    elif mode not in ('dry', 'wet', 'both'):
        raise ValueError(f"mode must be 'dry', 'wet' or 'both', got {mode!r}")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    st_total = time.time()
    engine = design(inputs, schedules=schedules, verbose=True)
    if pla is not None:
        df = sweep(engine, mach=machs, alt=alts, dts=dTs_vals,
                   pla=pla, out_dir=out_dir, verbose=True)
        print(f"\nSweep complete in {time.time() - st_total:.1f}s")
        print(f"  PLA: {df['converged'].sum()} / {len(df)} converged "
              f"→ {out_dir / 'cycle_deck_pla.csv'}")
        return {'pla': df}

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
