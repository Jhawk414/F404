"""Tests for the command-line interface.

The range flags are the contract: a malformed one must stop the run before a
model is built, because the alternative is a deck that quietly covers a
different envelope than the one requested.
"""
import importlib

import pandas as pd
import pytest

from f404 import cli, sweep_full_envelope as sfe
from f404.cli import (
    RangeError,
    alt_axis,
    dts_axis,
    expand_range,
    mach_axis,
    parse_range,
    throttle_axis,
)
from f404.sweep_full_envelope import (
    DEFAULT_ALTS,
    DEFAULT_DRY_POWERS,
    DEFAULT_DTS,
    DEFAULT_MACHS,
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
    ('', 'must all be numbers'),
    ('ten', 'must all be numbers'),
    ('inf', 'finite'),
    ('5,', 'exactly 3 values'),
    ('0,10000,1000,5', 'exactly 3 values'),
    ('[0,10000]', 'exactly 3 values'),
    ('0,,1000', 'must all be numbers'),
    ('0,ten,1000', 'must all be numbers'),
    ('nan,10,1', 'finite'),
    ('0,inf,1', 'finite'),
    ('0,10,0', 'step must be positive'),
    ('0,0,0', 'pass a single value, e.g. 0'),
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

@pytest.mark.parametrize('text', ['0', '[0]', ' 0 ', '0.0'])
def test_a_single_value_is_a_constant_axis(text):
    assert expand_range(*parse_range(text)) == [0.]


def test_the_constant_axis_hint_is_in_the_wrong_arity_message():
    with pytest.raises(RangeError, match='single value'):
        parse_range('0,10000')


def test_single_values_work_on_every_axis_builder():
    assert alt_axis('2500') == [2500.]
    assert dts_axis('-20') == [-20.]
    assert throttle_axis('3100') == [3100.]
    assert mach_axis('0.8') == [0.8]


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
    assert throttle_axis('3007.68,3607.68,200') == pytest.approx(DEFAULT_WET_POWERS)


def test_dts_axis_without_a_cold_side_is_plain_ascending():
    assert dts_axis('0,30,10') == [0., 10., 20., 30.]


def test_dts_axis_of_cold_only_range_walks_away_from_zero():
    assert dts_axis('-30,-10,10') == [-10., -20., -30.]


def test_mach_axis_is_ascending_from_static():
    assert mach_axis('0,0.9,0.3') == [0., 0.3, 0.6, 0.9]


@pytest.mark.parametrize('text', ['-0.2,0.4,0.2', '0.5,1.5,0.5', '1'])
def test_mach_axis_rejects_negative_and_supersonic_mach(text):
    with pytest.raises(RangeError, match="subsonic only"):
        mach_axis(text)


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
    assert kw['machs'] == DEFAULT_MACHS
    assert kw['out_dir'].as_posix() == '.'


def test_sweep_flags_override_only_what_they_name(recorded):
    cli.main(['sweep', '--mode', 'dry', '--alt', '[0,2000,1000]',
              '--throttle', '2900,3100,100', '--mach', '0,0.5,0.25',
              '--out', 'somewhere'])

    (mode,), kw = recorded[0]
    assert mode == 'dry'
    assert kw['machs'] == [0., 0.25, 0.5]
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


@pytest.mark.parametrize('flag', ['--dts', '--dt'])
def test_a_negative_start_range_is_accepted_as_a_separate_token(recorded, flag):
    cli.main(['sweep', flag, '-20,20,20'])

    _, kw = recorded[0]
    assert kw['dTs_vals'] == [0., 20., -20.]


def test_single_values_hold_axes_constant_in_a_sweep(recorded):
    cli.main(['sweep', '--mode', 'dry', '--alt', '0', '--dts', '-20',
              '--throttle', '3100'])

    _, kw = recorded[0]
    assert kw['alts'] == [0.]
    assert kw['dTs_vals'] == [-20.]
    assert kw['dry_powers'] == [3100.]


def test_the_default_dts_range_can_be_typed_back_in(recorded):
    cli.main(['sweep', '--dts', '-50,50,10'])

    _, kw = recorded[0]
    assert kw['dTs_vals'] == DEFAULT_DTS


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
    (['sweep', '--mode', 'hot'], 'invalid choice'),
    (['sweep', '--mach', '-0.5,0.5,0.5'], 'subsonic only'),
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
    # One engine now, so there is no mode to pick, and the wet target is an
    # off-design max-AB temperature rather than a DESIGN one (#2).
    (['design', '--mode', 'dry'], 'unrecognized arguments'),
    (['design', '--dsn-tt7', '3800'], 'unrecognized arguments'),
    (['design', '--fn-target', '-5'], 'fn_target must be a positive'),
    (['design', '--mil-tt4', 'nan'], 'must be a finite number'),
    (['design', '--max-tt7', '0'], 'max_Tt7 must be a positive'),
])
def test_bad_design_arguments_fail_before_any_solve(capsys, argv, fragment):
    fails(capsys, argv, fragment)


def test_python_dash_m_and_the_console_script_share_one_entry_point():
    # setup.py registers f404=f404.cli:main; __main__ calls the same.
    assert importlib.import_module('f404.cli').main is cli.main
    assert "f404=f404.cli:main" in open('setup.py').read()


