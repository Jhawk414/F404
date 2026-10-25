"""Tests for problem construction: fail-fast validation and golden baselines.

The validation tests are instant — they never build a model. The rest assert
against a converged baseline, so that the solver work queued behind this suite
(#3, #8) has something to regress against.

Golden values are held to a 1e-4 relative tolerance: tight enough that any
real change to the cycle trips them, loose enough to survive last-digit
differences in BLAS/LAPACK across platforms.
"""
import pytest

from f404.problems import (
    DRY_DSN_FN,
    MAX_AB_FN,
    MAX_Tt7,
    MIL_Tt4,
    MaxTt7TooLowError,
    build_problem,
)
from f404.sweep_utils import _scalar

REL = 1e-4

# Converged DESIGN-point baseline, SLS (0 ft, MN 0.001), dry mil.
# Fn is the balance target, not a result; the rest fall out of the cycle.
DRY_DESIGN = {
    'perf.Fg': 11005.01451726,     # lbf
    'perf.TSFC': 0.62144387,
    'balance.W': 144.50217961,     # lbm/s
    'balance.BPR': 0.75287320,
    'balance.FAR_core': 0.02726330,
    'hpt.PR': 2.64068934,
    'lpt.PR': 2.44780953,
}
# The same engine at SLS max afterburner (OD at Tt7 = MAX_Tt7). Thrust is
# an output here, not a target.
MAX_AB = {
    'perf.Fg': 17705.02439903,     # lbf
    'perf.TSFC': 1.48094658,
    'balance.W': 144.41428112,     # lbm/s
    'balance.BPR': 0.75119816,
    'balance.FAR_core': 0.02726239,
    'balance.FAR_ab': 0.03726690,
    'a8_sched.A8': 331.39681755,   # in**2
    'afterburner.dPqP': 0.06600499,
}

# Lighting the afterburner moves the gas generator off dry mil by no more
# than this. The nozzle schedule's ideal-gas Γ(γ) leaves 0.24% BPR at SLS.
GAS_GENERATOR_REL = 3e-3

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

@pytest.mark.parametrize('fn_target', [0., -1., -11000.])
def test_non_positive_thrust_target_is_rejected(fn_target):
    with pytest.raises(ValueError, match='fn_target'):
        build_problem(fn_target=fn_target)


@pytest.mark.parametrize('target', ['fn_target', 'mil_Tt4', 'max_Tt7'])
@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -float('inf')])
def test_non_finite_targets_are_rejected(target, bad):
    # A NaN passes through prob.set_val() and into the residual without
    # complaint, so it surfaces only as an unexplained divergence.
    with pytest.raises(ValueError, match='finite'):
        build_problem(**{target: bad})


def test_non_positive_burner_temperature_is_rejected():
    with pytest.raises(ValueError, match='mil_Tt4'):
        build_problem(mil_Tt4=0.)


@pytest.mark.parametrize('max_Tt7', [0., -3608.])
def test_non_positive_augmentor_target_is_rejected(max_Tt7):
    with pytest.raises(ValueError, match='max_Tt7'):
        build_problem(max_Tt7=max_Tt7)


@pytest.mark.slow
def test_augmentor_target_below_core_temperature_still_burns_fuel():
    # The augmentor heats mixed flow at ~1500 R, downstream of the turbines,
    # so T7 below Tt4 is a valid min-AB setting, not negative fuel flow. The
    # default wet grid bottoms out at 3008 R, below MIL_Tt4.
    prob, mp = build_problem(max_Tt7=MIL_Tt4 - 92., verbose=False)

    assert _scalar(prob.get_val(f"{mp.od_pt}.balance.FAR_ab")) > 1e-3


@pytest.mark.slow
@pytest.mark.parametrize('max_Tt7', [1000., 1500.])
def test_max_ab_target_at_or_below_the_augmentor_inlet_is_rejected(max_Tt7):
    # The OD point reads any Tt7 command at or below Tt6 (~1502 R at SLS mil)
    # as dry. build_problem() promises max AB, so it must raise rather than
    # hand back a dry engine with no error.
    with pytest.raises(MaxTt7TooLowError, match=r'max_Tt7 must exceed .* Tt6 = 150\d\.\d R'):
        build_problem(max_Tt7=max_Tt7, verbose=False)


def test_validation_errors_name_the_offending_value_and_the_expected_range():
    with pytest.raises(ValueError) as excinfo:
        build_problem(fn_target=-5.)

    message = str(excinfo.value)
    assert '-5.0' in message           # what was passed
    assert 'lbf' in message            # the units it was read as
    assert str(int(DRY_DSN_FN)) in message  # what a sane value looks like


