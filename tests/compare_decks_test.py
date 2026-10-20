"""Tests for the deck comparison behind `f404 compare`.

It is the yardstick for spikes and PR proof, so the matching rule, the
convergence lists and the %/absolute switch are pinned here: a wrong join
silently compares different operating points.
"""
import pandas as pd
import pytest

from f404.compare_decks import compare_decks, format_report, read_deck

P1 = ('dry', 0, 0, 0.001, 3100, 0)
P2 = ('dry', 2500, 20, 0.001, 2900, 0)


def deck(**cols):
    """A two-row dry deck at SLS std day mil and 2500 ft, +20 R, 2900 R."""
    base = {'mode': ['dry', 'dry'], 'converged': [True, True],
            'alt': [0., 2500.], 'dTs': [0., 20.], 'MN': [0.001, 0.001],
            'T4_cmd': [3100., 2900.], 'T7_cmd': [0., 0.],
            'Fn': [11000., 9000.], 'T4': [3100.0000001, 2899.9999998],
            'FAR_ab': [0., 0.], 'failure': [None, None]}
    base.update(cols)
    return pd.DataFrame(base)


def row(table, column):
    return table.set_index('column').loc[column]


def test_identical_decks_differ_by_zero_everywhere():
    table, points = compare_decks(deck(), deck())

    assert (table['max_abs'] == 0).all()
    assert not any(points.values())


def test_reports_signed_percent_range_and_worst_point():
    table, _ = compare_decks(deck(), deck(Fn=[11110., 8910.]))

    fn = row(table, 'Fn')
    assert fn['kind'] == '%'
    assert (fn['min'], fn['max']) == pytest.approx((-1., 1.))
    assert fn['worst'] in [P1, P2]


def test_near_zero_base_is_compared_in_absolute_terms():
    # A solved FAR_ab of ~1e-18 against a literal 0 is no change, not inf %.
    table, _ = compare_decks(deck(), deck(FAR_ab=[4e-18, 0.]))

    far = row(table, 'FAR_ab')
    assert far['kind'] == 'abs'
    assert far['max_abs'] == pytest.approx(4e-18)


def test_points_match_on_flight_mach_and_both_commands():
    _, mach = compare_decks(deck(), deck(MN=[0.001, 0.2]))
    _, t7 = compare_decks(deck(), deck(T7_cmd=[0., 3400.]))

    assert mach['only in base'] == t7['only in base'] == [P2]
    assert mach['only in new'] == [('dry', 2500, 20, 0.2, 2900, 0)]
    assert t7['only in new'] == [('dry', 2500, 20, 0.001, 2900, 3400)]


def test_convergence_changes_are_listed_and_kept_out_of_the_values():
    failed = dict(converged=[True, False], Fn=[11000., None], T4=[3100., None],
                  failure=[None, 'bound:balance.BPR'])
    lost, gained = deck(), deck()
    table, points = compare_decks(lost, deck(**failed))
    _, back = compare_decks(deck(**failed), gained)
    _, neither = compare_decks(deck(**failed), deck(**failed))

    assert points['converged only in base'] == back['converged only in new'] == [P2]
    assert neither['failed in both'] == [P2]
    # The failed row's blanks are a convergence change, not invalid values.
    assert 'invalid' not in table['kind'].tolist()
    report = format_report(table, neither, 2, 2)
    assert 'converged in both 1' in report and 'failed in both: 1' in report


def test_a_full_envelope_deck_compares_both_modes_at_once():
    wet = deck(mode=['wet', 'wet'], T4_cmd=[3100., 3100.], T7_cmd=[3598.35, 3398.35])
    both = pd.concat([deck(), wet], ignore_index=True)

    table, points = compare_decks(both, both.assign(Fn=both['Fn'] * 1.01))

    assert not any(points.values())
    assert row(table, 'Fn')['min'] == pytest.approx(1.)


