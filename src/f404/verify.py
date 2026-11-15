"""Install check behind ``f404 verify`` (docs/adr/0004-verify-install-check.md).

Solves DESIGN and OD at sea-level static dry mil and max AB, and compares a
few outputs with ``verify_reference.json`` to a relative tolerance.
"""
import json
import platform
import sys
from importlib.resources import files

from f404.problems import build_problem
from f404.sweep_utils import DECK_COLUMNS, _scalar

QUANTITIES = ('Fn', 'TSFC', 'BPR', 'W', 'A8', 'T4', 'T7')


def _read(prob, pt):
    return {q: _scalar(prob.get_val(f'{pt}.{DECK_COLUMNS[q][0]}',
                                    units=DECK_COLUMNS[q][1]))
            for q in QUANTITIES}


def measure():
    """Solve the engine and return ``{point: {quantity: value}}``."""
    mil = {}
    prob, mp = build_problem(
        verbose=False, on_mil=lambda p, od: mil.update(_read(p, od)))
    return {'DESIGN': _read(prob, 'DESIGN'), 'SLS dry mil': mil,
            'SLS max AB': _read(prob, mp.od_pt)}


def load_reference():
    """The packaged ``{"rel_tol": float, "points": {point: {quantity: value}}}``."""
    return json.loads(
        files('f404').joinpath('verify_reference.json').read_text(encoding='utf-8'))


def compare(measured, reference):
    """One check per reference value: value, expected, rel_diff and ok."""
    rel_tol = reference['rel_tol']
    checks = []
    for point, expected_values in reference['points'].items():
        for quantity, expected in expected_values.items():
            value = measured[point][quantity]
            rel_diff = abs(value - expected) / abs(expected)
            checks.append({'point': point, 'quantity': quantity, 'value': value,
                           'expected': expected, 'rel_diff': rel_diff,
                           'ok': rel_diff <= rel_tol})
    return checks


def versions():
    import numpy, openmdao, scipy
    return {'python': platform.python_version(), 'openmdao': openmdao.__version__,
            'numpy': numpy.__version__, 'scipy': scipy.__version__,
            'platform': platform.platform()}


def format_report(checks, rel_tol, env):
    """Human-readable versions header, check table and summary line."""
    lines = ['  '.join(f'{k} {v}' for k, v in env.items()), '',
             f"{'point':<12} {'qty':<5} {'value':>16} {'expected':>16} "
             f"{'rel diff':>9}  result"]
    for c in checks:
        lines.append(f"{c['point']:<12} {c['quantity']:<5} {c['value']:>16.10g} "
                     f"{c['expected']:>16.10g} {c['rel_diff']:>9.1e}  "
                     f"{'PASS' if c['ok'] else 'FAIL'}")
    failed = [f"{c['point']} {c['quantity']}" for c in checks if not c['ok']]
    lines.append('')
    lines.append(f"FAIL: {len(failed)} of {len(checks)} checks outside relative "
                 f"tolerance {rel_tol:g}: {', '.join(failed)}" if failed else
                 f"PASS: all {len(checks)} checks within relative tolerance {rel_tol:g}")
    return '\n'.join(lines)
