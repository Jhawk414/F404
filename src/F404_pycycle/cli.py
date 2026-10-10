"""Command-line interface for the F404 cycle model.

Entry points::

    f404 sweep  [--mode {dry,wet,both}] [--alt R] [--dts R] [--throttle R] [--out DIR]
    f404 design [--fn-target LBF] [--mil-tt4 DEGR] [--max-tt7 DEGR]

``python -m F404_pycycle`` is equivalent to ``f404``. Every range flag takes one
``min,max,step`` triple (inclusive of ``max``), bare or bracketed.

Input is validated eagerly: a malformed flag stops the run before any model is
built. A partial or misread range that silently swept the wrong envelope would
only be discovered later, in a deck that doesn't match what was asked for.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np


class RangeError(ValueError):
    """A ``min,max,step`` range flag that can't be turned into a sweep axis."""


# max-min must be a whole number of steps to within this fraction of a step.
_STEP_TOL = 1e-9


def parse_range(text):
    """Parse ``'min,max,step'`` (optionally in ``[...]``) into three floats.

    The order is fixed at min, max, step: a step in any other position can't be
    told apart from a bound without a marker, so it is not accepted.

    Raises
    ------
    RangeError
        If there aren't exactly three finite numbers, ``step`` isn't positive,
        ``min`` exceeds ``max``, or ``step`` doesn't divide ``max - min`` evenly
        (which would otherwise stop the sweep short of the requested ``max``).
    """
    raw = text
    text = text.strip()
    if text.startswith('[') and text.endswith(']'):
        text = text[1:-1]

    parts = [p.strip() for p in text.split(',')]
    if len(parts) != 3:
        raise RangeError(
            f"expected exactly 3 values as min,max,step, got {len(parts)} in "
            f"{raw!r}. Example: 0,10000,1000"
        )

    try:
        lo, hi, step = (float(p) for p in parts)
    except ValueError:
        raise RangeError(
            f"min,max,step must all be numbers, got {raw!r}. Example: 0,10000,1000"
        ) from None

    if not all(math.isfinite(v) for v in (lo, hi, step)):
        raise RangeError(f"min,max,step must be finite, got {raw!r}")
    if step <= 0:
        raise RangeError(
            f"step must be positive, got {step:g} in {raw!r}. The order is "
            f"min,max,step; sweeps are built from min up to max."
        )
    if lo > hi:
        raise RangeError(
            f"min ({lo:g}) must not exceed max ({hi:g}) in {raw!r}. The order "
            f"is min,max,step."
        )

    n_steps = (hi - lo) / step
    if abs(n_steps - round(n_steps)) > _STEP_TOL * max(1.0, n_steps):
        raise RangeError(
            f"step {step:g} does not divide max - min ({hi - lo:g}) evenly in "
            f"{raw!r}; the sweep would stop at {lo + math.floor(n_steps) * step:g}, "
            f"short of max {hi:g}. Adjust max or step."
        )
    return lo, hi, step


def expand_range(lo, hi, step):
    """Return the ascending values ``lo, lo+step, ... hi`` as a list of floats."""
    n = int(round((hi - lo) / step)) + 1
    return [float(v) for v in np.round(lo + step * np.arange(n), 9)]


def alt_axis(text):
    """Altitude axis in ft, ascending."""
    return expand_range(*parse_range(text))


def dts_axis(text):
    """Temperature-offset axis in degR, in the sweep's traversal order.

    Anchored at 0 and walked hot-first (0, +10, ... +max), then jumping to the
    cold side (-10, ... -min) — the same order as the default grid, which the
    bridge-point logic is built around. Plain ascending order would instead
    start at the most extreme cold corner, the hardest point to converge from
    the design-condition warm start.
    """
    values = expand_range(*parse_range(text))
    hot = sorted(v for v in values if v >= 0)
    cold = sorted((v for v in values if v < 0), reverse=True)
    return hot + cold


def throttle_axis(text):
    """Throttle axis (Tt4 dry, Tt7 wet) in degR, highest power first.

    Matches the default grids, which start at the design-point throttle (mil
    Tt4 / max-AB Tt7) and walk down to part power.
    """
    values = expand_range(*parse_range(text))
    if values[0] <= 0:
        raise RangeError(
            f"throttle temperatures must be positive degR, got a minimum of "
            f"{values[0]:g}"
        )
    return values[::-1]


