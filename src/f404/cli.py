"""CLI entry point for YAML runs, sweeps, design solves, and deck comparisons."""
import argparse
import re
import sys
from pathlib import Path
from reprlib import repr as short_repr

import openmdao.api as om
import yaml
from pydantic import ValidationError
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from f404 import sweep_full_envelope as sfe
from f404.compare_decks import compare_decks, format_report, read_deck
from f404.config import (
    EXAMPLE_YAML, RangeError, SweepConfig, alt_axis, dts_axis, load_config,
    mach_axis, throttle_axis,
)
from f404.problems import build_problem


# ── argparse wiring ───────────────────────────────────────────────────────────

_RANGE_FLAGS = ('--mach', '--alt', '--dts', '--throttle')

def _axis_arg(builder):
    """Adapt an axis builder to argparse's ``type=``.

    argparse only reports a type function's message when it raises
    ArgumentTypeError; a bare ValueError becomes a generic "invalid value".
    """
    def convert(text):
        try:
            return builder(text)
        except RangeError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from None
    return convert


class _PanelHelpParser(argparse.ArgumentParser):
    """ArgumentParser that prints ``--help`` as rounded panels.

    Only ``-h``/``--help`` output is restyled. Usage errors still go through
    argparse's plain ``usage:`` + ``error:`` text on stderr, which is what
    scripts and agents parse. Subparsers inherit this class, so ``f404 sweep
    -h`` is styled the same way. When stdout isn't a terminal rich drops the
    colour but keeps the box characters, so piped help carries no ANSI codes.
    """

    def _help_sections(self):
        """Group actions into (title, [(label, help), ...]) for display.

        A "Required" section appears only when some flag is required; the
        subcommand list is shown as "Commands".
        """
        commands, required, options = [], [], []
        for action in self._actions:
            if action.help == argparse.SUPPRESS:
                continue
            if isinstance(action, argparse._SubParsersAction):
                commands += [(sub.metavar, sub.help)
                             for sub in action._choices_actions]
            elif action.option_strings:
                label = ', '.join(action.option_strings)
                if action.nargs != 0:  # takes a value
                    label += ' ' + (
                        action.metavar
                        or ('{' + ','.join(map(str, action.choices)) + '}'
                            if action.choices else action.dest.upper()))
                (required if action.required else options).append(
                    (label, action.help))
        return [(title, rows) for title, rows in (
            ('Commands', commands), ('Required', required),
            ('Options', options)) if rows]

    def _has_required_flags(self):
        return any(a.required and a.option_strings for a in self._actions)

    def _takes_options_only(self):
        """True for a leaf command: it has flags and no subcommands."""
        return not any(isinstance(a, argparse._SubParsersAction)
                       for a in self._actions)

    def print_help(self, file=None):
        console = Console(file=file, highlight=False)
        label, _, synopsis = self.format_usage().rstrip().partition(' ')
        console.print(Text.assemble((label, 'bold'), ' ', (synopsis, 'cyan')))
        if self.description:
            console.print()
            console.print(Text(self.description))
        for title, rows in self._help_sections():
            grid = Table.grid(padding=(0, 2))
            grid.add_column(style='bold cyan', no_wrap=True)
            grid.add_column()
            for label, text in rows:
                # Text, not str: help strings contain [..] that rich would
                # otherwise read as markup.
                grid.add_row(Text(label), Text(text or ''))
            console.print(Panel(grid, title=title, title_align='left',
                                box=box.ROUNDED, padding=(0, 1)))
        if self.epilog:
            console.print(Text(self.epilog))
        if self._takes_options_only() and not self._has_required_flags():
            console.print(Text("No flag is required: omitted flags use the "
                               "defaults shown.", style='dim'))