@pytest.mark.slow
def test_sweep_end_to_end_writes_the_requested_deck(tmp_path, capsys):
    out = tmp_path / 'nested' / 'run'

    status = cli.main(['sweep', '--mode', 'dry', '--alt', '0,0,1',
                       '--dts', '0,0,1', '--throttle', '3100,3100,1',
                       '--mach', '0', '--out', str(out)])

    deck = pd.read_csv(out / 'cycle_deck_dry.csv')
    assert status == 0
    assert len(deck) == 1
    assert deck['alt'].iloc[0] == 0 and deck['dTs'].iloc[0] == 0
    assert deck['MN'].iloc[0] == 0.001   # Mach 0 is flown as static
    assert deck['T4'].iloc[0] == pytest.approx(3100.0, abs=0.01)


@pytest.mark.slow
def test_documented_wet_range_sweeps_below_core_temperature(tmp_path, capsys):
    # The README's wet example, thinned to its two ends. 3008 R is below the
    # 3100 R core Tt4, which the CLI used to reject.
    status = cli.main(['sweep', '--mode', 'wet', '--alt', '0,0,1',
                       '--dts', '0,0,1', '--throttle', '3008,3608,600',
                       '--mach', '0', '--out', str(tmp_path)])

    deck = pd.read_csv(tmp_path / 'cycle_deck_wet.csv')
    assert status == 0
    assert sorted(deck['T7'].round()) == [3008., 3608.]
    assert (deck['Wf_ab'] > 0).all()


@pytest.mark.slow
def test_design_prints_the_design_and_the_off_design_point_dry_and_wet(capsys):
    assert cli.main(['design']) == 0

    out = capsys.readouterr().out
    assert all(s in out for s in ('DESIGN', 'OD at SLS mil', 'OD at SLS max AB'))


@pytest.mark.slow
def test_design_rejects_a_max_ab_target_that_leaves_the_afterburner_dry(capsys):
    # Caught only after the dry solve, but still a bad argument: exit 2 with
    # the inlet temperature it has to beat, not a dry engine reported as max AB.
    with pytest.raises(SystemExit) as exc:
        cli.main(['design', '--max-tt7', '1000'])

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert 'MaxTt7TooLowError: max_Tt7 must exceed' in err
    assert 'Tt6 =' in err and 'at sea-level static' in err


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
                     '--mach MIN,MAX,STEP', '--out DIR', '0,5000,2500', '-50,50,10',
                     '0.001,0.2,0.4,0.6,0.8,0.95'):
        assert fragment in out, fragment


def test_every_range_flag_says_a_single_value_holds_it_constant(capsys):
    out = ' '.join(help_text(capsys, 'sweep').split())

    assert out.count('a single value holds it constant') == 4


def test_usage_line_is_styled_on_a_terminal(capsys, monkeypatch):
    # Rich also honours TERM=dumb and NO_COLOR; pin them so the caller's
    # environment can't switch the colour off.
    monkeypatch.setenv('FORCE_COLOR', '1')
    monkeypatch.setenv('TERM', 'xterm')
    monkeypatch.delenv('NO_COLOR', raising=False)
    parser = cli._PanelHelpParser(prog='x')

    parser.print_help()

    out = capsys.readouterr().out
    assert out.startswith('\x1b[1musage:\x1b[0m \x1b[36m')


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


# ── compare ───────────────────────────────────────────────────────────────────

def test_compare_prints_the_markdown_report(tmp_path, capsys):
    base = pd.DataFrame({'mode': ['dry'], 'converged': [True], 'alt': [0.],
                         'dTs': [0.], 'MN': [0.001], 'T4_cmd': [3100.], 'T7_cmd': [0.],
                         'Fn': [11000.]})
    new = base.assign(Fn=[11011.])
    base.to_csv(tmp_path / 'a.csv', index=False)
    new.to_csv(tmp_path / 'b.csv', index=False)

    status = cli.main(['compare', str(tmp_path / 'a.csv'), str(tmp_path / 'b.csv'),
                       '--changed-only'])

    out = capsys.readouterr().out
    assert status == 0
    assert 'matched 1' in out
    assert "| Fn % | +0.1 | +0.1 | 0.1 | ('dry', 0, 0, 0.001, 3100, 0) |" in out


def test_compare_rejects_a_missing_deck(capsys, tmp_path):
    fails(capsys, ['compare', str(tmp_path / 'nope.csv'), str(tmp_path / 'nope.csv')],
          'is not a file')


def test_compare_exits_1_when_a_deck_has_a_blank_value(tmp_path, capsys):
    base = pd.DataFrame({'mode': ['dry'], 'converged': [True], 'alt': [0.],
                         'dTs': [0.], 'MN': [0.001], 'T4_cmd': [3100.], 'T7_cmd': [0.],
                         'Fn': [11000.]})
    base.to_csv(tmp_path / 'a.csv', index=False)
    base.assign(Fn=[None]).to_csv(tmp_path / 'b.csv', index=False)

    status = cli.main(['compare', str(tmp_path / 'a.csv'), str(tmp_path / 'b.csv')])

    assert status == 1
    assert "non-finite values in ['Fn']" in capsys.readouterr().err
