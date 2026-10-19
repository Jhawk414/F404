import pycycle.api as pyc

from f404.engine_model import MixedFlowTurbofan

# Augmentor pressure loss, dPqP = q * (AB_CD + AB_ETA * (Tt7/Tt6 - 1)), with q
# the dynamic head over Pt at the flameholder approach Mach AB_K_M * MN6
# (Kumar 1980, Eq. 13; #33). Literature constants: the RM12 rig's approach
# Mach is ~0.22 against MN6 = 0.446 here; C_D 0.6-0.7 at 29-31% blockage;
# eta = 1 is small-Mach Rayleigh. The cold part (~2.1%) also applies to the
# DESIGN Duct, so it is in the sizing. See docs/adr/0002-single-od-topology.md.
AB_K_M = 0.5
AB_CD = 0.65
AB_ETA = 1.0


class MPMixedFlowTurbofan(pyc.MPCycle):
    """One sized engine and one off-design point for every power setting.

    DESIGN sizes the engine at dry mil power, with the afterburner as a Duct.
    ``OD`` runs on that geometry with the afterburner as a Combustor whose
    commanded Tt7 (``aug_ctrl.Tt7_cmd``) selects the regime: 0, or anything
    at or below the augmentor inlet temperature, is dry. See ADR-0002.
    """

    od_pt = 'OD'

    def setup(self):
        # Create design instance of model — dry mil sizes the gas generator
        self.pyc_add_pnt('DESIGN', MixedFlowTurbofan(design=True, thermo_method='TABULAR'))

        # BPR balance drives mixer.ER (= Pt_core/Pt_bypass) to 1.0 — equal total
        # pressures at mixer inlet. The actual BPR falls out of the thermodynamics.
        self.set_input_defaults('DESIGN.balance.rhs:BPR', 1.0, units=None)
        self.set_input_defaults('DESIGN.inlet.MN', 0.751)
        self.set_input_defaults('DESIGN.inlet_duct.MN', 0.4463)
        self.set_input_defaults('DESIGN.fan.MN', 0.4578)
        self.set_input_defaults('DESIGN.splitter.MN1', 0.3104)
        self.set_input_defaults('DESIGN.splitter.MN2', 0.4518)
        self.set_input_defaults('DESIGN.splitter_core_duct.MN', 0.3121)
        # self.set_input_defaults('DESIGN.lpc.MN', 0.3059)
        # self.set_input_defaults('DESIGN.lpc_duct.MN', 0.3563)
        self.set_input_defaults('DESIGN.hpc.MN', 0.2442)
        self.set_input_defaults('DESIGN.bld3.MN', 0.3000)
        self.set_input_defaults('DESIGN.burner.MN', 0.1025)
        self.set_input_defaults('DESIGN.hpt.MN', 0.3650)
        self.set_input_defaults('DESIGN.hpt_duct.MN', 0.3063)
        self.set_input_defaults('DESIGN.lpt.MN', 0.4127)
        self.set_input_defaults('DESIGN.lpt_duct.MN', 0.4463)
        self.set_input_defaults('DESIGN.bypass_duct.MN', 0.4463)
        self.set_input_defaults('DESIGN.mixer_duct.MN', 0.4463)
        self.set_input_defaults('DESIGN.afterburner.MN', 0.1025)
        self.set_input_defaults('DESIGN.LP_Nmech', 10000, units='rpm')
        self.set_input_defaults('DESIGN.HP_Nmech', 14000, units='rpm')

        # Cycle parameters shared across all points
        self.pyc_add_cycle_param('hp_shaft.HPX', 250, units='hp')
        self.pyc_add_cycle_param('inlet.ram_recovery', 0.9990)
        self.pyc_add_cycle_param('inlet_duct.dPqP', 0.0107)
        self.pyc_add_cycle_param('splitter_core_duct.dPqP', 0.0048)
        # self.pyc_add_cycle_param('lpc_duct.dPqP', 0.0101)
        #self.pyc_add_cycle_param('burner.dPqP', 0.0540)
        self.pyc_add_cycle_param('hpt_duct.dPqP', 0.0051)
        self.pyc_add_cycle_param('lpt_duct.dPqP', 0.0107)
        self.pyc_add_cycle_param('bypass_duct.dPqP', 0.015) #0.0107
        self.pyc_add_cycle_param('mixer_duct.dPqP', 0.0107)
        self.pyc_add_cycle_param('aug_ctrl.k_M', AB_K_M)
        self.pyc_add_cycle_param('aug_ctrl.CD', AB_CD)
        self.pyc_add_cycle_param('aug_ctrl.eta', AB_ETA)
        #self.pyc_add_cycle_param('mixed_nozz.Cfg', 0.9933)
        self.pyc_add_cycle_param('hpc.cool1:frac_W', 0.050708) #0.050708
        self.pyc_add_cycle_param('hpc.cool1:frac_P', 0.5)
        self.pyc_add_cycle_param('hpc.cool1:frac_work', 0.5)

        self.pyc_add_cycle_param('bld3.cool3:frac_W', 0.11) #0.067214
        self.pyc_add_cycle_param('hpt.cool3:frac_P', 1.0)
        self.pyc_add_cycle_param('lpt.cool1:frac_P', 1.0)

        # Off-design point — conditions set by the calling script via prob.set_val()
        self.pyc_add_pnt(self.od_pt, MixedFlowTurbofan(design=False, thermo_method='TABULAR'))

        # Map scalars: transfer design compressor/turbine map scaling to OD
        self.pyc_connect_des_od('fan.s_PR', 'fan.s_PR')
        self.pyc_connect_des_od('fan.s_Wc', 'fan.s_Wc')
        self.pyc_connect_des_od('fan.s_eff', 'fan.s_eff')
        self.pyc_connect_des_od('fan.s_Nc', 'fan.s_Nc')

        self.pyc_connect_des_od('hpc.s_PR', 'hpc.s_PR')
        self.pyc_connect_des_od('hpc.s_Wc', 'hpc.s_Wc')
        self.pyc_connect_des_od('hpc.s_eff', 'hpc.s_eff')
        self.pyc_connect_des_od('hpc.s_Nc', 'hpc.s_Nc')

        self.pyc_connect_des_od('hpt.s_PR', 'hpt.s_PR')
        self.pyc_connect_des_od('hpt.s_Wp', 'hpt.s_Wp')
        self.pyc_connect_des_od('hpt.s_eff', 'hpt.s_eff')
        self.pyc_connect_des_od('hpt.s_Np', 'hpt.s_Np')

        self.pyc_connect_des_od('lpt.s_PR', 'lpt.s_PR')
        self.pyc_connect_des_od('lpt.s_Wp', 'lpt.s_Wp')
        self.pyc_connect_des_od('lpt.s_eff', 'lpt.s_eff')
        self.pyc_connect_des_od('lpt.s_Np', 'lpt.s_Np')

        # Nozzle throat: OD scales the DESIGN A8 (engine_model.NozzleSchedule)
        self.connect('DESIGN.mixed_nozz.Throat:stat:area', self.od_pt + '.a8_sched.A8_dsn')

        # Flow areas: transfer design station areas to OD
        self.pyc_connect_des_od('inlet.Fl_O:stat:area', 'inlet.area')
        self.pyc_connect_des_od('fan.Fl_O:stat:area', 'fan.area')
        self.pyc_connect_des_od('splitter.Fl_O1:stat:area', 'splitter.area1')
        self.pyc_connect_des_od('splitter.Fl_O2:stat:area', 'splitter.area2')
        self.pyc_connect_des_od('splitter_core_duct.Fl_O:stat:area', 'splitter_core_duct.area')
        # self.pyc_connect_des_od('lpc.Fl_O:stat:area', 'lpc.area')
        # self.pyc_connect_des_od('lpc_duct.Fl_O:stat:area', 'lpc_duct.area')
        self.pyc_connect_des_od('hpc.Fl_O:stat:area', 'hpc.area')
        self.pyc_connect_des_od('bld3.Fl_O:stat:area', 'bld3.area')
        self.pyc_connect_des_od('burner.Fl_O:stat:area', 'burner.area')
        self.pyc_connect_des_od('hpt.Fl_O:stat:area', 'hpt.area')
        self.pyc_connect_des_od('hpt_duct.Fl_O:stat:area', 'hpt_duct.area')
        self.pyc_connect_des_od('lpt.Fl_O:stat:area', 'lpt.area')
        self.pyc_connect_des_od('lpt_duct.Fl_O:stat:area', 'lpt_duct.area')
        self.pyc_connect_des_od('bypass_duct.Fl_O:stat:area', 'bypass_duct.area')
        self.pyc_connect_des_od('mixer.Fl_O:stat:area', 'mixer.area')
        self.pyc_connect_des_od('mixer.Fl_I1_calc:stat:area', 'mixer.Fl_I1_stat_calc.area')
        self.pyc_connect_des_od('mixer_duct.Fl_O:stat:area', 'mixer_duct.area')
        self.pyc_connect_des_od('afterburner.Fl_O:stat:area', 'afterburner.area')

        super().setup()
