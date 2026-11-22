"""Tests for the OD drivers (sweep, run_point, run_sweeps) and the deck writer.

`write_deck_csv` is the single exit point for every deck (dry, wet,
combined). It writes full float64 precision so that deck-to-deck comparisons
(spike studies, PR proof) measure the model, not the rounding.
"""
from pathlib import Path

import pandas as pd
import pytest

from f404.config import DesignInputs
from f404.problems import design
from f404.sweep_full_envelope import (
    DEFAULT_ALTS,
    DEFAULT_DRY_POWERS,
    DEFAULT_DTS,
    DEFAULT_MACHS,
    DEFAULT_WET_POWERS,
    run_point,
    run_sweeps,
    sweep,
    write_deck_csv,
)

ROW = {
    'mode': 'wet', 'converged': True,
    'alt': 2500.0, 'dTs': -10.0, 'MN': 0.001,
    'T4_cmd': 3100.0, 'T7_cmd': 3598.35,
    'Fn': 10999.999999964, 'Fg': 11050.034232431, 'TSFC': 0.6200833312,
    'W': 144.1824854712, 'BPR': 0.7528120845,
    'FAR_core': 0.0272629812, 'FAR_ab': 4.4e-18,
    'T4': 3100.0000000012, 'A8': 381.2345678,
}


def test_every_value_round_trips_bit_identically(tmp_path):
    path = tmp_path / 'deck.csv'
    write_deck_csv(pd.DataFrame([ROW]), path)

    reread = pd.read_csv(path).iloc[0]
    for column, original in ROW.items():
        assert reread[column] == original, f"{column} lost precision"


def test_column_order_is_preserved_and_no_index_is_written(tmp_path):
    path = tmp_path / 'deck.csv'
    write_deck_csv(pd.DataFrame([ROW]), path)

    header = path.read_text().splitlines()[0].split(',')
    assert header == list(ROW)


def test_writing_does_not_mutate_the_caller_s_dataframe(tmp_path):
    # The combined deck is written from a concat of the per-mode frames.
    df = pd.DataFrame([ROW])

    write_deck_csv(df, tmp_path / 'deck.csv')

    assert df['W'].dtype == float
    assert df['W'].iloc[0] == ROW['W']


# ── Driver ────────────────────────────────────────────────────────────────────

def test_default_grid_is_the_committed_envelope():
    # The committed decks were generated from this grid. Changing it silently
    # changes every deck, so it is pinned here rather than inferred.
    assert DEFAULT_MACHS == [0.001, 0.2, 0.4, 0.6, 0.8, 0.95]
    assert list(DEFAULT_ALTS) == [0, 2500, 5000]
    assert DEFAULT_DTS == [0., 10., 20., 30., 40., 50.,
                           -10., -20., -30., -40., -50.]
    assert DEFAULT_DRY_POWERS == [3100., 2900., 2700., 2500.]
    assert DEFAULT_WET_POWERS == pytest.approx([3607.68, 3407.68, 3207.68, 3007.68])


@pytest.mark.parametrize('call', [
    lambda: run_sweeps('hot'),
    lambda: sweep(None, mode='both'),
    lambda: run_point(None, mode='both', alt=0, mach=0, dts=0, throttle=3100),
])
def test_unknown_mode_is_rejected_before_any_work(call):
    with pytest.raises(ValueError, match="mode must be"):
        call()


@pytest.mark.slow
@pytest.mark.parametrize('mode, power', [('dry', 3100.), ('wet', 3608.)])
def test_sweep_writes_a_deck_for_the_requested_grid(engine, tmp_path, mode, power):
    df = sweep(engine, mode=mode, mach=[0.5], alt=[0.], dts=[0.], throttle=[power],
               out_dir=tmp_path)

    deck = pd.read_csv(tmp_path / f'cycle_deck_{mode}.csv')
    assert len(df) == len(deck) == 1
    assert deck['converged'].iloc[0]
    assert deck['mode'].iloc[0] == mode
    assert (deck['alt'].iloc[0], deck['MN'].iloc[0]) == (0.0, 0.5)


