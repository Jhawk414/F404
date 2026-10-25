"""Validated YAML configuration for a full-envelope sweep."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from f404.sweep_utils import STATIC_MN


class RangeError(ValueError):
    """A range expression that cannot be turned into a sweep axis."""


_STEP_TOL = 1e-9


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
    n = int(round((hi - lo) / step)) + 1
    if n > np.iinfo(np.intp).max:
        raise RangeError("range has too many steps to represent as an axis")
    try:
        with np.errstate(over='ignore', invalid='ignore'):
            values = [float(v) for v in np.round(lo + step * np.arange(n), 9)]
    except (ValueError, OverflowError, MemoryError) as exc:
        raise RangeError(f"cannot expand range into an axis: {exc}") from exc
    if not all(math.isfinite(v) for v in values):
        raise RangeError("range expansion produced non-finite axis values")
    if len(set(values)) != len(values):
        raise RangeError("range step collapses to duplicate axis values at 9-digit precision")
    return values


def mach_axis(text):
    """Flight Mach axis; zero represents the sweep's static Mach."""
    values = expand_range(*parse_range(text))
    if values[0] < 0 or values[-1] >= 1:
        raise RangeError(
            f"Mach must be at least 0 and below 1 (the inlet model is subsonic "
            f"only), got {values[0]:g} to {values[-1]:g}"
        )
    if len({max(value, STATIC_MN) for value in values}) != len(values):
        raise RangeError("Mach values contain duplicates after static Mach normalization")
    return values


def alt_axis(text):
    """Altitude axis in ft, ascending."""
    return expand_range(*parse_range(text))


def dts_axis(text):
    """Temperature offsets in hot-ascending, then cold-descending order."""
    values = expand_range(*parse_range(text))
    return sorted((v for v in values if v >= 0)) + sorted(
        (v for v in values if v < 0), reverse=True
    )


def throttle_axis(text):
    """Throttle temperature axis in positive, descending order."""
    values = expand_range(*parse_range(text))
    if values[0] <= 0:
        raise RangeError(
            f"throttle temperatures must be positive degR, got a minimum of "
            f"{values[0]:g}"
        )
    return values[::-1]


def _numeric_axis(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number, range string, or list of numbers")
    if isinstance(value, (int, float)):
        try:
            values = [float(value)]
        except (OverflowError, ValueError):
            raise ValueError(f"{name} values must be finite representable numbers") from None
    elif isinstance(value, list):
        if not value or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in value):
            raise ValueError(f"{name} list must be non-empty and contain only numbers")
        try:
            values = [float(v) for v in value]
        except (OverflowError, ValueError):
            raise ValueError(f"{name} values must be finite representable numbers") from None
    else:
        raise ValueError(f"{name} must be a number, range string, or list of numbers")
    if not all(math.isfinite(v) for v in values):
        raise ValueError(f"{name} values must be finite")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} values must not contain duplicates")
    return values


def _axis(value, name):
    builders = {'mach': mach_axis, 'alt': alt_axis, 'dts': dts_axis,
                'throttle': throttle_axis}
    if isinstance(value, str):
        return builders[name](value)
    values = _numeric_axis(value, name)
    if name == 'mach':
        if any(v < 0 or v >= 1 for v in values):
            raise ValueError("Mach values must be at least 0 and below 1")
        if any(a >= b for a, b in zip(values, values[1:])):
            raise ValueError("mach values must be strictly ascending")
        if len({max(v, STATIC_MN) for v in values}) != len(values):
            raise ValueError("Mach values contain duplicates after static Mach normalization")
    elif name == 'alt' and any(a >= b for a, b in zip(values, values[1:])):
        raise ValueError("alt values must be strictly ascending")
    elif name == 'dts':
        values = sorted((v for v in values if v >= 0)) + sorted(
            (v for v in values if v < 0), reverse=True
        )
    elif name == 'throttle':
        if any(v <= 0 for v in values):
            raise ValueError("throttle temperatures must be positive degR")
        values.sort(reverse=True)
    return values


class SweepConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    mode: Literal['dry', 'wet', 'both']
    mach: list[float]
    alt: list[float]
    dts: list[float]
    throttle: dict[str, list[float]]
    out: Path

    @field_validator('mach', 'alt', 'dts', mode='before')
    @classmethod
    def normalize_axis(cls, value, info):
        return _axis(value, info.field_name)

    @field_validator('throttle', mode='before')
    @classmethod
    def normalize_throttle(cls, value):
        if not isinstance(value, dict) or set(value) != {'dry', 'wet'}:
            raise ValueError("throttle must contain exactly 'dry' and 'wet'")
        return {key: _axis(axis, 'throttle') for key, axis in value.items()}

    @field_validator('out', mode='before')
    @classmethod
    def strict_out_path(cls, value):
        if isinstance(value, Path):
            return value
        if isinstance(value, str) and value:
            return Path(value)
        raise ValueError("out must be a non-empty path string or Path")

    @field_validator('out')
    @classmethod
    def valid_out_path(cls, value):
        if value.exists() and not value.is_dir():
            raise ValueError(f"out path exists and is not a directory: {value}")
        if any(parent.exists() and not parent.is_dir() for parent in value.parents):
            raise ValueError(f"an ancestor of out is not a directory: {value}")
        return value


class RunConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

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
    """Read and validate a YAML run file; file/YAML errors are ValueErrors."""
    path = Path(path)
    try:
        with path.open(encoding='utf-8') as stream:
            raw = yaml.load(stream, Loader=_UniqueKeyLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read YAML config {path}: {exc}") from exc
    try:
        return RunConfig.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"invalid run config {path}: {exc}") from exc


EXAMPLE_YAML = '''sweep: # dict; required. Full-envelope run settings
  mode: # str; required. dry, wet, or both
  mach: # float/int/list/range; required. Flight Mach values
  alt: # float/int/list/range; required. Altitudes in ft
  dts: # float/int/list/range; required. Temperature offsets in degR
  throttle: # dict; required. Dry and wet power axes
    dry: # float/int/list/range; required. Dry Tt4 levels in degR
    wet: # float/int/list/range; required. Wet Tt7 levels in degR
  out: # str; required. Output directory path
'''
