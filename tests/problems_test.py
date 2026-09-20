"""Tests for problem construction: fail-fast validation and golden baselines.

The validation tests are instant — they never build a model. The rest assert
against a converged baseline captured on this branch, so that the solver work
queued behind this suite (#2, #3, #8) has something to regress against.

Golden values are held to a 1e-4 relative tolerance: tight enough that any
real change to the cycle trips them, loose enough to survive last-digit
differences in BLAS/LAPACK across platforms.
"""
import pytest

from F404_pycycle.problems import (
    DRY_DSN_FN,
    DSN_Tt7,
    MIL_Tt4,
    WET_DSN_FN,
    build_dry_problem,
    build_wet_problem,
)
from F404_pycycle.sweep_utils import _scalar

REL = 1e-4

# Converged DESIGN-point baseline, SLS (0 ft, MN 0.01).
# Fn is the balance target, not a result; the rest fall out of the cycle.
DRY_DESIGN = {
    'perf.Fg': 11050.03423243,     # lbf
    'perf.TSFC': 0.62008333,
    'balance.W': 144.18248547,     # lbm/s
    'balance.BPR': 0.75281208,
    'balance.FAR_core': 0.02726298,
    'hpt.PR': 2.64073722,
    'lpt.PR': 2.44776515,
}
WET_DESIGN = {
    'perf.Fg': 17747.57393833,     # lbf
    'perf.TSFC': 1.52447529,
    'balance.W': 137.09271321,     # lbm/s
    'balance.BPR': 0.75281208,
    'balance.FAR_core': 0.02726298,
    'balance.FAR_ab': 0.04153251,
}

# Mechanical spool speeds the engine is sized at (mp_cycle.py input defaults).
DSN_LP_NMECH = 10000.  # rpm
DSN_HP_NMECH = 14000.  # rpm


def assert_matches_baseline(prob, point, baseline):
    for var, expected in baseline.items():
        actual = _scalar(prob.get_val(f'{point}.{var}'))
        assert actual == pytest.approx(expected, rel=REL), (
            f"{point}.{var} drifted: {actual:.8f} vs baseline {expected:.8f}"
        )


# ── Fail-fast validation ──────────────────────────────────────────────────────
# These must raise before the solve, not several minutes into a diverging
# Newton — that is the whole point of validating at all.

@pytest.mark.parametrize('build', [build_dry_problem, build_wet_problem])
@pytest.mark.parametrize('fn_target', [0., -1., -11000.])
def test_non_positive_thrust_target_is_rejected(build, fn_target):
    with pytest.raises(ValueError, match='fn_target'):
        build(fn_target=fn_target)


@pytest.mark.parametrize('build', [build_dry_problem, build_wet_problem])
@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -float('inf')])
def test_non_finite_targets_are_rejected(build, bad):
    # A NaN passes through prob.set_val() and into the residual without
    # complaint, so it surfaces only as an unexplained divergence.
    with pytest.raises(ValueError, match='finite'):
        build(fn_target=bad)


@pytest.mark.parametrize('build', [build_dry_problem, build_wet_problem])
def test_non_positive_burner_temperature_is_rejected(build):
    with pytest.raises(ValueError, match='mil_Tt4'):
        build(mil_Tt4=0.)


@pytest.mark.parametrize('dsn_Tt7', [MIL_Tt4, MIL_Tt4 - 100.])
def test_augmentor_target_below_core_target_is_rejected(dsn_Tt7):
    # The afterburner adds heat downstream of the turbines, so asking for an
    # exit cooler than the core burner's is asking for negative fuel flow.
    with pytest.raises(ValueError, match='dsn_Tt7'):
        build_wet_problem(dsn_Tt7=dsn_Tt7)


def test_validation_errors_name_the_offending_value_and_the_expected_range():
    with pytest.raises(ValueError) as excinfo:
        build_dry_problem(fn_target=-5.)

    message = str(excinfo.value)
    assert '-5.0' in message           # what was passed
    assert 'lbf' in message            # the units it was read as
    assert str(int(DRY_DSN_FN)) in message  # what a sane value looks like


