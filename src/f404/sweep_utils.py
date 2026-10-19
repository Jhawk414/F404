"""
Sweep utilities for F404 cycle deck generation.

Provides:
- build_snake_sweep(): Generates an ordered sweep matrix with snake-pattern traversal
- generate_bridge_points(): Creates intermediate points for smooth solver transitions
- extract_od_results(): Pulls key performance outputs from a converged OD solution
- SweepRunner: Orchestrates the full sweep loop with warm-starting and bridge points
"""
import logging

import numpy as np
import openmdao.api as om
import pandas as pd

log = logging.getLogger(__name__)


class SweepConfigurationError(Exception):
    """The sweep is wired wrong — as distinct from a point failing to converge.

    Deliberately not a RuntimeError: _run_point treats RuntimeError as a
    failed point and carries on, which is right for a singular Jacobian and
    wrong for a model that no longer matches the tables here.
    """

# OD BalanceComp bounds — must mirror engine_model.py off-design block.
# Used by SweepRunner._state_at_bounds() to flag bound-clipped solutions
# that Newton would otherwise report as "converged".
_OD_BOUNDS = {
    'balance.W':         (25.,   200.),
    'balance.BPR':       (0.1,   1.0),
    'balance.FAR_core':  (1e-4,  0.06),
    'balance.LP_Nmech':  (500.,  None),  # no upper bound in BalanceComp
    'balance.HP_Nmech':  (500.,  None),
    # Lower bound 0 is the unlit solution, not saturation; a lit point pinned
    # there misses its Tt7 target and fails _target_met instead.
    'balance.FAR_ab':    (None,  0.06),
}

# Fraction of bound width within which a state is considered saturated.
_BOUND_TOL_FRAC = 0.01

# Burner/afterburner exit temperature must be within this many degR of the
# requested target for the run to count as a real solution.
_TARGET_TOL_DEGR = 5.0


def _scalar(value):
    """Collapse an OpenMDAO value to a plain Python float.

    ``prob.get_val()`` and ``prob[...]`` return length-1 ``ndarray``s, and
    ``float()`` on an array with ``ndim > 0`` has been deprecated since NumPy
    1.25 and is slated to raise. Every read in this module goes through here
    so the deck stays plain floats without accumulating that deprecation
    across ~18 columns per sweep point.
    """
    return float(np.asarray(value).item())


def build_snake_sweep(alts, dTs_values, powers):
    """
    Build an ordered sweep matrix using a snake (boustrophedon) pattern.

    At each altitude, dTs is swept in alternating directions so that
    consecutive points are always neighbors — minimizing jumps that
    can cause Newton solver convergence issues.

    Ordering (outermost → innermost):
        power → altitude → dTs (snake)

    Parameters
    ----------
    alts : array-like
        Altitudes in ft, sorted ascending.
    dTs_values : array-like
        Delta-ISA temperature offsets in degR, sorted ascending.
    powers : array-like
        Power levels (Tt4 in degR), ordered as desired (e.g. high → low).

    Returns
    -------
    list of dict
        Each entry: {'alt': float, 'dTs': float, 'power': float}
        Ordered for minimal inter-point jumps.
    """
    sweep = []
    for power in powers:
        for i, alt in enumerate(alts):
            # Reverse dTs direction on odd altitude indices (snake)
            dTs_ordered = dTs_values if (i % 2 == 0) else dTs_values[::-1]
            for dTs in dTs_ordered:
                sweep.append({'alt': float(alt), 'dTs': float(dTs), 'power': float(power)})
    return sweep


def generate_bridge_points(pt_from, pt_to, n_steps):
    """
    Linearly interpolate bridge points between two sweep conditions.

    Bridge points help the Newton solver transition across large jumps
    in altitude or temperature. Their results are discarded — they exist
    solely to provide a warm-start path.

    Parameters
    ----------
    pt_from : dict
        Starting point {'alt', 'dTs', 'power'}.
    pt_to : dict
        Target point {'alt', 'dTs', 'power'}.
    n_steps : int
        Number of intermediate steps (not including from/to).

    Returns
    -------
    list of dict
        Intermediate points, excluding pt_from and pt_to.
    """
    bridges = []
    for k in range(1, n_steps + 1):
        frac = k / (n_steps + 1)
        bridges.append({
            'alt': pt_from['alt'] + frac * (pt_to['alt'] - pt_from['alt']),
            'dTs': pt_from['dTs'] + frac * (pt_to['dTs'] - pt_from['dTs']),
            'power': pt_from['power'] + frac * (pt_to['power'] - pt_from['power']),
        })
    return bridges


