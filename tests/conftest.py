"""Shared fixtures for the F404 test suite.

The two solved-problem fixtures are session-scoped: building and converging
a DESIGN + OD point takes a couple of seconds, and most tests only read from
the result. Tests that mutate solver state (setting new flight conditions and
re-solving) build their own problem rather than taking these.
"""
import warnings

import pytest

from F404_pycycle.problems import build_dry_problem, build_wet_problem

# pyCycle's Newton iterations legitimately pass through non-physical
# intermediate states (negative gamma, bound violations) before recovering.
# The resulting warnings are expected and would bury real test output.
warnings.filterwarnings('ignore', category=RuntimeWarning)
try:
    from openmdao.utils.om_warnings import SolverWarning
    warnings.filterwarnings('ignore', category=SolverWarning)
except ImportError:
    pass


@pytest.fixture(scope='session')
def dry_problem():
    """Converged dry (afterburner off) problem. Read-only — do not re-solve."""
    return build_dry_problem(verbose=False)


@pytest.fixture(scope='session')
def wet_problem():
    """Converged wet (afterburning) problem. Read-only — do not re-solve."""
    return build_wet_problem(verbose=False)