@pytest.mark.slow
def test_a_sweep_holds_the_temperatures_the_engine_was_built_with(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # An engine built with custom targets and handed in via engine= must keep
    # its own mil Tt4 in the wet sweep, not the module default (3100 R).
    engine = design(DesignInputs(mil_Tt4=3000.))

    wet = sweep(engine, mode='wet', mach=0, alt=0, dts=0, throttle=3608.)
    # The default dry throttle runs down from this engine's mil, not 3100 R.
    dry = sweep(engine, mode='dry', mach=0, alt=0, dts=0)

    assert wet['T4'].iloc[0] == pytest.approx(3000., abs=0.01)
    assert list(dry['T4_cmd']) == [3000., 2800., 2600., 2400.]
    assert list(tmp_path.iterdir()) == []   # no out_dir, nothing written


DECK = Path(__file__).parents[1] / 'deck' / 'cycle_deck_dry.csv'


@pytest.mark.slow
def test_run_point_reproduces_a_deck_row_whatever_ran_before(engine):
    # A cold, fast, part-power corner the deck reaches through ~600 converged
    # neighbours; run_point reaches it from the SLS anchor alone.
    deck = pd.read_csv(DECK).set_index(['alt', 'MN', 'dTs', 'T4_cmd'])
    expected = deck.loc[(5000., 0.8, -30., 2700.)]
    point = dict(mode='dry', alt=5000, mach=0.8, dts=-30, throttle=2700)

    first = run_point(engine, **point)
    run_point(engine, mode='wet', alt=2500, mach=0.4, dts=20, throttle=3207.68)
    again = run_point(engine, **point)

    assert first == again
    assert first['converged']
    for column in ('Fn', 'TSFC', 'W', 'BPR'):
        assert first[column] == pytest.approx(expected[column], rel=1e-5)


@pytest.mark.slow
def test_a_dry_sweep_does_not_steer_a_later_wet_sweep():
    # pyCycle's Ps guess caches live outside the model's vectors; before
    # restore_anchor() reset them, this grid moved the wet deck (#59).
    grid = dict(mach=0.001, alt=0, dts=[0, 10])
    alone = sweep(design(), mode='wet', **grid)
    engine = design()
    sweep(engine, mode='dry', **grid)

    pd.testing.assert_frame_equal(sweep(engine, mode='wet', **grid), alone,
                                  check_exact=True)


@pytest.mark.slow
def test_run_point_returns_a_failed_point_as_a_row(engine):
    # 800 R is below compressor delivery: no solution exists.
    row = run_point(engine, mode='dry', alt=0, mach=0, dts=0, throttle=800)

    assert (row['converged'], row['MN']) == (False, 0.001)
    assert row['failure'] and pd.isna(row['Fn'])


@pytest.mark.slow
def test_both_modes_sweep_one_problem_and_survive_a_failed_point(tmp_path):
    # --mode both sizes once and sweeps dry then wet on the same problem. The
    # dry grid ends on an unreachable point (800 R is below compressor
    # delivery), so the wet sweep only produces a row if the failure didn't
    # leave the shared OD point broken: each mode restarts from the SLS state.
    results = run_sweeps('both', alts=[0.], dTs_vals=[0.],
                         dry_powers=[3100., 800.], wet_powers=[3608.],
                         machs=[0.001], out_dir=tmp_path)

    # Converged plus failed rows are the whole attempted grid (#27).
    assert list(results['dry']['converged']) == [True, False]
    assert list(results['wet']['T7'].round()) == [3608.]
    assert results['dry']['W'].iloc[0] == pytest.approx(
        results['wet']['W'].iloc[0], rel=1e-3)
    combined = pd.read_csv(tmp_path / 'cycle_deck_full_envelope.csv')
    assert list(combined['mode']) == ['dry', 'dry', 'wet']
    # On disk a failed row keeps its inputs, reads back NaN outputs and says why.
    failed = pd.read_csv(tmp_path / 'cycle_deck_dry.csv').iloc[1]
    assert (failed['converged'], failed['T4_cmd']) == (False, 800.)
    assert failed[['Fn', 'W', 'T4', 'V9']].isna().all()
    assert failed['failure'] in ('AnalysisError', 'RuntimeError', 'target') \
        or failed['failure'].startswith('bound:')
