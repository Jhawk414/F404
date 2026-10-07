"""Command-line interface for the F404 cycle model.

Entry points::

    f404 sweep  [--mode {dry,wet,both}] [--alt R] [--dts R] [--throttle R] [--out DIR]
    f404 design [--mode {dry,wet,both}] [--fn-target LBF] [--mil-tt4 DEGR] [--dsn-tt7 DEGR]

``python -m F404_pycycle`` is equivalent to ``f404``. Every range flag takes one
``min,max,step`` triple (inclusive of ``max``), bare or bracketed.

Input is validated eagerly: a malformed flag stops the run before any model is
built. A partial or misread range that silently swept the wrong envelope would
only be discovered later, in a deck that doesn't match what was asked for.
"""
import math

import numpy as np


class RangeError(ValueError):
    """A ``min,max,step`` range flag that can't be turned into a sweep axis."""


# max-min must be a whole number of steps to within this fraction of a step.
_STEP_TOL = 1e-9


def parse_range(text):
    """Parse ``'min,max,step'`` (optionally in ``[...]``) into three floats.

    The order is fixed at min, max, step: a step in any other position can't be
    told apart from a bound without a marker, so it is not accepted.

    Raises
    ------
    RangeError
        If there aren't exactly three finite numbers, ``step`` isn't positive,
        ``min`` exceeds ``max``, or ``step`` doesn't divide ``max - min`` evenly
        (which would otherwise stop the sweep short of the requested ``max``).
    """
    raw = text
    text = text.strip()
    if text.startswith('[') and text.endswith(']'):
        text = text[1:-1]

    parts = [p.strip() for p in text.split(',')]
    if len(parts) != 3:
        raise RangeError(
            f"expected exactly 3 values as min,max,step, got {len(parts)} in "
            f"{raw!r}. Example: 0,10000,1000"
        )

    try:
        lo, hi, step = (float(p) for p in parts)
    except ValueError:
        raise RangeError(
            f"min,max,step must all be numbers, got {raw!r}. Example: 0,10000,1000"
        ) from None

    if not all(math.isfinite(v) for v in (lo, hi, step)):
        raise RangeError(f"min,max,step must be finite, got {raw!r}")
    if step <= 0:
        raise RangeError(
            f"step must be positive, got {step:g} in {raw!r}. The order is "
            f"min,max,step; sweeps are built from min up to max."
        )
    if lo > hi:
        raise RangeError(
            f"min ({lo:g}) must not exceed max ({hi:g}) in {raw!r}. The order "
            f"is min,max,step."
        )

    n_steps = (hi - lo) / step
    if abs(n_steps - round(n_steps)) > _STEP_TOL * max(1.0, n_steps):
        raise RangeError(
            f"step {step:g} does not divide max - min ({hi - lo:g}) evenly in "
            f"{raw!r}; the sweep would stop at {lo + math.floor(n_steps) * step:g}, "
            f"short of max {hi:g}. Adjust max or step."
        )
    return lo, hi, step


def expand_range(lo, hi, step):
    """Return the ascending values ``lo, lo+step, ... hi`` as a list of floats."""
    n = int(round((hi - lo) / step)) + 1
    return [float(v) for v in np.round(lo + step * np.arange(n), 9)]


def alt_axis(text):
    """Altitude axis in ft, ascending."""
    return expand_range(*parse_range(text))


def dts_axis(text):
    """Temperature-offset axis in degR, in the sweep's traversal order.

    Anchored at 0 and walked hot-first (0, +10, ... +max), then jumping to the
    cold side (-10, ... -min) — the same order as the default grid, which the
    bridge-point logic is built around. Plain ascending order would instead
    start at the most extreme cold corner, the hardest point to converge from
    the design-condition warm start.
    """
    values = expand_range(*parse_range(text))
    hot = sorted(v for v in values if v >= 0)
    cold = sorted((v for v in values if v < 0), reverse=True)
    return hot + cold


def throttle_axis(text):
    """Throttle axis (Tt4 dry, Tt7 wet) in degR, highest power first.

    Matches the default grids, which start at the design-point throttle (mil
    Tt4 / max-AB Tt7) and walk down to part power.
    """
    values = expand_range(*parse_range(text))
    if values[0] <= 0:
        raise RangeError(
            f"throttle temperatures must be positive degR, got a minimum of "
            f"{values[0]:g}"
        )
    return values[::-1]
