import numpy as np
import openmdao.api as om

import pycycle.api as pyc


def _dynamic_head(g, m):
    """Kumar (1980) Eq. 13: q/Pt at Mach ``m``, and its partials in g and m."""
    x = 1. + 0.5 * (g - 1.) * m**2
    e = -g / (g - 1.)
    q = 0.5 * g * m**2 * x**e
    dq_dm = g * m * x**e * (1. - 0.5 * g * m**2 / x)
    dq_dg = q * (1. / g + np.log(x) / (g - 1.)**2 - 0.5 * g * m**2 / ((g - 1.) * x))
    return q, dq_dg, dq_dm


def _flow_function(g):
    """Choked flow function Γ(γ) = √γ·(2/(γ+1))^((γ+1)/(2(γ−1))), and d ln Γ/dγ."""
    r = 2. / (g + 1.)
    gam = np.sqrt(g) * r**((g + 1.) / (2. * (g - 1.)))
    dln = 0.5 / g - np.log(r) / (g - 1.)**2 - 0.5 / (g - 1.)
    return gam, dln


class AugmentorControl(om.ExplicitComponent):
    """Afterburner command and pressure loss for one OD topology, dry to max AB.

    ``Tt7_cmd`` at or below the augmentor inlet temperature ``Tt_in`` (Tt6)
    means dry, so 0 is the usual dry command.

    - ``Tt7 = max(Tt7_cmd, Tt_in)`` is the FAR_ab balance target. When dry, it
      drives FAR_ab to its lower bound of exactly 0, and the Combustor is a Duct.
    - ``dPqP = q * (CD + eta * (tau - 1))``, ``tau = Tt7 / Tt_in``: a
      flameholder drag loss plus a Rayleigh (momentum) loss that is 0 dry.
      ``q`` is the approach dynamic head over Pt at the flameholder Mach
      ``k_M * MN_in`` (Kumar 1980, Eq. 13). ``dPqP_dry = q * CD`` is the
      loss the same inlet state would see dry (``NozzleSchedule``).
    """

    def setup(self):
        self.add_input('Tt7_cmd', val=0., units='degR')
        self.add_input('Tt_in', val=1500., units='degR')
        self.add_input('MN_in', val=0.45)
        self.add_input('gamma_in', val=1.34)
        self.add_input('k_M', val=0.5, desc='flameholder approach Mach / MN_in')
        self.add_input('CD', val=0.65, desc='flameholder cold drag coefficient')
        self.add_input('eta', val=1., desc='momentum (Rayleigh) loss factor')

        self.add_output('Tt7', val=1500., units='degR')
        self.add_output('dPqP', val=0.)
        self.add_output('dPqP_dry', val=0.)

        self.declare_partials('Tt7', ['Tt7_cmd', 'Tt_in'])
        self.declare_partials('dPqP', ['Tt7_cmd', 'Tt_in', 'MN_in', 'gamma_in',
                                       'k_M', 'CD', 'eta'])
        self.declare_partials('dPqP_dry', ['MN_in', 'gamma_in', 'k_M', 'CD'])

    def compute(self, inputs, outputs):
        cmd, t_in = inputs['Tt7_cmd'], inputs['Tt_in']
        tt7 = np.where(cmd.real > t_in.real, cmd, t_in)
        q, _, _ = _dynamic_head(inputs['gamma_in'], inputs['k_M'] * inputs['MN_in'])
        outputs['Tt7'] = tt7
        outputs['dPqP_dry'] = q * inputs['CD']
        outputs['dPqP'] = q * (inputs['CD'] + inputs['eta'] * (tt7 / t_in - 1.))

    def compute_partials(self, inputs, J):
        cmd, t_in, k_m, mn = inputs['Tt7_cmd'], inputs['Tt_in'], inputs['k_M'], inputs['MN_in']
        cd, eta = inputs['CD'], inputs['eta']
        wet = (cmd > t_in).astype(float)
        tau = np.where(wet, cmd / t_in, 1.)
        q, dq_dg, dq_dm = _dynamic_head(inputs['gamma_in'], k_m * mn)
        loss_per_q = cd + eta * (tau - 1.)

        J['Tt7', 'Tt7_cmd'] = wet
        J['Tt7', 'Tt_in'] = 1. - wet

        J['dPqP', 'Tt7_cmd'] = wet * q * eta / t_in
        J['dPqP', 'Tt_in'] = -wet * q * eta * cmd / t_in**2
        J['dPqP', 'MN_in'] = loss_per_q * dq_dm * k_m
        J['dPqP', 'k_M'] = loss_per_q * dq_dm * mn
        J['dPqP', 'gamma_in'] = loss_per_q * dq_dg
        J['dPqP', 'CD'] = q
        J['dPqP', 'eta'] = q * (tau - 1.)

        J['dPqP_dry', 'MN_in'] = cd * dq_dm * k_m
        J['dPqP_dry', 'k_M'] = cd * dq_dm * mn
        J['dPqP_dry', 'gamma_in'] = cd * dq_dg
        J['dPqP_dry', 'CD'] = q


