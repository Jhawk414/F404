"""Tests for problem construction: fail-fast validation and golden baselines.

The validation tests are instant — they never build a model. The rest assert
against a converged baseline, so that the solver work queued behind this suite
(#3, #8) has something to regress against.

Golden values are held to a 1e-4 relative tolerance: tight enough that any
real change to the cycle trips them, loose enough to survive last-digit
differences in BLAS/LAPACK across platforms.
"""
import pytest

from F404_pycycle.problems import (
    DRY_DSN_FN,
    MAX_Tt7,
    MIL_Tt4,
    build_problem,
)
from F404_pycycle.sweep_utils import _scalar

REL = 1e-4

# Converged DESIGN-point baseline, SLS (0 ft, MN 0.01), dry mil.
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
# The same engine at SLS max afterburner (OD_wet at Tt7 = MAX_Tt7). Thrust is
# an output here, not a target.
MAX_AB = {
    'perf.Fn': 18615.35841749,     # lbf
    'perf.Fg': 18665.39264996,     # lbf
    'perf.TSFC': 1.52447529,
    'balance.W': 144.18248547,     # lbm/s
    'balance.BPR': 0.75281208,
    'balance.FAR_core': 0.02726298,
    'balance.FAR_ab': 0.04153251,
    'a8_ctrl.A8': 319.62694512,    # in**2
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


@pytest.mark.parametrize('max_Tt7', [MIL_Tt4, MIL_Tt4 - 100.])
def test_augmentor_target_below_core_target_is_rejected(max_Tt7):
    # The afterburner adds heat downstream of the turbines, so asking for an
    # exit cooler than the core burner's is asking for negative fuel flow.
    with pytest.raises(ValueError, match='max_Tt7'):
        build_problem(max_Tt7=max_Tt7)


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
def test_dry_off_design_reproduces_the_design_point(problem):
    """OD_dry, run at design conditions, must recover the design solve.

    Both points are set to the same altitude, Mach and power targets, so any
    disagreement means the design-to-off-design handoff — map scalars and
    station areas wired in mp_cycle.py — is dropping something.
    """
    prob, mp = problem

    for var in ('perf.Fn', 'perf.TSFC', 'balance.W', 'balance.BPR',
                'balance.FAR_core'):
        design = _scalar(prob.get_val(f'DESIGN.{var}'))
        off_design = _scalar(prob.get_val(f"{mp.od_pts['dry']}.{var}"))
        assert off_design == pytest.approx(design, rel=REL), (
            f"{var}: OD {off_design:.8f} != DESIGN {design:.8f} at identical "
            f"conditions"
        )


@pytest.mark.slow
@pytest.mark.parametrize('mode', ['dry', 'wet'])
def test_off_design_spools_return_to_their_design_speeds(problem, mode):
    # LP/HP Nmech are fixed inputs at DESIGN and solved-for states at OD, so
    # recovering them is an independent check on the shaft power balances.
    # The wet point recovers them too: its A8 control holds the fan on its
    # design operating line, so lighting the afterburner leaves the gas
    # generator where dry mil put it.
    prob, mp = problem
    pt = mp.od_pts[mode]

    assert _scalar(prob.get_val(f'{pt}.balance.LP_Nmech', units='rpm')) == \
        pytest.approx(DSN_LP_NMECH, rel=REL)
    assert _scalar(prob.get_val(f'{pt}.balance.HP_Nmech', units='rpm')) == \
        pytest.approx(DSN_HP_NMECH, rel=REL)


# ── Max afterburner baseline ──────────────────────────────────────────────────

@pytest.mark.slow
def test_max_afterburner_matches_baseline(problem):
    prob, mp = problem

    assert_matches_baseline(prob, mp.od_pts['wet'], MAX_AB)


@pytest.mark.slow
def test_max_afterburner_runs_at_the_commanded_augmentor_temperature(problem):
    prob, mp = problem

    assert _scalar(prob.get_val(f"{mp.od_pts['wet']}.afterburner.Fl_O:tot:T",
                                units='degR')) == pytest.approx(MAX_Tt7, rel=1e-6)


@pytest.mark.slow
def test_nozzle_control_opens_the_throat_and_holds_the_fan_operating_line(problem):
    # The wet throat is a solved state, not the DESIGN area: hot augmented
    # flow needs a bigger nozzle to pass the same corrected flow.
    prob, mp = problem
    wet = mp.od_pts['wet']

    assert _scalar(prob.get_val(f'{wet}.fan.map.RlineMap')) == pytest.approx(
        2.0, rel=1e-6)
    assert _scalar(prob.get_val(f'{wet}.mixed_nozz.Throat:stat:area')) > \
        1.5 * _scalar(prob.get_val('DESIGN.mixed_nozz.Throat:stat:area'))


@pytest.mark.slow
def test_augmentor_burns_fuel_only_on_the_wet_point(problem):
    prob, mp = problem

    assert _scalar(prob.get_val(f"{mp.od_pts['wet']}.balance.FAR_ab")) > 0.
    # The dry point's afterburner is a Duct, so the balance is absent
    # entirely rather than present and zeroed.
    with pytest.raises(Exception):
        prob.get_val(f"{mp.od_pts['dry']}.balance.FAR_ab")


@pytest.mark.slow
def test_afterburner_roughly_doubles_specific_fuel_consumption(problem):
    # A coarse physical sanity check independent of the golden numbers: max
    # AB should cost far more fuel per pound of thrust than mil power.
    prob, mp = problem

    dry_tsfc = _scalar(prob.get_val(f"{mp.od_pts['dry']}.perf.TSFC"))
    wet_tsfc = _scalar(prob.get_val(f"{mp.od_pts['wet']}.perf.TSFC"))

    assert wet_tsfc > 2 * dry_tsfc


# ── One engine for both modes (#2) ────────────────────────────────────────────

@pytest.mark.slow
def test_dry_and_wet_run_the_same_engine(problem):
    # The fix for #2: both modes take their map scalars and station areas from
    # the one DESIGN point, so at SLS mil and max AB they swallow the same air.
    prob, mp = problem

    assert _scalar(prob.get_val(f"{mp.od_pts['dry']}.balance.W", units='lbm/s')) \
        == pytest.approx(_scalar(prob.get_val(f"{mp.od_pts['wet']}.balance.W",
                                              units='lbm/s')), rel=REL)


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
    # the dry afterburner (a Duct) for a burner table — went unexercised.
    build_problem()

    out = capsys.readouterr().out
    assert all(pt in out for pt in ('DESIGN', 'OD_dry', 'OD_wet'))
