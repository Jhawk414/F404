"""Tests for problem construction: fail-fast validation and golden baselines.

Input validation lives in ``DesignInputs`` (config_test.py). Most tests here
assert against a converged baseline, so that the solver work queued behind this suite
(#3, #8) has something to regress against.

Golden values are held to a 1e-4 relative tolerance: tight enough that any
real change to the cycle trips them, loose enough to survive last-digit
differences in BLAS/LAPACK across platforms.
"""
import openmdao.api as om
import pytest

from f404.mp_cycle import MPMixedFlowTurbofan
from f404.problems import (
    DRY_DSN_FN,
    DSN_MN,
    MAX_AB_FN,
    MAX_Tt7,
    MIL_Tt4,
    DESIGN_INPUT_PATHS,
    DesignInputs,
    MaxTt7TooLowError,
    PlaSchedule,
    _apply_design_inputs,
    design,
)
from f404.sweep_utils import STATIC_MN, _scalar

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


# ── Max-AB target ─────────────────────────────────────────────────────────────

@pytest.mark.slow
def test_augmentor_target_below_core_temperature_still_burns_fuel():
    # The augmentor heats mixed flow at ~1500 R, downstream of the turbines,
    # so T7 below Tt4 is a valid min-AB setting, not negative fuel flow. The
    # default wet grid bottoms out at 3008 R, below MIL_Tt4.
    engine = design(DesignInputs(max_Tt7=MIL_Tt4 - 92.))
    prob, mp = engine.prob, engine.prob.model

    assert _scalar(prob.get_val(f"{mp.od_pt}.balance.FAR_ab")) > 1e-3


@pytest.mark.slow
@pytest.mark.parametrize('max_Tt7', [1000., 1500.])
def test_max_ab_target_at_or_below_the_augmentor_inlet_is_rejected(max_Tt7):
    # The OD point reads any Tt7 command at or below Tt6 (~1502 R at SLS mil)
    # as dry. design() promises max AB, so it must raise rather than
    # hand back a dry engine with no error.
    with pytest.raises(MaxTt7TooLowError, match=r'max_Tt7 must exceed .* Tt6 = 150\d\.\d R'):
        design(DesignInputs(max_Tt7=max_Tt7))


def test_design_is_sized_at_the_sweeps_static_mach():
    # #37: sizing at MN 0.01 while the sweeps' static runs at 0.001 left SLS
    # dry mil making 11,045 lbf against the 11,000 lbf target.
    assert DSN_MN == STATIC_MN


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

def test_every_design_input_reaches_the_model():
    # Each field must land on its model path, not stop at the config object
    # (#47). max_Tt7 is the OD max-AB command, set by design() after the dry solve.
    assert set(DESIGN_INPUT_PATHS) == set(DesignInputs.model_fields) - {'max_Tt7'}
    defaults = DesignInputs()
    inputs = DesignInputs(**{f: getattr(defaults, f) * 0.99 for f in DESIGN_INPUT_PATHS})
    prob = om.Problem(reports=False)
    prob.model = MPMixedFlowTurbofan()
    prob.setup()
    _apply_design_inputs(prob, inputs)
    prob.final_setup()

    for field, (path, units) in DESIGN_INPUT_PATHS.items():
        assert _scalar(prob.get_val(path, units=units)) == getattr(inputs, field), field


@pytest.mark.slow
def test_every_design_input_moves_the_solved_engine(problem):
    # Landing on its path isn't enough: hp_shaft.HPX did, and the shaft
    # balances never read it (#60). One linear solve gives every field's
    # total derivative on outputs that DESIGN and OD sizing set.
    prob, _ = problem
    of = ['DESIGN.perf.TSFC', 'DESIGN.balance.W', 'DESIGN.balance.BPR',
          'OD.perf.Fn', 'OD.balance.LP_Nmech', 'OD.balance.HP_Nmech']
    totals = prob.compute_totals(of=of, wrt=[p for p, _ in DESIGN_INPUT_PATHS.values()])

    for field, (path, _) in DESIGN_INPUT_PATHS.items():
        assert any(abs(totals[o, path]).max() > 1e-6 for o in of), field


@pytest.mark.parametrize('inputs', [
    {'fan_eff': 1.05},
    DesignInputs().model_copy(update={'fan_eff': 1.05}),   # copy skips validation
])
def test_design_validates_its_inputs_before_building_anything(inputs):
    with pytest.raises(ValueError, match='fan_eff'):
        design(inputs)


@pytest.mark.parametrize('schedules, match', [
    (PlaSchedule(idle_Tt4=3100.0), 'idle_Tt4'),
    (PlaSchedule(min_ab_Tt7=3700.0), 'min_ab_Tt7'),
])
def test_pla_sweep_validates_schedule_temperatures_before_solving(schedules, match):
    from f404.problems import Engine
    from f404.sweep_full_envelope import sweep
    stub = Engine(prob=None, inputs=DesignInputs(), anchor=None, ps_guesses=(),
                  schedules=schedules)
    with pytest.raises(ValueError, match=match):
        sweep(stub, pla=[87.0])


@pytest.mark.slow
def test_design_allows_valid_temperature_only_engine_below_default_min_ab_tt7():
    eng = design(DesignInputs(max_Tt7=1800.0))
    assert eng.inputs.max_Tt7 == 1800.0


@pytest.mark.slow
def test_non_default_component_inputs_size_a_different_engine():
    prob = design(DesignInputs(hpc_PR=7.0, hpc_cool1_frac_W=0.04)).prob

    assert _scalar(prob.get_val('DESIGN.hpc.PR')) == 7.0
    assert _scalar(prob.get_val('DESIGN.perf.TSFC')) != pytest.approx(
        DRY_DESIGN['perf.TSFC'], rel=1e-3)


@pytest.mark.slow
def test_a_lower_thrust_target_sizes_a_smaller_engine():
    # Confirms fn_target is actually wired to the sizing balance rather than
    # only being validated — the defaults alone can't show that.
    prob = design(DesignInputs(fn_target=DRY_DSN_FN * 0.8)).prob

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
    # verbose=True is what `f404 design` relies on. Every other test runs
    # quiet, so without this the print path — which asks the DESIGN
    # afterburner (a Duct) for a burner table — went unexercised.
    design(verbose=True)

    out = capsys.readouterr().out
    assert all(s in out for s in ('DESIGN', 'OD at SLS mil', 'OD at SLS max AB'))
