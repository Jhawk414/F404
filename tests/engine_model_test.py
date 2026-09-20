"""Structural tests for the single-point cycle.

No solving here — these build the model and inspect what got wired, which
is enough to lock in the structural decisions that were paid for in
debugging time and are easy to undo by accident. Each runs in milliseconds.
"""
import openmdao.api as om
import pycycle.api as pyc
import pytest

from F404_pycycle.engine_model import MixedFlowTurbofan

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
    # This is why dry and wet need separate om.Problem instances: the
    # balance is structural and can't be toggled after setup.
    wet = cycle(design=design, afterburn=True)
    dry = cycle(design=design, afterburn=False)

    assert 'FAR_ab' in wet._get_subsystem('balance')._state_vars
    assert 'FAR_ab' not in dry._get_subsystem('balance')._state_vars


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
