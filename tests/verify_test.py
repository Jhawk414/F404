"""Tests for the ``f404 verify`` install check."""
import json

import openmdao.api as om
import pytest

from f404 import cli, verify


def perturbed(rel):
    """The reference values, with SLS max AB A8 moved by ``rel``."""
    measured = {pt: dict(v) for pt, v in verify.load_reference()['points'].items()}
    measured['SLS max AB']['A8'] *= 1 + rel
    return measured


@pytest.fixture
def perturbed_run(monkeypatch):
    monkeypatch.setattr(verify, 'measure', lambda: perturbed(2e-6))


def test_compare_passes_the_reference_and_flags_only_the_perturbed_value():
    reference = verify.load_reference()
    assert all(c['ok'] for c in verify.compare(reference['points'], reference))

    failed = [c for c in verify.compare(perturbed(2e-6), reference) if not c['ok']]
    assert [(c['point'], c['quantity']) for c in failed] == [('SLS max AB', 'A8')]
    assert failed[0]['rel_diff'] == pytest.approx(2e-6)


def test_verify_names_the_failing_check_and_exits_1(perturbed_run, capsys):
    assert cli.main(['verify']) == 1

    out = capsys.readouterr().out
    assert 'openmdao' in out and 'numpy' in out
    assert 'FAIL: 1 of 21 checks outside relative tolerance 1e-06: SLS max AB A8' in out


def test_verify_json_reports_the_failure(perturbed_run, capsys):
    assert cli.main(['verify', '--json']) == 1

    result = json.loads(capsys.readouterr().out)
    assert result['passed'] is False and result['rel_tol'] == 1e-6
    assert {'python', 'openmdao', 'numpy', 'scipy'} <= set(result['versions'])
    assert [c['quantity'] for c in result['checks'] if not c['ok']] == ['A8']


def test_verify_exits_1_when_the_solve_does_not_converge(monkeypatch, capsys):
    def diverge():
        raise om.AnalysisError('Newton failed')
    monkeypatch.setattr(verify, 'measure', diverge)

    assert cli.main(['verify']) == 1
    assert 'the solve did not converge: Newton failed' in capsys.readouterr().err


@pytest.mark.slow
def test_verify_passes_on_this_install(capsys):
    assert cli.main(['verify']) == 0
    assert 'PASS: all 21 checks' in capsys.readouterr().out