# ── DESIGN (dry mil) baseline ─────────────────────────────────────────────────

@pytest.mark.slow
def test_design_meets_its_thrust_target(problem):
    prob, _ = problem

    assert _scalar(prob.get_val('DESIGN.perf.Fn', units='lbf')) == pytest.approx(
        DRY_DSN_FN, rel=1e-6)


@pytest.mark.slow
def test_design_matches_baseline(problem):
    prob, _ = problem

    assert_matches_baseline(prob, 'DESIGN', DRY_DESIGN)


@pytest.mark.slow
def test_design_holds_the_commanded_burner_exit_temperature(problem):
    prob, _ = problem

    assert _scalar(prob.get_val('DESIGN.burner.Fl_O:tot:T', units='degR')) == \
        pytest.approx(MIL_Tt4, rel=1e-6)


@pytest.mark.slow
def test_mixer_streams_are_pressure_matched_at_design(problem):
    # The DESIGN BPR balance drives mixer.ER (core Pt / bypass Pt) to 1.0;
    # BPR itself is whatever the thermodynamics require to get there. An ER
    # off 1.0 means that balance did not actually close.
    prob, _ = problem

    assert _scalar(prob.get_val('DESIGN.mixer.ER')) == pytest.approx(1.0, rel=1e-6)


# ── Off-design consistency ────────────────────────────────────────────────────

@pytest.mark.slow
def test_dry_off_design_reproduces_the_design_point(dry_mil):
    """OD, dry at design conditions, must recover the design solve.

    Both points are set to the same altitude, Mach and power targets, so any
    disagreement means the design-to-off-design handoff — map scalars, station
    areas and the augmentor loss wired in mp_cycle.py — is dropping something.
    """
    prob, mp = dry_mil

    for var in ('perf.Fn', 'perf.TSFC', 'balance.W', 'balance.BPR',
                'balance.FAR_core', 'afterburner.dPqP',
                'mixed_nozz.Throat:stat:area'):
        design = _scalar(prob.get_val(f'DESIGN.{var}'))
        off_design = _scalar(prob.get_val(f"{mp.od_pt}.{var}"))
        assert off_design == pytest.approx(design, rel=REL), (
            f"{var}: OD {off_design:.8f} != DESIGN {design:.8f} at identical "
            f"conditions"
        )


@pytest.mark.slow
def test_dry_off_design_spools_return_to_their_design_speeds(dry_mil):
    # LP/HP Nmech are fixed inputs at DESIGN and solved-for states at OD, so
    # recovering them is an independent check on the shaft power balances.
    prob, mp = dry_mil
    pt = mp.od_pt

    assert _scalar(prob.get_val(f'{pt}.balance.LP_Nmech', units='rpm')) == \
        pytest.approx(DSN_LP_NMECH, rel=REL)
    assert _scalar(prob.get_val(f'{pt}.balance.HP_Nmech', units='rpm')) == \
        pytest.approx(DSN_HP_NMECH, rel=REL)


# ── Max afterburner baseline ──────────────────────────────────────────────────

@pytest.mark.slow
def test_max_afterburner_is_calibrated_to_the_wet_thrust_target(problem):
    # MAX_Tt7 is chosen, given the augmentor loss, so that the dry-sized
    # engine makes the F404's SLS max-AB thrust; at 3800 R it overshoots (#2).
    prob, mp = problem

    assert _scalar(prob.get_val(f"{mp.od_pt}.perf.Fn", units='lbf')) == \
        pytest.approx(MAX_AB_FN, rel=REL)


@pytest.mark.slow
def test_augmentor_loss_is_the_flameholder_loss_dry_plus_rayleigh_wet(problem, dry_mil):
    # About 2.1% cold at the design augmentor inlet (also in the DESIGN
    # sizing), about 6.6% at SLS max AB (#33).
    (wet, mp), (dry, _) = problem, dry_mil
    od = mp.od_pt

    cold = _scalar(dry.get_val(f"{od}.afterburner.dPqP"))
    assert cold == pytest.approx(_scalar(dry.get_val(f"{od}.aug_ctrl.dPqP_dry")))
    assert cold == pytest.approx(0.021, abs=5e-4)
    assert _scalar(wet.get_val(f"{od}.afterburner.dPqP")) == pytest.approx(0.066, abs=5e-4)


@pytest.mark.slow
def test_max_afterburner_matches_baseline(problem):
    prob, mp = problem

    assert_matches_baseline(prob, mp.od_pt, MAX_AB)


