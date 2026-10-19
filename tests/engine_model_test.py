"""Structural tests for the single-point cycle.

No solving here — these build the model and inspect what got wired, which
is enough to lock in the structural decisions that were paid for in
debugging time and are easy to undo by accident. Each runs in milliseconds.
"""
import openmdao.api as om
import pycycle.api as pyc
import pytest
from openmdao.utils.assert_utils import assert_check_partials

from f404.engine_model import AugmentorControl, MixedFlowTurbofan, NozzleSchedule
from f404.sweep_utils import _scalar

DESIGN_BALANCES = {'W', 'BPR', 'FAR_core', 'hpt_PR', 'lpt_PR'}
OD_BALANCES = {'W', 'BPR', 'FAR_core', 'LP_Nmech', 'HP_Nmech'}


@pytest.fixture
def cycle():
    """Build (but don't solve) a DESIGN or off-design cycle."""
    def build(design=True):
        prob = om.Problem()
        prob.model = MixedFlowTurbofan(design=design, thermo_method='TABULAR')
        prob.setup()
        return prob.model
    return build


# ── Afterburner ───────────────────────────────────────────────────────────────

def test_design_uses_a_duct_for_the_afterburner(cycle):
    """Regression on 51c9bb6.

    A Combustor with its FAR *fixed* at zero is rank-deficient — every output
    equation collapses to a copy of its input — which crashed the OD linear
    solve at part-power dry conditions. DESIGN never lights, so it keeps a
    Duct; the OD Combustor gets a FAR_ab balance with a zero lower bound.
    """
    model = cycle(design=True)

    assert isinstance(model._get_subsystem('afterburner'), pyc.Duct)


def test_off_design_uses_a_combustor_for_the_afterburner(cycle):
    # One OD topology from dry to max AB (ADR-0002): when dry, the same
    # Combustor burns no fuel.
    model = cycle(design=False)

    assert isinstance(model._get_subsystem('afterburner'), pyc.Combustor)


@pytest.mark.parametrize('design, n_burners', [(True, 1), (False, 2)])
def test_performance_counts_only_the_burners_that_burn(cycle, design, n_burners):
    # DESIGN's Duct produces no Wfuel, so a Performance expecting two fuel
    # flows would be left with an unconnected input.
    model = cycle(design=design)

    assert model._get_subsystem('perf').options['num_burners'] == n_burners


# ── Balance sets ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize('design, expected', [(True, DESIGN_BALANCES),
                                              (False, OD_BALANCES | {'FAR_ab'})])
def test_balance_set_matches_the_point_type(cycle, design, expected):
    # At DESIGN the turbine pressure ratios are solved and the spool speeds
    # are given; off-design it is the other way round. Mixing the two up
    # produces a model that is over- or under-determined.
    model = cycle(design=design)

    assert set(model._get_subsystem('balance')._state_vars) == expected


def test_far_ab_balance_reaches_zero_and_targets_the_augmentor_command(cycle):
    # When dry, aug_ctrl targets the augmentor inlet temperature, and the root
    # is FAR_ab = 0 exactly, on the bound.
    model = cycle(design=False)
    meta = model._get_subsystem('balance')._var_rel2meta['FAR_ab']

    assert _scalar(meta['lower']) == 0.
    assert model._conn_global_abs_in2out['balance.rhs:FAR_ab'] == 'aug_ctrl.Tt7'


@pytest.mark.parametrize('design', [True, False])
def test_both_points_take_the_augmentor_loss_from_aug_ctrl(cycle, design):
    model = cycle(design=design)

    assert model._conn_global_abs_in2out['afterburner.p_loss.dPqP'] == 'aug_ctrl.dPqP'


@pytest.mark.parametrize('design, expected', [(False, True), (True, False)])
def test_only_off_design_schedules_the_nozzle_throat(cycle, design, expected):
    # DESIGN computes A8. OD scales it explicitly, with no Newton state.
    model = cycle(design=design)
    names = {s.name for s in model._subsystems_myproc}

    assert ('a8_sched' in names) is expected
    assert 'a8_ctrl' not in names
    if not design:
        assert model._conn_global_abs_in2out['balance.rhs:W'] == 'a8_sched.A8'


# ── Augmentor control and nozzle schedule ─────────────────────────────────────

def solve_component(comp, **inputs):
    prob = om.Problem()
    prob.model.add_subsystem('c', comp, promotes=['*'])
    prob.setup(force_alloc_complex=True)
    for name, value in inputs.items():
        prob.set_val(name, value)
    prob.run_model()
    return prob


def augmentor(**inputs):
    return solve_component(AugmentorControl(),
                           **{'Tt_in': 1500., 'MN_in': 0.446, 'gamma_in': 1.341, **inputs})


def kumar_q(g, m):
    return g / 2 * m**2 * (1 + (g - 1) / 2 * m**2) ** (-g / (g - 1))


def test_dry_augmentor_targets_its_inlet_and_carries_only_the_flameholder_loss():
    prob = augmentor(Tt7_cmd=0.)

    assert prob['Tt7'] == 1500.          # FAR_ab balance target = inlet
    assert prob['dPqP'] == pytest.approx(0.65 * kumar_q(1.341, 0.5 * 0.446))
    assert prob['dPqP'] == prob['dPqP_dry']