# ── argparse wiring ───────────────────────────────────────────────────────────

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
        # Imported here so only help output pays for rich.
        from rich import box
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console = Console(file=file, highlight=False)
        console.print(Text(self.format_usage().rstrip()))
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
        if self._takes_options_only() and not self._has_required_flags():
            console.print(Text("No flag is required: omitted flags use the "
                               "defaults shown.", style='dim'))


def build_parser():
    parser = _PanelHelpParser(
        prog='f404',
        description="GE F404 mixed-flow twin-spool turbofan cycle model.",
    )
    sub = parser.add_subparsers(dest='command', required=True, metavar='COMMAND')

    sweep = sub.add_parser(
        'sweep',
        help="run the alt/dTs/throttle sweep and write cycle decks",
        description="Sweep the sized engine over altitude, temperature offset "
                    "and throttle, writing one CSV deck per mode. Each range "
                    "flag takes min,max,step (inclusive of max), bare or "
                    "bracketed; omitted flags keep the default grid.",
    )
    sweep.add_argument(
        '--mode', choices=['dry', 'wet', 'both'], default='both',
        help="dry (mil power and below), wet (afterburning) or both "
             "(default: both)")
    sweep.add_argument(
        '--alt', type=_axis_arg(alt_axis), metavar='MIN,MAX,STEP',
        help="altitude, ft (default: 0,5000,2500)")
    sweep.add_argument(
        '--dts', type=_axis_arg(dts_axis), metavar='MIN,MAX,STEP',
        help="ISA temperature offset, degR; swept hot side first "
             "(default: -50,50,10)")
    sweep.add_argument(
        '--throttle', type=_axis_arg(throttle_axis), metavar='MIN,MAX,STEP',
        help="Tt4 in dry mode, Tt7 in wet mode, degR; swept high to low "
             "(default: 2500,3100,200 dry / 3200,3800,200 wet). Requires "
             "--mode dry or wet, since the two are different temperatures")
    sweep.add_argument(
        '--out', type=Path, default=Path('.'), metavar='DIR',
        help="directory for the decks, created if missing (default: .)")
    sweep.set_defaults(handler=_run_sweep_command)

    design = sub.add_parser(
        'design',
        help="solve and print the DESIGN point and both OD points",
        description="Size the engine at sea-level static dry mil power and "
                    "print the DESIGN, dry OD and max-afterburner OD result "
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
        help="max-afterburner exit temperature, degR (default: 3800)")
    design.set_defaults(handler=_run_design_command)
    return parser


def _run_sweep_command(args, parser):
    if args.throttle is not None and args.mode == 'both':
        parser.error(
            "--throttle is Tt4 in dry mode and Tt7 in wet mode, so one range "
            "can't serve --mode both. Run --mode dry and --mode wet separately.")
    if args.out.exists() and not args.out.is_dir():
        parser.error(f"--out {args.out} exists and is not a directory")

    # Imported here, not at module level, so that --help and every argument
    # error above return immediately instead of after loading OpenMDAO.
    from F404_pycycle.problems import MIL_Tt4
    from F404_pycycle import sweep_full_envelope as sfe

    if args.throttle is not None and args.mode == 'wet' and min(args.throttle) <= MIL_Tt4:
        parser.error(
            f"--throttle for wet mode is Tt7 and must exceed the fixed core "
            f"Tt4 of {MIL_Tt4:g} degR (the afterburner only adds heat), got a "
            f"minimum of {min(args.throttle):g}")

    throttle = {'dry': sfe.DEFAULT_DRY_POWERS, 'wet': sfe.DEFAULT_WET_POWERS}
    if args.throttle is not None:
        throttle[args.mode] = args.throttle

    sfe.configure_runtime()
    sfe.run_sweeps(
        args.mode,
        alts=args.alt if args.alt is not None else sfe.DEFAULT_ALTS,
        dTs_vals=args.dts if args.dts is not None else sfe.DEFAULT_DTS,
        dry_powers=throttle['dry'],
        wet_powers=throttle['wet'],
        out_dir=args.out,
    )
    return 0


def _run_design_command(args, parser):
    import openmdao.api as om
    from F404_pycycle.problems import build_problem

    targets = {name: value for name, value in (
        ('fn_target', args.fn_target), ('mil_Tt4', args.mil_tt4),
        ('max_Tt7', args.max_tt7)) if value is not None}

    try:
        build_problem(**targets)
    except ValueError as exc:
        parser.error(str(exc))
    except om.AnalysisError as exc:
        print(f"f404 design: the solve did not converge: {exc}",
              file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    """Run the CLI and return its exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args, parser)


if __name__ == '__main__':
    sys.exit(main())