class NozzleSchedule(om.ExplicitComponent):
    """Nozzle throat area A8 for one OD topology, dry to max AB (#8, wet half).

    Choked-throat continuity with the dry nozzle. The throat passes the wet
    flow (``_out``, afterburner exit) at the gas-generator exit state
    (``_in``, afterburner inlet) that the dry nozzle would see::

        A8 = A8_dsn * (W_out/W_in) * sqrt(R_out*Tt_out / (R_in*Tt_in))
                    * Γ(gam_in)/Γ(gam_out) * (1 - dPqP_dry)/(1 - dPqP)

    Lighting the afterburner then leaves W and Pt6, and with them the whole
    gas generator, where the dry engine put them. When dry, the factor is 1 and
    A8 is the DESIGN throat. A dry (part-power) opening waits for #25/#30.
    """

    def setup(self):
        self.add_input('A8_dsn', val=200., units='inch**2')
        for name, val, units in (('W_in', 150., 'lbm/s'), ('W_out', 150., 'lbm/s'),
                                 ('Tt_in', 1500., 'degR'), ('Tt_out', 1500., 'degR'),
                                 ('R_in', 53.3, 'ft*lbf/(lbm*degR)'),
                                 ('R_out', 53.3, 'ft*lbf/(lbm*degR)'),
                                 ('gam_in', 1.34, None), ('gam_out', 1.34, None),
                                 ('dPqP', 0., None), ('dPqP_dry', 0., None)):
            self.add_input(name, val=val, units=units)
        self.add_output('A8', val=200., units='inch**2')
        self.declare_partials('A8', '*')

    def compute(self, inputs, outputs):
        flow_in, _ = _flow_function(inputs['gam_in'])
        flow_out, _ = _flow_function(inputs['gam_out'])
        outputs['A8'] = (inputs['A8_dsn'] * (inputs['W_out'] / inputs['W_in'])
                         * np.sqrt(inputs['R_out'] * inputs['Tt_out']
                                   / (inputs['R_in'] * inputs['Tt_in']))
                         * flow_in / flow_out
                         * (1. - inputs['dPqP_dry']) / (1. - inputs['dPqP']))

    def compute_partials(self, inputs, J):
        out = {}
        self.compute(inputs, out)
        a8 = out['A8']
        # A8 is a product of powers, so each partial is A8 * exponent / factor.
        for name, power in (('A8_dsn', 1.), ('W_out', 1.), ('W_in', -1.),
                            ('R_out', .5), ('Tt_out', .5), ('R_in', -.5), ('Tt_in', -.5)):
            J['A8', name] = power * a8 / inputs[name]
        J['A8', 'gam_in'] = a8 * _flow_function(inputs['gam_in'])[1]
        J['A8', 'gam_out'] = -a8 * _flow_function(inputs['gam_out'])[1]
        J['A8', 'dPqP_dry'] = -a8 / (1. - inputs['dPqP_dry'])
        J['A8', 'dPqP'] = a8 / (1. - inputs['dPqP'])


