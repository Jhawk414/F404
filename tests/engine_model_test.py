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

DESIGN_BALANCES = {'W', 'BPR', 'FAR_core', 'hpt_PR', 'lpt_PR'}
OD_BALANCES = {'W', 'BPR', 'FAR_core', 'LP_Nmech', 'HP_Nmech'}


@pytest.fixture
def cycle():
    """Build (but don't solve) a cycle at the requested design/afterburn mode."""
    def build(design=True, afterburn=True):
        prob = om.Problem()
        prob.model = MixedFlowTurbofan(design=design, thermo_method='TABULAR',
                                       afterburn=afterburn)
        prob.setup()
        return prob.model
    return build


# ── Afterburner mode ──────────────────────────────────────────────────────────

def test_dry_mode_uses_a_duct_for_the_afterburner(cycle):
    """Regression on 51c9bb6.

    A Combustor with no fuel addition is rank-deficient — every output
    equation collapses to a copy of its input — which crashes the OD linear
    solve at part-power dry conditions. Dry mode has to substitute a Duct,
    not a zero-FAR Combustor.
    """
    model = cycle(afterburn=False)

    assert isinstance(model._get_subsystem('afterburner'), pyc.Duct)


def test_wet_mode_uses_a_combustor_for_the_afterburner(cycle):
    model = cycle(afterburn=True)

    assert isinstance(model._get_subsystem('afterburner'), pyc.Combustor)


@pytest.mark.parametrize('afterburn, n_burners', [(False, 1), (True, 2)])
def test_performance_counts_only_the_burners_that_burn(cycle, afterburn,
                                                       n_burners):
    # Dry mode's Duct produces no Wfuel, so a Performance expecting two fuel
    # flows would be left with an unconnected input.
    model = cycle(afterburn=afterburn)

    assert model._get_subsystem('perf').options['num_burners'] == n_burners


# ── Balance sets ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize('design, expected', [(True, DESIGN_BALANCES),
                                              (False, OD_BALANCES)])
def test_balance_set_matches_the_point_type(cycle, design, expected):
    # At DESIGN the turbine pressure ratios are solved and the spool speeds
    # are given; off-design it is the other way round. Mixing the two up
    # produces a model that is over- or under-determined.
    model = cycle(design=design, afterburn=False)

    assert set(model._get_subsystem('balance')._state_vars) == expected


@pytest.mark.parametrize('design', [True, False])
def test_far_ab_balance_exists_only_in_wet_mode(cycle, design):
    # The balance is structural and can't be toggled after setup, which is
    # why dry and wet run on separate OD points of the one problem.
    wet = cycle(design=design, afterburn=True)
    dry = cycle(design=design, afterburn=False)

    assert 'FAR_ab' in wet._get_subsystem('balance')._state_vars
    assert 'FAR_ab' not in dry._get_subsystem('balance')._state_vars


@pytest.mark.parametrize('design, afterburn, expected', [
    (False, True, True), (False, False, False), (True, True, False),
])
def test_only_a_wet_off_design_point_controls_the_nozzle_throat(
        cycle, design, afterburn, expected):
    # DESIGN computes A8 and dry OD inherits it; only the wet point solves
    # its own, holding the fan on its design operating line.
    model = cycle(design=design, afterburn=afterburn)

    assert ('a8_ctrl' in {s.name for s in model._subsystems_myproc}) is expected


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


def test_unlit_augmentor_targets_its_inlet_and_carries_only_the_flameholder_loss():
    prob = augmentor(Tt7_cmd=0.)

    assert prob['Tt7'] == 1500.          # FAR_ab balance target = inlet
    assert prob['dPqP'] == pytest.approx(0.65 * kumar_q(1.341, 0.5 * 0.446))
    assert prob['dPqP'] == prob['dPqP_unlit']


def test_flameholder_loss_is_about_two_percent_at_the_design_augmentor_inlet():
    # k_M * MN6 = 0.22, the RM12 rig's flameholder approach Mach, with
    # C_D 0.65 gives the 1-3% cold loss of the NASA flameholder rigs (#33).
    assert augmentor()['dPqP_unlit'] == pytest.approx(0.021, abs=5e-4)


def test_lit_augmentor_adds_a_rayleigh_loss_proportional_to_heat_addition():
    prob = augmentor(Tt7_cmd=3600.)
    q = kumar_q(1.341, 0.5 * 0.446)

    assert prob['Tt7'] == 3600.
    assert prob['dPqP'] == pytest.approx(q * (0.65 + 1.0 * (3600. / 1500. - 1.)))
    assert prob['dPqP_unlit'] == pytest.approx(q * 0.65)


@pytest.mark.filterwarnings('ignore::openmdao.utils.om_warnings.DerivativesWarning')
@pytest.mark.parametrize('Tt7_cmd', [0., 1500.5, 3600.])
def test_augmentor_partials_match_complex_step(Tt7_cmd):
    # The max() makes half the Tt7 partials zero on each side of light-off.
    prob = augmentor(Tt7_cmd=Tt7_cmd)

    assert_check_partials(prob.check_partials(method='cs', out_stream=None))


NOZZLE_UNLIT = dict(A8_dsn=187.75, W_in=144., W_out=144., Tt_in=1502., Tt_out=1502.,
                    R_in=53.35, R_out=53.35, gam_in=1.341, gam_out=1.341,
                    dPqP=0.021, dPqP_unlit=0.021)
NOZZLE_LIT = {**NOZZLE_UNLIT, 'W_out': 149.4, 'Tt_out': 3600., 'R_out': 53.4,
              'gam_out': 1.27, 'dPqP': 0.065}


def test_unlit_nozzle_is_the_design_throat():
    assert solve_component(NozzleSchedule(), **NOZZLE_UNLIT)['A8'] == \
        pytest.approx(187.75, rel=1e-12)


def test_lit_nozzle_opens_to_pass_the_hotter_flow_at_the_same_pt6():
    # Roughly √(Tt7/Tt6) for the temperature, times the fuel mass, the loss
    # and the γ change: about 1.7x the dry throat at max AB.
    a8 = solve_component(NozzleSchedule(), **NOZZLE_LIT)['A8']

    assert 1.6 * 187.75 < a8 < 1.8 * 187.75


@pytest.mark.parametrize('inputs', [NOZZLE_UNLIT, NOZZLE_LIT], ids=['unlit', 'lit'])
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
