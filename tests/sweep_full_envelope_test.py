"""Tests for the cycle-deck writer.

`write_deck_csv` is the single exit point for every deck (dry, wet,
combined). It writes full float64 precision so that deck-to-deck comparisons
(spike studies, PR proof) measure the model, not the rounding.
"""
import pandas as pd
import pytest

from f404.problems import build_problem
from f404.sweep_full_envelope import (
    DEFAULT_ALTS,
    DEFAULT_DRY_POWERS,
    DEFAULT_DTS,
    DEFAULT_WET_POWERS,
    run_mode_sweep,
    run_sweeps,
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
    assert list(DEFAULT_ALTS) == [0, 2500, 5000]
    assert DEFAULT_DTS == [0., 10., 20., 30., 40., 50.,
                           -10., -20., -30., -40., -50.]
    assert DEFAULT_DRY_POWERS == [3100., 2900., 2700., 2500.]
    assert DEFAULT_WET_POWERS == pytest.approx([3598.35, 3398.35, 3198.35, 2998.35])


@pytest.mark.parametrize('call', [
    lambda: run_sweeps('hot'),
    lambda: run_mode_sweep('both', [0.], [0.], [3100.]),
])
def test_unknown_mode_is_rejected_before_any_work(call):
    with pytest.raises(ValueError, match="mode must be"):
        call()


@pytest.mark.slow
@pytest.mark.parametrize('mode, power', [('dry', 3100.), ('wet', 3608.)])
def test_run_mode_sweep_writes_a_deck_for_the_requested_grid(tmp_path, mode, power):
    df = run_mode_sweep(mode, [0.], [0.], [power], out_dir=tmp_path)

    deck = pd.read_csv(tmp_path / f'cycle_deck_{mode}.csv')
    assert len(df) == len(deck) == 1
    assert deck['converged'].iloc[0]
    assert deck['mode'].iloc[0] == mode
    assert deck['alt'].iloc[0] == 0.0


@pytest.mark.slow
def test_wet_sweep_holds_the_mil_temperature_the_engine_was_built_with(tmp_path):
    # A problem built with custom targets and handed in via built= must keep
    # its own mil Tt4 in the wet sweep, not the module default (3100 R).
    built = build_problem(mil_Tt4=3000., verbose=False)

    df = run_mode_sweep('wet', [0.], [0.], [3608.], out_dir=tmp_path,
                           built=built)

    assert df['T4'].iloc[0] == pytest.approx(3000., abs=0.01)


@pytest.mark.slow
def test_both_modes_sweep_one_problem_and_survive_a_failed_point(tmp_path):
    # --mode both sizes once and sweeps dry then wet on the same problem. The
    # dry grid opens with an unreachable point (800 R is below compressor
    # delivery), so the wet sweep only produces a row if the failure didn't
    # leave the shared OD point broken: each mode restarts from the SLS state.
    results = run_sweeps('both', alts=[0.], dTs_vals=[0.],
                         dry_powers=[800., 3100.], wet_powers=[3608.],
                         out_dir=tmp_path)

    # Converged plus failed rows are the whole attempted grid (#27).
    assert list(results['dry']['converged']) == [False, True]
    assert list(results['wet']['T7'].round()) == [3608.]
    assert results['dry']['W'].iloc[1] == pytest.approx(
        results['wet']['W'].iloc[0], rel=1e-3)
    combined = pd.read_csv(tmp_path / 'cycle_deck_full_envelope.csv')
    assert list(combined['mode']) == ['dry', 'dry', 'wet']
