"""Validated user input: design-point inputs and the YAML run configuration."""
import math
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, field_validator

from f404.sweep_utils import STATIC_MN

# ── Design-point targets ──────────────────────────────────────────────────────
MIL_Tt4    = 3100.   # degR — core burner exit at mil power (throttle wall)
DRY_DSN_FN = 11000.  # lbf  — SLS mil power (no afterburner); sizes the engine
MAX_Tt7    = 3607.68 # degR — afterburner exit at max AB. With the augmentor
                     # loss (mp_cycle.py; 6.6% at this point) the default
                     # engine makes 17,700 lbf here (problems.MAX_AB_FN). The
                     # cycle's augmentation ratio exceeds the targets'
                     # (ADR-0001), so this sits below the F404's ~3800 R.
                     # Combustion efficiency (#35) will move it again. See
                     # docs/adr/0002-single-od-topology.md.


class StrictModel(BaseModel):
    """Base for every user-input model: no unknown keys, no type coercion,
    no NaN or inf, and immutable once validated."""
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True,
                              allow_inf_nan=False)


PressureRatio = Annotated[float, Field(gt=1)]
Efficiency = Annotated[float, Field(gt=0, le=1)]
LossFraction = Annotated[float, Field(ge=0, lt=1)]


class DesignInputs(StrictModel):
    """Everything that sizes the engine at sea-level-static dry mil.

    The defaults are the calibrated F404 engine. Each field name is its model
    path with ``.`` and ``:`` replaced by ``_``; ``problems.DESIGN_INPUT_PATHS``
    maps it back (docs/adr/0005-public-python-api.md).
    """
    fn_target: PositiveFloat = DRY_DSN_FN   # lbf, SLS dry mil thrust; sets W
    mil_Tt4: PositiveFloat = MIL_Tt4        # degR, core burner exit at mil
    max_Tt7: PositiveFloat = MAX_Tt7        # degR, afterburner exit at max AB.
    # Its default is calibrated to 17,700 lbf for the default sizing only.

    fan_PR: PressureRatio = 4.1
    fan_eff: Efficiency = 0.8948
    hpc_PR: PressureRatio = 6.5
    hpc_eff: Efficiency = 0.8707
    hpt_eff: Efficiency = 0.8888
    lpt_eff: Efficiency = 0.8996
    LP_Nmech: PositiveFloat = 10000.        # rpm, design spool speeds; they
    HP_Nmech: PositiveFloat = 14000.        # set the map speed scalars

    ram_recovery: Efficiency = 0.9990       # inlet Pt recovery
    inlet_duct_dPqP: LossFraction = 0.0107
    splitter_core_duct_dPqP: LossFraction = 0.0048
    hpt_duct_dPqP: LossFraction = 0.0051
    lpt_duct_dPqP: LossFraction = 0.0107
    bypass_duct_dPqP: LossFraction = 0.015
    mixer_duct_dPqP: LossFraction = 0.0107

    hpc_cool1_frac_W: LossFraction = 0.050708  # HPC bleed to the LPT, of HPC inflow
    bld3_cool3_frac_W: LossFraction = 0.11     # HPC exit bleed to the HPT


class RangeError(ValueError):
    """A range expression that cannot be turned into a sweep axis."""


_STEP_TOL = 1e-9
MAX_AXIS_POINTS = 10_000
_ORDER_HINT = " For a range, quote min,max,step."


