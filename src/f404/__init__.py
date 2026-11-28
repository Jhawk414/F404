"""F404 mixed-flow turbofan cycle model.

Application code for the GE F404 cycle deck, built on NASA Glenn's pyCycle.
Kept separate from the vendored upstream ``pycycle`` library at the repo root.

The public Python API (docs/guide/python.md, docs/adr/0005-public-python-api.md)::

    from f404 import DesignInputs, design, run_point, sweep
"""
from f404.config import DesignInputs, PlaSchedule
from f404.problems import Engine, design
from f404.sweep_full_envelope import run_point, sweep

__all__ = ['DesignInputs', 'Engine', 'PlaSchedule', 'design', 'run_point', 'sweep']
