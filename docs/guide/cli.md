# CLI guide

The `f404` command (or `python -m f404`) sweeps the sized engine, prints its design
result, and compares decks. Install with `pip install -e .[all]`; see the
[README](https://github.com/Jhawk414/F404/blob/main/README.md#installation).

```bash
f404 run.yml                    # run the committed YAML grid; decks in deck/
f404 --example-yaml             # print a runnable commented example
f404 sweep                      # dry + wet, default grid, decks in the cwd
f404 sweep --mode wet           # one mode only
f404 sweep --mach 0             # static only (flown at Mach 0.001)
f404 sweep --alt 0 --dts -20,20,10   # one altitude, a dTs range
f404 design                     # solve and print DESIGN, and OD at mil and max AB
f404 compare old.csv new.csv    # % change of every deck column, new vs old
f404 --help                     # and `f404 sweep --help`, `f404 design --help`
                                # (rich panels; plain argparse text for usage errors)
```

## YAML run configuration

Pass a single `.yml` or `.yaml` filename: `f404 run.yml`. Extra arguments are
rejected; edit the file to change settings. The committed
[`run.yml`](https://github.com/Jhawk414/F404/blob/main/run.yml) reproduces the
default dry and wet grids, with output in `deck/`.

```yaml
sweep:
  mode: both
  mach: [0.001, 0.2, 0.4, 0.6, 0.8, 0.95]
  alt: "0,5000,2500"
  dts: "-50,50,10"
  throttle:
    dry: "2500,3100,200"
    wet: "3007.68,3607.68,200"
  out: deck
```

Every key shown is required, including both `throttle` keys even when running
one mode. Unknown keys at any level and duplicate YAML keys are errors. Only
`sweep:` is supported today; design inputs and PLA will be added separately.

| Key | Accepted input | Meaning |
|---|---|---|
| `mode` | `dry`, `wet`, `both` | Which deck modes to run |
| `mach` | scalar, range string, numeric list | Flight Mach, at least 0 and below 1 |
| `alt` | scalar, range string, numeric list | Altitude, ft |
| `dts` | scalar, range string, numeric list | ISA temperature offset, R |
| `throttle.dry` | scalar, range string, numeric list | Core Tt4, R |
| `throttle.wet` | scalar, range string, numeric list | Augmentor Tt7, R |
| `out` | non-empty path string | Output directory, created if missing |

A scalar holds an axis constant. A quoted range is `"min,max,step"`, inclusive
of max; a YAML list contains explicit points, never a range triple. Each axis
is limited to **10,000 points**, checked before range expansion. This caps one
axis, not the product of the sweep dimensions.

Explicit lists must be nonempty, finite, and duplicate-free, with no booleans
or numeric strings. They must already follow traversal order:

- Mach and altitude: ascending.
- dTs: non-negative values ascending, then negative values descending
  (`[0, 10, 20, -10, -20]`).
- Dry/wet throttle: descending, with positive temperatures.

An out-of-order list is an error, never silently sorted. For example,
`dts: [-50, 50, 10]` is rejected; write `dts: "-50,50,10"` for a range.
Range strings are expanded into the same traversal order used by CLI flags.
Mach values below 0.001 are flown at 0.001; inputs that collapse to duplicate
static points are rejected.

`out` is relative to the **working directory**, just like `--out`, rather than
the YAML file's directory. The models validate path syntax independently of the
filesystem; the CLI creates the directory and checks snapshot writes before
solving. Invalid settings or unusable output paths exit 2 with field/input or
filesystem error context. For example:

```text
sweep.throttle.dry: throttle values must be in descending traversal order. For a range, quote min,max,step. (got [2500, 3100, 100])
```

Every YAML or flag sweep saves resolved axes and an absolute output path in a
snapshot matching each deck:

| Deck | Snapshot |
|---|---|
| `cycle_deck_dry.csv` | `run_dry.resolved.yml` |
| `cycle_deck_wet.csv` | `run_wet.resolved.yml` |
| `cycle_deck_full_envelope.csv` | `run_both.resolved.yml` |

A `both` run writes all three snapshots. A later single-mode run replaces only
its own snapshot and deck, preserving the other mode and combined snapshots.
Snapshots record requested settings before solving, are ignored by Git, and
can be rerun with `f404 path/to/run_dry.resolved.yml`. Reusing the same mode
and output directory overwrites that mode's files; use separate directories
to retain multiple runs.

Print a runnable example with all three axis forms and a short inline comment
beside every key:

```bash
f404 --example-yaml > custom.yml
# Review or edit the example settings, then:
f404 custom.yml
```

The example writes a small grid to `deck/example/`; it is distinct from the
full default envelope in the committed `run.yml`. `--example-yaml` runs without
a subcommand. Existing `sweep`, `design`, and `compare` commands remain available.
Help and validation import OpenMDAO eagerly, but no model is built or solved
until inputs and snapshot writes succeed.

## `f404 sweep`

Sweeps the sized engine over flight Mach, altitude, temperature offset and
throttle, and writes `cycle_deck_dry.csv` / `cycle_deck_wet.csv` (plus
`cycle_deck_full_envelope.csv` for `--mode both`). With no range flags the
grid is the default one below, so the output matches the committed decks in
[`deck/`](https://github.com/Jhawk414/F404/tree/main/deck).

Every requested point is a row, failed ones included
([#27](https://github.com/Jhawk414/F404/issues/27)):

- The deck leads with the inputs: `mode, converged, alt, dTs, MN, T4_cmd, T7_cmd`.
- `T4_cmd`/`T7_cmd` are the commanded burner and augmentor exit temperatures: dry is `(Tt4, 0)`, wet is `(3100, Tt7)`.
- A failed row has blank outputs, and its last column, `failure`, says why:
  - `AnalysisError`: Newton failed;
  - `RuntimeError`: singular Jacobian;
  - `bound:<state>`: a balance state saturated at its bound;
  - `target`: T4/T7 missed.
- `df[df.converged]` is the converged deck.

| Flag | Meaning | Default |
|---|---|---|
| `--mode {dry,wet,both}` | afterburner mode | `both` |
| `--mach MIN,MAX,STEP` | flight Mach, below 1 | `0.001, 0.2, 0.4, 0.6, 0.8, 0.95` |
| `--alt MIN,MAX,STEP` | altitude, ft | `0,5000,2500` |
| `--dts MIN,MAX,STEP` | ISA temperature offset, R | `-50,50,10` |
| `--throttle MIN,MAX,STEP` | Tt4 (dry) or Tt7 (wet), R | `2500,3100,200` dry, `3007.68,3607.68,200` wet |
| `--out DIR` | deck directory, created if missing | `.` |

```bash
# Wet sweep: T7 from max AB (3607.68 R) down in 200 R steps (Tt4 held at mil, 3100 R)
f404 sweep --mode wet --alt 0,10000,2500 --dts 0,20,10 --out /tmp/run1
```

The wet default steps down from the calibrated max AB, `MAX_Tt7`. Decks from
before [#37](https://github.com/Jhawk414/F404/issues/37) used 3598.35 → 2998.35 R; to
compare against one point for point, add `--throttle 2998.35,3598.35,200`.

- Each range is one `min,max,step` triple, inclusive of `max`, bare or
  bracketed (`--alt [0,10000,1000]`). The order is fixed.
- A single value holds the axis constant (`--alt 0`, `--throttle 3100`).
  Step 0 is not a constant axis; it is an error.
- A range may start with a negative number (`--dts -20,20,10`). `main()` joins
  it to its flag before argparse, which would otherwise read it as a flag
  ([#22](https://github.com/Jhawk414/F404/issues/22)).
- Axes are walked in the order the solver's warm-starting expects, whatever
  the flag order: `--dts` hot side first (0, +10 … then −10 …), `--throttle`
  high power to low, `--mach` ascending. Nesting is throttle → Mach → alt →
  dTs. Each Mach step walks the alt/dTs block back the way it came, so
  consecutive points stay neighbours.
- `--throttle` needs `--mode dry` or `--mode wet`: it is a different
  temperature in each.
- Mach 0 is flown at 0.001 (`STATIC_MN`): at exactly 0 the flow solve
  gives NaN. Mach 1 and above is rejected, because the inlet's fixed ram
  recovery is subsonic only ([#38](https://github.com/Jhawk414/F404/issues/38)).

A malformed flag stops the run before any model is built, with a message
naming the problem: a range that isn't exactly three finite numbers, a
non-positive step, `min` above `max`, a step that doesn't divide `max − min`
evenly (so the sweep would silently stop short of `max`), an unusable
`--throttle` or `--out`. Exit status 2 for bad arguments.

## `f404 design`

Sizes the engine and prints the DESIGN result tables, then those of `OD` at
mil (dry) and at max AB at sea-level static, without sweeping. There is one engine, so
there is no `--mode`. Three flags override the targets:

- `--fn-target`: dry mil sizing thrust.
- `--mil-tt4`: core burner exit temperature.
- `--max-tt7`: max-AB afterburner exit temperature.

A non-converging solve exits 1 with the solver's message. A `--max-tt7` at or
below the SLS-mil augmentor inlet temperature (~1502 R) would leave the
afterburner dry, so it exits 2 with `MaxTt7TooLowError`.

`python -m f404.sweep_full_envelope [--mode ...]` still works and is
the same as `f404 sweep`.

## `f404 compare`

Compares two decks, `NEW` against `BASE`, and prints a markdown report:
- which points converge in only one of them;
- for every shared column, over the points converged in both, the min and max % change, the largest |%|, and the point where it occurs.

```bash
f404 compare deck/cycle_deck_wet.csv /tmp/run1/cycle_deck_wet.csv
f404 compare old.csv new.csv --cols Fn,TSFC,BPR --changed-only
```

- **Matching.** Rows match on the inputs: (mode, alt, dTs, MN, T4_cmd,
  T7_cmd).
  - alt, dTs, MN and the commands match at 1e-6, so fractional grids stay
    distinct.
  - Full-envelope decks (both modes) compare too.
  - Points in only one deck are listed.
  - Decks from before #27 have no command columns. Their solved T4 (dry) or
    T7 (wet) stands in: it takes the other deck's command within 0.5 R, or
    rounds to 1 R if the other deck has no commands either.
- **Convergence.** The report lists points converged only in base
  (regressions) and only in new (gains), and counts points failed in both.
- **Errors (exit 2).** Two rows on one key; two commands within 0.5 R of one
  solved T4/T7 of a deck without commands; and `--cols` naming a column either
  deck lacks, one that isn't numeric, or an input or summary column (`mode`,
  `alt`, `dTs`, `MN`, `T4_cmd`, `T7_cmd`, `converged`, `failure`).
- **Near-zero base values.** Points whose base value is ~0 (dry `FAR_ab`, a
  zero loss) are compared in absolute terms, on a separate `(abs)` row.
- **Missing values.** Blank or non-finite values are reported on an
  `(invalid)` row and the command exits 1. A missing result never reads as
  "no change".
- **Proof for a model change.** Sweep before and after, then compare. Decks
  are read back at round-trip precision, so a 0 means bit-identical.