def test_flameholder_loss_is_about_two_percent_at_the_design_augmentor_inlet():
    # k_M * MN6 = 0.22, the RM12 rig's flameholder approach Mach, with
    # C_D 0.65 gives the 1-3% cold loss of the NASA flameholder rigs (#33).
    assert augmentor()['dPqP_dry'] == pytest.approx(0.021, abs=5e-4)


def test_lit_augmentor_adds_a_rayleigh_loss_proportional_to_heat_addition():
    prob = augmentor(Tt7_cmd=3600.)
    q = kumar_q(1.341, 0.5 * 0.446)

    assert prob['Tt7'] == 3600.
    assert prob['dPqP'] == pytest.approx(q * (0.65 + 1.0 * (3600. / 1500. - 1.)))
    assert prob['dPqP_dry'] == pytest.approx(q * 0.65)


@pytest.mark.filterwarnings('ignore::openmdao.utils.om_warnings.DerivativesWarning')
@pytest.mark.parametrize('Tt7_cmd', [0., 1500.5, 3600.])
def test_augmentor_partials_match_complex_step(Tt7_cmd):
    # The max() makes half the Tt7 partials zero on each side of light-off.
    prob = augmentor(Tt7_cmd=Tt7_cmd)

    assert_check_partials(prob.check_partials(method='cs', out_stream=None))


NOZZLE_DRY = dict(A8_dsn=187.75, W_in=144., W_out=144., Tt_in=1502., Tt_out=1502.,
                    R_in=53.35, R_out=53.35, gam_in=1.341, gam_out=1.341,
                    dPqP=0.021, dPqP_dry=0.021)
NOZZLE_WET = {**NOZZLE_DRY, 'W_out': 149.4, 'Tt_out': 3600., 'R_out': 53.4,
              'gam_out': 1.27, 'dPqP': 0.065}


def test_dry_nozzle_is_the_design_throat():
    assert solve_component(NozzleSchedule(), **NOZZLE_DRY)['A8'] == \
        pytest.approx(187.75, rel=1e-12)


def test_lit_nozzle_opens_to_pass_the_hotter_flow_at_the_same_pt6():
    # Roughly √(Tt7/Tt6) for the temperature, times the fuel mass, the loss
    # and the γ change: about 1.7x the dry throat at max AB.
    a8 = solve_component(NozzleSchedule(), **NOZZLE_WET)['A8']

    assert 1.6 * 187.75 < a8 < 1.8 * 187.75


@pytest.mark.parametrize('inputs', [NOZZLE_DRY, NOZZLE_WET], ids=['dry', 'wet'])
def test_nozzle_partials_match_complex_step(inputs):
    prob = solve_component(NozzleSchedule(), **inputs)

    assert_check_partials(prob.check_partials(method='cs', out_stream=None))


# ── Solver configuration ──────────────────────────────────────────────────────

def test_newton_raises_rather_than_returning_an_unconverged_state(cycle):
    """Regression on the false-convergence bug fixed in 51c9bb6.

    With err_on_non_converge off, Newton silently returns whatever
    bound-clipped or stalled state it landed in, and the sweep writes it to
    the deck as a converged row. That produced decks with Fn > 100,000 lbf.
    SweepRunner's guards are the second line of defence; this is the first.
    """
    model = cycle()

    assert model.nonlinear_solver.options['err_on_non_converge'] is True


def test_linesearch_defaults_to_no_backtracking(cycle):
    # ArmijoGoldsteinLS at maxiter=0 behaves like BoundsEnforceLS, skipping
    # Armijo's cost on the ~95% of points that converge without it.
    # SweepRunner raises maxiter only on a per-point retry.
    model = cycle()
    linesearch = model.nonlinear_solver.linesearch

    assert isinstance(linesearch, om.ArmijoGoldsteinLS)
    assert linesearch.options['maxiter'] == 0
    assert linesearch.options['bound_enforcement'] == 'scalar'


# ── F404 architecture ─────────────────────────────────────────────────────────

def test_no_low_pressure_compressor_in_the_flow_path(cycle):
    # The F404's LP spool is fan + LPT only. A stray LPC would change OPR
    # and quietly invalidate the whole deck.
    names = {s.name for s in cycle()._subsystems_myproc}

    assert 'lpc' not in names
    assert {'fan', 'hpc', 'burner', 'hpt', 'lpt', 'mixer', 'mixed_nozz'} <= names


def test_lp_shaft_carries_only_the_fan_and_the_lp_turbine(cycle):
    # num_ports must match the LPC-less architecture above: an extra port
    # would leave an unconnected torque input summing into the power balance.
    model = cycle()

    assert model._get_subsystem('lp_shaft').options['num_ports'] == 2
    assert model._get_subsystem('hp_shaft').options['num_ports'] == 2


def test_both_cooling_bleeds_are_wired_to_their_turbines(cycle):
    # HPC interstage bleed cools the LPT, compressor discharge bleed cools
    # the HPT — losing either changes turbine work and the sizing with it.
    model = cycle()

    assert model._get_subsystem('hpc').options['bleed_names'] == ['cool1']
    assert model._get_subsystem('lpt').options['bleed_names'] == ['cool1']
    assert model._get_subsystem('bld3').options['bleed_names'] == ['cool3']
    assert model._get_subsystem('hpt').options['bleed_names'] == ['cool3']


def test_nozzle_is_convergent_divergent(cycle):
    # A mixed-flow augmented engine needs a CD nozzle to expand max-AB flow;
    # a convergent-only nozzle would cap thrust at the wet design point.
    model = cycle()

    assert model._get_subsystem('mixed_nozz').options['nozzType'] == 'CD'
