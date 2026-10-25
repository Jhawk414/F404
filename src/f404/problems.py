"""Construction of the converged F404 ``om.Problem``.

``build_problem()`` wires an ``MPMixedFlowTurbofan`` into a Problem, applies
the design-point targets and the initial guesses that get Newton into the
right basin, and solves the DESIGN point (which sizes the engine at dry mil)
plus the one OD point at sea-level static, first at mil power and then at max
afterburner. One engine and one OD topology serve both modes — see
``docs/adr/0001-single-engine-sizing.md`` and ``0002-single-od-topology.md``.
"""
import math

import openmdao.api as om

from f404.mp_cycle import MPMixedFlowTurbofan
from f404.printer import page_viewer
from f404.sweep_utils import STATIC_MN, _scalar

# ── Design-point targets ──────────────────────────────────────────────────────
MIL_Tt4    = 3100.   # degR — core burner exit at mil power (throttle wall)
DRY_DSN_FN = 11000.  # lbf  — SLS mil power (no afterburner); sizes the engine
MAX_AB_FN  = 17700.  # lbf  — SLS max afterburner; an output the next line calibrates to
MAX_Tt7    = 3607.68 # degR — afterburner exit at max AB. With the augmentor
                     # loss (mp_cycle.py; 6.6% at this point) the dry-sized
                     # engine makes MAX_AB_FN here. The cycle's augmentation
                     # ratio exceeds the targets' (ADR-0001), so this sits below
                     # the F404's ~3800 R. Combustion efficiency (#35) will move
                     # it again. See docs/adr/0002-single-od-topology.md.

# ── Design-point conditions and component performance ─────────────────────────
DSN_ALT = 0.0   # ft  — sea level static
DSN_MN  = STATIC_MN   # Mach — the sweeps' static Mach, so DESIGN and OD agree (#37)


class MaxTt7TooLowError(ValueError):
    """``max_Tt7`` is at or below the augmentor inlet temperature at SLS mil.

    The afterburner would stay dry, so there is no max-AB point to solve. A
    ``ValueError`` subclass, so callers that catch bad targets still do.
    """


def _validate_design_targets(fn_target, mil_Tt4, max_Tt7):
    """Reject design targets that can't produce a meaningful sizing.

    These three checks cover the mistakes that otherwise surface only as an
    opaque Newton failure — or worse, as a silently bound-clipped "solution"
    that sizes a nonsense engine and corrupts every OD point downstream.
    """
    for name, value in (('fn_target', fn_target), ('mil_Tt4', mil_Tt4),
                        ('max_Tt7', max_Tt7)):
        if not math.isfinite(value):
            raise ValueError(
                f"{name} must be a finite number, got {value!r}. A NaN or inf "
                f"target propagates through prob.set_val() into the Newton "
                f"residual without raising, so it has to be caught here."
            )

    if fn_target <= 0:
        raise ValueError(
            f"fn_target must be a positive thrust in lbf, got {fn_target}. "
            f"The DESIGN W balance solves inlet mass flow against this target; "
            f"a non-positive target drives W to its 25 lbm/s lower bound and "
            f"sizes an engine that no off-design point can be trusted from. "
            f"The default is DRY_DSN_FN ({DRY_DSN_FN:.0f}), SLS mil power."
        )

    if mil_Tt4 <= 0:
        raise ValueError(
            f"mil_Tt4 must be a positive burner exit temperature in degR, got "
            f"{mil_Tt4}. The FAR_core balance drives burner exit temperature to "
            f"this target."
        )

    if max_Tt7 <= 0:
        raise ValueError(
            f"max_Tt7 must be a positive afterburner exit temperature in degR, "
            f"got {max_Tt7}. It has to exceed the augmentor inlet (mixer exit) "
            f"temperature, ~1500 R at SLS mil; that depends on the cycle, so "
            f"build_problem() checks it after the dry solve."
        )


def _apply_design_inputs(prob, fn_target, mil_Tt4):
    """Set DESIGN-point targets, component performance, and initial guesses."""
    prob.set_val('DESIGN.fc.alt', DSN_ALT, units='ft')
    prob.set_val('DESIGN.fc.MN', DSN_MN)
    prob.set_val('DESIGN.balance.rhs:W', fn_target, units='lbf')
    prob.set_val('DESIGN.balance.rhs:FAR_core', mil_Tt4, units='degR')

    prob.set_val('DESIGN.fan.PR', 4.1)
    prob.set_val('DESIGN.fan.eff', 0.8948)
    prob.set_val('DESIGN.hpc.PR', 6.5)
    prob.set_val('DESIGN.hpc.eff', 0.8707)
    prob.set_val('DESIGN.hpt.eff', 0.8888)
    prob.set_val('DESIGN.lpt.eff', 0.8996)

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


def build_problem(fn_target=DRY_DSN_FN, mil_Tt4=MIL_Tt4, max_Tt7=MAX_Tt7,
                  verbose=True):
    """Build and solve the single-engine MPCycle problem.

    Parameters
    ----------
    fn_target : float
        SLS dry mil thrust, lbf. Sizes the engine — see
        ``_validate_design_targets``.
    mil_Tt4 : float
        Core burner exit temperature at mil power, degR. Wet points hold it.
    max_Tt7 : float
        Afterburner exit temperature at max AB, degR — the ``OD`` target
        at the SLS point solved here. It must exceed the SLS-mil augmentor
        inlet temperature (~1500 R), or ``ValueError`` is raised after the
        dry solve (``MaxTt7TooLowError``, a ``ValueError``).
    verbose : bool
        Print Newton iterations and the DESIGN/OD result tables.

    Returns
    -------
    (openmdao.api.Problem, MPMixedFlowTurbofan)
        The solved problem, left at SLS max AB, and its model, whose ``od_pt``
        attribute names the off-design point.
    """
    _validate_design_targets(fn_target, mil_Tt4, max_Tt7)

    prob = om.Problem()
    prob.model = mp = MPMixedFlowTurbofan()
    prob.setup()

    od = mp.od_pt
    _apply_design_inputs(prob, fn_target, mil_Tt4)
    _apply_od_inputs(prob, od, mil_Tt4)
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

    _check_max_Tt7_is_wet(prob, od, max_Tt7)

    # Go wet, warm-started from dry mil.
    prob.set_val(od + '.aug_ctrl.Tt7_cmd', max_Tt7, units='degR')
    if verbose:
        print("=" * 60)
        print("Running OD at SLS max AB...")
        print("=" * 60)
    prob.run_model()
    if verbose:
        page_viewer(prob, od)
    return prob, mp
