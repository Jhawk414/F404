import math
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from f404 import sweep_full_envelope as sfe
from f404.config import (
    EXAMPLE_YAML,
    RangeError,
    RunConfig,
    SweepConfig,
    alt_axis,
    dts_axis,
    expand_range,
    load_config,
    mach_axis,
    parse_range,
    throttle_axis,
)


def raw_sweep(**changes):
    raw = {
        'mode': 'both',
        'mach': [0.001, 0.2],
        'alt': [0, 2500],
        'dts': [0, 10, -10],
        'throttle': {'dry': [3100, 2900], 'wet': [3607.68, 3407.68]},
        'out': 'deck',
    }
    raw.update(changes)
    return raw


def test_config_normalizes_axis_inputs_and_json_dump(tmp_path):
    config = RunConfig.model_validate({'sweep': {
        **raw_sweep(), 'mach': '0,0.4,0.2', 'alt': 2500,
        'dts': '-20,20,10', 'throttle': {
            'dry': '2500,3100,200', 'wet': [3007.68, 3607.68, 3407.68]},
        'out': str(tmp_path / 'decks'),
    }})
    assert config.sweep.mach == [0.0, 0.2, 0.4]
    assert config.sweep.alt == [2500.0]
    assert config.sweep.dts == [0.0, 10.0, 20.0, -10.0, -20.0]
    assert config.sweep.throttle['dry'] == [3100.0, 2900.0, 2700.0, 2500.0]
    assert config.sweep.throttle['wet'] == [3607.68, 3407.68, 3007.68]
    assert config.model_dump(mode='json')['sweep']['out'] == str(tmp_path / 'decks')
    path_config = SweepConfig.model_validate(raw_sweep(out=Path('deck')))
    assert path_config.out == Path('deck')


def test_root_run_config_matches_default_grids_bit_for_bit():
    sweep = load_config('run.yml').sweep
    pairs = [
        (sweep.mach, sfe.DEFAULT_MACHS),
        (sweep.alt, sfe.DEFAULT_ALTS),
        (sweep.dts, sfe.DEFAULT_DTS),
        (sweep.throttle['dry'], sfe.DEFAULT_DRY_POWERS),
        (sweep.throttle['wet'], sfe.DEFAULT_WET_POWERS),
    ]
    for actual, expected in pairs:
        assert [value.hex() for value in actual] == [float(value).hex() for value in expected]


def test_explicit_values_are_not_rounded():
    value = 0.123456789123
    config = SweepConfig.model_validate(raw_sweep(mach=[value], alt=[value]))
    assert config.mach == [value]
    assert config.alt == [value]


@pytest.mark.parametrize(('axis', 'value'), [
    ('mach', True), ('mach', [0.2, 0.4, 0.4]), ('mach', [0.2, math.inf]),
    ('alt', True), ('alt', [0, 2500, 2500]), ('alt', [0, math.nan]),
    ('dts', True), ('dts', [0, 10, 10]), ('dts', [0, math.inf]),
    ('dry', True), ('dry', [3100, 3100]), ('dry', [3100, math.inf]),
    ('wet', True), ('wet', [3607.68, 3607.68]), ('wet', [3607.68, math.nan]),
])
def test_axes_reject_bools_nonfinite_values_and_duplicates(axis, value):
    raw = raw_sweep()
    if axis in {'dry', 'wet'}:
        raw['throttle'][axis] = value
    else:
        raw[axis] = value
    with pytest.raises(ValidationError):
        SweepConfig.model_validate(raw)


def test_axis_lists_reject_string_values():
    with pytest.raises(ValidationError):
        SweepConfig.model_validate(raw_sweep(alt=[0, '2500']))


def test_mach_rejects_effective_duplicate_static_values():
    with pytest.raises(ValidationError, match='static Mach'):
        SweepConfig.model_validate(raw_sweep(mach=[0, 0.001]))


def test_mach_requires_ascending_explicit_values():
    with pytest.raises(ValidationError, match='ascending'):
        SweepConfig.model_validate(raw_sweep(mach=[0.8, 0.4]))


def test_alt_requires_ascending_explicit_values():
    with pytest.raises(ValidationError, match='ascending'):
        SweepConfig.model_validate(raw_sweep(alt=[2500, 0]))


