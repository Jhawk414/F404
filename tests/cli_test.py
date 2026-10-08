"""Tests for the command-line interface.

The range flags are the contract: a malformed one must stop the run before a
model is built, because the alternative is a deck that quietly covers a
different envelope than the one requested.
"""
import importlib

import pandas as pd
import pytest

from F404_pycycle import cli, sweep_full_envelope as sfe
from F404_pycycle.cli import (
    RangeError,
    alt_axis,
    dts_axis,
    expand_range,
    parse_range,
    throttle_axis,
)
from F404_pycycle.problems import MIL_Tt4
from F404_pycycle.sweep_full_envelope import (
    DEFAULT_ALTS,
    DEFAULT_DRY_POWERS,
    DEFAULT_DTS,
    DEFAULT_WET_POWERS,
)


# ── parse_range ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize('text', [
    '0,10000,1000',
    '[0,10000,1000]',
    ' 0 , 10000 , 1000 ',
    '[ 0, 10000, 1000 ]',
    '0.0,1e4,1e3',
])
def test_bare_bracketed_and_spaced_forms_parse_identically(text):
    assert parse_range(text) == (0.0, 10000.0, 1000.0)


@pytest.mark.parametrize('text, fragment', [
    ('0,10000', 'exactly 3 values'),
    ('0', 'exactly 3 values'),
    ('', 'exactly 3 values'),
    ('0,10000,1000,5', 'exactly 3 values'),
    ('[0,10000]', 'exactly 3 values'),
    ('0,,1000', 'must all be numbers'),
    ('0,ten,1000', 'must all be numbers'),
    ('nan,10,1', 'finite'),
    ('0,inf,1', 'finite'),
    ('0,10,0', 'step must be positive'),
    ('0,10,-1', 'step must be positive'),
    ('10,0,1', 'must not exceed max'),
    ('0,1000,300', 'does not divide'),
])
def test_malformed_ranges_raise_with_a_message_naming_the_problem(text, fragment):
    with pytest.raises(RangeError, match=fragment):
        parse_range(text)


def test_error_message_quotes_the_offending_input():
    with pytest.raises(RangeError, match=r"'0,10000'"):
        parse_range('0,10000')


def test_a_step_in_the_wrong_position_is_rejected_not_reinterpreted():
    # The issue's open question: 0,1000,10000 could mean min,step,max. The
    # order is fixed, so this reads as min=0 max=1000 step=10000 and the step
    # that overshoots max is an error rather than a guess.
    with pytest.raises(RangeError):
        parse_range('0,1000,10000')


def test_range_error_is_a_value_error():
    assert issubclass(RangeError, ValueError)


# ── expand_range ──────────────────────────────────────────────────────────────

def test_expand_range_includes_both_endpoints():
    assert expand_range(0., 5000., 2500.) == [0., 2500., 5000.]


def test_a_single_point_range_is_allowed():
    assert expand_range(1000., 1000., 500.) == [1000.]


def test_expand_range_has_no_floating_point_drift():
    assert expand_range(0.2, 0.5, 0.1) == [0.2, 0.3, 0.4, 0.5]


def test_fractional_steps_that_divide_evenly_are_accepted():
    assert parse_range('0.2,0.9,0.1') == (0.2, 0.9, 0.1)


# ── axes reproduce the defaults ───────────────────────────────────────────────

def test_alt_axis_reproduces_the_default_altitudes():
    assert alt_axis('0,5000,2500') == [float(a) for a in DEFAULT_ALTS]


def test_dts_axis_reproduces_the_default_order():
    # Hot-first with the cold side after, anchored at 0 — not ascending.
    assert dts_axis('-50,50,10') == DEFAULT_DTS


def test_throttle_axis_reproduces_both_default_power_lists():
    assert throttle_axis('2500,3100,200') == DEFAULT_DRY_POWERS
    assert throttle_axis('3200,3800,200') == DEFAULT_WET_POWERS


def test_dts_axis_without_a_cold_side_is_plain_ascending():
    assert dts_axis('0,30,10') == [0., 10., 20., 30.]