# Deck columns read straight off the OD point: name -> (path under the point,
# units). The first block is the original deck schema, in its original order;
# the rest add the station data that downstream work reads: augmentor inlet
# (#33), compressor operating point and stall margin (#8), turbine exit
# temperatures (T5 is the F404's T5.6 control temperature), and the nozzle
# inlet and exit states a method-of-characteristics nozzle tool needs.
DECK_COLUMNS = {
    'alt':      ('fc.alt', 'ft'),
    'dTs':      ('fc.dTs', 'degR'),
    'MN':       ('fc.MN', None),
    'Fn':       ('perf.Fn', 'lbf'),
    'Fg':       ('perf.Fg', 'lbf'),
    'TSFC':     ('perf.TSFC', None),
    'W':        ('balance.W', 'lbm/s'),
    'BPR':      ('balance.BPR', None),
    'FAR_core': ('balance.FAR_core', None),
    'FAR_ab':   ('balance.FAR_ab', None),
    'OPR':      None,  # fan PR x HPC PR, derived below
    'fan_PR':   ('fan.PR', None),
    'hpc_PR':   ('hpc.PR', None),
    'hpt_PR':   ('hpt.PR', None),
    'lpt_PR':   ('lpt.PR', None),
    'T4':       ('burner.Fl_O:tot:T', 'degR'),
    'T7':       ('afterburner.Fl_O:tot:T', 'degR'),
    'LP_Nmech': ('balance.LP_Nmech', 'rpm'),
    'HP_Nmech': ('balance.HP_Nmech', 'rpm'),
    'Wf_core':  ('burner.Wfuel', 'lbm/s'),
    'Wf_ab':    ('afterburner.Wfuel', 'lbm/s'),
    'A8':       ('mixed_nozz.Throat:stat:area', 'inch**2'),

    'Ps_amb':   ('fc.Fl_O:stat:P', 'psi'),
    'F_ram':    ('inlet.F_ram', 'lbf'),
    'Tt2':      ('inlet.Fl_O:tot:T', 'degR'),
    'Pt2':      ('inlet.Fl_O:tot:P', 'psi'),
    'fan_Rline': ('fan.map.RlineMap', None),
    'fan_Nc':   ('fan.Nc', 'rpm'),
    'fan_Wc':   ('fan.Wc', 'lbm/s'),
    'fan_eff':  ('fan.eff', None),
    'fan_SMN':  ('fan.SMN', None),
    'fan_SMW':  ('fan.SMW', None),
    'hpc_Rline': ('hpc.map.RlineMap', None),
    'hpc_Nc':   ('hpc.Nc', 'rpm'),
    'hpc_Wc':   ('hpc.Wc', 'lbm/s'),
    'hpc_eff':  ('hpc.eff', None),
    'hpc_SMN':  ('hpc.SMN', None),
    'hpc_SMW':  ('hpc.SMW', None),
    'Tt3':      ('hpc.Fl_O:tot:T', 'degR'),
    'Pt3':      ('hpc.Fl_O:tot:P', 'psi'),
    'Tt45':     ('hpt.Fl_O:tot:T', 'degR'),
    'Tt5':      ('lpt.Fl_O:tot:T', 'degR'),
    'Pt5':      ('lpt.Fl_O:tot:P', 'psi'),
    'Tt6':      ('afterburner.Fl_I:tot:T', 'degR'),
    'Pt6':      ('afterburner.Fl_I:tot:P', 'psi'),
    'MN6':      ('afterburner.Fl_I:stat:MN', None),
    'ab_dPqP':  ('afterburner.dPqP', None),
    'Pt7':      ('afterburner.Fl_O:tot:P', 'psi'),
    'W7':       ('afterburner.Fl_O:stat:W', 'lbm/s'),
    'gamma7':   ('afterburner.Fl_O:tot:gamma', None),
    'R7':       ('afterburner.Fl_O:tot:R', 'ft*lbf/(lbm*degR)'),
    'nozz_PR':  ('mixed_nozz.PR', None),
    'A9':       ('mixed_nozz.Fl_O:stat:area', 'inch**2'),
    'MN9':      ('mixed_nozz.Fl_O:stat:MN', None),
    'Ps9':      ('mixed_nozz.Fl_O:stat:P', 'psi'),
    'V9':       ('mixed_nozz.Fl_O:stat:V', 'ft/s'),
}


