"""Shared fixtures for the F404 test suite.

The solved-problem fixture is session-scoped: building and converging the
DESIGN and both OD points takes a few seconds, and most tests only read from
the result. Tests that mutate solver state (setting new flight conditions and
re-solving) build their own problem rather than taking these.
Warning suppression lives in pyproject.toml's filterwarnings, not here:
pytest re-applies its own configuration around each test, so module-level
warnings.filterwarnings() calls in a conftest are overridden and silently do
nothing.
"""
import pytest

from F404_pycycle.problems import build_problem


@pytest.fixture(scope='session')
def problem():
    """Converged single-engine problem. Read-only — do not re-solve."""
    return build_problem(verbose=False)
