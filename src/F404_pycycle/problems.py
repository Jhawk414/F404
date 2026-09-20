"""Construction of converged F404 ``om.Problem`` instances.

Two builders, one per afterburner mode — ``build_dry_problem()`` and
``build_wet_problem()``. Each wires an ``MPMixedFlowTurbofan`` into a
Problem, applies the design-point targets and the initial guesses that get
Newton into the right basin, and solves the DESIGN point (which sizes the
engine) plus the OD point at design conditions.

Dry and wet are separate Problems because the ``FAR_ab`` balance is
structural — it exists or it doesn't, and can't be toggled at runtime.
Unifying the two sizings is tracked in
`#2 <https://github.com/Jhawk414/F404/issues/2>`_.
"""
import math

import openmdao.api as om

from F404_pycycle.mp_cycle import MPMixedFlowTurbofan
from F404_pycycle.printer import page_viewer

# ── Design-point targets ──────────────────────────────────────────────────────
MIL_Tt4    = 3100.   # degR — core burner exit at mil power (throttle wall)
DSN_Tt7    = 3800.   # degR — afterburner exit at DESIGN point (wet only; max AB)
DRY_DSN_FN = 11000.  # lbf  — SLS mil power (no afterburner)
WET_DSN_FN = 17700.  # lbf  — SLS max afterburner

# ── Design-point conditions and component performance ─────────────────────────
DSN_ALT = 0.0   # ft  — sea level static
DSN_MN  = 0.01  # Mach — nominally static; 0 is singular in the flow solve


def _validate_design_targets(fn_target, mil_Tt4, dsn_Tt7=None):
    """Reject design targets that can't produce a meaningful sizing.

    These three checks cover the mistakes that otherwise surface only as an
    opaque Newton failure — or worse, as a silently bound-clipped "solution"
    that sizes a nonsense engine and corrupts every OD point downstream.
    """
    for name, value in (('fn_target', fn_target), ('mil_Tt4', mil_Tt4),
                        ('dsn_Tt7', dsn_Tt7)):
        if value is not None and not math.isfinite(value):
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
            f"Use DRY_DSN_FN ({DRY_DSN_FN:.0f}) for dry or WET_DSN_FN "
            f"({WET_DSN_FN:.0f}) for wet."
        )

    if mil_Tt4 <= 0:
        raise ValueError(
            f"mil_Tt4 must be a positive burner exit temperature in degR, got "
            f"{mil_Tt4}. The FAR_core balance drives burner exit temperature to "
            f"this target."
        )

    if dsn_Tt7 is not None and dsn_Tt7 <= mil_Tt4:
        raise ValueError(
            f"dsn_Tt7 ({dsn_Tt7} degR) must exceed mil_Tt4 ({mil_Tt4} degR). "
            f"The afterburner adds heat downstream of the turbines, so its exit "
            f"is always hotter than the core burner's; a target at or below "
            f"mil_Tt4 asks the FAR_ab balance for negative fuel flow and it "
            f"pins at its 1e-4 lower bound instead."
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


def _solve(prob, pt, label, verbose):
    """Run the DESIGN + OD solve, optionally printing both result pages."""
    prob.set_solver_print(level=-1)
    if verbose:
        prob.set_solver_print(level=2, depth=1)
        print("=" * 60)
        print(f"{label} — Running DESIGN + OD at design conditions...")
        print("=" * 60)

    prob.run_model()

    if verbose:
        page_viewer(prob, 'DESIGN')
        page_viewer(prob, pt)


def build_dry_problem(fn_target=DRY_DSN_FN, mil_Tt4=MIL_Tt4, verbose=True):
    """Build and solve a dry (no afterburner) MPCycle problem.

    Parameters
    ----------
    fn_target : float
        SLS DESIGN thrust target, lbf. Sizes the engine — see
        ``_validate_design_targets``.
    mil_Tt4 : float
        Core burner exit temperature at mil power, degR.
    verbose : bool
        Print Newton iterations and the DESIGN/OD result tables.

    Returns
    -------
    (openmdao.api.Problem, MPMixedFlowTurbofan)
        The solved problem and its model, whose ``od_pt`` attribute names
        the off-design point.
    """
    _validate_design_targets(fn_target, mil_Tt4)

    prob = om.Problem()
    prob.model = mp = MPMixedFlowTurbofan(afterburn=False)
    prob.setup()

    _apply_design_inputs(prob, fn_target, mil_Tt4)
    # Dry mode: the afterburner is a pyc.Duct, so there is no Fl_I:FAR
    # balance to seed. FAR propagates through from the mixer duct as-is.
    _apply_od_inputs(prob, mp.od_pt, mil_Tt4)

    _solve(prob, mp.od_pt, 'DRY', verbose)
    return prob, mp


def build_wet_problem(fn_target=WET_DSN_FN, mil_Tt4=MIL_Tt4, dsn_Tt7=DSN_Tt7,
                      verbose=True):
    """Build and solve a wet (afterburning) MPCycle problem.

    Parameters
    ----------
    fn_target : float
        SLS DESIGN thrust target, lbf, at max afterburner.
    mil_Tt4 : float
        Core burner exit temperature, degR. Held fixed across a wet sweep.
    dsn_Tt7 : float
        Afterburner exit temperature at the DESIGN point, degR. This is the
        sizing corner, so it belongs at max AB, not mid-AB.
    verbose : bool
        Print Newton iterations and the DESIGN/OD result tables.

    Returns
    -------
    (openmdao.api.Problem, MPMixedFlowTurbofan)
        The solved problem and its model.
    """
    _validate_design_targets(fn_target, mil_Tt4, dsn_Tt7)

    prob = om.Problem()
    prob.model = mp = MPMixedFlowTurbofan(afterburn=True)
    prob.setup()

    _apply_design_inputs(prob, fn_target, mil_Tt4)
    prob.set_val('DESIGN.balance.rhs:FAR_ab', dsn_Tt7, units='degR')
    prob['DESIGN.balance.FAR_ab'] = 0.0375

    pt = mp.od_pt
    _apply_od_inputs(prob, pt, mil_Tt4)
    prob.set_val(pt + '.balance.rhs:FAR_ab', dsn_Tt7, units='degR')
    prob[pt + '.balance.FAR_ab'] = 0.025

    _solve(prob, pt, 'WET', verbose)
    return prob, mp
