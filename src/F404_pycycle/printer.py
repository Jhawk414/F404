import sys

import pycycle.api as pyc


def print_perf(prob, ptName, file=None):
    """Print the headline performance numbers for one point."""
    # Resolved at call time, not as a default argument: pyCycle's own print_*
    # helpers bind sys.stdout at import, which makes their output impossible
    # to redirect afterwards.
    file = sys.stdout if file is None else file

    print('Altd  ', prob[ptName+'.fc.alt'], file=file)
    print('Mach  ', prob[ptName+'.fc.MN'], file=file); print(file=file)

    print('ṁ      ', prob[ptName+'.balance.W'], file=file) # Mass Flowrate
    print('Fg     ', prob[ptName+'.perf.Fg'], file=file) #uninstalled gross thrust
    print('Fnet   ', prob[ptName+'.perf.Fn'], file=file) #uninstalled net thrust
    print('SFC    ', prob[ptName+'.perf.TSFC'], file=file)

    print('BPR    ', prob[ptName+'.balance.BPR'], file=file)
    print('ER     ', prob[ptName+'.mixer.ER'], file=file); print(file=file)

    # OPR = pi_f * pi_hpc (since no LPC)
    print('OPR    ', prob[ptName+'.fan.PR']*prob[ptName+'.hpc.PR'], file=file)
    print('Fan PR ', prob[ptName+'.fan.PR'], file=file)
    print('HPC PR ', prob[ptName+'.hpc.PR'], file=file); print(file=file)
    print('HPT PR ', prob[ptName+'.hpt.PR'], file=file)
    print('LPT PR ', prob[ptName+'.lpt.PR'], file=file)


def page_viewer(prob, point, file=None):
    """Print the full station/component table set for one point."""
    file = sys.stdout if file is None else file

    flow_stations = ['fc.Fl_O', 'inlet.Fl_O', 'inlet_duct.Fl_O', 'fan.Fl_O', 'bypass_duct.Fl_O',
                     'splitter.Fl_O2', 'splitter.Fl_O1', 'splitter_core_duct.Fl_O',
                     'hpc.Fl_O', 'bld3.Fl_O', 'burner.Fl_O', #OG: had 'lpc.Fl_O', 'lpc_duct.Fl_O' before hpc.Fl_O
                     'hpt.Fl_O', 'hpt_duct.Fl_O', 'lpt_duct.Fl_O',
                     'mixer.Fl_O', 'mixer_duct.Fl_O', 'afterburner.Fl_O', 'mixed_nozz.Fl_O']

    compressors = ['fan', 'hpc'] #OG: lpc after hpc
    burners = ['burner', 'afterburner']
    turbines = ['hpt', 'lpt']
    shafts = ['hp_shaft', 'lp_shaft']

    print('*'*60, file=file)
    print('* ' + ' '*10 + point, file=file)
    print('*'*60, file=file)
    print_perf(prob, point, file=file)

    pyc.print_flow_station(prob, [point+"."+fl for fl in flow_stations], file=file)
    pyc.print_compressor(prob, [point+"."+c for c in compressors], file=file)
    pyc.print_burner(prob, [point+"."+b for b in burners], file=file)
    pyc.print_turbine(prob, [point+"."+turb for turb in turbines], file=file)
    pyc.print_mixer(prob, [point+'.mixer'], file=file)
    pyc.print_nozzle(prob, [point+'.mixed_nozz'], file=file)
    pyc.print_shaft(prob, [point+"."+s for s in shafts], file=file)
    pyc.print_bleed(prob, [point+'.hpc', point+'.bld3'], file=file)