def extract_od_results(prob, pt):
    """
    Extract the deck row (``DECK_COLUMNS``) from a converged OD solution.

    Parameters
    ----------
    prob : openmdao.api.Problem
        The solved problem.
    pt : str
        Point name (e.g. 'OD').

    Returns
    -------
    dict
        Performance results, in ``DECK_COLUMNS`` order.
    """
    row = {}
    for name, spec in DECK_COLUMNS.items():
        if spec is None:
            row[name] = _scalar(prob[f'{pt}.fan.PR'] * prob[f'{pt}.hpc.PR'])
        else:
            path, units = spec
            row[name] = _scalar(prob.get_val(f'{pt}.{path}', units=units))
    return row


class SweepRunner:
    """
    Runs a sequential OD sweep on a configured, design-converged problem.

    The solver state from the previous point carries over to the next
    (warm-starting). When the jump between consecutive points exceeds
    a threshold, bridge points are automatically inserted and discarded.

    Parameters
    ----------
    prob : openmdao.api.Problem
        Problem with DESIGN already converged via prob.run_model().
    od_pt : str
        Name of the OD point to drive, e.g. ``mp.od_pt``.
    mach : float
        Mach number to use for all sweep points.
    afterburn : bool
        True = wet mode: 'power' in sweep points is T7 (degR); Tt4 is fixed at mil_Tt4.
        False = dry mode: 'power' in sweep points is Tt4 (degR); afterburner unlit.
    mil_Tt4 : float
        Core burner exit temp (degR) held fixed during a wet sweep (mil power).
        Ignored in dry mode.
    """

    def __init__(self, prob, od_pt, mach=0.01, afterburn=True, mil_Tt4=3100.):
        self.prob = prob
        self.od_pt = od_pt
        self.mach = mach
        self.afterburn = afterburn
        self.mil_Tt4 = mil_Tt4
        # Snapshot of the most recently converged OD state — used to restore a
        # clean warm-start before retrying a failed point with safe linesearch.
        self._last_good_state = None

    def _od_newton(self):
        """Get the OD subsystem's Newton solver."""
        return self.prob.model._get_subsystem(self.od_pt).nonlinear_solver

    def _set_linesearch_mode(self, mode):
        """Toggle linesearch backtracking on the OD Newton.

        'fast' (maxiter=0): no Armijo backtracking — fast path.
        'safe' (maxiter=3): up to 3 Armijo backtracks — robust fallback for
                            points that fail with the fast linesearch.
        """
        self._od_newton().linesearch.options['maxiter'] = (
            0 if mode == 'fast' else 5
        )

    def _snapshot_state(self):
        """Capture the FULL OD output vector (all implicit Newton states).

        A previous version of this code snapshotted only a dozen named primary
        balance states (W, BPR, FAR_core, etc.).  That's insufficient: pyCycle
        has many nested implicit states inside its sub-components — every
        Nozzle/Mixer has a `staticMN.ps_resid` with an implicit Ps state, every
        compressor/turbine has internal map states, etc.  When Newton failed
        at a cold corner, those sub-Newton states were left at exploded values,
        and a partial restore of just the primary states left the model in an
        inconsistent state that immediately blew up gamma to non-physical
        values on the next run.

        Snapshotting `_outputs.asarray()` captures the entire OD subsystem's
        output vector, which contains every implicit Newton state in one shot.
        """
        od_group = self.prob.model._get_subsystem(self.od_pt)
        return od_group._outputs.asarray().copy()

    def _restore_state(self, snap):
        """Restore the full OD output vector captured by _snapshot_state."""
        od_group = self.prob.model._get_subsystem(self.od_pt)
        od_group._outputs.asarray()[:] = snap

    def _set_od_conditions(self, alt, dTs, power):
        """Set flight conditions and power level on the OD point.

        In dry mode, 'power' is the Tt4 target (degR) and the afterburner is
        unlit (Tt7 command 0).
        In wet mode, 'power' is the T7 (Tt7) target (degR); Tt4 is fixed at mil_Tt4.
        """
        pt = self.od_pt
        self.prob.set_val(f'{pt}.fc.alt', alt, units='ft')
        self.prob.set_val(f'{pt}.fc.dTs', dTs, units='degR')
        self.prob.set_val(f'{pt}.fc.MN', self.mach)
        tt4, tt7 = (self.mil_Tt4, power) if self.afterburn else (power, 0.)
        self.prob.set_val(f'{pt}.balance.rhs:FAR_core', tt4, units='degR')
        self.prob.set_val(f'{pt}.aug_ctrl.Tt7_cmd', tt7, units='degR')

    def _state_at_bounds(self):
        """Return True if any OD BalanceComp state is at/near its bound.

        Newton can satisfy `_iter_count < maxiter` while the state is clipped
        at a BalanceComp lower/upper bound — producing a residual minimum
        that's not a real solution. Bound saturation is the dead-giveaway.
        """
        pt = self.od_pt
        for key, (lo, hi) in _OD_BOUNDS.items():
            try:
                val = _scalar(self.prob[f'{pt}.{key}'])
            except Exception as err:
                # Fail loudly rather than skipping the state. Every key in
                # _OD_BOUNDS exists on the OD point, so an unreadable one means the
                # table has drifted from the model — and silently skipping it
                # would retire this guard for that state without a symptom,
                # which is the exact false-convergence failure it exists to
                # catch.
                raise SweepConfigurationError(
                    f"Cannot read OD balance state '{pt}.{key}' while checking "
                    f"for bound saturation ({type(err).__name__}: {err}). "
                    f"_OD_BOUNDS in sweep_utils.py mirrors the bounds declared "
                    f"in engine_model.py's off-design block; if a balance was "
                    f"renamed or removed there, update it here too."
                ) from err
            if lo is not None and hi is not None:
                tol = _BOUND_TOL_FRAC * (hi - lo)
                if val > hi - tol or val < lo + tol:
                    return True
            elif hi is None:
                # Half-bounded — only check the lower bound, scale tol off lo.
                if val < lo * (1.0 + _BOUND_TOL_FRAC):
                    return True
            elif val > hi * (1.0 - _BOUND_TOL_FRAC):
                return True
        return False

    def _target_met(self, power):
        """Verify the FAR balances actually drove T4 (and T7, if wet) to target.

        Belt-and-suspenders against false-converged states where Newton
        reports success but the burner/afterburner exit temps are far from
        the requested target — e.g. stalled-LP-spool basins.
        """
        pt = self.od_pt
        try:
            t4 = _scalar(self.prob.get_val(f'{pt}.burner.Fl_O:tot:T',
                                           units='degR'))
        except Exception:
            return False
        if self.afterburn:
            if abs(t4 - self.mil_Tt4) > _TARGET_TOL_DEGR:
                return False
            try:
                t7 = _scalar(self.prob.get_val(f'{pt}.afterburner.Fl_O:tot:T',
                                               units='degR'))
            except Exception:
                return False
            return abs(t7 - power) <= _TARGET_TOL_DEGR
        return abs(t4 - power) <= _TARGET_TOL_DEGR

    def _run_bridge(self):
        """Run a bridge point, accepting any forward progress.

        Bridges exist only to warm-start Newton toward the next real sweep
        point — they do not need to converge to their intermediate target.
        Partial progress (e.g. T7 moved from 3800 toward 3766 without fully
        landing on 3766) is still a better warm-start than the previous state.

        Only hard failures (bound saturation / NaN) trigger a state restore;
        an unconverged-but-sane intermediate state is kept.  To allow partial
        convergence without an AnalysisError, err_on_non_converge is
        temporarily disabled for the duration of this run.
        """
        newton = self._od_newton()
        newton.options['err_on_non_converge'] = False
        try:
            self.prob.run_model()
        except (om.AnalysisError, RuntimeError) as err:
            log.warning("Bridge point failed (%s): %s", type(err).__name__, err)
            return False
        finally:
            newton.options['err_on_non_converge'] = True
        return not self._state_at_bounds()

    def _run_point(self, power=None):
        """Run the model. Return True only if Newton actually converged.

        Three independent checks must pass:
          1. prob.run_model() didn't raise (Newton hit atol/rtol).
          2. No BalanceComp state is clipped at its lower/upper bound.
          3. The burner/AB exit temps match the requested power target.

        `power` may be None — in that case the target check is skipped (used
        when re-verifying state after a bridge restore, where power doesn't
        correspond to the most recently set conditions).

        RuntimeError is caught alongside AnalysisError because a sufficiently
        degenerate point doesn't fail in Newton at all — it fails underneath
        it, in the linear solve, where DirectSolver raises RuntimeError for a
        singular or rank-deficient Jacobian. That is still just one bad point;
        letting it propagate would abandon an entire multi-hundred-point sweep
        over a corner the deck is expected to lose anyway.

        Only those two. Everything else propagates: a mistyped variable or a
        drifted bounds table raises KeyError, TypeError or
        SweepConfigurationError, none of which describe a point that merely
        failed to converge, and all of which should stop the run rather than
        be recorded as 264 unexplained failures.
        """
        try:
            self.prob.run_model()
        except (om.AnalysisError, RuntimeError) as err:
            # Warning, not debug: this is the only record that a point failed
            # for a reason other than "Newton ran out of iterations", and a
            # burst of them across every point is the signature of a real
            # problem rather than a hard corner.
            log.warning("Point failed (%s): %s", type(err).__name__, err)
            return False
        if self._state_at_bounds():
            return False
        if power is not None and not self._target_met(power):
            return False
        return True

    def run_sweep(self, sweep_points, bridge_threshold=None, max_bridge_steps=5):
        """
        Execute the sweep, collecting results for each real (non-bridge) point.

        Parameters
        ----------
        sweep_points : list of dict
            Ordered sweep points from build_snake_sweep().
            Each dict has keys: 'alt', 'dTs', 'power'.
        bridge_threshold : dict, optional
            Max allowed jump per variable before bridge points are inserted.
            Example: {'alt': 5000, 'dTs': 30}
            Defaults to {'alt': 5000, 'dTs': 30} if not provided.
        max_bridge_steps : int
            Number of intermediate bridge points when threshold is exceeded.

        Returns
        -------
        pandas.DataFrame
            One row per converged sweep point with performance columns.
        """
        if bridge_threshold is None:
            bridge_threshold = {'alt': 5000, 'dTs': 30}

        results = []
        prev_pt = None
        power_label = "Tt7" if self.afterburn else "Tt4"
        n_total = len(sweep_points)

        if self._last_good_state is None:
            # Anchor the fallback on the state we were handed. The problem
            # arrives with OD converged at design conditions (see
            # problems.build_problem), which is a
            # perfectly good warm start. Without this, a failure before the
            # first success has nothing to restore from, so the model stays in
            # whatever state Newton abandoned and every later point
            # warm-starts from it — one bad point at the head of the sweep
            # takes the entire deck with it.
            self._last_good_state = self._snapshot_state()

        for i, pt_cond in enumerate(sweep_points):
            # Check if bridge points are needed
            if prev_pt is not None:
                needs_bridge = any(
                    abs(pt_cond[key] - prev_pt[key]) > bridge_threshold.get(key, float('inf'))
                    for key in ('alt', 'dTs', 'power')
                )
                if needs_bridge:
                    bridges = generate_bridge_points(prev_pt, pt_cond, max_bridge_steps)
                    for j, bp in enumerate(bridges, 1):
                        print(f"  [BRIDGE {j}/{len(bridges)}] alt={bp['alt']:6.0f} ft  "
                              f"dTs={bp['dTs']:+5.1f} R  MN={self.mach:.3f}  "
                              f"{power_label}={bp['power']:6.1f} R")
                        self._set_od_conditions(bp['alt'], bp['dTs'], bp['power'])
                        bridge_ok = self._run_bridge()
                        if not bridge_ok and self._last_good_state is not None:
                            # Hard failure (bound saturation / NaN) — restore
                            # so the next bridge doesn't inherit blown-up state.
                            self._restore_state(self._last_good_state)

            # Run the actual sweep point — fast linesearch first, fall back to
            # safe (Armijo backtracking) only if the fast attempt diverges.
            print(f"  [SWEEP  {i+1:3d}/{n_total}] alt={pt_cond['alt']:6.0f} ft  "
                  f"dTs={pt_cond['dTs']:+5.1f} R  MN={self.mach:.3f}  "
                  f"{power_label}={pt_cond['power']:6.1f} R", end="", flush=True)
            self._set_od_conditions(pt_cond['alt'], pt_cond['dTs'], pt_cond['power'])

            self._set_linesearch_mode('fast')
            converged = self._run_point(power=pt_cond['power'])
            mode_used = 'fast'

            if not converged:
                # Restore last known-good state (Newton may have left NaNs/junk
                # in the state vector) and retry with safe linesearch.
                if self._last_good_state is not None:
                    self._restore_state(self._last_good_state)
                self._set_od_conditions(pt_cond['alt'], pt_cond['dTs'], pt_cond['power'])
                self._set_linesearch_mode('safe')
                converged = self._run_point(power=pt_cond['power'])
                self._set_linesearch_mode('fast')  # restore default for next point
                mode_used = 'safe'

            if converged:
                row = extract_od_results(self.prob, self.od_pt)
                results.append(row)
                self._last_good_state = self._snapshot_state()
                tag = "" if mode_used == 'fast' else " (safe)"
                print(f"  → converged{tag}")
            else:
                # Both attempts failed — restore last-good state so the next
                # sweep point doesn't warm-start from corrupted state and
                # cascade more false convergences.
                if self._last_good_state is not None:
                    self._restore_state(self._last_good_state)
                print("  → FAILED")
                log.warning("Point did not converge: alt=%.0f dTs=%.1f power=%.0f",
                            pt_cond['alt'], pt_cond['dTs'], pt_cond['power'])

            prev_pt = pt_cond

        log.info("Sweep complete: %d / %d points converged",
                 len(results), len(sweep_points))

        return pd.DataFrame(results)
