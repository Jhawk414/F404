"""Unit tests for the sweep infrastructure.

Everything here runs without an ``om.Problem``: the grid builders are pure
functions, and ``SweepRunner``'s convergence guards only read scalars off the
problem, so a stub standing in for it exercises them in milliseconds. That
matters because those guards are the regression surface — they are what
distinguishes a real solution from a bound-clipped one that Newton is willing
to call converged.
"""
import pytest

from F404_pycycle.sweep_utils import (
    _BOUND_TOL_FRAC,
    _OD_BOUNDS,
    _OD_FAR_AB_BOUNDS,
    _TARGET_TOL_DEGR,
    SweepRunner,
    _scalar,
    build_snake_sweep,
    extract_od_results,
    generate_bridge_points,
)

OD = 'OD'

# A physically sensible mid-envelope OD state: every balance comfortably
# inside its bounds. Individual tests push one value at a time out of range.
CLEAN_STATE = {
    f'{OD}.balance.W':        144.18,
    f'{OD}.balance.BPR':      0.7528,
    f'{OD}.balance.FAR_core': 0.025,
    f'{OD}.balance.FAR_ab':   0.035,
    f'{OD}.balance.LP_Nmech': 10000.,
    f'{OD}.balance.HP_Nmech': 14000.,
}


class StubProblem:
    """Stand-in for ``om.Problem`` over the read-only API the guards use.

    ``SweepRunner._state_at_bounds`` indexes the problem directly and
    ``_target_met`` calls ``get_val``; both swallow lookup failures, so a
    missing key must raise rather than return a default for the
    "variable absent" paths to be tested honestly.
    """

    def __init__(self, values):
        self._values = dict(values)

    def __getitem__(self, key):
        return self._values[key]

    def get_val(self, key, units=None):
        return self._values[key]


def runner(values, afterburn=True, mil_Tt4=3100.):
    return SweepRunner(StubProblem(values), od_pt=OD, afterburn=afterburn,
                       mil_Tt4=mil_Tt4)


# ── build_snake_sweep ─────────────────────────────────────────────────────────

def test_snake_sweep_covers_the_full_grid():
    sweep = build_snake_sweep([0, 2500, 5000], [0., 10., -10.], [3100., 2900.])

    assert len(sweep) == 3 * 3 * 2
    assert {(p['alt'], p['dTs'], p['power']) for p in sweep} == {
        (alt, dTs, power)
        for alt in (0., 2500., 5000.)
        for dTs in (0., 10., -10.)
        for power in (3100., 2900.)
    }


def test_snake_sweep_orders_power_then_alt_then_dTs():
    sweep = build_snake_sweep([0, 2500], [0., 10.], [3100., 2900.])

    # Power is outermost: every 3100 point precedes every 2900 point.
    powers = [p['power'] for p in sweep]
    assert powers == [3100.] * 4 + [2900.] * 4
    # Altitude is next: it only advances once dTs is exhausted.
    assert [p['alt'] for p in sweep[:4]] == [0., 0., 2500., 2500.]


def test_snake_sweep_reverses_dTs_on_alternating_altitudes():
    # The whole point of the snake: consecutive points stay neighbours across
    # an altitude step instead of jumping the full dTs span, which is what
    # gives Newton a usable warm start.
    dTs_values = [0., 10., 20.]
    sweep = build_snake_sweep([0, 2500, 5000], dTs_values, [3100.])

    assert [p['dTs'] for p in sweep] == [0., 10., 20.,   # alt 0, ascending
                                         20., 10., 0.,   # alt 2500, reversed
                                         0., 10., 20.]   # alt 5000, ascending
    # The two points either side of each altitude change share a dTs.
    assert sweep[2]['dTs'] == sweep[3]['dTs']
    assert sweep[5]['dTs'] == sweep[6]['dTs']


def test_snake_sweep_does_not_mutate_the_caller_s_dTs_list():
    dTs_values = [0., 10., 20.]
    build_snake_sweep([0, 2500], dTs_values, [3100.])

    assert dTs_values == [0., 10., 20.]


def test_snake_sweep_coerces_grid_values_to_float():
    # numpy integer altitudes from np.arange() are the normal caller input;
    # they must not leak into the results dict as numpy scalars.
    point = build_snake_sweep([0], [0], [3100])[0]

    assert all(type(v) is float for v in point.values())


