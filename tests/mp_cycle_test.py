"""Tests for the DESIGN-to-off-design wiring.

``MPMixedFlowTurbofan``'s job is to size the engine once at DESIGN and hand
that geometry to the OD point. A dropped connection here doesn't fail loudly:
the OD point just solves a subtly different engine, and the error lands in
the deck as a plausible-looking number. Everything below inspects the built
model without solving.
"""
import openmdao.api as om
import pytest

from F404_pycycle.mp_cycle import MPMixedFlowTurbofan
from F404_pycycle.sweep_utils import _scalar

# Scaled map coordinates. Without these the OD point runs on unscaled
# textbook maps instead of the sized engine's.
MAP_SCALARS = {
    'fan': ('s_PR', 's_Wc', 's_eff', 's_Nc'),
    'hpc': ('s_PR', 's_Wc', 's_eff', 's_Nc'),
    'hpt': ('s_PR', 's_Wp', 's_eff', 's_Np'),
    'lpt': ('s_PR', 's_Wp', 's_eff', 's_Np'),
}

# Stations whose flow area is frozen at its design value for off-design,
# as (component, area variable) pairs.
FROZEN_AREAS = (
    ('inlet', 'Fl_O:stat:area'), ('fan', 'Fl_O:stat:area'),
    ('splitter', 'Fl_O1:stat:area'), ('splitter', 'Fl_O2:stat:area'),
    ('splitter_core_duct', 'Fl_O:stat:area'), ('hpc', 'Fl_O:stat:area'),
    ('bld3', 'Fl_O:stat:area'), ('burner', 'Fl_O:stat:area'),
    ('hpt', 'Fl_O:stat:area'), ('hpt_duct', 'Fl_O:stat:area'),
    ('lpt', 'Fl_O:stat:area'), ('lpt_duct', 'Fl_O:stat:area'),
    ('bypass_duct', 'Fl_O:stat:area'), ('mixer', 'Fl_O:stat:area'),
    ('mixer', 'Fl_I1_calc:stat:area'), ('mixer_duct', 'Fl_O:stat:area'),
    ('afterburner', 'Fl_O:stat:area'),
)


def is_transferred(design_to_od, component, variable):
    """True if some DESIGN output under `component` named `variable` feeds OD.

    Matched on prefix and suffix rather than an exact path: OpenMDAO resolves
    these to the innermost pyCycle subcomponent that owns the output (e.g.
    `DESIGN.fan.map.scalars.s_PR`), and pinning the tests to those internals
    would make them break on an upstream refactor that changed nothing here.
    """
    return any(source.startswith(f'DESIGN.{component}.')
               and source.endswith(variable)
               for source in design_to_od)


@pytest.fixture(scope='module')
def wiring():
    """Map every OD input fed from the DESIGN point to its source."""
    prob = om.Problem()
    prob.model = mp = MPMixedFlowTurbofan(afterburn=True)
    prob.setup()

    design_to_od = {
        source for target, source in prob.model._conn_global_abs_in2out.items()
        if source.startswith('DESIGN.') and target.startswith(f'{mp.od_pt}.')
    }
    return mp, design_to_od


def test_off_design_point_is_named_consistently(wiring):
    # Callers address the OD point through mp.od_pt rather than hardcoding
    # the string; the two must not drift.
    mp, _ = wiring

    assert mp.od_pt == 'OD'


@pytest.mark.parametrize('component, scalars', sorted(MAP_SCALARS.items()))
def test_map_scalars_reach_the_off_design_point(wiring, component, scalars):
    _, design_to_od = wiring

    missing = [s for s in scalars
               if not is_transferred(design_to_od, component, f'.{s}')]
    assert not missing, (
        f"{component} map scalars not transferred to OD: {missing} — the OD "
        f"point would run on an unscaled map"
    )


def test_every_frozen_station_area_reaches_the_off_design_point(wiring):
    _, design_to_od = wiring

    missing = [f'{comp}.{var}' for comp, var in FROZEN_AREAS
               if not is_transferred(design_to_od, comp, var)]
    assert not missing, f"station areas not transferred to OD: {missing}"


def test_nozzle_throat_area_drives_the_off_design_flow_balance(wiring):
    # The OD W balance solves inlet flow against the design throat area —
    # the frozen-A8 assumption that #8 proposes to replace with a
    # T7-scheduled schedule, and that #3's wet-corner failures trace back to.
    _, design_to_od = wiring

    assert is_transferred(design_to_od, 'mixed_nozz', 'Throat:stat:area')


def test_augmentor_target_is_settable_independently_per_point():
    """T7 must not be a cycle parameter.

    A cycle param is shared across every point, which would force the OD
    afterburner to the design-point T7 and make the wet throttle sweep
    impossible — the sweep's entire job is varying T7 while DESIGN stays at
    max AB.
    """
    prob = om.Problem()
    prob.model = mp = MPMixedFlowTurbofan(afterburn=True)
    prob.setup()

    prob.set_val('DESIGN.balance.rhs:FAR_ab', 3800., units='degR')
    prob.set_val(f'{mp.od_pt}.balance.rhs:FAR_ab', 3400., units='degR')

    assert _scalar(prob.get_val('DESIGN.balance.rhs:FAR_ab',
                                units='degR')) == 3800.
    assert _scalar(prob.get_val(f'{mp.od_pt}.balance.rhs:FAR_ab',
                                units='degR')) == 3400.


@pytest.mark.parametrize('afterburn', [True, False])
def test_both_points_are_built_in_either_mode(afterburn):
    prob = om.Problem()
    prob.model = mp = MPMixedFlowTurbofan(afterburn=afterburn)
    prob.setup()

    names = {s.name for s in prob.model._subsystems_myproc}
    assert {'DESIGN', mp.od_pt} <= names
