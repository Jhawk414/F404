"""Sizing the F404: ``design()`` turns ``DesignInputs`` into a solved ``Engine``.

``design()`` wires an ``MPMixedFlowTurbofan`` into a Problem, applies the
design inputs and the initial guesses that get Newton into the right basin,
and solves the DESIGN point (which sizes the engine at dry mil) plus the one
OD point at sea-level static, first at mil power and then at max afterburner.
One engine and one OD topology serve both modes — see
``docs/adr/0001-single-engine-sizing.md`` and ``0002-single-od-topology.md``;
the public API is ``docs/adr/0005-public-python-api.md``.
"""
from dataclasses import dataclass, field

import numpy as np
import openmdao.api as om
from pycycle.thermo.static_ps_resid import PsResid

from f404.config import (  # noqa: F401 (targets re-exported)
    DRY_DSN_FN, MAX_Tt7, MIL_Tt4, DesignInputs, PlaSchedule,
)
from f404.mp_cycle import MPMixedFlowTurbofan
from f404.printer import page_viewer
from f404.sweep_utils import STATIC_MN, _scalar

MAX_AB_FN = 17700.  # lbf — SLS max AB of the default engine; MAX_Tt7 is calibrated to it

# ── Design-point conditions and component performance ─────────────────────────
DSN_ALT = 0.0   # ft  — sea level static
DSN_MN  = STATIC_MN   # Mach — the sweeps' static Mach, so DESIGN and OD agree (#37)


class MaxTt7TooLowError(ValueError):
    """``max_Tt7`` is at or below the augmentor inlet temperature at SLS mil.

    The afterburner would stay dry, so there is no max-AB point to solve. A
    ``ValueError`` subclass, so callers that catch bad targets still do.
    """


# DesignInputs field -> (model path, units). max_Tt7 is absent: it is the OD
# afterburner command at the max-AB anchor, not a DESIGN input. mil_Tt4 maps
# to its DESIGN target only; wet OD points also hold OD.balance.rhs:FAR_core
# at mil_Tt4, so a wet-point total with respect to mil_Tt4 needs both paths.
DESIGN_INPUT_PATHS = {
    'fn_target':  ('DESIGN.balance.rhs:W', 'lbf'),
    'mil_Tt4':    ('DESIGN.balance.rhs:FAR_core', 'degR'),
    'fan_PR':     ('DESIGN.fan.PR', None),
    'fan_eff':    ('DESIGN.fan.eff', None),
    'hpc_PR':     ('DESIGN.hpc.PR', None),
    'hpc_eff':    ('DESIGN.hpc.eff', None),
    'hpt_eff':    ('DESIGN.hpt.eff', None),
    'lpt_eff':    ('DESIGN.lpt.eff', None),
    'LP_Nmech':   ('DESIGN.LP_Nmech', 'rpm'),
    'HP_Nmech':   ('DESIGN.HP_Nmech', 'rpm'),
    'ram_recovery':            ('inlet.ram_recovery', None),
    'inlet_duct_dPqP':         ('inlet_duct.dPqP', None),
    'splitter_core_duct_dPqP': ('splitter_core_duct.dPqP', None),
    'hpt_duct_dPqP':           ('hpt_duct.dPqP', None),
    'lpt_duct_dPqP':           ('lpt_duct.dPqP', None),
    'bypass_duct_dPqP':        ('bypass_duct.dPqP', None),
    'mixer_duct_dPqP':         ('mixer_duct.dPqP', None),
    'hpc_cool1_frac_W':        ('hpc.cool1:frac_W', None),
    'bld3_cool3_frac_W':       ('bld3.cool3:frac_W', None),
}


def _apply_design_inputs(prob, inputs):
    """Set the DESIGN flight condition, every design input, and initial guesses."""
    prob.set_val('DESIGN.fc.alt', DSN_ALT, units='ft')
    prob.set_val('DESIGN.fc.MN', DSN_MN)
    for field, (path, units) in DESIGN_INPUT_PATHS.items():
        prob.set_val(path, getattr(inputs, field), units=units)

    prob['DESIGN.fc.balance.Pt']    = 5.3
    prob['DESIGN.fc.balance.Tt']    = 450.
    prob['DESIGN.balance.W']        = 120.0
    prob['DESIGN.balance.BPR']      = 0.65
    prob['DESIGN.balance.FAR_core'] = 0.025
    prob['DESIGN.balance.hpt_PR']   = 2.5506
    prob['DESIGN.balance.lpt_PR']   = 2.5    # core exit P ≈ bypass exit P (ER≈1)
    prob['DESIGN.mixer.balance.P_tot'] = 55.  # ≈ bypass total P


