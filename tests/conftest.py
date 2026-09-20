"""Shared fixtures for the F404 test suite.

The two solved-problem fixtures are session-scoped: building and converging
a DESIGN + OD point takes a couple of seconds, and most tests only read from
the result. Tests that mutate solver state (setting new flight conditions and
re-solving) build their own problem rather than taking these.
Warning suppression lives in pyproject.toml's filterwarnings, not here:
pytest re-applies its own configuration around each test, so module-level
warnings.filterwarnings() calls in a conftest are overridden and silently do
nothing.
"""
import pytest

from F404_pycycle.problems import build_dry_problem, build_wet_problem


@pytest.fixture(scope='session')
def dry_problem():
    """Converged dry (afterburner off) problem. Read-only — do not re-solve."""
    return build_dry_problem(verbose=False)


@pytest.fixture(scope='session')
def wet_problem():
    """Converged wet (afterburning) problem. Read-only — do not re-solve."""
    return build_wet_problem(verbose=False)