# ── generate_bridge_points ────────────────────────────────────────────────────

def test_bridge_points_interpolate_strictly_between_the_endpoints():
    pt_from = {'alt': 0., 'dTs': 0., 'power': 3800.}
    pt_to = {'alt': 2000., 'dTs': -50., 'power': 3800.}

    bridges = generate_bridge_points(pt_from, pt_to, n_steps=3)

    assert len(bridges) == 3
    assert [b['alt'] for b in bridges] == [500., 1000., 1500.]
    assert [b['dTs'] for b in bridges] == [-12.5, -25., -37.5]
    # power is constant across this jump, so it must not drift.
    assert [b['power'] for b in bridges] == [3800.] * 3
    assert pt_from not in bridges and pt_to not in bridges


def test_bridge_points_empty_when_no_steps_requested():
    pt = {'alt': 0., 'dTs': 0., 'power': 3100.}

    assert generate_bridge_points(pt, pt, n_steps=0) == []


# ── extract_od_results ────────────────────────────────────────────────────────

def _results_state(**overrides):
    state = {
        f'{OD}.fc.alt': 5000., f'{OD}.fc.dTs': -10., f'{OD}.fc.MN': 0.001,
        f'{OD}.perf.Fn': 9000., f'{OD}.perf.Fg': 9500., f'{OD}.perf.TSFC': 0.62,
        f'{OD}.balance.W': 144.18, f'{OD}.balance.BPR': 0.7528,
        f'{OD}.balance.FAR_core': 0.025, f'{OD}.balance.FAR_ab': 0.035,
        f'{OD}.fan.PR': 4.1, f'{OD}.hpc.PR': 6.5,
        f'{OD}.hpt.PR': 2.523, f'{OD}.lpt.PR': 2.401,
        f'{OD}.burner.Fl_O:tot:T': 3100., f'{OD}.afterburner.Fl_O:tot:T': 3800.,
        f'{OD}.balance.LP_Nmech': 10000., f'{OD}.balance.HP_Nmech': 14000.,
    }
    state.update(overrides)
    return state


def test_extract_od_results_derives_opr_from_the_two_compressors():
    # There is no LPC in the F404, so OPR is exactly fan PR x HPC PR.
    row = extract_od_results(StubProblem(_results_state()), OD)

    assert row['OPR'] == pytest.approx(4.1 * 6.5)


def test_extract_od_results_reports_zero_far_ab_in_dry_mode():
    # Dry mode has no FAR_ab balance at all; reading it would raise, so the
    # column has to be filled in as a literal zero to keep the deck schema
    # identical between modes.
    state = _results_state()
    del state[f'{OD}.balance.FAR_ab']

    row = extract_od_results(StubProblem(state), OD, afterburn=False)

    assert row['FAR_ab'] == 0.0


def test_extract_od_results_schema_matches_between_modes():
    dry = extract_od_results(StubProblem(_results_state()), OD, afterburn=False)
    wet = extract_od_results(StubProblem(_results_state()), OD, afterburn=True)

    assert dry.keys() == wet.keys()
    assert all(type(v) is float for v in wet.values())


# ── SweepRunner._state_at_bounds ──────────────────────────────────────────────
# Regression net for the false-convergence class of bug: Newton reports
# success while a BalanceComp state sits clipped at a bound, which is a
# residual minimum but not a solution.

def test_clean_state_is_not_flagged_as_bound_saturated():
    assert runner(CLEAN_STATE)._state_at_bounds() is False


@pytest.mark.parametrize('state_var, value', [
    ('balance.W', 199.5),        # inlet flow pinned at the 200 lbm/s ceiling
    ('balance.W', 25.5),         # ...or at the 25 lbm/s floor
    ('balance.BPR', 0.995),      # bypass ratio clipped at 1.0
    ('balance.FAR_core', 0.0599),
    ('balance.FAR_ab', 0.0599),
    ('balance.LP_Nmech', 502.),  # stalled LP spool sitting on its 500 rpm floor
    ('balance.HP_Nmech', 502.),
])
def test_saturated_state_is_flagged(state_var, value):
    state = dict(CLEAN_STATE, **{f'{OD}.{state_var}': value})

    assert runner(state)._state_at_bounds() is True


