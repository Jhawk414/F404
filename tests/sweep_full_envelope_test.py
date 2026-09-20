"""Tests for the cycle-deck writer.

`write_deck_csv` is the single exit point for every deck (dry, wet,
combined), and #12 made its precision deliberate per column rather than
pandas' global float_format. The decks are the repo's actual product and are
committed for review, so a formatting change is a diff across every row —
these pin the format down.
"""
import pandas as pd
import pytest

from F404_pycycle.sweep_full_envelope import (
    DECK_HI_PRECISION_COLS,
    DECK_SCI_COLS,
    write_deck_csv,
)

ROW = {
    'alt': 2500.0, 'dTs': -10.0, 'MN': 0.001,
    'Fn': 10999.999999964, 'Fg': 11050.034232431, 'TSFC': 0.6200833312,
    'W': 144.1824854712, 'BPR': 0.7528120845,
    'FAR_core': 0.0272629812, 'FAR_ab': 0.0415325149,
    'OPR': 26.6500000001, 'fan_PR': 4.1, 'hpc_PR': 6.5,
    'hpt_PR': 2.6407372249, 'lpt_PR': 2.4477651512,
    'T4': 3100.0000000012, 'T7': 3799.9999958999,
    'LP_Nmech': 9999.9999867901, 'HP_Nmech': 13999.9999421201,
    'mode': 'wet',
}


@pytest.fixture
def written(tmp_path):
    """Write one deck row and hand back the raw text fields, unparsed."""
    path = tmp_path / 'deck.csv'
    write_deck_csv(pd.DataFrame([ROW]), path)

    text = path.read_text().splitlines()
    return dict(zip(text[0].split(','), text[1].split(',')))


def test_fuel_air_ratios_are_written_in_scientific_notation(written):
    # FAR sits around 0.03-0.04, so fixed decimals spend their digits on
    # leading zeros and flatten the small dTs-driven fueling change that the
    # deck exists to show. Scientific keeps every shown digit significant.
    assert written['FAR_core'] == '2.7263e-02'
    assert written['FAR_ab'] == '4.1533e-02'


def test_continuous_quantities_keep_four_decimals(written):
    # Rates, ratios and spool speeds are what a downstream optimizer reads.
    assert written['W'] == '144.1825'
    assert written['BPR'] == '0.7528'
    assert written['TSFC'] == '0.6201'
    assert written['LP_Nmech'] == '10000.0000'  # 9999.99998679, rounded up
    assert written['MN'] == '0.0010'


def test_thrust_temperatures_and_flight_conditions_keep_two_decimals(written):
    assert written['Fn'] == '11000.00'
    assert written['T4'] == '3100.00'
    assert written['T7'] == '3800.00'
    assert written['alt'] == '2500.00'


def test_every_numeric_column_is_assigned_a_precision(written):
    # A new column added to extract_od_results falls through to the 2-decimal
    # default rather than being written at full float64 repr — the thing #12
    # set out to stop.
    for column, value in written.items():
        if column == 'mode':
            continue
        assert len(value.split('.')[-1].split('e')[0]) <= 4, (
            f"{column} written as {value!r} — more precision than any "
            f"deck column is assigned"
        )


def test_non_numeric_columns_pass_through_unformatted(written):
    assert written['mode'] == 'wet'


def test_column_order_is_preserved_and_no_index_is_written(tmp_path):
    path = tmp_path / 'deck.csv'
    write_deck_csv(pd.DataFrame([ROW]), path)

    header = path.read_text().splitlines()[0].split(',')
    assert header == list(ROW)


def test_writing_does_not_mutate_the_caller_s_dataframe(tmp_path):
    # The combined deck is written from a concat of the per-mode frames, so
    # an in-place reformat would corrupt the frames already written.
    df = pd.DataFrame([ROW])

    write_deck_csv(df, tmp_path / 'deck.csv')

    assert df['W'].dtype == float
    assert df['W'].iloc[0] == ROW['W']


def test_precision_column_sets_do_not_overlap():
    # DECK_SCI_COLS is checked first, so an overlap would silently win there
    # and the 4-decimal intent would never apply.
    assert not (DECK_SCI_COLS & DECK_HI_PRECISION_COLS)


def test_written_values_round_trip_within_their_stated_precision(tmp_path):
    path = tmp_path / 'deck.csv'
    write_deck_csv(pd.DataFrame([ROW]), path)

    reread = pd.read_csv(path).iloc[0]
    for column, original in ROW.items():
        if column == 'mode':
            continue
        tolerance = 1e-4 if column in DECK_SCI_COLS else 5e-3
        assert reread[column] == pytest.approx(original, rel=tolerance), (
            f"{column} lost more precision than intended"
        )