@pytest.mark.slow
def test_max_afterburner_runs_at_the_commanded_augmentor_temperature(problem):
    # BalanceComp normalises the residual by rhs, so Newton's atol (1e-5)
    # allows ~0.04 R at 3600 R. The warm start from dry mil lands closer.
    prob, mp = problem

    assert _scalar(prob.get_val(f"{mp.od_pt}.afterburner.Fl_O:tot:T",
                                units='degR')) == pytest.approx(MAX_Tt7, abs=0.01)


@pytest.mark.slow
def test_nozzle_schedule_opens_the_throat_for_the_hot_flow(problem):
    # Hot augmented flow needs a bigger nozzle to pass the same gas-generator
    # flow: about 1.7x the DESIGN throat at max AB.
    prob, mp = problem

    assert _scalar(prob.get_val(f'{mp.od_pt}.mixed_nozz.Throat:stat:area')) > \
        1.5 * _scalar(prob.get_val('DESIGN.mixed_nozz.Throat:stat:area'))


@pytest.mark.slow
@pytest.mark.parametrize('var', ['balance.W', 'balance.BPR', 'balance.LP_Nmech',
                                 'balance.HP_Nmech', 'fan.map.RlineMap',
                                 'mixer_duct.Fl_O:tot:P'])
def test_lighting_the_afterburner_leaves_the_gas_generator_where_dry_put_it(
        problem, dry_mil, var):
    # The nozzle schedule's job (#8, wet half): the F404 holds N1 and T5.6
    # through the AB range, so the fan and core should not see light-off.
    (wet, mp), (dry, _) = problem, dry_mil

    assert _scalar(wet.get_val(f'{mp.od_pt}.{var}')) == pytest.approx(
        _scalar(dry.get_val(f'{mp.od_pt}.{var}')), rel=GAS_GENERATOR_REL)


@pytest.mark.slow
def test_augmentor_burns_fuel_only_when_wet(problem, dry_mil):
    (wet, mp), (dry, _) = problem, dry_mil

    assert _scalar(wet.get_val(f"{mp.od_pt}.balance.FAR_ab")) > 0.
    # When dry, the balance root sits on its zero lower bound.
    assert _scalar(dry.get_val(f"{mp.od_pt}.balance.FAR_ab")) == \
        pytest.approx(0., abs=1e-12)


@pytest.mark.slow
def test_dry_nozzle_holds_the_design_throat(dry_mil):
    prob, mp = dry_mil

    assert _scalar(prob.get_val(f"{mp.od_pt}.a8_sched.A8")) == pytest.approx(
        _scalar(prob.get_val('DESIGN.mixed_nozz.Throat:stat:area')), rel=1e-6)


@pytest.mark.slow
def test_afterburner_roughly_doubles_specific_fuel_consumption(problem, dry_mil):
    # A coarse physical sanity check independent of the golden numbers: max
    # AB should cost far more fuel per pound of thrust than mil power.
    (wet, mp), (dry, _) = problem, dry_mil

    dry_tsfc = _scalar(dry.get_val(f"{mp.od_pt}.perf.TSFC"))
    wet_tsfc = _scalar(wet.get_val(f"{mp.od_pt}.perf.TSFC"))

    assert wet_tsfc > 2 * dry_tsfc


# ── Off-nominal sizing ────────────────────────────────────────────────────────

@pytest.mark.slow
def test_a_lower_thrust_target_sizes_a_smaller_engine():
    # Confirms fn_target is actually wired to the sizing balance rather than
    # only being validated — the defaults alone can't show that.
    prob, _ = build_problem(fn_target=DRY_DSN_FN * 0.8, verbose=False)

    assert _scalar(prob.get_val('DESIGN.perf.Fn', units='lbf')) == pytest.approx(
        DRY_DSN_FN * 0.8, rel=1e-6)
    assert _scalar(prob.get_val('DESIGN.balance.W', units='lbm/s')) < \
        DRY_DESIGN['balance.W']
    # Mass flow scales with thrust; the cycle itself is unchanged.
    assert _scalar(prob.get_val('DESIGN.balance.BPR')) == pytest.approx(
        DRY_DESIGN['balance.BPR'], rel=REL)


# ── Verbose path ──────────────────────────────────────────────────────────────

@pytest.mark.slow
def test_verbose_build_prints_every_result_page(capsys):
    # verbose=True is the default and what `f404 design` relies on. Every other
    # test passes verbose=False, so without this the print path — which asks
    # the DESIGN afterburner (a Duct) for a burner table — went unexercised.
    build_problem()

    out = capsys.readouterr().out
    assert all(s in out for s in ('DESIGN', 'OD at SLS mil', 'OD at SLS max AB'))