def parse_range(text):
    """Parse ``min,max,step`` or a single held value into three floats."""
    raw = text
    text = text.strip()
    if text.startswith('[') and text.endswith(']'):
        text = text[1:-1]

    parts = [part.strip() for part in text.split(',')]
    if len(parts) == 1:
        parts = parts * 2 + ['1']
    if len(parts) != 3:
        raise RangeError(
            f"expected exactly 3 values as min,max,step, got {len(parts)} in "
            f"{raw!r}. Example: 0,10000,1000. For a constant axis pass a "
            f"single value, e.g. 0"
        )
    try:
        lo, hi, step = (float(part) for part in parts)
    except ValueError:
        raise RangeError(
            f"min,max,step must all be numbers, got {raw!r}. Example: 0,10000,1000"
        ) from None
    if not all(math.isfinite(v) for v in (lo, hi, step)):
        raise RangeError(f"min,max,step must be finite, got {raw!r}")
    if step <= 0:
        hint = (f"For a constant axis pass a single value, e.g. {lo:g}."
                if lo == hi else
                "The order is min,max,step; sweeps are built from min up to max.")
        raise RangeError(f"step must be positive, got {step:g} in {raw!r}. {hint}")
    if lo > hi:
        raise RangeError(
            f"min ({lo:g}) must not exceed max ({hi:g}) in {raw!r}. The order "
            f"is min,max,step."
        )
    n_steps = (hi - lo) / step
    if not math.isfinite(n_steps):
        raise RangeError(f"range has too many steps to represent in {raw!r}")
    if abs(n_steps - round(n_steps)) > _STEP_TOL * max(1.0, n_steps):
        raise RangeError(
            f"step {step:g} does not divide max - min ({hi - lo:g}) evenly in "
            f"{raw!r}; the sweep would stop at {lo + math.floor(n_steps) * step:g}, "
            f"short of max {hi:g}. Adjust max or step."
        )
    return lo, hi, step


def expand_range(lo, hi, step):
    """Return inclusive ascending range values, rounded as the CLI has done."""
    n_steps = (hi - lo) / step
    if not math.isfinite(n_steps):
        raise RangeError("range has too many steps to represent as an axis")
    n = int(round(n_steps)) + 1
    if n > MAX_AXIS_POINTS:
        raise RangeError(
            f"range has too many steps: axis has {n} points; "
            f"maximum is {MAX_AXIS_POINTS}. "
            "Use a larger step or a narrower range."
        )
    values = [round(lo + step * index, 9) for index in range(n)]
    if not all(math.isfinite(v) for v in values):
        raise RangeError("range expansion produced non-finite axis values")
    if len(set(values)) != len(values):
        raise RangeError("range step collapses to duplicate axis values at 9-digit precision")
    return values


def mach_axis(text):
    """Flight Mach axis; zero represents the sweep's static Mach."""
    return axis(text, 'mach')


def alt_axis(text):
    """Altitude axis in ft, ascending."""
    return axis(text, 'alt')


def dts_axis(text):
    """Temperature offsets in hot-ascending, then cold-descending order."""
    return axis(text, 'dts')


def throttle_axis(text):
    """Throttle temperature axis in positive, descending order."""
    return axis(text, 'throttle')


def _numeric_axis(value, name):
    if isinstance(value, bool):
        raise RangeError(f"{name} must be a number, range string, or list of numbers")
    if isinstance(value, (int, float)):
        try:
            values = [float(value)]
        except (OverflowError, ValueError):
            raise RangeError(f"{name} values must be finite representable numbers") from None
    elif isinstance(value, list):
        if len(value) > MAX_AXIS_POINTS:
            raise RangeError(
                f"{name} axis has {len(value)} points; maximum is "
                f"{MAX_AXIS_POINTS}"
            )
        if not value or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in value):
            raise RangeError(f"{name} list must be non-empty and contain only numbers")
        try:
            values = [float(v) for v in value]
        except (OverflowError, ValueError):
            raise RangeError(f"{name} values must be finite representable numbers") from None
    else:
        raise RangeError(f"{name} must be a number, range string, or list of numbers")
    if not all(math.isfinite(v) for v in values):
        raise RangeError(f"{name} values must be finite")
    if len(set(values)) != len(values):
        raise RangeError(f"{name} values must not contain duplicates")
    return values


