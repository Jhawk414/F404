[![Status: In Development](https://img.shields.io/badge/status-in%20development-orange.svg)](https://github.com/Jhawk414/F404#current-status)
[![Last Commit](https://img.shields.io/github/last-commit/Jhawk414/F404?logo=github)](https://github.com/Jhawk414/F404/commits/main)
[![Open Issues](https://img.shields.io/github/issues/Jhawk414/F404?logo=github)](https://github.com/Jhawk414/F404/issues)

# F404

A GE F404 twin-spool, low-bypass, mixed-flow, afterburning turbofan cycle model
with design-point sizing and off-design flight sweeps, built on
[NASA Glenn's pyCycle](https://github.com/OpenMDAO/pyCycle) and
[OpenMDAO](https://openmdao.org/).

Given a target thrust and component parameters (fan and HPC pressure ratios,
component efficiencies, cooling bleed fractions), the model sizes the engine
at sea-level-static conditions and sweeps altitude, ambient temperature offset,
and throttle to generate a converged off-design performance deck.

**Status:** In development. One sized engine, with DESIGN at sea-level-static
dry mil power, operated both dry (military power and below) and wet
(afterburning) on two off-design points of the same model. Also:
altitude/dTs/throttle sweep infrastructure, and an `f404` command line for
sweeps and single design points. See [Current status](#current-status) for
convergence coverage and [Roadmap](#roadmap) for planned work. Not yet
validated against public F404 performance data; the public reports are
archived and indexed in
[`docs/unclassified_perf_data/`](docs/unclassified_perf_data/README.md).

## Table of contents

- [Repo layout](#repo-layout)
- [Cycle architecture](#cycle-architecture)
- [Software architecture and data flow](#software-architecture-and-data-flow)
- [Installation](#installation)
- [Usage](#usage)
- [Testing](#testing)
- [Current status](#current-status)
- [Roadmap](#roadmap)
- [Acknowledgments](#acknowledgments)
- [License](#license)

## Repo layout

F404 application code lives under `src/f404/`, separate from the
vendored upstream `pycycle` library at the repo root (see
[#4](https://github.com/Jhawk414/F404/issues/4)).

| Path | Role |
|---|---|
| `src/f404/engine_model.py` | `MixedFlowTurbofan(pyc.Cycle)`: single-point thermodynamic cycle (fan, HPC, burner, HPT/LPT, mixer, afterburner, nozzle), plus `AugmentorControl` (afterburner command and pressure loss) and `NozzleSchedule` (A8) |
| `src/f404/mp_cycle.py` | `MPMixedFlowTurbofan(pyc.MPCycle)`: one DESIGN point (dry mil) feeding one off-design point, `OD`, for dry and wet alike, with map scalars, station areas and the nozzle throat; the augmentor-loss constants |
| `src/f404/problems.py` | `build_problem()`: design targets, the max-AB calibration, initial guesses and input validation |
| `src/f404/sweep_utils.py` | Sweep infrastructure: snake-pattern sweep grid, bridge-point warm-starting, `SweepRunner`, result extraction |
| `src/f404/cli.py` | `f404` command line: `sweep` and `design` subcommands, `min,max,step` range parsing and validation |
| `src/f404/sweep_full_envelope.py` | Sweep driver: default grid, `run_sweeps()` for dry, wet, or both modes, and the cycle-deck CSV writer |
| `src/f404/printer.py` | Console table formatter for DESIGN/OD results |
| `src/f404/compare_decks.py` | Column-by-column deck comparison behind `f404 compare` |
| `tests/` | pytest suite, one `<module>_test.py` per module ([#5](https://github.com/Jhawk414/F404/issues/5)) |
| `deck/` | Cycle-deck output CSVs |
| `docs/` | System architecture diagrams (`f404_cycle.typ`, `f404_cycle.svg`), architecture decision records (`adr/`), planning docs (`improvements/`), and reference material (`unclassified_perf_data/`: an [index and cross-study reference map](docs/unclassified_perf_data/README.md) of published F404 performance data, with source PDFs in `pdf/` and Obsidian-compatible markdown conversions with their figures in `md/`) |
| `AGENTS/` | Session handoff notes |
| `meta/` | Vendored-library provenance (`LICENSE.txt`) |
| `pycycle/`, `setup.py`, `pyproject.toml`, `example_cycles/` | Vendored upstream `pyCycle` library |

## Cycle architecture

The thermodynamic cycle model in `engine_model.py` (`MixedFlowTurbofan`) represents the twin-spool, mixed-flow, augmented F404 turbofan engine:

![F404 Turbofan Cycle Architecture](docs/f404_cycle.svg)

*Diagram source maintained in [`docs/f404_cycle.typ`](docs/f404_cycle.typ).*

Key cycle components and mechanical couplings:
- **Low Pressure (LP) Spool**: 3-stage fan driven by the single-stage LP turbine via `lp_shaft` (10,000 rpm).
- **High Pressure (HP) Spool**: 7-stage HP compressor driven by the single-stage HP turbine via `hp_shaft` (14,000 rpm, 250 hp customer power extraction).
- **Cooling Bleeds**: HPC interstage bleed (`cool1`, 5.07% flow) cools the LPT; compressor discharge bleed (`cool3`, 11.0% flow) cools the HPT.
- **Mixed Exhaust & Augmentor**: Core flow and bypass flow mix in a confluent mixer, then pass through the afterburner and expand through a variable convergent-divergent nozzle (`mixed_nozz`). Off-design, the afterburner is always a combustor: a commanded Tt7 at or below its inlet temperature (0 included) is dry, with zero fuel. Its pressure loss is a flameholder drag loss (2.1%, dry and wet, also in the DESIGN sizing) plus a Rayleigh loss that grows with heat addition (6.6% in total at SLS max AB), after Kumar (1980) ([#33](https://github.com/Jhawk414/F404/issues/33)).
- **One engine, two modes**: the engine is sized once, at SLS dry mil (11,000 lbf, Tt4 3100 R). Dry and wet run on one off-design point. When dry, it uses the DESIGN nozzle throat (A8). When wet, A8 opens by choked-throat continuity, just enough to pass the hotter flow, so the gas generator stays within about 0.25% BPR of where dry put it at that flight condition ([#8](https://github.com/Jhawk414/F404/issues/8), wet half). Max AB is Tt7 3598.35 R, calibrated to 17,700 lbf SLS. See [ADR-0001](docs/adr/0001-single-engine-sizing.md) for the sizing and [ADR-0002](docs/adr/0002-single-od-topology.md) for the single OD topology, the loss and the A8 law.

## Software architecture and data flow

Current data flow from CLI invocation to output CSV.

```mermaid
flowchart TD
    subgraph Drivers["Entry point (src/f404/)"]
        CLI["cli.py  (f404)<br/>sweep · design<br/>--mode · --alt · --dts · --throttle · --out"]
        A["sweep_full_envelope.py<br/>run_sweeps · write_deck_csv"]
    end

    subgraph Model["Cycle model"]
        B["problems.py<br/>build_problem<br/>targets, calibration, guesses, validation"]
        C["mp_cycle.py<br/>MPMixedFlowTurbofan(pyc.MPCycle)<br/>wires DESIGN + OD"]
        D["engine_model.py<br/>MixedFlowTurbofan(pyc.Cycle)<br/>single-point thermodynamic cycle"]
    end

    subgraph Sweep["Sweep infrastructure"]
        E["sweep_utils.py<br/>build_snake_sweep · generate_bridge_points<br/>SweepRunner · extract_od_results"]
    end

    subgraph Output["Output"]
        F["printer.py<br/>page_viewer() console tables"]
        G["deck/*.csv<br/>cycle_deck_dry / _wet / _full_envelope"]
    end

    CLI --> A
    CLI --> B
    A --> B
    B --> C
    C --> D
    B --> F
    A --> E
    E --> C
    E --> G
```

`mp_cycle.py` instantiates `MixedFlowTurbofan` twice:

- with `design=True`: the DESIGN point, solved once to size the engine, with
  the afterburner as a duct;
- with `design=False`: `OD`, with the afterburner as a combustor.

It passes converged map scalars, station areas and the nozzle throat from
DESIGN into `OD`, so off-design calculations use the one sized engine
geometry. `aug_ctrl.Tt7_cmd` sets the mode: a dry sweep holds it at 0 and
throttles Tt4, and a wet sweep holds Tt4 at mil and throttles Tt7.

## Installation

This repository vendors OpenMDAO's `pyCycle` library. Install in editable mode
from a local clone:

```bash
git clone git@github.com:Jhawk414/F404.git
cd F404
pip install -e .[all]
```

Requires Python 3.9+ and OpenMDAO 3.10.0+.

## Usage

`pip install -e .[all]` installs an `f404` command (re-run it in an existing
checkout to pick up the entry point). `python -m f404` is equivalent
and needs no install beyond the package being importable.

```bash
f404 sweep                      # dry + wet, default grid, decks in the cwd
f404 sweep --mode wet           # one mode only
f404 sweep --alt 0 --dts -20,20,10   # one altitude, a dTs range
f404 design                     # solve and print DESIGN, and OD at mil and max AB
f404 compare old.csv new.csv    # % change of every deck column, new vs old
f404 --help                     # and `f404 sweep --help`, `f404 design --help`
                                # (rich panels; plain argparse text for usage errors)
```

### `f404 sweep`

Sweeps the sized engine over altitude, temperature offset and throttle, and
writes `cycle_deck_dry.csv` / `cycle_deck_wet.csv` (plus
`cycle_deck_full_envelope.csv` for `--mode both`). With no range flags the
grid is the default one below, so the output matches earlier decks.

| Flag | Meaning | Default |
|---|---|---|
| `--mode {dry,wet,both}` | afterburner mode | `both` |
| `--alt MIN,MAX,STEP` | altitude, ft | `0,5000,2500` |
| `--dts MIN,MAX,STEP` | ISA temperature offset, R | `-50,50,10` |
| `--throttle MIN,MAX,STEP` | Tt4 (dry) or Tt7 (wet), R | `2500,3100,200` dry, `2998.35,3598.35,200` wet |
| `--out DIR` | deck directory, created if missing | `.` |

```bash
# Wet sweep: T7 from 3608 down to 3008 R (Tt4 held at mil, 3100 R)
f404 sweep --mode wet --alt 0,10000,2500 --dts 0,20,10 \
           --throttle 3008,3608,200 --out /tmp/run1
```

The wet default is 3598.35 → 2998.35 R, stepping down from the calibrated
max AB. The example's round-number grid is the one decks before ADR-0002
used, which keeps `f404 compare` against those decks matched point for point.

- Each range is one `min,max,step` triple, inclusive of `max`, bare or
  bracketed (`--alt [0,10000,1000]`). The order is fixed.
- A single value holds the axis constant (`--alt 0`, `--throttle 3100`).
  Step 0 is not a constant axis; it is an error.
- A range may start with a negative number (`--dts -20,20,10`). `main()` joins
  it to its flag before argparse, which would otherwise read it as a flag
  ([#22](https://github.com/Jhawk414/F404/issues/22)).
- Axes are walked in the order the solver's warm-starting expects, whatever
  the flag order: `--dts` hot side first (0, +10 … then −10 …), `--throttle`
  high power to low.
- `--throttle` needs `--mode dry` or `--mode wet`: it is a different
  temperature in each.
- There is no `--mach` yet; Mach is pinned at 0.001 until a Mach sweep
  dimension exists in `sweep_utils.py`
  ([#13](https://github.com/Jhawk414/F404/issues/13)).

A malformed flag stops the run before any model is built, with a message
naming the problem: a range that isn't exactly three finite numbers, a
non-positive step, `min` above `max`, a step that doesn't divide `max − min`
evenly (so the sweep would silently stop short of `max`), an unusable
`--throttle` or `--out`. Exit status 2 for bad arguments.

### `f404 design`

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

### `f404 compare`

Compares two decks of the same mode, `NEW` against `BASE`, and prints a
markdown table. For every shared column it gives the min and max % change,
the largest |%|, and the point where that occurs.

```bash
f404 compare deck/cycle_deck_wet.csv /tmp/run1/cycle_deck_wet.csv
f404 compare old.csv new.csv --cols Fn,TSFC,BPR --changed-only
```

- **Matching.** Rows match on (alt, dTs, throttle). alt and dTs match at
  1e-6, so fractional grids stay distinct. The throttle is the solved T4 for
  a dry deck or T7 for a wet one, matched to 1 R. Points in only one deck are
  listed.
- **Errors (exit 2).** Two rows on one key, a mixed-mode deck, a dry deck
  against a wet one, and `--cols` naming a column either deck lacks.
- **Near-zero base values.** Points whose base value is ~0 (dry `FAR_ab`, a
  zero loss) are compared in absolute terms, on a separate `(abs)` row.
- **Missing values.** Blank or non-finite values are reported on an
  `(invalid)` row and the command exits 1. A missing result never reads as
  "no change".
- **Proof for a model change.** Sweep before and after, then compare. Decks
  are read back at round-trip precision, so a 0 means bit-identical.

## Testing

```bash
pytest tests                    # full suite, ~2 min
pytest tests -m "not slow"      # structural and unit tests only, ~7 s
```

One `tests/<module>_test.py` per module ([#5](https://github.com/Jhawk414/F404/issues/5)).
Tests marked `slow` build and solve a full `om.Problem`; the rest either use
pure functions or build a model without solving it. `pytest` needs no prior
install — `pythonpath` in `pyproject.toml` puts `src/` on the path.

CI ([#31](https://github.com/Jhawk414/F404/issues/31)): a PR runs only the fast
tests (`-m "not slow"`, Ubuntu 3.12, about a minute). The full suite on Ubuntu
(3.9, 3.12) and macOS (3.12) runs on every push to `main`, on manual dispatch,
and on a PR carrying the `full-ci` label. Apply that label when the PR is about
to merge: the golden baselines and convergence regressions are all `slow`.

219 tests (178 fast), 97% coverage. The driver and
CLI are importable and covered; what remains uncovered is mostly
`sweep_utils.py`'s solver-failure paths and the one-line `__main__` shims.

## Current status

Latest full-envelope sweep (`--mode both`, OpenMDAO 3.39.0) at
alt ∈ {0, 2500, 5000} ft, dTs ∈ {0, ±10, ±20, ±30, ±40, ±50} R, static
(MN ≈ 0.001), 4 throttle levels per mode, all on the one sized engine:

| Mode | Converged | Throttle sweep |
|---|---|---|
| Dry | 120 / 132 | Tt4 3100 → 2500 R |
| Wet | 95 / 132 | Tt7 3598.35 → 2998.35 R (Tt4 fixed at 3100 R MIL) |

Decks: [`deck/cycle_deck_dry.csv`](deck/cycle_deck_dry.csv),
[`deck/cycle_deck_wet.csv`](deck/cycle_deck_wet.csv). Every value is written
at full float64 precision (shortest round-trip repr). Columns are
`DECK_COLUMNS` in `sweep_utils.py`: the original 22 performance columns
first, then fan and HPC operating point and stall margin, T3/T45/T5,
augmentor inlet state and loss, and the nozzle inlet and exit states.

Where the failures are, tracked in
[issue #3](https://github.com/Jhawk414/F404/issues/3):

- **Dry:** 69 of the 72 non-cold points converge. Three hot-day, low-power
  points fail at Tt4 = 2500 R: dTs +40 and +50 R at 0 ft and +50 R at
  2500 ft. The other nine failures are all at mil (Tt4 3100 R) on the cold
  side: dTs ≤ −40 R at 0 ft, ≤ −30 R at 2500 ft and ≤ −20 R at 5000 ft.
- **Wet:** every point with dTs ≥ 0 R converges. Wet now fails at exactly the
  conditions where dry mil fails, plus one point (2500 ft, −20 R, 3398 R).
  The A8 law holds the wet gas generator at the dry-mil operating point, so
  the two modes share one cold-corner problem.
- The counts moved with ADR-0002, from 118 dry / 100 wet. Both shifts are
  warm-start path effects at marginal points: a 12-point hot-day probe
  converged 12/12 with each model change on its own. The wet cold corner
  converged before only because the old Rline-2.0 hold moved the gas
  generator off the dry-mil operating point.

## Roadmap

Done:

- [x] Modular cycle model (`engine_model.py` / `mp_cycle.py`), refactored off
      the original monolithic `MFTF_od_CRZ.py`
- [x] Full alt/dTs/throttle sweep infrastructure with bridge-point
      warm-starting (`sweep_utils.py`)
- [x] Dry (MIL) / wet (max-AB) mode split, with convergence-detection bugs
      fixed (bound-saturated states no longer reported as converged)
- [x] Repo-root cleanup: removed the superseded `MFTF_od_CRZ.py` monolith
      and unused vendor/CI cruft (`release_notes.md`, `.travis.yml`,
      `.bumpversion.cfg`), moved reference PDFs into `docs/unclassified_perf_data/`
- [x] Single `write_deck_csv()` writer for every deck
      ([#12](https://github.com/Jhawk414/F404/issues/12)), now at full
      float64 precision with 56 columns, station data included, so deck-to-deck
      comparisons measure the model rather than the rounding
- [x] Per-module test suite (`tests/<module>_test.py`), 87% coverage, with
      golden DESIGN/OD baselines and regression cover on the
      false-convergence guards ([#5](https://github.com/Jhawk414/F404/issues/5))
- [x] Single-engine sizing: one DESIGN at dry mil feeding dry and wet OD
      points, wet A8 control law, max AB calibrated to 17,700 lbf
      ([#2](https://github.com/Jhawk414/F404/issues/2),
      [ADR-0001](docs/adr/0001-single-engine-sizing.md))
- [x] One OD point from dry to max AB, a closed-form augmentor loss
      ([#33](https://github.com/Jhawk414/F404/issues/33)) and a
      choked-continuity wet A8 schedule
      ([#8](https://github.com/Jhawk414/F404/issues/8), wet half;
      [ADR-0002](docs/adr/0002-single-od-topology.md))
- [x] `src/` restructure: F404 app code separated from the vendored pyCycle
      library, now the `f404` package under `src/f404/`
      ([#4](https://github.com/Jhawk414/F404/issues/4))
- [x] Vendored `pycycle/` synced against upstream
      ([#6](https://github.com/Jhawk414/F404/issues/6))
- [x] `f404` CLI with `sweep` and `design` and `--alt` / `--dts` /
      `--throttle` range flags; single-value constant axes
      ([#24](https://github.com/Jhawk414/F404/issues/24)) and negative-start
      ranges ([#22](https://github.com/Jhawk414/F404/issues/22))
- [x] CI: fast tests on PRs, full matrix on merge or the `full-ci` label
      ([#31](https://github.com/Jhawk414/F404/issues/31))
- [x] Published F404 performance reports archived as Obsidian-compatible
      markdown, with an index and cross-study reference map
      ([`docs/unclassified_perf_data/`](docs/unclassified_perf_data/README.md))

Planned (see `docs/improvements/IMPROVEMENTS.md` for full detail), roughly in
order:

- [ ] CLI sweep-axis follow-ups: `--mach` (needs a Mach sweep dimension,
      [#13](https://github.com/Jhawk414/F404/issues/13)) and a PLA axis
      (needs PLA defined in the cycle first,
      [#30](https://github.com/Jhawk414/F404/issues/30))
- [ ] Write failed sweep points to `deck/` beside each cycle deck
      ([#27](https://github.com/Jhawk414/F404/issues/27))
- [ ] Pydantic models for design-point inputs, sweep points and the
      duplicated OD bounds table ([#17](https://github.com/Jhawk414/F404/issues/17))
- [ ] Dry (part-power) nozzle throat schedule
      ([#8](https://github.com/Jhawk414/F404/issues/8), dry half), together with
      defining idle and calibrating the dry part-power end against the
      published data ([#25](https://github.com/Jhawk414/F404/issues/25))
- [ ] Resolve remaining cold/high-alt/max-AB Newton convergence failures
      ([#3](https://github.com/Jhawk414/F404/issues/3))
- [ ] CLI `init-config` and YAML configuration
      ([#16](https://github.com/Jhawk414/F404/issues/16))
- [ ] Inline creep/LCF life estimation
      ([#10](https://github.com/Jhawk414/F404/issues/10))
- [ ] `deck/` as a durable, reviewed home for cycle-deck CSVs + solver logs
- [ ] YAML-driven run configuration (`run.yml`), on top of
      [#17](https://github.com/Jhawk414/F404/issues/17)'s models
- [ ] Auto-generated sweep-envelope coverage plot

## Acknowledgments

This repo is a fork of NASA Glenn's
[pyCycle](https://github.com/OpenMDAO/pyCycle) (`om-pycycle` on PyPI),
built on the [OpenMDAO](https://openmdao.org/) framework. The `pycycle/`
library code, `setup.py`, and `example_cycles/` are vendored upstream
scaffolding, not F404-specific.

If you use pyCycle itself, please cite:

> E. S. Hendricks and J. S. Gray, "pyCycle: A Tool for Efficient
> Optimization of Gas Turbine Engine Cycles," *Aerospace*, vol. 6, iss. 87,
> 2019. doi:10.3390/aerospace6080087

## License

Apache License 2.0. See [`meta/LICENSE.txt`](meta/LICENSE.txt).