class MixedFlowTurbofan(pyc.Cycle):
    """The F404 cycle. DESIGN is dry mil; OD runs every power setting.

    The afterburner is a ``Duct`` at DESIGN, which never lights, and a
    ``Combustor`` off-design, where ``aug_ctrl.Tt7_cmd`` selects the regime
    (0 = dry) and ``a8_sched`` sets the nozzle throat.
    """

    def setup(self):
        design = self.options['design']
        afterburn = not design

        USE_TABULAR = True

        if USE_TABULAR:
            self.options['thermo_method'] = 'TABULAR'
            self.options['thermo_data'] = pyc.AIR_JETA_TAB_SPEC
            FUEL_TYPE = "FAR"
        else:
            self.options['thermo_method'] = 'TABULAR'
            self.options['thermo_data'] = pyc.species_data.janaf
            FUEL_TYPE = "Jet-A(g)"

        self.add_subsystem('fc', pyc.FlightConditions())
        # Inlet Components
        self.add_subsystem('inlet', pyc.Inlet())
        self.add_subsystem('inlet_duct', pyc.Duct())
        # Fan Components - Split here for CFD integration Add a CFDStart Component
        self.add_subsystem('fan', pyc.Compressor(map_data=pyc.AXI5,
                                             map_extrap=True),promotes_inputs=[('Nmech','LP_Nmech')])
        self.add_subsystem('splitter', pyc.Splitter())
        # Core Stream components
        self.add_subsystem('splitter_core_duct', pyc.Duct())
        # self.add_subsystem('lpc', pyc.Compressor(map_data=pyc.LPCMap, map_extrap=True),
        #                                      promotes_inputs=[('Nmech','LP_Nmech')])
        # self.add_subsystem('lpc_duct', pyc.Duct())
        self.add_subsystem('hpc', pyc.Compressor(map_data=pyc.HPCMap,
                                        bleed_names=['cool1'],map_extrap=True),promotes_inputs=[('Nmech','HP_Nmech')])
        self.add_subsystem('bld3', pyc.BleedOut(bleed_names=['cool3']))

        self.add_subsystem('burner', pyc.Combustor(fuel_type=FUEL_TYPE))

        self.add_subsystem('hpt', pyc.Turbine(map_data=pyc.HPTMap,
                                          bleed_names=['cool3'],map_extrap=True),promotes_inputs=[('Nmech','HP_Nmech')])
        self.add_subsystem('hpt_duct', pyc.Duct())
        self.add_subsystem('lpt', pyc.Turbine(map_data=pyc.LPTMap,
                                        bleed_names=['cool1'],map_extrap=True), promotes_inputs=[('Nmech','LP_Nmech')])
        self.add_subsystem('lpt_duct', pyc.Duct())
        # Bypass Components
        self.add_subsystem('bypass_duct', pyc.Duct())
        # Mixer component
        self.add_subsystem('mixer', pyc.Mixer(designed_stream=1))
        self.add_subsystem('mixer_duct', pyc.Duct())
        # Afterburner Components — a Duct at DESIGN, which never lights. Off
        # design, a Combustor at every power setting. A Combustor with its
        # fuel-air ratio *fixed* at zero produced a rank-deficient Jacobian at
        # part-power dry conditions (51c9bb6). The OD Combustor instead carries
        # a FAR_ab balance whose lower bound of exactly 0 is the dry root
        # (ADR-0002). aug_ctrl sets the augmentor loss on both points.
        self.add_subsystem('aug_ctrl', AugmentorControl())
        if afterburn:
            self.add_subsystem('afterburner', pyc.Combustor(fuel_type=FUEL_TYPE))
            self.add_subsystem('a8_sched', NozzleSchedule())
        else:
            self.add_subsystem('afterburner', pyc.Duct())

        # Nozzle
        self.add_subsystem('mixed_nozz', pyc.Nozzle(nozzType='CD', lossCoef='Cfg'))

        # Mechanical components
        self.add_subsystem('lp_shaft', pyc.Shaft(num_ports=2),promotes_inputs=[('Nmech','LP_Nmech')]) #OG: 3
        self.add_subsystem('hp_shaft', pyc.Shaft(num_ports=2),promotes_inputs=[('Nmech','HP_Nmech')])

        # Aggregating component — only one burner in dry mode (no afterburner fuel)
        n_burners = 2 if afterburn else 1
        self.add_subsystem('perf', pyc.Performance(num_nozzles=1, num_burners=n_burners))

        # Connect flow paths
        self.pyc_connect_flow('fc.Fl_O', 'inlet.Fl_I')
        self.pyc_connect_flow('inlet.Fl_O', 'inlet_duct.Fl_I')
        self.pyc_connect_flow('inlet_duct.Fl_O', 'fan.Fl_I')
        self.pyc_connect_flow('fan.Fl_O', 'splitter.Fl_I')
        # Core connections
        self.pyc_connect_flow('splitter.Fl_O1', 'splitter_core_duct.Fl_I') # splitter Fl_O1 goes thru core, Fl_O2 is bypass
        self.pyc_connect_flow('splitter_core_duct.Fl_O', 'hpc.Fl_I') # connect to hpc.Fl_I

        self.pyc_connect_flow('hpc.Fl_O', 'bld3.Fl_I')

        self.pyc_connect_flow('bld3.Fl_O', 'burner.Fl_I')
        self.pyc_connect_flow('burner.Fl_O', 'hpt.Fl_I')

        self.pyc_connect_flow('hpt.Fl_O', 'hpt_duct.Fl_I')
        self.pyc_connect_flow('hpt_duct.Fl_O', 'lpt.Fl_I')
        self.pyc_connect_flow('lpt.Fl_O', 'lpt_duct.Fl_I')
        self.pyc_connect_flow('lpt_duct.Fl_O','mixer.Fl_I1')
        # Bypass Connections
        self.pyc_connect_flow('splitter.Fl_O2', 'bypass_duct.Fl_I') # splitter Fl_O1 goes thru core, Fl_O2 is bypass
        self.pyc_connect_flow('bypass_duct.Fl_O', 'mixer.Fl_I2')

        #Mixer Connections
        self.pyc_connect_flow('mixer.Fl_O', 'mixer_duct.Fl_I')
        # Afterburner
        self.pyc_connect_flow('mixer_duct.Fl_O','afterburner.Fl_I')

        self.connect('mixer_duct.Fl_O:tot:T', 'aug_ctrl.Tt_in')
        self.connect('mixer_duct.Fl_O:stat:MN', 'aug_ctrl.MN_in')
        self.connect('mixer_duct.Fl_O:tot:gamma', 'aug_ctrl.gamma_in')
        self.connect('aug_ctrl.dPqP', 'afterburner.dPqP')

        # Nozzle
        self.pyc_connect_flow('afterburner.Fl_O','mixed_nozz.Fl_I')

        # Connect cooling flows
        self.pyc_connect_flow('hpc.cool1', 'lpt.cool1', connect_stat=False)
        self.pyc_connect_flow('bld3.cool3', 'hpt.cool3', connect_stat=False)

        # Make additional model connections
        self.connect('inlet.Fl_O:tot:P', 'perf.Pt2')
        self.connect('hpc.Fl_O:tot:P', 'perf.Pt3')
        self.connect('burner.Wfuel', 'perf.Wfuel_0')
        if afterburn:
            self.connect('afterburner.Wfuel', 'perf.Wfuel_1')
        self.connect('inlet.F_ram', 'perf.ram_drag')
        self.connect('mixed_nozz.Fg', 'perf.Fg_0')

        # Attach Element Torques to Shaft Ports
        self.connect('fan.trq', 'lp_shaft.trq_0')
        #self.connect('lpc.trq', 'lp_shaft.trq_1')
        self.connect('hpc.trq', 'hp_shaft.trq_0')
        self.connect('hpt.trq', 'hp_shaft.trq_1')
        self.connect('lpt.trq', 'lp_shaft.trq_1') #LP spool hot section
        self.connect('fc.Fl_O:stat:P', 'mixed_nozz.Ps_exhaust')

        # Add BALANCE components to close the implicit components
        balance = self.add_subsystem('balance', om.BalanceComp())
        if design:
            balance.add_balance('W', lower=25, upper=200., units='lbm/s', eq_units='lbf') #OG lower = 1e-3
            self.connect('balance.W', 'fc.W')
            self.connect('perf.Fn', 'balance.lhs:W')
            # self.add_subsystem('wDV',IndepVarComp('wDes',100,units='lbm/s'))
            # self.connect('wDV.wDes','fc.W')

            balance.add_balance('BPR', eq_units=None, lower=0.25, upper=0.80, val=0.65)
            self.connect('balance.BPR', 'splitter.BPR')
            self.connect('mixer.ER', 'balance.lhs:BPR')

            balance.add_balance('FAR_core', eq_units='degR', lower=1e-4, val=.017)
            self.connect('balance.FAR_core', 'burner.Fl_I:FAR')
            self.connect('burner.Fl_O:tot:T', 'balance.lhs:FAR_core')

            balance.add_balance('hpt_PR', val=2.0, lower=1.001, upper=3.0, eq_units='hp', use_mult=True, mult_val=-1)
            self.connect('balance.hpt_PR', 'hpt.PR')
            self.connect('hp_shaft.pwr_in', 'balance.lhs:hpt_PR')
            self.connect('hp_shaft.pwr_out', 'balance.rhs:hpt_PR')

            balance.add_balance('lpt_PR', val=2.5, lower=1.001, upper=3.5, eq_units='hp', use_mult=True, mult_val=-1)
            self.connect('balance.lpt_PR', 'lpt.PR')
            self.connect('lp_shaft.pwr_in', 'balance.lhs:lpt_PR')
            self.connect('lp_shaft.pwr_out', 'balance.rhs:lpt_PR')

        else:

            # W floats until the nozzle throat matches the commanded A8 (rhs:W).
            balance.add_balance('W', lower=25, upper=200., units='lbm/s', eq_units='inch**2') #OG lower = 1e-3
            self.connect('balance.W', 'fc.W')
            self.connect('mixed_nozz.Throat:stat:area', 'balance.lhs:W')

            # Nozzle schedule: the DESIGN throat when dry, opened when wet just enough
            # to pass the hotter flow at the dry gas-generator state, so
            # lighting the afterburner doesn't move the fan or the core.
            self.connect('a8_sched.A8', 'balance.rhs:W')
            for port, src in (('W_in', 'mixer_duct.Fl_O:stat:W'),
                              ('W_out', 'afterburner.Fl_O:stat:W'),
                              ('Tt_in', 'mixer_duct.Fl_O:tot:T'),
                              ('Tt_out', 'afterburner.Fl_O:tot:T'),
                              ('R_in', 'mixer_duct.Fl_O:tot:R'),
                              ('R_out', 'afterburner.Fl_O:tot:R'),
                              ('gam_in', 'mixer_duct.Fl_O:tot:gamma'),
                              ('gam_out', 'afterburner.Fl_O:tot:gamma'),
                              ('dPqP', 'aug_ctrl.dPqP'),
                              ('dPqP_dry', 'aug_ctrl.dPqP_dry')):
                self.connect(src, f'a8_sched.{port}')

            balance.add_balance('BPR', lower=0.1, upper=1.0, val=0.34, eq_units='psi')
            self.connect('balance.BPR', 'splitter.BPR')
            self.connect('mixer.Fl_I1_calc:stat:P', 'balance.lhs:BPR')
            self.connect('bypass_duct.Fl_O:stat:P', 'balance.rhs:BPR')

            balance.add_balance('FAR_core', eq_units='degR', lower=1e-4, upper=.06, val=.017)
            self.connect('balance.FAR_core', 'burner.Fl_I:FAR')
            self.connect('burner.Fl_O:tot:T', 'balance.lhs:FAR_core')

            # Lower bound exactly 0: when dry, aug_ctrl targets the inlet
            # temperature and the root sits on the bound.
            balance.add_balance('FAR_ab', eq_units='degR', lower=0., upper=.06, val=0.)
            self.connect('balance.FAR_ab', 'afterburner.Fl_I:FAR')
            self.connect('afterburner.Fl_O:tot:T', 'balance.lhs:FAR_ab')
            self.connect('aug_ctrl.Tt7', 'balance.rhs:FAR_ab')

            balance.add_balance('LP_Nmech', val=1., units='rpm', lower=500., eq_units='hp', use_mult=True, mult_val=-1)
            self.connect('balance.LP_Nmech', 'LP_Nmech')
            self.connect('lp_shaft.pwr_in', 'balance.lhs:LP_Nmech')
            self.connect('lp_shaft.pwr_out', 'balance.rhs:LP_Nmech')

            balance.add_balance('HP_Nmech', val=1., units='rpm', lower=500., eq_units='hp', use_mult=True, mult_val=-1)
            self.connect('balance.HP_Nmech', 'HP_Nmech')
            self.connect('hp_shaft.pwr_in', 'balance.lhs:HP_Nmech')
            self.connect('hp_shaft.pwr_out', 'balance.rhs:HP_Nmech')

        # Off design
        newton = self.nonlinear_solver = om.NewtonSolver()
        newton.options['atol'] = 1e-5 #1e-6
        newton.options['rtol'] = 1e-9 #1e-10
        newton.options['iprint'] = 1 #2
        newton.options['maxiter'] = 50  # SweepRunner caps sweeps at SWEEP_MAXITER
        newton.options['solve_subsystems'] = True
        newton.options['max_sub_solves'] = 100 #100
        newton.options['reraise_child_analysiserror'] = False
        # Raise AnalysisError when Newton fails to drive residual below atol/rtol
        # within maxiter. Without this, the solver silently returns whatever
        # bound-clipped or stalled state it landed in — and SweepRunner would
        # report it as "converged", producing garbage rows in the cycle deck.
        newton.options['err_on_non_converge'] = True
        # ArmijoGoldsteinLS with maxiter=0 by default — skips the Armijo
        # backtracking loop entirely and behaves like BoundsEnforceLS (fast).
        # SweepRunner toggles maxiter to 5 on per-point failure to enable
        # backtracking as a fallback strategy. This avoids paying Armijo's
        # overhead on the ~95% of points that converge cleanly without it.
        newton.linesearch = om.ArmijoGoldsteinLS(bound_enforcement='scalar')
        newton.linesearch.options['maxiter'] = 0  # SweepRunner bumps to 5 on retry
        newton.linesearch.options['rho'] = 0.5    # halve step on rejection
        newton.linesearch.options['c'] = 0.1      # Armijo sufficient-decrease constant
        newton.linesearch.options['iprint'] = -1  # suppress per-backtrack residual lines


        self.linear_solver = om.DirectSolver(assemble_jac=True)

        super().setup()