def axis(value, name):
    """Parse and validate one sweep axis, preserving explicit list order."""
    if isinstance(value, str):
        values = expand_range(*parse_range(value))
        if name == 'dts':
            values = sorted((v for v in values if v >= 0)) + sorted(
                (v for v in values if v < 0), reverse=True
            )
        elif name == 'throttle':
            values.reverse()
    else:
        values = _numeric_axis(value, name)
    if name == 'mach':
        if any(v < 0 or v >= 1 for v in values):
            raise RangeError("Mach values must be at least 0 and below 1")
        if any(a >= b for a, b in zip(values, values[1:])):
            raise RangeError("mach values must be strictly ascending." + _ORDER_HINT)
        if len({max(v, STATIC_MN) for v in values}) != len(values):
            raise RangeError("Mach values contain duplicates after static Mach normalization")
    elif name == 'alt' and any(a >= b for a, b in zip(values, values[1:])):
        raise RangeError("alt values must be strictly ascending." + _ORDER_HINT)
    elif name == 'dts':
        expected = sorted((v for v in values if v >= 0)) + sorted(
            (v for v in values if v < 0), reverse=True
        )
        if values != expected:
            raise RangeError(
                "dts values must be in traversal order: non-negative ascending, "
                "then negative descending." + _ORDER_HINT
            )
    elif name == 'throttle':
        if any(v <= 0 for v in values):
            raise RangeError("throttle temperatures must be positive degR")
        if any(a <= b for a, b in zip(values, values[1:])):
            raise RangeError(
                "throttle values must be in descending traversal order." + _ORDER_HINT
            )
    return values


class ThrottleConfig(StrictModel):

    dry: list[float]
    wet: list[float]

    @field_validator('dry', 'wet', mode='before')
    @classmethod
    def normalize_axis(cls, value):
        return axis(value, 'throttle')


class SweepConfig(StrictModel):

    mode: Literal['dry', 'wet', 'both']
    mach: list[float]
    alt: list[float]
    dts: list[float]
    throttle: ThrottleConfig
    out: Path

    @field_validator('mach', 'alt', 'dts', mode='before')
    @classmethod
    def normalize_axis(cls, value, info):
        return axis(value, info.field_name)

    @field_validator('out', mode='before')
    @classmethod
    def strict_out_path(cls, value):
        if isinstance(value, (str, Path)) and str(value):
            return Path(value).expanduser()
        raise ValueError("out must be a non-empty path string or Path")


class RunConfig(StrictModel):
    design: DesignInputs = DesignInputs()
    sweep: SweepConfig


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError:
            raise yaml.constructor.ConstructorError(
                'while constructing a mapping', node.start_mark,
                'found an unhashable key', key_node.start_mark,
            ) from None
        if duplicate:
            raise yaml.constructor.ConstructorError(
                'while constructing a mapping', node.start_mark,
                f"found duplicate key {key!r}", key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def load_config(path) -> RunConfig:
    """Read a YAML run file; file/YAML errors are ValueErrors."""
    path = Path(path)
    try:
        with path.open(encoding='utf-8') as stream:
            raw = yaml.load(stream, Loader=_UniqueKeyLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read YAML config {path}: {exc}") from exc
    return RunConfig.model_validate(raw)


EXAMPLE_YAML = '''\
# f404 sweep run: f404 <file>.yml. Every sweep key is required.
# design is optional; any key left out keeps the calibrated default engine.
design:
  fn_target: 11000          # lbf, SLS dry mil thrust that sizes the engine
  hpc_PR: 6.5               # also: fan_PR, *_eff, *_dPqP, *_frac_W, ... (CLI guide)
# Each axis (mach, alt, dts, throttle.dry, throttle.wet) takes any of:
#   number          0             one held point
#   quoted range    '0,0.4,0.2'   min,max,step, inclusive of max
#   list            [0, 2500]     these points, already in sweep order
# A list is never a range: [0, 5000, 2500] is three points.
sweep:
  mode: both                # dry, wet, or both
  mach: '0,0.4,0.2'         # flight Mach below 1; 0 flies at 0.001; lists ascend
  alt: [0, 2500, 5000]      # ft; lists ascend
  dts: 0                    # ISA offset, degR; lists go 0, 10, 20, then -10, -20
  throttle:                 # dry and wet both required, even for a single mode
    dry: '2900,3100,200'    # Tt4, degR; lists go high to low
    wet: [3607.68, 3407.68] # Tt7, degR; lists go high to low
  out: deck/example         # output directory, relative to the working directory
'''
