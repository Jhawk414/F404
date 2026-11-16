"""Shared fixtures for the F404 test suite.

The solved-problem fixtures are session-scoped: building and converging the
DESIGN and OD points takes a few seconds, and most tests only read from
the result. Tests that mutate solver state (setting new flight conditions and
re-solving) build their own problem rather than taking these.
Warning suppression lives in pyproject.toml's filterwarnings, not here:
pytest re-applies its own configuration around each test, so module-level
warnings.filterwarnings() calls in a conftest are overridden and silently do
nothing.
"""
import os
import tempfile

import pytest

from f404.problems import design


def pytest_configure(config):
    """Send OpenMDAO's ``<script>_out/`` folders to a temp dir, not the cwd.

    Tests that call ``om.Problem()`` directly bypass design()'s
    ``reports=False``. An explicit OPENMDAO_WORKDIR is respected.
    """
    os.environ.setdefault('OPENMDAO_WORKDIR', tempfile.mkdtemp(prefix='f404_om_'))


@pytest.fixture(scope='session')
def problem():
    """Converged single-engine problem, OD at SLS max AB. Read-only."""
    prob = design().prob
    return prob, prob.model


@pytest.fixture(scope='session')
def engine():
    """A default Engine for OD calls; each restores its anchor, so share it."""
    return design()


@pytest.fixture(scope='session')
def dry_mil():
    """The same engine with OD re-solved dry, at SLS mil. Read-only."""
    prob = design().prob
    mp = prob.model
    prob.set_val(f'{mp.od_pt}.aug_ctrl.Tt7_cmd', 0., units='degR')
    prob.run_model()
    return prob, mp