def test_dts_axis_of_cold_only_range_walks_away_from_zero():
    assert dts_axis('-30,-10,10') == [-10., -20., -30.]


def test_throttle_axis_rejects_non_positive_temperatures():
    with pytest.raises(RangeError, match="positive degR"):
        throttle_axis('0,100,50')


# ── command line ──────────────────────────────────────────────────────────────
# Handlers are exercised with run_sweeps stubbed out, so these check what the
# CLI asks the driver to do without building a model.

@pytest.fixture
def recorded(monkeypatch):
    """Capture the arguments `f404 sweep` hands to run_sweeps."""
    calls = []
    monkeypatch.setattr(sfe, 'run_sweeps', lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(sfe, 'configure_runtime', lambda: None)
    return calls


def test_sweep_with_no_flags_uses_the_default_grid(recorded):
    assert cli.main(['sweep']) == 0

    (mode,), kw = recorded[0]
    assert mode == 'both'
    assert list(kw['alts']) == list(DEFAULT_ALTS)
    assert kw['dTs_vals'] == DEFAULT_DTS
    assert kw['dry_powers'] == DEFAULT_DRY_POWERS
    assert kw['wet_powers'] == DEFAULT_WET_POWERS
    assert kw['out_dir'].as_posix() == '.'


def test_sweep_flags_override_only_what_they_name(recorded):
    cli.main(['sweep', '--mode', 'dry', '--alt', '[0,2000,1000]',
              '--throttle', '2900,3100,100', '--out', 'somewhere'])

    (mode,), kw = recorded[0]
    assert mode == 'dry'
    assert kw['alts'] == [0., 1000., 2000.]
    assert kw['dry_powers'] == [3100., 3000., 2900.]
    assert kw['wet_powers'] == DEFAULT_WET_POWERS
    assert kw['dTs_vals'] == DEFAULT_DTS
    assert kw['out_dir'].as_posix() == 'somewhere'


def test_a_wet_throttle_range_feeds_the_wet_powers(recorded):
    cli.main(['sweep', '--mode', 'wet', '--throttle', '3300,3500,100'])

    _, kw = recorded[0]
    assert kw['wet_powers'] == [3500., 3400., 3300.]
    assert kw['dry_powers'] == DEFAULT_DRY_POWERS


def fails(capsys, argv, fragment):
    """Assert argv exits with usage error 2 and a message containing fragment."""
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert fragment in err, err


@pytest.mark.parametrize('argv, fragment', [
    (['sweep', '--alt', '0,10000'], 'exactly 3 values'),
    (['sweep', '--dts', '0,ten,5'], 'must all be numbers'),
    (['sweep', '--throttle', '3100,2500,200', '--mode', 'dry'], 'must not exceed max'),
    (['sweep', '--throttle', '2500,3100,200'], 'can\'t serve --mode both'),
    (['sweep', '--mode', 'wet', '--throttle', f'{MIL_Tt4 - 100:g},3800,100'],
     'must exceed the fixed core'),
    (['sweep', '--mode', 'hot'], 'invalid choice'),
])
def test_bad_sweep_arguments_fail_before_any_model_is_built(
        recorded, capsys, argv, fragment):
    fails(capsys, argv, fragment)
    assert recorded == []


def test_out_pointing_at_a_file_is_rejected(recorded, capsys, tmp_path):
    a_file = tmp_path / 'deck.csv'
    a_file.write_text('x')

    fails(capsys, ['sweep', '--out', str(a_file)], 'not a directory')
    assert recorded == []


def test_a_command_is_required(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code == 2


@pytest.mark.parametrize('argv, fragment', [
    (['design', '--fn-target', '9000'], 'Use --mode dry or --mode wet'),
    (['design', '--mode', 'dry', '--dsn-tt7', '3800'], 'wet (afterburning)'),
    (['design', '--mode', 'dry', '--fn-target', '-5'], 'fn_target must be a positive'),
    (['design', '--mode', 'dry', '--mil-tt4', 'nan'], 'must be a finite number'),
    (['design', '--mode', 'wet', '--dsn-tt7', '3000'], 'must exceed mil_Tt4'),
])
def test_bad_design_arguments_fail_before_any_solve(capsys, argv, fragment):
    fails(capsys, argv, fragment)


def test_python_dash_m_and_the_console_script_share_one_entry_point():
    # setup.py registers f404=F404_pycycle.cli:main; __main__ calls the same.
    assert importlib.import_module('F404_pycycle.cli').main is cli.main
    assert "f404=F404_pycycle.cli:main" in open('setup.py').read()


@pytest.mark.slow
def test_sweep_end_to_end_writes_the_requested_deck(tmp_path, capsys):
    out = tmp_path / 'nested' / 'run'

    status = cli.main(['sweep', '--mode', 'dry', '--alt', '0,0,1',
                       '--dts', '0,0,1', '--throttle', '3100,3100,1',
                       '--out', str(out)])

    deck = pd.read_csv(out / 'cycle_deck_dry.csv')
    assert status == 0
    assert len(deck) == 1
    assert deck['alt'].iloc[0] == 0 and deck['dTs'].iloc[0] == 0
    assert deck['T4'].iloc[0] == pytest.approx(3100.0, abs=0.01)


@pytest.mark.slow
def test_design_prints_the_requested_engine(capsys):
    assert cli.main(['design', '--mode', 'dry']) == 0

    out = capsys.readouterr().out
    assert 'DRY' in out and 'WET' not in out


# ── help rendering ────────────────────────────────────────────────────────────

def help_text(capsys, *argv):
    with pytest.raises(SystemExit) as exc:
        cli.main([*argv, '-h'])
    assert exc.value.code == 0
    return capsys.readouterr().out


def test_top_level_help_lists_commands_in_a_rounded_panel(capsys):
    out = help_text(capsys)

    assert 'GE F404 mixed-flow twin-spool turbofan cycle model.' in out
    assert '╭─ Commands' in out and '╰' in out
    assert 'sweep' in out and 'design' in out


def test_sweep_help_documents_every_flag_with_its_default(capsys):
    out = help_text(capsys, 'sweep')

    for fragment in ('--mode {dry,wet,both}', '--alt MIN,MAX,STEP',
                     '--dts MIN,MAX,STEP', '--throttle MIN,MAX,STEP',
                     '--out DIR', '0,5000,2500', '-50,50,10'):
        assert fragment in out, fragment


def test_help_says_when_no_flag_is_required(capsys):
    assert 'No flag is required' in help_text(capsys, 'sweep')
    assert 'No flag is required' in help_text(capsys, 'design')


def test_help_has_no_required_section_while_nothing_is_required(capsys):
    assert 'Required' not in help_text(capsys, 'sweep')


def test_a_required_flag_gets_its_own_panel(capsys):
    parser = cli._PanelHelpParser(prog='x')
    parser.add_argument('--must', required=True, metavar='N', help='needed')
    parser.add_argument('--may', help='optional')

    parser.print_help()

    out = capsys.readouterr().out
    assert '╭─ Required' in out and '╭─ Options' in out
    assert 'No flag is required' not in out
    assert out.index('--must N') < out.index('--may')


def test_piped_help_carries_no_ansi_escape_codes(capsys):
    assert '\x1b' not in help_text(capsys, 'sweep')


def test_bracketed_text_in_help_is_not_read_as_markup(capsys):
    parser = cli._PanelHelpParser(prog='x')
    parser.add_argument('--r', help='e.g. [0,10000,1000] and [bold]')

    parser.print_help()

    assert '[0,10000,1000] and [bold]' in capsys.readouterr().out


def test_usage_errors_stay_plain_argparse_text(capsys):
    with pytest.raises(SystemExit):
        cli.main(['sweep', '--alt', '0,1'])

    err = capsys.readouterr().err
    assert err.startswith('usage: f404 sweep')
    assert '╭' not in err and 'error: argument --alt' in err