def test_throttle_requires_both_axes_and_positive_levels():
    with pytest.raises(ValidationError, match='exactly'):
        SweepConfig.model_validate(raw_sweep(throttle={'dry': [1]}))
    with pytest.raises(ValidationError, match='positive'):
        SweepConfig.model_validate(raw_sweep(throttle={'dry': [0], 'wet': [1]}))


@pytest.mark.parametrize('raw', [
    {'sweep': {**raw_sweep(), 'extra': True}},
    {'sweep': raw_sweep(), 'extra': True},
    {'sweep': {**raw_sweep(), 'mode': 1}},
    {'sweep': {**raw_sweep(), 'out': 123}},
    {'sweep': {**raw_sweep(), 'mode': 'DRY'}},
])
def test_models_reject_unknown_keys_and_coercions(raw):
    with pytest.raises(ValidationError):
        RunConfig.model_validate(raw)


def test_out_rejects_existing_file_and_file_ancestor(tmp_path):
    existing_file = tmp_path / 'file'
    existing_file.write_text('x')
    with pytest.raises(ValidationError, match='not a directory'):
        SweepConfig.model_validate(raw_sweep(out=str(existing_file)))
    with pytest.raises(ValidationError, match='ancestor'):
        SweepConfig.model_validate(raw_sweep(out=str(existing_file / 'decks')))


def test_load_config_rejects_duplicate_yaml_keys(tmp_path):
    config_path = tmp_path / 'run.yml'
    config_path.write_text('sweep:\n  mode: dry\n  mode: wet\n')
    with pytest.raises(ValueError, match='duplicate key'):
        load_config(config_path)


def test_load_config_wraps_read_and_yaml_errors(tmp_path):
    with pytest.raises(ValueError, match='cannot read YAML config'):
        load_config(tmp_path / 'missing.yml')
    path = tmp_path / 'bad.yml'
    path.write_text('sweep: [')
    with pytest.raises(ValueError, match='cannot read YAML config'):
        load_config(path)


def test_example_is_a_blank_invalid_template():
    parsed = yaml.safe_load(EXAMPLE_YAML)
    with pytest.raises(ValidationError):
        RunConfig.model_validate(parsed)


@pytest.mark.parametrize('missing', [
    'mode', 'mach', 'alt', 'dts', 'throttle', 'out',
])
def test_every_sweep_field_is_required(missing):
    raw = raw_sweep()
    del raw[missing]
    with pytest.raises(ValidationError):
        RunConfig.model_validate({'sweep': raw})


@pytest.mark.parametrize('missing', ['dry', 'wet'])
def test_both_throttle_axes_are_required(missing):
    throttle = raw_sweep()['throttle']
    del throttle[missing]
    with pytest.raises(ValidationError):
        SweepConfig.model_validate(raw_sweep(throttle=throttle))


def test_range_helpers_match_cli_behavior():
    assert parse_range('0,0.6,0.2') == (0.0, 0.6, 0.2)
    assert expand_range(0, 0.6, 0.2) == [0.0, 0.2, 0.4, 0.6]
    assert mach_axis('0,0.6,0.2') == [0.0, 0.2, 0.4, 0.6]
    assert alt_axis('0,5000,2500') == [0.0, 2500.0, 5000.0]
    assert dts_axis('-30,30,10') == [0.0, 10.0, 20.0, 30.0, -10.0, -20.0, -30.0]
    assert throttle_axis('2500,3100,200') == [3100.0, 2900.0, 2700.0, 2500.0]
    with pytest.raises(RangeError):
        parse_range('0,5,2')


def test_range_expansion_rejects_unrepresentable_step_counts():
    with pytest.raises(RangeError, match='too many steps'):
        expand_range(*parse_range('0,1,1e-30'))


def test_range_expansion_rejects_nonfinite_rounded_values():
    with pytest.raises(RangeError, match='non-finite'):
        alt_axis('1e308')
    with pytest.raises(ValidationError, match='non-finite'):
        SweepConfig.model_validate(raw_sweep(alt='1e308'))


def test_huge_yaml_integer_is_a_validation_error_not_an_overflow(tmp_path):
    path = tmp_path / 'huge.yml'
    path.write_text(yaml.safe_dump({'sweep': raw_sweep(alt=10 ** 400)}))
    with pytest.raises(ValueError, match='finite representable'):
        load_config(path)
