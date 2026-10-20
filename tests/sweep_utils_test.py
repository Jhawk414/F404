"""Unit tests for the sweep infrastructure.

Everything here runs without an ``om.Problem``: the grid builders are pure
functions, and ``SweepRunner``'s convergence guards only read scalars off the
problem, so a stub standing in for it exercises them in milliseconds. That
matters because those guards are the regression surface — they are what
distinguishes a real solution from a bound-clipped one that Newton is willing
to call converged.
"""
import pytest

from f404.problems import build_problem
from f404.sweep_utils import (
    DECK_COLUMNS,
    FAILURE_COLUMN,
    INPUT_COLUMNS,
    STATIC_MN,
    SweepConfigurationError,
    _BOUND_TOL_FRAC,
    _OD_BOUNDS,
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
    ``_target_met`` calls ``get_val``. A missing key raises rather than
    returning a default, so the two guards' different responses to an
    unreadable variable are exercised honestly: ``_state_at_bounds`` raises
    (fail closed on a drifted bounds table), ``_target_met`` rejects the
    point (fail closed on an unverifiable target).
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


def test_snake_sweep_defaults_to_static_mach():
    assert {p['MN'] for p in build_snake_sweep([0, 2500], [0., 10.], [3100.])} == {STATIC_MN}


def test_snake_sweep_reverses_the_flight_block_on_alternating_machs():
    # Mach sits between power and altitude. Each Mach step walks the
    # altitude/dTs block back the way it came, so the points either side of
    # a Mach step share alt and dTs; a new power level restarts at the first
    # Mach.
    machs = [STATIC_MN, 0.2, 0.4]
    one = build_snake_sweep([0, 2500], [0., 10.], [3100.])
    sweep = build_snake_sweep([0, 2500], [0., 10.], [3100., 2900.], machs)

    flight = [(p['alt'], p['dTs']) for p in one]
    assert [(p['alt'], p['dTs']) for p in sweep[:12]] == flight + flight[::-1] + flight
    assert [p['MN'] for p in sweep[:12]] == [m for m in machs for _ in range(4)]
    assert sweep[12]['MN'] == STATIC_MN and sweep[12]['power'] == 2900.
    for a, b in zip(sweep[3:12:4], sweep[4:12:4]):
        assert (a['alt'], a['dTs']) == (b['alt'], b['dTs'])


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


def test_bridge_points_interpolate_flight_mach():
    bridges = generate_bridge_points({'MN': 0.95, 'alt': 0., 'dTs': 0., 'power': 2900.},
                                     {'MN': 0.001, 'alt': 0., 'dTs': 0., 'power': 2700.}, 1)

    assert bridges == [pytest.approx({'MN': 0.4755, 'alt': 0., 'dTs': 0., 'power': 2800.})]


def test_bridge_points_empty_when_no_steps_requested():
    pt = {'alt': 0., 'dTs': 0., 'power': 3100.}

    assert generate_bridge_points(pt, pt, n_steps=0) == []


# ── extract_od_results ────────────────────────────────────────────────────────

def _results_state(**overrides):
    # Every column the deck reads, at a distinct value, then the overrides.
    state = {f'{OD}.{spec[0]}': float(i)
             for i, spec in enumerate(DECK_COLUMNS.values()) if spec}
    state.update({
        f'{OD}.fan.PR': 4.1, f'{OD}.hpc.PR': 6.5,
        f'{OD}.burner.Wfuel': 2.42, f'{OD}.afterburner.Wfuel': 4.1,
        f'{OD}.mixed_nozz.Throat:stat:area': 380.,
    })
    state.update(overrides)
    return state


def test_extract_od_results_derives_opr_from_the_two_compressors():
    # There is no LPC in the F404, so OPR is exactly fan PR x HPC PR.
    row = extract_od_results(StubProblem(_results_state()), OD)

    assert row['OPR'] == pytest.approx(4.1 * 6.5)


def test_extract_od_results_reports_fuel_flows_and_nozzle_throat():
    row = extract_od_results(StubProblem(_results_state()), OD)

    assert (row['Wf_core'], row['Wf_ab'], row['A8']) == (2.42, 4.1, 380.)


def test_extract_od_results_follows_the_deck_schema():
    row = extract_od_results(StubProblem(_results_state()), OD)

    assert list(row) == list(DECK_COLUMNS)
    assert all(type(v) is float for v in row.values())


def test_deck_leads_with_the_inputs_then_the_original_performance_columns():
    # Inputs first, so a failed point's row still says what was asked (#27).
    assert INPUT_COLUMNS == ['mode', 'converged', 'alt', 'dTs', 'MN',
                             'T4_cmd', 'T7_cmd']
    assert list(DECK_COLUMNS)[:19] == [
        'Fn', 'Fg', 'TSFC', 'W', 'BPR', 'FAR_core', 'FAR_ab',
        'OPR', 'fan_PR', 'hpc_PR', 'hpt_PR', 'lpt_PR', 'T4', 'T7',
        'LP_Nmech', 'HP_Nmech', 'Wf_core', 'Wf_ab', 'A8']


# ── SweepRunner._state_at_bounds ──────────────────────────────────────────────
# Regression net for the false-convergence class of bug: Newton reports
# success while a BalanceComp state sits clipped at a bound, which is a
# residual minimum but not a solution.

def test_clean_state_is_not_flagged_as_bound_saturated():
    assert runner(CLEAN_STATE)._state_at_bounds() is None


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

    assert runner(state)._state_at_bounds() == state_var


@pytest.mark.parametrize('afterburn', [False, True])
def test_far_ab_on_its_zero_lower_bound_is_the_dry_solution(afterburn):
    # When dry, the FAR_ab root sits on its lower bound of exactly 0. That is
    # not saturation. A wet point pinned there misses its Tt7 target instead,
    # and _target_met catches it.
    state = dict(CLEAN_STATE, **{f'{OD}.balance.FAR_ab': 0.})

    assert runner(state, afterburn=afterburn)._state_at_bounds() is None


def test_an_unreadable_state_is_an_error_not_a_free_pass():
    # If _OD_BOUNDS drifts from the balances engine_model.py declares, the
    # affected state must stop being checked *loudly*. Skipping it would
    # retire this guard for that state with no symptom — a bound-clipped
    # solution would sail through as converged, which is the precise failure
    # the guard exists to catch.
    state = {k: v for k, v in CLEAN_STATE.items() if 'LP_Nmech' not in k}

    with pytest.raises(SweepConfigurationError, match='LP_Nmech'):
        runner(state)._state_at_bounds()


def test_the_unreadable_state_error_says_where_to_look():
    with pytest.raises(SweepConfigurationError) as excinfo:
        runner({})._state_at_bounds()

    message = str(excinfo.value)
    assert '_OD_BOUNDS' in message
    assert 'engine_model.py' in message


def test_bound_tolerance_is_a_fraction_of_the_bound_width():
    # W spans 25-200 lbm/s, so the 1% band is 1.75 lbm/s wide: 197.0 is a
    # legitimate high-flow solution, 198.5 is saturated.
    width = _OD_BOUNDS['balance.W'][1] - _OD_BOUNDS['balance.W'][0]
    assert width * _BOUND_TOL_FRAC == pytest.approx(1.75)

    assert runner(dict(CLEAN_STATE, **{f'{OD}.balance.W': 197.0}))._state_at_bounds() is None
    assert runner(dict(CLEAN_STATE, **{f'{OD}.balance.W': 198.5}))._state_at_bounds() == 'balance.W'


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

def test_od_bounds_table_matches_the_bounds_the_model_declares(problem):
    """`_OD_BOUNDS` is hand-maintained alongside the real BalanceComp bounds.

    It exists because ``_state_at_bounds`` needs the numbers without
    introspecting the model, but that makes it a second source of truth: edit
    a bound in engine_model.py's off-design block and the saturation check
    silently starts measuring against the old one. This locks the two
    together until they are unified (#5's follow-on pydantic work).
    """
    prob, mp = problem

    def scalar(bound):
        # OpenMDAO stores bounds as length-1 arrays.
        return None if bound is None else _scalar(bound)

    for key, (lo, hi) in _OD_BOUNDS.items():
        comp, var = key.split('.', 1)
        owner = prob.model._get_subsystem(f"{mp.od_pt}.{comp}")
        meta = owner._var_rel2meta[var]
        declared_lo = scalar(meta['lower'])
        declared_hi = scalar(meta['upper'])

        # None for FAR_ab's lower bound means "not checked", not "unbounded".
        if lo is None:
            declared_lo = None
        assert (declared_lo, declared_hi) == (lo, hi), (
            f"{key}: engine_model.py declares ({declared_lo}, {declared_hi}) "
            f"but sweep_utils._OD_BOUNDS says ({lo}, {hi})"
        )


# ── End to end ────────────────────────────────────────────────────────────────

def dry_point(mp):
    """SweepRunner kwargs that drive the OD point dry."""
    return dict(od_pt=mp.od_pt)


@pytest.mark.slow
def test_a_short_dry_sweep_converges_and_returns_a_deck_frame():
    """Drives the real loop — solve, guard, extract, collect — on 3 points.

    Builds its own problem because running a sweep mutates OD solver state.
    Three points at conditions the deck already covers (SLS, dTs >= 0), so
    this asserts the machinery works, not that the hard corners converge —
    those are #3.
    """
    prob, mp = build_problem(verbose=False)
    prob.set_solver_print(level=-1)
    points = build_snake_sweep([0.], [0., 10., 20.], [3100.])

    runner = SweepRunner(prob, **dry_point(mp), afterburn=False)
    deck = runner.run_sweep(points)

    assert deck['converged'].all(), "a nominal SLS sweep should fully converge"
    assert list(deck['dTs']) == [0., 10., 20.]
    assert list(deck['T4_cmd']) == [3100.] * 3
    assert (deck['mode'] == 'dry').all() and (deck['T7_cmd'] == 0.).all()
    assert deck[FAILURE_COLUMN].isna().all()
    # Every row carries the full schema, and the guards passed on each.
    assert list(deck.columns) == (INPUT_COLUMNS + list(extract_od_results(prob, mp.od_pt))
                                  + [FAILURE_COLUMN])
    assert (deck['T4'] - 3100.).abs().max() <= _TARGET_TOL_DEGR
    # build_problem() leaves OD at max AB; a dry sweep puts the AB out.
    assert deck['Wf_ab'].abs().max() < 1e-9
    assert (deck['T7'] - deck['Tt6']).abs().max() < 1e-3   # Newton tolerance, R
    # A hotter day thins the air, so the sized engine swallows less of it.
    assert deck['W'].is_monotonic_decreasing
    assert deck['Fn'].is_monotonic_decreasing


@pytest.mark.slow
def test_a_sweep_point_that_cannot_converge_is_recorded_as_failed():
    """An unreachable power target gets a failed row, not a corrupt or aborted deck.

    Two failure modes in one test. The row must not carry
    whatever state Newton stalled in — the bug class this suite exists for —
    and run_sweep must return normally rather than propagating, since a real
    sweep is hundreds of points and losing all of them to one bad corner is
    its own kind of failure. How the point fails is platform-dependent: it
    may exhaust Newton (AnalysisError) or collapse the Jacobian underneath it
    (RuntimeError from the linear solve).
    """
    prob, mp = build_problem(verbose=False)
    prob.set_solver_print(level=-1)
    # 800 degR is below the compressor discharge temperature, so the burner
    # would have to remove heat — FAR_core pins at its 1e-4 floor.
    points = build_snake_sweep([0.], [0.], [800.])

    deck = SweepRunner(prob, **dry_point(mp),
                       afterburn=False).run_sweep(points)

    row = deck.iloc[0]
    assert len(deck) == 1 and not row['converged']
    assert (row['alt'], row['dTs'], row['T4_cmd']) == (0., 0., 800.)
    assert deck[list(DECK_COLUMNS)].isna().all(axis=None)
    assert row[FAILURE_COLUMN]


@pytest.mark.slow
def test_a_failed_point_does_not_abandon_the_rest_of_the_sweep():
    # The failure is deliberately placed first, so the two points after it
    # only converge if the sweep survived it. Every attempted point has a row.
    prob, mp = build_problem(verbose=False)
    prob.set_solver_print(level=-1)
    points = (build_snake_sweep([0.], [0.], [800.])
              + build_snake_sweep([0.], [0., 10.], [3100.]))

    deck = SweepRunner(prob, **dry_point(mp),
                       afterburn=False).run_sweep(points)

    assert list(deck['converged']) == [False, True, True]
    assert list(deck['T4_cmd']) == [800., 3100., 3100.]


@pytest.mark.slow
def test_an_unexpected_error_aborts_the_sweep_rather_than_failing_a_point():
    """Only solver failures are absorbed; everything else must surface.

    _run_point swallows AnalysisError and RuntimeError so that one hard
    corner can't cost a multi-hour sweep. That tolerance must not extend to
    the error types a mistake produces — a typo'd variable or a drifted
    bounds table reaching the caller as "264 points failed" would hide the
    cause completely.
    """
    prob, mp = build_problem(verbose=False)
    prob.set_solver_print(level=-1)
    runner = SweepRunner(prob, **dry_point(mp), afterburn=False)

    def exploding_run_model():
        raise KeyError("OD.balance.typo")

    prob.run_model = exploding_run_model

    with pytest.raises(KeyError, match='typo'):
        runner.run_sweep(build_snake_sweep([0.], [0.], [3100.]))


@pytest.mark.slow
def test_a_drifted_bounds_table_aborts_the_sweep():
    # SweepConfigurationError is deliberately not a RuntimeError, so it
    # travels through _run_point's except clause instead of being recorded
    # as an ordinary failed point.
    prob, mp = build_problem(verbose=False)
    prob.set_solver_print(level=-1)
    runner = SweepRunner(prob, **dry_point(mp), afterburn=False)

    with pytest.raises(SweepConfigurationError, match='balance.nonexistent'):
        with_drift = dict(_OD_BOUNDS, **{'balance.nonexistent': (0., 1.)})
        import f404.sweep_utils as su
        original, su._OD_BOUNDS = su._OD_BOUNDS, with_drift
        try:
            runner.run_sweep(build_snake_sweep([0.], [0.], [3100.]))
        finally:
            su._OD_BOUNDS = original