def test_far_ab_saturation_is_ignored_in_dry_mode():
    # Dry mode builds no FAR_ab balance, so a stale value at that bound is
    # not evidence of anything.
    state = dict(CLEAN_STATE, **{f'{OD}.balance.FAR_ab': 0.0599})

    assert runner(state, afterburn=False)._state_at_bounds() is False


def test_missing_state_is_skipped_rather_than_failing_the_point():
    state = {k: v for k, v in CLEAN_STATE.items() if 'LP_Nmech' not in k}

    assert runner(state)._state_at_bounds() is False


def test_bound_tolerance_is_a_fraction_of_the_bound_width():
    # W spans 25-200 lbm/s, so the 1% band is 1.75 lbm/s wide: 197.0 is a
    # legitimate high-flow solution, 198.5 is saturated.
    width = _OD_BOUNDS['balance.W'][1] - _OD_BOUNDS['balance.W'][0]
    assert width * _BOUND_TOL_FRAC == pytest.approx(1.75)

    assert runner(dict(CLEAN_STATE, **{f'{OD}.balance.W': 197.0}))._state_at_bounds() is False
    assert runner(dict(CLEAN_STATE, **{f'{OD}.balance.W': 198.5}))._state_at_bounds() is True


# ── SweepRunner._target_met ───────────────────────────────────────────────────
# Second guard against false convergence: Newton can land in a stalled basin
# whose residual is small but whose burner exit temperature is nowhere near
# what was asked for.

def test_dry_target_met_when_burner_exit_hits_the_commanded_tt4():
    state = {f'{OD}.burner.Fl_O:tot:T': 2900.}

    assert runner(state, afterburn=False)._target_met(2900.) is True


def test_dry_target_missed_when_burner_exit_drifts_past_tolerance():
    state = {f'{OD}.burner.Fl_O:tot:T': 2900. - _TARGET_TOL_DEGR - 1.}

    assert runner(state, afterburn=False)._target_met(2900.) is False


def test_wet_target_requires_both_core_and_augmentor_temperatures():
    # In wet mode the core is held at mil power while the augmentor is
    # throttled, so a drifted Tt4 invalidates the point even if T7 is on
    # target — the deck row would be labelled mil power but not be at it.
    on_target = {f'{OD}.burner.Fl_O:tot:T': 3100.,
                 f'{OD}.afterburner.Fl_O:tot:T': 3600.}
    core_drifted = dict(on_target, **{f'{OD}.burner.Fl_O:tot:T': 3050.})
    ab_drifted = dict(on_target, **{f'{OD}.afterburner.Fl_O:tot:T': 3500.})

    assert runner(on_target)._target_met(3600.) is True
    assert runner(core_drifted)._target_met(3600.) is False
    assert runner(ab_drifted)._target_met(3600.) is False


def test_target_not_met_when_temperature_is_unreadable():
    assert runner({}, afterburn=False)._target_met(3100.) is False


# ── _OD_BOUNDS drift ──────────────────────────────────────────────────────────

def test_od_bounds_table_matches_the_bounds_the_model_declares(wet_problem):
    """`_OD_BOUNDS` is hand-maintained alongside the real BalanceComp bounds.

    It exists because ``_state_at_bounds`` needs the numbers without
    introspecting the model, but that makes it a second source of truth: edit
    a bound in engine_model.py's off-design block and the saturation check
    silently starts measuring against the old one. This locks the two
    together until they are unified (#5's follow-on pydantic work).
    """
    prob, _ = wet_problem
    balance = prob.model._get_subsystem('OD.balance')

    def scalar(bound):
        # OpenMDAO stores bounds as length-1 arrays.
        return None if bound is None else _scalar(bound)

    expected = dict(_OD_BOUNDS, **{'balance.FAR_ab': _OD_FAR_AB_BOUNDS})
    for key, (lo, hi) in expected.items():
        meta = balance._var_rel2meta[key.split('.', 1)[1]]
        declared_lo = scalar(meta['lower'])
        declared_hi = scalar(meta['upper'])

        assert (declared_lo, declared_hi) == (lo, hi), (
            f"{key}: engine_model.py declares ({declared_lo}, {declared_hi}) "
            f"but sweep_utils._OD_BOUNDS says ({lo}, {hi})"
        )
