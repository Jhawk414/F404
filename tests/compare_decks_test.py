"""Tests for the deck comparison behind `f404 compare`.

It is the yardstick for spikes and PR proof, so the matching rule and the
%/absolute switch are pinned here: a wrong join silently compares
different operating points.
"""
import pandas as pd
import pytest

from f404.compare_decks import compare_decks, format_report


def deck(mode, **cols):
    """A two-row deck at SLS std day and 2500 ft, +20 R."""
    base = {'alt': [0., 2500.], 'dTs': [0., 20.], 'MN': [0.001, 0.001],
            'T4': [3100.0000001, 2899.9999998], 'T7': [3608., 3408.],
            'Fn': [11000., 9000.], 'FAR_ab': [0., 0.], 'mode': [mode, mode]}
    base.update(cols)
    return pd.DataFrame(base)


def row(table, column):
    return table.set_index('column').loc[column]


def test_identical_decks_differ_by_zero_everywhere():
    table, only_base, only_new = compare_decks(deck('dry'), deck('dry'))

    assert (table['max_abs'] == 0).all()
    assert only_base == only_new == []


def test_reports_signed_percent_range_and_worst_point():
    table, _, _ = compare_decks(deck('dry'), deck('dry', Fn=[11110., 8910.]))

    fn = row(table, 'Fn')
    assert fn['kind'] == '%'
    assert (fn['min'], fn['max']) == pytest.approx((-1., 1.))
    assert fn['worst'] in [(0, 0, 3100), (2500, 20, 2900)]


def test_near_zero_base_is_compared_in_absolute_terms():
    # A solved FAR_ab of ~1e-18 against a literal 0 is no change, not inf %.
    table, _, _ = compare_decks(deck('dry'), deck('dry', FAR_ab=[4e-18, 0.]))

    far = row(table, 'FAR_ab')
    assert far['kind'] == 'abs'
    assert far['max_abs'] == pytest.approx(4e-18)


def test_dry_rows_match_on_t4_and_wet_rows_on_t7():
    # Same T4, different T7: matches when dry, not when wet.
    other_t7 = {'T7': [3608., 3208.]}

    _, dry_only_base, _ = compare_decks(deck('dry'), deck('dry', **other_t7))
    _, wet_only_base, wet_only_new = compare_decks(deck('wet'), deck('wet', **other_t7))

    assert dry_only_base == []
    assert wet_only_base == [(2500, 20, 3408)]
    assert wet_only_new == [(2500, 20, 3208)]


def test_columns_filter_and_flight_mach_is_skipped():
    table, _, _ = compare_decks(deck('dry'), deck('dry'), columns={'Fn', 'MN'})

    assert table['column'].tolist() == ['Fn']


def test_report_lists_unmatched_points_and_can_hide_unchanged_columns():
    table, only_base, only_new = compare_decks(
        deck('dry'), deck('dry', Fn=[11110., 9000.]).iloc[:1])

    text = format_report(table, only_base, only_new, 2, 1, changed_only=True)

    assert 'matched 1' in text
    assert 'only in base (alt, dTs, throttle): [(2500, 20, 2900)]' in text
    assert '| Fn % |' in text and '| T7' not in text
