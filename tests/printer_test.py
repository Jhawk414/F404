"""Tests for the console result formatter.

Nothing depends on these tables numerically, but they are how a run gets
eyeballed, and they hardcode a list of station and component names. Rename a
station in engine_model.py and the physics stays correct while every
interactive run ends in a KeyError — with no test to catch it, because
everything else reads the model programmatically.
"""
import io

import pytest

from F404_pycycle.printer import page_viewer, print_perf

# One table per component family. A missing section means a name in
# printer.py no longer matches the model.
TABLE_HEADINGS = ('FLOW STATION', 'COMPRESSOR', 'BURNER', 'TURBINE',
                  'MIXER', 'NOZZLE', 'SHAFT', 'BLEED')


def rendered(render, *args, **kwargs):
    out = io.StringIO()
    render(*args, file=out, **kwargs)
    return out.getvalue()


@pytest.mark.slow
@pytest.mark.parametrize('point', ['DESIGN', 'OD_dry'])
def test_page_viewer_renders_every_table_in_dry_mode(problem, point):
    prob, _ = problem

    out = rendered(page_viewer, prob, point, afterburn=False)

    assert point in out
    for heading in TABLE_HEADINGS:
        assert heading in out.upper(), f"{heading} table missing"


@pytest.mark.slow
def test_page_viewer_renders_every_table_in_wet_mode(problem):
    # The dry points' afterburner is a Duct and the wet point's is a
    # Combustor, and the printer asks both configurations for a burner table.
    prob, _ = problem

    out = rendered(page_viewer, prob, 'OD_wet')

    for heading in TABLE_HEADINGS:
        assert heading in out.upper(), f"{heading} table missing"


@pytest.mark.slow
def test_print_perf_reports_the_headline_numbers(problem):
    prob, _ = problem

    out = rendered(print_perf, prob, 'DESIGN')

    for label in ('Altd', 'Mach', 'Fnet', 'SFC', 'BPR', 'OPR'):
        assert label in out
