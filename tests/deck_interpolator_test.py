"""Tests for the cycle deck interpolator."""
from pathlib import Path

import pandas as pd
import pytest

from F404_pycycle.deck_interpolator import DeckInterpolator


SAMPLE_WET_ROW = {
    'alt': 0.0, 'dTs': 0.0, 'MN': 0.001,
    'Fn': 17740.0, 'Fg': 17750.0, 'TSFC': 1.52,
    'W': 137.0, 'BPR': 0.75,
    'FAR_core': 0.027, 'FAR_ab': 0.041,
    'OPR': 26.6, 'fan_PR': 4.1, 'hpc_PR': 6.5,
    'hpt_PR': 2.64, 'lpt_PR': 2.45,
    'T4': 3100.0, 'T7': 3800.0,
    'LP_Nmech': 10000.0, 'HP_Nmech': 14000.0,
    'mode': 'wet',
}


@pytest.fixture
def sample_grid_df():
    """Create a regular 2x2x2 wet grid for testing trilinear interpolation."""
    rows = []
    for alt in [0.0, 2000.0]:
        for dts in [-10.0, 10.0]:
            for t7 in [3400.0, 3800.0]:
                r = dict(SAMPLE_WET_ROW)
                r['alt'] = alt
                r['dTs'] = dts
                r['T7'] = t7
                # Fn decreases with alt, decreases with dTs, increases with T7
                r['Fn'] = 17000.0 - 0.5 * alt - 20.0 * dts + 2.0 * (t7 - 3400.0)
                # TSFC increases with T7
                r['TSFC'] = 1.30 + 0.0005 * (t7 - 3400.0)
                rows.append(r)
    return pd.DataFrame(rows)


def test_interpolator_exact_node_evaluation(sample_grid_df):
    interp = DeckInterpolator(sample_grid_df)
    res = interp.interpolate('wet', alt=0.0, dTs=-10.0, throttle=3400.0)
    assert res['outputs']['Fn'] == pytest.approx(17200.0, abs=1e-4)
    assert res['outputs']['TSFC'] == pytest.approx(1.30, abs=1e-4)


def test_interpolator_trilinear_midpoint(sample_grid_df):
    interp = DeckInterpolator(sample_grid_df)
    # Midpoint: alt=1000, dts=0, t7=3600
    # Expected Fn: 17000 - 0.5*1000 - 20*0 + 2.0*200 = 16900
    res = interp.interpolate('wet', alt=1000.0, dTs=0.0, throttle=3600.0)
    assert res['method'] == 'multilinear'
    assert res['outputs']['Fn'] == pytest.approx(16900.0, abs=1e-4)
    assert res['outputs']['TSFC'] == pytest.approx(1.40, abs=1e-4)
    assert len(res['corners']) == 8


def test_interpolator_derives_fuel_flows(sample_grid_df):
    interp = DeckInterpolator(sample_grid_df)
    res = interp.interpolate('wet', alt=0.0, dTs=0.0, throttle=3800.0)
    outputs = res['outputs']

    # Total fuel flow = TSFC * Fn / 3600
    expected_wf_tot = outputs['TSFC'] * outputs['Fn'] / 3600.0
    assert outputs['Wf_tot'] == pytest.approx(expected_wf_tot, rel=1e-4)
    assert outputs['Wf_tot_pph'] == pytest.approx(expected_wf_tot * 3600.0, rel=1e-4)
    assert outputs['Wf_core'] > 0.0
    assert outputs['Wf_ab'] >= 0.0


def test_interpolator_idw_fallback_on_incomplete_grid():
    # Only 3 points, not a full 2x2x2 cube
    rows = [
        dict(SAMPLE_WET_ROW, alt=0.0, dTs=0.0, T7=3400.0, Fn=16000.0),
        dict(SAMPLE_WET_ROW, alt=2000.0, dTs=0.0, T7=3400.0, Fn=15000.0),
        dict(SAMPLE_WET_ROW, alt=0.0, dTs=20.0, T7=3800.0, Fn=17000.0),
    ]
    interp = DeckInterpolator(pd.DataFrame(rows))
    res = interp.interpolate('wet', alt=1000.0, dTs=10.0, throttle=3600.0)
    assert res['method'] in ('idw', 'exact')
    assert 15000.0 <= res['outputs']['Fn'] <= 17000.0


def test_interpolator_loads_actual_repo_deck():
    deck_path = Path('deck/cycle_deck_wet.csv')
    if not deck_path.exists():
        pytest.skip("deck/cycle_deck_wet.csv not present in repo")

    interp = DeckInterpolator(deck_path)
    assert 'wet' in interp.get_modes()
    axes = interp.get_axes('wet')
    assert axes['alt']['min'] == 0.0
    assert axes['alt']['max'] == 5000.0
    assert axes['throttle']['min'] == 3200.0
    assert axes['throttle']['max'] == 3800.0

    # Evaluate at sea-level static design point
    res = interp.interpolate('wet', alt=0.0, dTs=0.0, throttle=3800.0)
    assert res['outputs']['Fn'] == pytest.approx(17741.91, abs=1.0)
    assert res['outputs']['W'] == pytest.approx(137.0873, abs=0.5)


def test_interpolator_export_deck_data(sample_grid_df):
    interp = DeckInterpolator(sample_grid_df)
    data = interp.export_deck_data()
    assert 'modes' in data
    assert 'wet' in data['modes']
    assert 'wet' in data['deck_data']
    wet_data = data['deck_data']['wet']
    assert wet_data['points_count'] == len(sample_grid_df)
    assert len(wet_data['points']) == len(sample_grid_df)
    assert 'throttle_col' in wet_data
