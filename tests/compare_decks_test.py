"""Tests for the deck comparison behind `f404 compare`.

It is the yardstick for spikes and PR proof, so the matching rule and the
%/absolute switch are pinned here: a wrong join silently compares
different operating points.
"""
import pandas as pd
import pytest

from f404.compare_decks import compare_decks, format_report, read_deck


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


def test_columns_filter_and_flight_mach_is_skipped_by_default():
    every, _, _ = compare_decks(deck('dry'), deck('dry'))
    chosen, _, _ = compare_decks(deck('dry'), deck('dry'), columns=['Fn'])

    assert 'MN' not in every['column'].tolist()
    assert chosen['column'].tolist() == ['Fn']


@pytest.mark.parametrize('columns, side', [(['FN'], 'BASE'), (['Fn', 'mode'], 'BASE')])
def test_requested_columns_that_do_not_exist_are_an_error(columns, side):
    # A typo used to give an empty table and exit 0, hiding any change.
    with pytest.raises(ValueError, match=f'{side} deck has no numeric column'):
        compare_decks(deck('dry'), deck('dry'), columns=columns)


def test_a_requested_column_missing_from_new_is_an_error():
    with pytest.raises(ValueError, match=r"NEW deck has no numeric column \['Fn'\]"):
        compare_decks(deck('dry'), deck('dry').drop(columns='Fn'), columns=['Fn'])


def test_report_lists_unmatched_points_and_can_hide_unchanged_columns():
    table, only_base, only_new = compare_decks(
        deck('dry'), deck('dry', Fn=[11110., 9000.]).iloc[:1])

    text = format_report(table, only_base, only_new, 2, 1, changed_only=True)

    assert 'matched 1' in text
    assert 'only in base (alt, dTs, throttle): [(2500, 20, 2900)]' in text
    assert '| Fn % |' in text and '| T7' not in text


def test_adjacent_float64_values_read_back_distinct(tmp_path):
    # Default read_csv parses both of these to the same float; a one-ULP model
    # change would then report as bit-identical.
    for name, fn in (('a', '0.0272629812'), ('b', '0.027262981200000005')):
        (tmp_path / f'{name}.csv').write_text(
            f'alt,dTs,T4,T7,Fn,FAR_ab,mode\n0,0,3100,1500,{fn},0,dry\n')

    table, _, _ = compare_decks(read_deck(tmp_path / 'a.csv'), read_deck(tmp_path / 'b.csv'))

    assert row(table, 'Fn')['max_abs'] > 0


def test_a_dry_deck_is_not_compared_with_a_wet_one():
    # Dry T4 = 3100 and wet T7 = 3100 would otherwise share a key.
    with pytest.raises(ValueError, match='BASE is a dry deck and NEW is a wet deck'):
        compare_decks(deck('dry'), deck('wet'))


def test_a_mixed_mode_deck_is_rejected():
    mixed = deck('dry').assign(mode=['dry', 'wet'])

    with pytest.raises(ValueError, match="BASE deck holds modes"):
        compare_decks(mixed, deck('dry'))


def test_a_fractional_dts_grid_keeps_its_points_distinct():
    # --dts 0,0.25,0.25 is a supported sweep; rounding dTs to 1 R merged them.
    frac = dict(alt=[0., 0.], dTs=[0., 0.25], T4=[3100., 3100.])
    table, only_base, only_new = compare_decks(
        deck('dry', **frac), deck('dry', Fn=[11000., 9900.], **frac))

    assert only_base == only_new == []
    assert row(table, 'Fn')['worst'] == (0, 0.25, 3100)


def test_row_order_does_not_change_the_result():
    new = deck('dry', Fn=[11110., 9000.])

    forward, _, _ = compare_decks(deck('dry'), new)
    reversed_, _, _ = compare_decks(deck('dry'), new.iloc[::-1])

    pd.testing.assert_frame_equal(forward, reversed_)


def test_two_rows_on_one_key_are_rejected():
    # A throttle grid finer than the 1 R match would pair arbitrary rows.
    crowded = deck('dry', alt=[0., 0.], dTs=[0., 0.], T4=[3100.2, 3099.9])

    with pytest.raises(ValueError, match=r"NEW deck has more than one row .*\(0, 0, 3100\)"):
        compare_decks(deck('dry'), crowded)
