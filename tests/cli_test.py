"""Tests for the command-line interface.

The range flags are the contract: a malformed one must stop the run before a
model is built, because the alternative is a deck that quietly covers a
different envelope than the one requested.
"""
import pytest

from F404_pycycle.cli import (
    RangeError,
    alt_axis,
    dts_axis,
    expand_range,
    parse_range,
    throttle_axis,
)
from F404_pycycle.sweep_full_envelope import (
    DEFAULT_ALTS,
    DEFAULT_DRY_POWERS,
    DEFAULT_DTS,
    DEFAULT_WET_POWERS,
)


# ── parse_range ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize('text', [
    '0,10000,1000',
    '[0,10000,1000]',
    ' 0 , 10000 , 1000 ',
    '[ 0, 10000, 1000 ]',
    '0.0,1e4,1e3',
])
def test_bare_bracketed_and_spaced_forms_parse_identically(text):
    assert parse_range(text) == (0.0, 10000.0, 1000.0)


@pytest.mark.parametrize('text, fragment', [
    ('0,10000', 'exactly 3 values'),
    ('0', 'exactly 3 values'),
    ('', 'exactly 3 values'),
    ('0,10000,1000,5', 'exactly 3 values'),
    ('[0,10000]', 'exactly 3 values'),
    ('0,,1000', 'must all be numbers'),
    ('0,ten,1000', 'must all be numbers'),
    ('nan,10,1', 'finite'),
    ('0,inf,1', 'finite'),
    ('0,10,0', 'step must be positive'),
    ('0,10,-1', 'step must be positive'),
    ('10,0,1', 'must not exceed max'),
    ('0,1000,300', 'does not divide'),
])
def test_malformed_ranges_raise_with_a_message_naming_the_problem(text, fragment):
    with pytest.raises(RangeError, match=fragment):
        parse_range(text)


def test_error_message_quotes_the_offending_input():
    with pytest.raises(RangeError, match=r"'0,10000'"):
        parse_range('0,10000')


def test_a_step_in_the_wrong_position_is_rejected_not_reinterpreted():
    # The issue's open question: 0,1000,10000 could mean min,step,max. The
    # order is fixed, so this reads as min=0 max=1000 step=10000 and the step
    # that overshoots max is an error rather than a guess.
    with pytest.raises(RangeError):
        parse_range('0,1000,10000')


def test_range_error_is_a_value_error():
    assert issubclass(RangeError, ValueError)


# ── expand_range ──────────────────────────────────────────────────────────────

def test_expand_range_includes_both_endpoints():
    assert expand_range(0., 5000., 2500.) == [0., 2500., 5000.]


def test_a_single_point_range_is_allowed():
    assert expand_range(1000., 1000., 500.) == [1000.]


def test_expand_range_has_no_floating_point_drift():
    assert expand_range(0.2, 0.5, 0.1) == [0.2, 0.3, 0.4, 0.5]


def test_fractional_steps_that_divide_evenly_are_accepted():
    assert parse_range('0.2,0.9,0.1') == (0.2, 0.9, 0.1)


# ── axes reproduce the defaults ───────────────────────────────────────────────

def test_alt_axis_reproduces_the_default_altitudes():
    assert alt_axis('0,5000,2500') == [float(a) for a in DEFAULT_ALTS]


def test_dts_axis_reproduces_the_default_order():
    # Hot-first with the cold side after, anchored at 0 — not ascending.
    assert dts_axis('-50,50,10') == DEFAULT_DTS


def test_throttle_axis_reproduces_both_default_power_lists():
    assert throttle_axis('2500,3100,200') == DEFAULT_DRY_POWERS
    assert throttle_axis('3200,3800,200') == DEFAULT_WET_POWERS


def test_dts_axis_without_a_cold_side_is_plain_ascending():
    assert dts_axis('0,30,10') == [0., 10., 20., 30.]


def test_dts_axis_of_cold_only_range_walks_away_from_zero():
    assert dts_axis('-30,-10,10') == [-10., -20., -30.]


def test_throttle_axis_rejects_non_positive_temperatures():
    with pytest.raises(RangeError, match="positive degR"):
        throttle_axis('0,100,50')