# ── Dry baseline ──────────────────────────────────────────────────────────────

@pytest.mark.slow
def test_dry_design_meets_its_thrust_target(dry_problem):
    prob, _ = dry_problem

    assert _scalar(prob.get_val('DESIGN.perf.Fn', units='lbf')) == pytest.approx(
        DRY_DSN_FN, rel=1e-6)


@pytest.mark.slow
def test_dry_design_matches_baseline(dry_problem):
    prob, _ = dry_problem

    assert_matches_baseline(prob, 'DESIGN', DRY_DESIGN)


@pytest.mark.slow
def test_dry_design_holds_the_commanded_burner_exit_temperature(dry_problem):
    prob, _ = dry_problem

    assert _scalar(prob.get_val('DESIGN.burner.Fl_O:tot:T', units='degR')) == \
        pytest.approx(MIL_Tt4, rel=1e-6)


@pytest.mark.slow
def test_mixer_streams_are_pressure_matched_at_design(dry_problem):
    # The DESIGN BPR balance drives mixer.ER (core Pt / bypass Pt) to 1.0;
    # BPR itself is whatever the thermodynamics require to get there. An ER
    # off 1.0 means that balance did not actually close.
    prob, _ = dry_problem

    assert _scalar(prob.get_val('DESIGN.mixer.ER')) == pytest.approx(1.0, rel=1e-6)


# ── Off-design consistency ────────────────────────────────────────────────────

@pytest.mark.slow
@pytest.mark.parametrize('point_fixture', ['dry_problem', 'wet_problem'])
def test_off_design_reproduces_the_design_point(point_fixture, request):
    """The OD point, run at design conditions, must recover the design solve.

    Both points are set to the same altitude, Mach and power targets, so any
    disagreement means the design-to-off-design handoff — map scalars and
    station areas wired in mp_cycle.py — is dropping something.
    """
    prob, mp = request.getfixturevalue(point_fixture)

    for var in ('perf.Fn', 'perf.TSFC', 'balance.W', 'balance.BPR',
                'balance.FAR_core'):
        design = _scalar(prob.get_val(f'DESIGN.{var}'))
        off_design = _scalar(prob.get_val(f'{mp.od_pt}.{var}'))
        assert off_design == pytest.approx(design, rel=REL), (
            f"{var}: OD {off_design:.8f} != DESIGN {design:.8f} at identical "
            f"conditions"
        )


@pytest.mark.slow
@pytest.mark.parametrize('point_fixture', ['dry_problem', 'wet_problem'])
def test_off_design_spools_return_to_their_design_speeds(point_fixture, request):
    # LP/HP Nmech are fixed inputs at DESIGN and solved-for states at OD, so
    # recovering them is an independent check on the shaft power balances
    # rather than a restatement of the point above.
    prob, mp = request.getfixturevalue(point_fixture)

    assert _scalar(prob.get_val(f'{mp.od_pt}.balance.LP_Nmech', units='rpm')) == \
        pytest.approx(DSN_LP_NMECH, rel=REL)
    assert _scalar(prob.get_val(f'{mp.od_pt}.balance.HP_Nmech', units='rpm')) == \
        pytest.approx(DSN_HP_NMECH, rel=REL)


# ── Wet baseline ──────────────────────────────────────────────────────────────

@pytest.mark.slow
def test_wet_design_meets_its_thrust_target(wet_problem):
    prob, _ = wet_problem

    assert _scalar(prob.get_val('DESIGN.perf.Fn', units='lbf')) == pytest.approx(
        WET_DSN_FN, rel=1e-6)


@pytest.mark.slow
def test_wet_design_matches_baseline(wet_problem):
    prob, _ = wet_problem

    assert_matches_baseline(prob, 'DESIGN', WET_DESIGN)


