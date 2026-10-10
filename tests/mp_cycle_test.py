"""Tests for the DESIGN-to-off-design wiring.

``MPMixedFlowTurbofan``'s job is to size the engine once at DESIGN and hand
that geometry to both OD points, dry and wet. A dropped connection here
doesn't fail loudly: the OD point just solves a subtly different engine, and
the error lands in the deck as a plausible-looking number — exactly the
two-engines problem of #2. Everything below inspects the built model without
solving.
"""
import openmdao.api as om
import pycycle.api as pyc
import pytest

from F404_pycycle.mp_cycle import MPMixedFlowTurbofan

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
def model():
    prob = om.Problem()
    prob.model = MPMixedFlowTurbofan()
    prob.setup()
    return prob.model


@pytest.fixture(scope='module', params=['dry', 'wet'])
def wiring(request, model):
    """Map every input of one OD point fed from the DESIGN point to its source."""
    pt = model.od_pts[request.param]
    design_to_od = {
        source for target, source in model._conn_global_abs_in2out.items()
        if source.startswith('DESIGN.') and target.startswith(f'{pt}.')
    }
    return request.param, design_to_od


def test_off_design_points_are_named_by_mode(model):
    # Callers address the OD points through mp.od_pts rather than hardcoding
    # the strings; the two must not drift.
    assert model.od_pts == {'dry': 'OD_dry', 'wet': 'OD_wet'}


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


def test_nozzle_throat_comes_from_design_dry_and_from_the_control_law_wet(model):
    # Dry runs the DESIGN A8. Wet sets its own: a hot augmented flow through
    # the dry throat would back-pressure the fan off its map, and holding the
    # wet point to the DESIGN area is what left single-engine Options 1 and
    # 2 with no dry solution (ADR-0001).
    feeds = model._conn_global_abs_in2out

    assert is_transferred({feeds['OD_dry.balance.rhs:W']},
                          'mixed_nozz', 'Throat:stat:area')
    assert feeds['OD_wet.balance.rhs:W'] == 'OD_wet.a8_ctrl.A8'


def test_design_sizes_the_engine_with_the_afterburner_unlit(model):
    # Dry mil is the sizing point: one engine, which the wet point then lights.
    design = model._get_subsystem('DESIGN')

    assert isinstance(design._get_subsystem('afterburner'), pyc.Duct)
    assert 'FAR_ab' not in design._get_subsystem('balance')._state_vars


def test_every_point_is_built(model):
    names = {s.name for s in model._subsystems_myproc}

    assert names == {'DESIGN', *model.od_pts.values()}