def test_a_deck_from_before_the_input_columns_matches_on_its_solved_temperatures():
    # Pre-#27 decks: converged rows only, keyed by the solved T4 (dry) / T7 (wet).
    legacy = deck().drop(columns=['converged', 'T4_cmd', 'T7_cmd', 'failure'])
    legacy_wet = legacy.assign(mode='wet', T4=[3100.0001, 3099.9999],
                               T7=[3598.3512, 3398.3488])
    new_wet = deck(mode=['wet', 'wet'], T4_cmd=[3100., 3100.],
                   T7_cmd=[3598.35, 3398.35])

    _, dry = compare_decks(legacy.assign(T7=[1500., 1400.]), deck())
    _, wet = compare_decks(legacy_wet, new_wet)

    assert not any(dry.values()) and not any(wet.values())


def test_a_fractional_throttle_grid_keeps_its_points_distinct():
    # Commands are inputs, so 3099.5 and 3100.5 are two points, not one.
    frac = dict(alt=[0., 0.], dTs=[0., 0.], T4_cmd=[3099.5, 3100.5])
    table, points = compare_decks(deck(**frac), deck(Fn=[11000., 9900.], **frac))

    assert not any(points.values())
    assert row(table, 'Fn')['worst'] == ('dry', 0, 0, 0.001, 3100.5, 0)


def test_a_legacy_deck_matches_fractional_commands_on_its_solved_temperatures():
    frac = dict(alt=[0., 0.], dTs=[0., 0.], T4_cmd=[3099.5, 3100.5])
    legacy = deck(alt=[0., 0.], dTs=[0., 0.], T4=[3099.4999, 3100.500058]).drop(
        columns=['converged', 'T4_cmd', 'T7_cmd', 'failure']).assign(T7=[1500., 1500.])

    _, points = compare_decks(legacy, deck(**frac))

    assert not any(points.values())


def test_a_legacy_deck_against_commands_closer_than_the_tolerance_is_an_error():
    legacy = deck().drop(columns=['converged', 'T4_cmd', 'T7_cmd', 'failure']).assign(
        T7=[1500., 1400.])
    close = deck(alt=[0., 0.], dTs=[0., 0.], T4_cmd=[3100., 3100.3])

    with pytest.raises(ValueError, match="closer together than 0.5 R"):
        compare_decks(legacy, close)


def test_a_deck_without_a_mode_column_gets_it_from_the_augmentor_fuel():
    # Decks from before PR #34 had no mode column.
    oldest = deck().drop(columns=['mode', 'converged', 'T4_cmd', 'T7_cmd', 'failure'])
    wet = deck(mode=['wet', 'wet'], T4_cmd=[3100., 3100.], T7_cmd=[3598.35, 3398.35])
    oldest_wet = oldest.assign(T4=[3100.0001, 3099.9999], T7=[3598.3512, 3398.3488],
                               FAR_ab=[0.03, 0.02])

    _, dry_points = compare_decks(oldest.assign(T7=[1500., 1400.]), deck())
    _, wet_points = compare_decks(oldest_wet, wet)

    assert not any(dry_points.values()) and not any(wet_points.values())


def test_columns_filter_and_inputs_are_not_compared_by_default():
    every, _ = compare_decks(deck(), deck())
    chosen, _ = compare_decks(deck(), deck(), columns=['Fn'])

    assert set(every['column']) == {'Fn', 'T4', 'FAR_ab'}
    assert chosen['column'].tolist() == ['Fn']


@pytest.mark.parametrize('columns, side', [(['FN'], 'BASE'), (['Fn', 'nope'], 'BASE')])
def test_requested_columns_that_do_not_exist_are_an_error(columns, side):
    # A typo used to give an empty table and exit 0, hiding any change.
    with pytest.raises(ValueError, match=f'{side} deck has no numeric column'):
        compare_decks(deck(), deck(), columns=columns)


