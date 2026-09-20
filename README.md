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

**Status:** In development. Single-engine model with separate dry (military
power) and wet (afterburning) design points and altitude/dTs/throttle sweep
infrastructure. See [Current status](#current-status) for convergence coverage
and [Roadmap](#roadmap) for planned work. Not yet validated against public
F404 performance data.

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

F404 application code lives under `src/F404_pycycle/`, separate from the
vendored upstream `pycycle` library at the repo root (see
[#4](https://github.com/Jhawk414/F404/issues/4)).

| Path | Role |
|---|---|
| `src/F404_pycycle/engine_model.py` | `MixedFlowTurbofan(pyc.Cycle)`: single-point thermodynamic cycle (fan, HPC, burner, HPT/LPT, mixer, afterburner, nozzle) |
| `src/F404_pycycle/mp_cycle.py` | `MPMixedFlowTurbofan(pyc.MPCycle)`: links a DESIGN point and an off-design (OD) point, transferring map scalars and station areas |
| `src/F404_pycycle/problems.py` | `build_dry_problem()` / `build_wet_problem()`: design targets, initial guesses and input validation for each afterburner mode |
| `src/F404_pycycle/sweep_utils.py` | Sweep infrastructure: snake-pattern sweep grid, bridge-point warm-starting, `SweepRunner`, result extraction |
| `src/F404_pycycle/sweep_full_envelope.py` | CLI driver: runs the alt/dTs/throttle sweep for dry, wet, or both modes |
| `src/F404_pycycle/printer.py` | Console table formatter for DESIGN/OD results |
| `tests/` | pytest suite, one `<module>_test.py` per module ([#5](https://github.com/Jhawk414/F404/issues/5)) |
| `deck/` | Cycle-deck output CSVs |
| `docs/` | System architecture diagrams (`f404_cycle.d2`, `f404_cycle.svg`), planning docs (`improvements/`), and reference PDFs (`unclassified_perf_data/`) |
| `AGENTS/` | Session handoff notes |
| `meta/` | Vendored-library provenance (`LICENSE.txt`) |
| `pycycle/`, `setup.py`, `pyproject.toml`, `example_cycles/` | Vendored upstream `pyCycle` library |

## Cycle architecture

The thermodynamic cycle model in `engine_model.py` (`MixedFlowTurbofan`) represents the twin-spool, mixed-flow, augmented F404 turbofan engine:

![F404 Turbofan Cycle Architecture](docs/f404_cycle.svg)

*Diagram source maintained in [`docs/f404_cycle.d2`](docs/f404_cycle.d2).*

Key cycle components and mechanical couplings:
- **Low Pressure (LP) Spool**: 3-stage fan driven by the single-stage LP turbine via `lp_shaft` (10,000 rpm).
- **High Pressure (HP) Spool**: 7-stage HP compressor driven by the single-stage HP turbine via `hp_shaft` (14,000 rpm, 250 hp customer power extraction).
- **Cooling Bleeds**: HPC interstage bleed (`cool1`, 5.07% flow) cools the LPT; compressor discharge bleed (`cool3`, 11.0% flow) cools the HPT.
- **Mixed Exhaust & Augmentor**: Core flow and bypass flow mix in a confluent mixer, feed into the afterburner duct (active combustor in wet mode, pass-through in dry mode), and expand through a variable convergent-divergent nozzle (`mixed_nozz`).

## Software architecture and data flow

Current data flow from CLI invocation to output CSV.

```mermaid
flowchart TD
    subgraph Drivers["Entry point (src/F404_pycycle/)"]
        A["sweep_full_envelope.py<br/>--mode dry|wet|both"]
    end

    subgraph Model["Cycle model"]
        B["problems.py<br/>build_dry_problem · build_wet_problem<br/>targets, guesses, validation"]
        C["mp_cycle.py<br/>MPMixedFlowTurbofan(pyc.MPCycle)<br/>wires DESIGN + OD points"]
        D["engine_model.py<br/>MixedFlowTurbofan(pyc.Cycle)<br/>single-point thermodynamic cycle"]
    end

    subgraph Sweep["Sweep infrastructure"]
        E["sweep_utils.py<br/>build_snake_sweep · generate_bridge_points<br/>SweepRunner · extract_od_results"]
    end

    subgraph Output["Output"]
        F["printer.py<br/>page_viewer() console tables"]
        G["deck/*.csv<br/>cycle_deck_dry / _wet / _full_envelope"]
    end

    A --> B
    B --> C
    C --> D
    B --> F
    A --> E
    E --> C
    E --> G
```

`mp_cycle.py` instantiates `MixedFlowTurbofan` twice: once with `design=True`
(DESIGN point, solved once to size the engine) and once with `design=False`
(OD point, re-solved at each sweep condition). It passes converged map scalars
and station areas from the DESIGN instance into the OD instance so off-design
calculations use the sized engine geometry.

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

`src/F404_pycycle/` is an importable package (installed by the editable
install above), so entry points are run with `-m`:

Run the altitude/dTs/throttle sweep for dry and wet modes:

```bash
python -m F404_pycycle.sweep_full_envelope --mode both
```

Use `--mode dry` or `--mode wet` to run an individual mode. Output files
(`cycle_deck_dry.csv`, `cycle_deck_wet.csv`, or `cycle_deck_full_envelope.csv`)
are written to the working directory. Moving output generation to `deck/` is
tracked in [Roadmap](#roadmap).

## Testing

```bash
pytest tests                    # full suite, ~25 s
pytest tests -m "not slow"      # structural and unit tests only, ~6 s
```

One `tests/<module>_test.py` per module ([#5](https://github.com/Jhawk414/F404/issues/5)).
Tests marked `slow` build and solve a full `om.Problem`; the rest either use
pure functions or build a model without solving it. `pytest` needs no prior
install — `pythonpath` in `pyproject.toml` puts `src/` on the path — and runs
in CI on Ubuntu (3.9, 3.12) and macOS (3.12).

Coverage is 86% of `src/F404_pycycle`. The bulk of the remainder is
`sweep_full_envelope.py`'s `if __name__ == "__main__"` block, which can't be
imported; extracting it behind a real entry point is tracked in
[#16](https://github.com/Jhawk414/F404/issues/16).

## Current status

Latest full-envelope sweep (`--mode both`) at
alt ∈ {0, 2500, 5000} ft, dTs ∈ {0, ±10, ±20, ±30, ±40, ±50} R, static
(MN ≈ 0.001), 4 throttle levels per mode:

| Mode | Converged | Throttle sweep |
|---|---|---|
| Dry | 125 / 132 | Tt4 3100 → 2500 R |
| Wet | 89 / 132 | Tt7 3800 → 3200 R (Tt4 fixed at 3100 R MIL) |

All points with dTs ≥ 0 R converge. Solver failures concentrate at cold
(dTs < 0 R), high-altitude, maximum afterburning conditions, tracked in
[issue #3](https://github.com/Jhawk414/F404/issues/3).

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
- [x] Cap cycle-deck CSV precision — single `write_deck_csv()` writer with
      per-column decimals (scientific `%.4e` for the fuel-air ratios)
      ([#12](https://github.com/Jhawk414/F404/issues/12))
- [x] Per-module test suite (`tests/<module>_test.py`), 86% coverage, with
      golden DESIGN/OD baselines and regression cover on the
      false-convergence guards ([#5](https://github.com/Jhawk414/F404/issues/5))

Planned (see `docs/improvements/IMPROVEMENTS.md` for full detail):

- [x] `src/` restructure: separate F404 app code from vendored pyCycle
      library ([#4](https://github.com/Jhawk414/F404/issues/4))
- [ ] Single-engine sizing: unify dry and wet DESIGN points
      ([#2](https://github.com/Jhawk414/F404/issues/2))
- [ ] Resolve remaining cold/high-alt/max-AB Newton convergence failures
      ([#3](https://github.com/Jhawk414/F404/issues/3))
- [ ] Sync vendored `pycycle/` against upstream
      ([#6](https://github.com/Jhawk414/F404/issues/6))
- [ ] CLI entry point (`design` / `sweep` / `init-config` subcommands), with
      `min,max,step` range flags ([#16](https://github.com/Jhawk414/F404/issues/16),
      [#13](https://github.com/Jhawk414/F404/issues/13))
- [ ] Pydantic models for design-point inputs, sweep points and the
      duplicated OD bounds table ([#17](https://github.com/Jhawk414/F404/issues/17))
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