def build_parser():
    parser = _PanelHelpParser(
        prog='f404',
        description="GE F404 mixed-flow twin-spool turbofan cycle model.",
        epilog="Run a YAML sweep: f404 run.yml",
    )
    parser.add_argument('--example-yaml', action='store_true',
                        help='print a runnable, commented YAML run example')
    sub = parser.add_subparsers(dest='command', metavar='COMMAND')

    sweep = sub.add_parser(
        'sweep',
        help="run the Mach/alt/dTs/throttle sweep and write cycle decks",
        description="Sweep the sized engine over flight Mach, altitude, "
                    "temperature offset and throttle, writing one CSV deck per "
                    "mode. Failed points are rows too, with converged False.",
    )
    sweep.add_argument(
        '--mode', choices=['dry', 'wet', 'both'], default='both',
        help="dry (mil power and below), wet (afterburning) or both "
             "(default: both)")
    sweep.add_argument(
        '--mach', type=_axis_arg(mach_axis), metavar='MIN,MAX,STEP',
        help="flight Mach, below 1; 0 is flown at 0.001 (static); a single "
             "value holds it constant (default: 0.001,0.2,0.4,0.6,0.8,0.95)")
    sweep.add_argument(
        '--alt', type=_axis_arg(alt_axis), metavar='MIN,MAX,STEP',
        help="altitude, ft; a single value holds it constant "
             "(default: 0,5000,2500)")
    sweep.add_argument(
        '--dts', type=_axis_arg(dts_axis), metavar='MIN,MAX,STEP',
        help="ISA temperature offset, degR; swept hot side first; a "
             "single value holds it constant (default: -50,50,10)")
    sweep.add_argument(
        '--throttle', type=_axis_arg(throttle_axis), metavar='MIN,MAX,STEP',
        help="Tt4 in dry mode, Tt7 in wet mode, degR; swept high to low; "
             "a single value holds it constant (default: 2500,3100,200 dry "
             "/ 3007.68,3607.68,200 wet). Requires --mode dry or wet, since the "
             "two are different temperatures")
    sweep.add_argument(
        '--out', type=Path, default=Path('.'), metavar='DIR',
        help="directory for the decks, created if missing (default: .)")
    sweep.set_defaults(handler=_run_sweep_command)

    design = sub.add_parser(
        'design',
        help="solve and print the DESIGN point and the OD point at mil and max AB",
        description="Size the engine at sea-level static dry mil power and "
                    "print the DESIGN, OD dry-mil and OD max-afterburner result "
                    "tables, without running a sweep.",
    )
    design.add_argument(
        '--fn-target', type=float, metavar='LBF',
        help="SLS dry mil thrust that sizes the engine, lbf (default: 11000)")
    design.add_argument(
        '--mil-tt4', type=float, metavar='DEGR',
        help="core burner exit temperature, degR (default: 3100)")
    design.add_argument(
        '--max-tt7', type=float, metavar='DEGR',
        help="max-afterburner exit temperature, degR (default: 3607.68)")
    design.set_defaults(handler=_run_design_command)

    compare = sub.add_parser(
        'compare',
        help="compare two cycle decks column by column",
        description="Match the rows of two decks on (mode, alt, dTs, MN, "
                    "T4_cmd, T7_cmd), list the points that converge in only "
                    "one of them, and report the min, max and largest % change "
                    "of every shared column over the points converged in both, "
                    "NEW against BASE. Columns whose base is ~0 are compared in "
                    "absolute terms.",
    )
    compare.add_argument('base', type=Path, metavar='BASE', help="reference deck CSV")
    compare.add_argument('new', type=Path, metavar='NEW', help="deck CSV to compare")
    compare.add_argument(
        '--cols', metavar='A,B,...',
        help="compare only these columns (default: every shared column)")
    compare.add_argument(
        '--changed-only', action='store_true',
        help="omit columns that match exactly (columns with blank or "
             "non-finite values are always shown, and exit 1)")
    compare.set_defaults(handler=_run_compare_command)
    return parser


def _run_sweep_command(args, parser):
    if args.throttle is not None and args.mode == 'both':
        parser.error(
            "--throttle is Tt4 in dry mode and Tt7 in wet mode, so one range "
            "can't serve --mode both. Run --mode dry and --mode wet separately.")
    throttle = {'dry': sfe.DEFAULT_DRY_POWERS, 'wet': sfe.DEFAULT_WET_POWERS}
    if args.throttle is not None:
        throttle[args.mode] = args.throttle

    try:
        config = SweepConfig(
            mode=args.mode,
            mach=args.mach if args.mach is not None else sfe.DEFAULT_MACHS,
            alt=args.alt if args.alt is not None else sfe.DEFAULT_ALTS,
            dts=args.dts if args.dts is not None else sfe.DEFAULT_DTS,
            throttle=throttle,
            out=args.out,
        )
    except ValidationError as exc:
        parser.error(_validation_errors(exc, prefix='sweep'))
    return _run_sweep(config, parser)