@pytest.mark.parametrize('column', ['mode', 'MN', 'T4_cmd', 'converged'])
def test_requesting_an_input_column_is_an_error_not_an_empty_table(column):
    with pytest.raises(ValueError, match='not compared'):
        compare_decks(deck(), deck(), columns=['Fn', column])


def test_a_requested_column_missing_from_new_is_an_error():
    with pytest.raises(ValueError, match=r"NEW deck has no numeric column \['Fn'\]"):
        compare_decks(deck(), deck().drop(columns='Fn'), columns=['Fn'])


def test_report_lists_unmatched_points_and_can_hide_unchanged_columns():
    table, points = compare_decks(deck(), deck(Fn=[11110., 9000.]).iloc[:1])

    text = format_report(table, points, 2, 1, changed_only=True)

    assert 'matched 1' in text
    assert f'only in base (mode, alt, dTs, MN, T4_cmd, T7_cmd): [{P2}]' in text
    assert '| Fn % |' in text and '| T4' not in text


def test_adjacent_float64_values_read_back_distinct(tmp_path):
    # Default read_csv parses both of these to the same float; a one-ULP model
    # change would then report as bit-identical.
    for name, fn in (('a', '0.0272629812'), ('b', '0.027262981200000005')):
        (tmp_path / f'{name}.csv').write_text(
            f'mode,converged,alt,dTs,MN,T4_cmd,T7_cmd,Fn,failure\n'
            f'dry,True,0,0,0.001,3100,0,{fn},\n')

    table, _ = compare_decks(read_deck(tmp_path / 'a.csv'), read_deck(tmp_path / 'b.csv'))

    assert row(table, 'Fn')['max_abs'] > 0


def test_a_fractional_dts_grid_keeps_its_points_distinct():
    # --dts 0,0.25,0.25 is a supported sweep; rounding dTs to 1 R merged them.
    frac = dict(alt=[0., 0.], dTs=[0., 0.25], T4_cmd=[3100., 3100.])
    table, points = compare_decks(deck(**frac), deck(Fn=[11000., 9900.], **frac))

    assert not any(points.values())
    assert row(table, 'Fn')['worst'] == ('dry', 0, 0.25, 0.001, 3100, 0)


def test_row_order_does_not_change_the_result():
    new = deck(Fn=[11110., 9000.])

    forward, _ = compare_decks(deck(), new)
    reversed_, _ = compare_decks(deck(), new.iloc[::-1])

    pd.testing.assert_frame_equal(forward, reversed_)


def test_two_rows_on_one_key_are_rejected():
    crowded = deck(alt=[0., 0.], dTs=[0., 0.], T4_cmd=[3100., 3100.])

    with pytest.raises(ValueError, match=r"NEW deck has more than one row .*3100, 0\)"):
        compare_decks(deck(), crowded)


def test_a_change_where_the_base_is_zero_is_reported_beside_the_percent_row():
    # Dry ab_dPqP is 0 and wet is 0.054: a new cold loss at the dry point
    # used to drop out of the % row, and --changed-only hid the column.
    table, _ = compare_decks(deck(ab_dPqP=[0., 0.054]), deck(ab_dPqP=[0.02, 0.054]))

    rows = table[table['column'] == 'ab_dPqP'].set_index('kind')
    assert rows.loc['%', 'max_abs'] == 0
    assert rows.loc['abs', 'max_abs'] == pytest.approx(0.02)
    assert rows.loc['abs', 'worst'] == P1


def test_a_blank_result_is_reported_not_read_as_unchanged():
    table, _ = compare_decks(deck(), deck(Fn=[11000., float('nan')]))

    rows = table[table['column'] == 'Fn'].set_index('kind')
    assert rows.loc['%', 'max_abs'] == 0          # the finite point
    assert rows.loc['invalid', 'max_abs'] == 1
    assert rows.loc['invalid', 'worst'] == P2
    report = format_report(table, compare_decks(deck(), deck())[1], 2, 2,
                           changed_only=True)
    assert '| Fn (invalid) |' in report
