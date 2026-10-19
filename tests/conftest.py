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
import pytest

from f404.problems import build_problem


@pytest.fixture(scope='session')
def problem():
    """Converged single-engine problem, OD at SLS max AB. Read-only."""
    return build_problem(verbose=False)


@pytest.fixture(scope='session')
def dry_mil():
    """The same engine with OD re-solved unlit, at SLS mil. Read-only."""
    prob, mp = build_problem(verbose=False)
    prob.set_val(f'{mp.od_pt}.aug_ctrl.Tt7_cmd', 0., units='degR')
    prob.run_model()
    return prob, mp