def _validation_errors(exc, prefix=''):
    lines = []
    for error in exc.errors(include_url=False):
        field = '.'.join(str(part) for part in error['loc'])
        location = '.'.join(part for part in (prefix, field) if part) or 'config'
        message = error['msg'].removeprefix('Value error, ')
        lines.append(f"{location}: {message} (got {short_repr(error['input'])})")
    return '\n'.join(lines)


def _run_sweep(config, parser):
    try:
        config.out.mkdir(parents=True, exist_ok=True)
        resolved = config.model_dump(mode='json')
        resolved['out'] = str(config.out.resolve())
        modes = ('dry', 'wet', 'both') if config.mode == 'both' else (config.mode,)
        for mode in modes:
            resolved['mode'] = mode
            (config.out / f'run_{mode}.resolved.yml').write_text(
                yaml.safe_dump({'sweep': resolved}, sort_keys=False), encoding='utf-8')
    except OSError as exc:
        parser.error(f"cannot write sweep configuration in {config.out}: {exc}")

    sfe.configure_runtime()
    sfe.run_sweeps(
        config.mode, alts=config.alt, dTs_vals=config.dts,
        dry_powers=config.throttle.dry, wet_powers=config.throttle.wet,
        machs=config.mach, out_dir=config.out,
    )
    return 0


def _run_design_command(args, parser):
    targets = {name: value for name, value in (
        ('fn_target', args.fn_target), ('mil_Tt4', args.mil_tt4),
        ('max_Tt7', args.max_tt7)) if value is not None}

    try:
        build_problem(**targets)
    except ValueError as exc:
        # A named subclass (e.g. MaxTt7TooLowError) says what was wrong.
        name = type(exc).__name__
        parser.error(str(exc) if name == 'ValueError' else f"{name}: {exc}")
    except om.AnalysisError as exc:
        print(f"f404 design: the solve did not converge: {exc}",
              file=sys.stderr)
        return 1
    return 0


def _run_compare_command(args, parser):
    for path in (args.base, args.new):
        if not path.is_file():
            parser.error(f"{path} is not a file")

    base, new = read_deck(args.base), read_deck(args.new)
    columns = args.cols.split(',') if args.cols else None
    try:
        table, points = compare_decks(base, new, columns)
    except ValueError as exc:
        parser.error(str(exc))
    print(format_report(table, points, len(base), len(new),
                        changed_only=args.changed_only))
    invalid = table.loc[table['kind'] == 'invalid', 'column'].tolist()
    if invalid:
        print(f"f404 compare: non-finite values in {invalid}", file=sys.stderr)
        return 1
    return 0


def _join_negative_ranges(argv):
    """Glue ``--dts -20,20,10`` into ``--dts=-20,20,10``.

    argparse reads any ``-``-prefixed token that isn't a plain number as a flag,
    so a range starting with a minus sign (the ``--dts`` default included)
    would be rejected as "expected one argument". Abbreviated flags
    (``--dt``) are joined too, as argparse accepts them.
    """
    out = []
    for token in argv:
        prev = out[-1] if out else ''
        if (re.match(r'-[\d.]', token) and prev.startswith('--')
                and '=' not in prev
                and any(flag.startswith(prev) for flag in _RANGE_FLAGS)):
            out[-1] = f'{prev}={token}'
        else:
            out.append(token)
    return out


def main(argv=None):
    """Run the CLI and return its exit status."""
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and Path(argv[0]).suffix.lower() in ('.yml', '.yaml'):
        if len(argv) != 1:
            parser.error("a YAML run file must be the only argument")
        try:
            config = load_config(Path(argv[0]))
        except ValidationError as exc:
            parser.error(f"invalid run config {argv[0]}:\n{_validation_errors(exc)}")
        except ValueError as exc:
            parser.error(str(exc))
        return _run_sweep(config.sweep, parser)

    args = parser.parse_args(_join_negative_ranges(argv))
    if args.example_yaml:
        if args.command is not None:
            parser.error("--example-yaml must be used without a command")
        print(EXAMPLE_YAML, end='')
        return 0
    if args.command is None:
        parser.error("a command or YAML run file is required")
    return args.handler(args, parser)


if __name__ == '__main__':
    sys.exit(main())