def _apply_od_inputs(prob, pt, mil_Tt4):
    """Set OD flight conditions at the design point, plus initial guesses.

    The conditions have to be in place before the first ``run_model()``: it
    solves DESIGN and OD together, so an unset OD target (``rhs:FAR_core``
    defaults to 0 degR) diverges immediately. The sweep overwrites all of
    these per point.
    """
    prob.set_val(pt + '.fc.alt', DSN_ALT, units='ft')
    prob.set_val(pt + '.fc.MN', DSN_MN)
    prob.set_val(pt + '.fc.dTs', 0.0, units='degR')
    prob.set_val(pt + '.balance.rhs:FAR_core', mil_Tt4, units='degR')

    prob[pt + '.fc.balance.Pt']    = 14.7
    prob[pt + '.fc.balance.Tt']    = 519.
    prob[pt + '.balance.FAR_core'] = 0.025
    prob[pt + '.balance.BPR']      = 0.35
    prob[pt + '.balance.W']        = 100.
    prob[pt + '.balance.HP_Nmech'] = 15000.
    prob[pt + '.balance.LP_Nmech'] = 10000.
    prob[pt + '.mixer.balance.P_tot'] = 55.
    prob[pt + '.hpt.PR']           = 2.523
    prob[pt + '.lpt.PR']           = 2.401
    prob[pt + '.fan.map.RlineMap'] = 2.0
    prob[pt + '.hpc.map.RlineMap'] = 2.0


def _check_max_Tt7_is_wet(prob, od, max_Tt7):
    """Reject a max-AB target the solved dry engine would treat as dry.

    The OD point reads any Tt7 command at or below the augmentor inlet
    temperature (Tt6) as dry, which a sweep relies on. Here it would return a
    dry engine as "max AB", with no error, so the target is checked against
    the Tt6 that the dry-mil solve just produced.
    """
    tt6 = _scalar(prob.get_val(od + '.mixer_duct.Fl_O:tot:T', units='degR'))
    if max_Tt7 <= tt6:
        raise MaxTt7TooLowError(
            f"max_Tt7 must exceed the augmentor inlet temperature at SLS mil, "
            f"Tt6 = {tt6:.1f} R for this engine, got {max_Tt7}. At or below "
            f"Tt6 the afterburner stays dry and there is no max-AB point. The "
            f"default, MAX_Tt7 = {MAX_Tt7} R, makes {MAX_AB_FN:.0f} lbf at sea-level "
            f"static (SLS)."
        )


@dataclass(frozen=True, eq=False)
class Engine:
    """A sized engine, as ``design()`` returns it.

    ``prob`` is the solved Problem; its OD point is ``prob.model.od_pt``.
    ``anchor`` is the OD output vector at SLS max AB; ``ps_guesses`` holds
    the OD static-pressure guess caches there. ``run_point()`` and
    ``sweep()`` restore both before every call, so earlier calls don't steer
    them.

    Treat an Engine as immutable: change the design through ``design()``.
    Setting a design value on ``prob`` would leave ``inputs`` and ``anchor``
    stale.
    """
    prob: om.Problem
    inputs: DesignInputs
    anchor: np.ndarray
    ps_guesses: tuple = field(repr=False)
    schedules: PlaSchedule = PlaSchedule()

    def restore_anchor(self):
        """Put the OD point back to SLS max AB, where ``design()`` left it.

        Restores the OD outputs and the static-pressure guess caches; OD
        inputs are re-set per point. After any ``run_point()`` or
        ``sweep()``, OD Newton's ``maxiter`` stays at ``SWEEP_MAXITER`` (20).
        """
        _od_outputs(self.prob)[:] = self.anchor
        for comp, cache in zip(_ps_resids(self.prob), self.ps_guesses):
            comp._ps_guess_cache = np.copy(cache)

    def home(self, mode):
        """The anchor's flight condition, as a sweep point at ``mode``'s top
        power: ``mil_Tt4`` dry, ``max_Tt7`` wet."""
        power = self.inputs.mil_Tt4 if mode == 'dry' else self.inputs.max_Tt7
        return {'MN': DSN_MN, 'alt': DSN_ALT, 'dTs': 0., 'power': power}

    def home_pla(self):
        """The anchor's flight condition at max AB PLA."""
        return {'MN': DSN_MN, 'alt': DSN_ALT, 'dTs': 0., 'power': self.schedules.max_ab_pla}