@pytest.mark.slow
def test_wet_design_is_anchored_at_max_augmentor_temperature(wet_problem):
    # Sizing at max AB rather than an arbitrary mid-AB point is the reason
    # the wet DESIGN exists; a drifted T7 here silently resizes the engine.
    prob, _ = wet_problem

    assert _scalar(prob.get_val('DESIGN.afterburner.Fl_O:tot:T', units='degR')) \
        == pytest.approx(DSN_Tt7, rel=1e-6)


@pytest.mark.slow
def test_augmentor_burns_fuel_only_in_wet_mode(dry_problem, wet_problem):
    dry_prob, _ = dry_problem
    wet_prob, _ = wet_problem

    assert _scalar(wet_prob.get_val('DESIGN.balance.FAR_ab')) > 0.
    # Dry mode replaces the Combustor with a Duct, so the balance is absent
    # entirely rather than present and zeroed.
    with pytest.raises(Exception):
        dry_prob.get_val('DESIGN.balance.FAR_ab')


@pytest.mark.slow
def test_afterburner_roughly_doubles_specific_fuel_consumption(dry_problem,
                                                               wet_problem):
    # A coarse physical sanity check independent of the golden numbers: max
    # AB should cost far more fuel per pound of thrust than mil power.
    dry_prob, _ = dry_problem
    wet_prob, _ = wet_problem

    dry_tsfc = _scalar(dry_prob.get_val('DESIGN.perf.TSFC'))
    wet_tsfc = _scalar(wet_prob.get_val('DESIGN.perf.TSFC'))

    assert wet_tsfc > 2 * dry_tsfc


# ── Dry/wet sizing divergence (#2) ────────────────────────────────────────────

@pytest.mark.slow
def test_dry_and_wet_agree_on_everything_except_size(dry_problem, wet_problem):
    # The two DESIGN solves produce the same cycle — same pressure ratios,
    # same Tt4 target, same bypass ratio — and differ only in how much air
    # they push through it. That is the contract #2 is scoped against: the
    # divergence is one of scale, not of cycle definition.
    dry_prob, _ = dry_problem
    wet_prob, _ = wet_problem

    for shared in ('balance.BPR', 'balance.FAR_core', 'fan.PR', 'hpc.PR'):
        assert _scalar(dry_prob.get_val(f'DESIGN.{shared}')) == pytest.approx(
            _scalar(wet_prob.get_val(f'DESIGN.{shared}')), rel=REL)


@pytest.mark.slow
@pytest.mark.xfail(strict=True, reason=(
    "Dry and wet each run their own DESIGN solve, so they size two engines "
    "rather than one — https://github.com/Jhawk414/F404/issues/2. Asserted as "
    "the behaviour we want, so that fixing #2 turns this XFAIL into an XPASS "
    "and fails the suite until the marker is removed."
))
def test_dry_and_wet_size_the_same_engine(dry_problem, wet_problem):
    dry_prob, _ = dry_problem
    wet_prob, _ = wet_problem

    assert _scalar(dry_prob.get_val('DESIGN.balance.W', units='lbm/s')) == \
        pytest.approx(
            _scalar(wet_prob.get_val('DESIGN.balance.W', units='lbm/s')),
            rel=REL)


# ── Off-nominal sizing ────────────────────────────────────────────────────────

@pytest.mark.slow
def test_a_lower_thrust_target_sizes_a_smaller_engine():
    # Confirms fn_target is actually wired to the sizing balance rather than
    # only being validated — the defaults alone can't show that.
    prob, _ = build_dry_problem(fn_target=DRY_DSN_FN * 0.8, verbose=False)

    assert _scalar(prob.get_val('DESIGN.perf.Fn', units='lbf')) == pytest.approx(
        DRY_DSN_FN * 0.8, rel=1e-6)
    assert _scalar(prob.get_val('DESIGN.balance.W', units='lbm/s')) < \
        DRY_DESIGN['balance.W']
    # Mass flow scales with thrust; the cycle itself is unchanged.
    assert _scalar(prob.get_val('DESIGN.balance.BPR')) == pytest.approx(
        DRY_DESIGN['balance.BPR'], rel=REL)