def _od_outputs(prob):
    """The OD point's full output vector: every implicit Newton state, as a view."""
    return prob.model._get_subsystem(prob.model.od_pt)._outputs.asarray()


def _ps_resids(prob):
    """The OD point's static-pressure solvers.

    Each keeps its last Ps guess as a Python attribute and re-seeds Ps only
    when a new guess differs from it, so that cache steers the next solve
    from outside the model's vectors (#59).
    """
    od = prob.model._get_subsystem(prob.model.od_pt)
    return list(od.system_iter(recurse=True, typ=PsResid))


def design(inputs=DesignInputs(), *, schedules=PlaSchedule(), verbose=False):
    """Size the engine and solve OD at SLS dry mil, then SLS max AB.

    Parameters
    ----------
    inputs : DesignInputs or mapping
        Design inputs; a mapping is validated as ``DesignInputs`` first.
        The defaults are the calibrated F404.
    schedules : PlaSchedule or mapping
        Off-design PLA schedule attached to the returned ``Engine``.
    verbose : bool
        Print Newton iterations and the DESIGN/OD result tables.

    Returns
    -------
    Engine
        Left at SLS max AB.

    Raises
    ------
    pydantic.ValidationError
        ``inputs`` or ``schedules`` is invalid or has an unknown field.
    ValueError
        ``schedules`` temperatures are inconsistent with ``inputs``.
    MaxTt7TooLowError
        ``inputs.max_Tt7`` is at or below the SLS-mil augmentor inlet
        temperature (~1500 R), checked after the dry solve.
    openmdao.api.AnalysisError
        DESIGN or OD did not converge.
    """
    validated_inputs = DesignInputs.model_validate(inputs)
    validated_schedules = PlaSchedule.model_validate(schedules)
    validated_schedules.validate_against(validated_inputs)
    return _solve(validated_inputs, verbose, schedules=validated_schedules)


def _solve(inputs, verbose, on_mil=None, schedules=PlaSchedule()):
    """``design()``, plus ``on_mil(prob, od_pt)`` called once OD has converged
    at SLS mil, to read that point before max AB overwrites it (``verify``)."""
    prob = om.Problem(reports=False)
    prob.model = mp = MPMixedFlowTurbofan()
    prob.setup()

    od = mp.od_pt
    _apply_design_inputs(prob, inputs)
    _apply_od_inputs(prob, od, inputs.mil_Tt4)
    prob.set_val(od + '.aug_ctrl.Tt7_cmd', 0., units='degR')   # dry

    prob.set_solver_print(level=-1)
    if verbose:
        prob.set_solver_print(level=2, depth=1)
        print("=" * 60)
        print("Running DESIGN (dry mil) + OD at SLS mil...")
        print("=" * 60)
    prob.run_model()
    if verbose:
        page_viewer(prob, 'DESIGN', afterburn=False)
        page_viewer(prob, od)
    if on_mil is not None:
        on_mil(prob, od)

    _check_max_Tt7_is_wet(prob, od, inputs.max_Tt7)

    # Go wet, warm-started from dry mil.
    prob.set_val(od + '.aug_ctrl.Tt7_cmd', inputs.max_Tt7, units='degR')
    if verbose:
        print("=" * 60)
        print("Running OD at SLS max AB...")
        print("=" * 60)
    prob.run_model()
    if verbose:
        page_viewer(prob, od)
    return Engine(prob, inputs, _od_outputs(prob).copy(),
                  tuple(np.copy(c._ps_guess_cache) for c in _ps_resids(prob)),
                  schedules)
