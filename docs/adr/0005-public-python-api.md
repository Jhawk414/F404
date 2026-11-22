# ADR-0005: A public Python API — `DesignInputs`, `design`, `run_point`, `sweep`

**Status:** Accepted
**Date:** 2026-11-15
**Deciders:** @Jhawk414
**Issues:** [#47](https://github.com/Jhawk414/F404/issues/47), and
[#17](https://github.com/Jhawk414/F404/issues/17) narrowed to "Pydantic at
user-input boundaries". Consumers: the studio
([#46](https://github.com/Jhawk414/F404/issues/46)), calibration
([#48](https://github.com/Jhawk414/F404/issues/48)), the PLA axis
([#30](https://github.com/Jhawk414/F404/issues/30)) and the dry A8 schedule
([#8](https://github.com/Jhawk414/F404/issues/8)).

## Context

Before this change there was no supported way to size and run a non-default
engine from Python. `build_problem()` took three targets; the six
turbomachinery values were literals in `problems._apply_design_inputs()`, and
duct losses, bleeds and power extraction were `pyc_add_cycle_param` defaults
in `mp_cycle.py`. `run_sweeps()` always built the default engine, nothing was
exported from `f404/__init__.py`, and a single OD point was reachable only as a
one-point sweep. Validation was three hand-written checks in
`_validate_design_targets()`; an efficiency of 1.05 converged to an impossible
engine.

The studio and calibration build on whatever ships here, and need to:

- re-size from changed inputs, many times, in parallel processes;
- reach OD conditions from a sized engine reproducibly: #46 requires
  `workers=1` and `workers=4` to give identical numbers;
- differentiate at a converged OD state (`compute_totals`), so the solved
  Problem must stay reachable, not hidden behind a CSV;
- name design variables, for `compute_totals(wrt=...)` and the studio's
  raw-path escape hatch.

The hard constraint: defaults reproduce today's engine bit for bit. `f404
verify` passes unchanged, the `tests/problems_test.py` goldens hold, and `f404
sweep --mode dry/wet` and `f404 run.yml` regenerate the committed decks
byte-identical.

## Decision

```python
from f404 import DesignInputs, Engine, design, run_point, sweep

eng = design(DesignInputs(fn_target=11_000, hpc_PR=7.0))   # Engine, at SLS max AB
row = run_point(eng, mode='dry', alt=5000, mach=0.8, dts=-30, throttle=2700)  # dict
deck = sweep(eng, mode='wet', mach=[0.001, 0.4], alt=0, dts=0)                  # DataFrame
```

1. **`DesignInputs`** (`config.py`): a flat, frozen Pydantic model. It is
   strict, forbids unknown keys and rejects NaN/inf, through a `StrictModel`
   base that `RunConfig`, `SweepConfig` and `ThrottleConfig` now share. It holds
   every value that sizes the engine. The defaults are the calibrated engine,
   and `mp_cycle.py` reads its defaults from it, so the values live in one place.
2. **Field names follow model paths** (`hpc.cool1:frac_W` → `hpc_cool1_frac_W`,
   `DESIGN.fan.PR` → `fan_PR`). `problems.DESIGN_INPUT_PATHS` is the public
   field → (path, units) table, and `design()` sets every field through it.
3. **`design(inputs=DesignInputs(), *, verbose=False) -> Engine`** replaces
   `build_problem()`. `Engine` is a frozen dataclass `(prob, inputs, anchor)`,
   where `anchor` is the OD output vector at SLS max AB. It raises
   `MaxTt7TooLowError` or `om.AnalysisError` as before.
4. **`run_point(engine, *, mode, alt, mach, dts, throttle) -> dict`** restores
   the anchor, bridges to the point with the existing sweep bridge, and returns
   one deck row. A failed point is a row with `converged` False, not an
   exception. A converged point leaves `engine.prob` solved there.
5. **`sweep(engine, *, mode, mach, alt, dts, throttle=None, out_dir=None,
   verbose=False) -> DataFrame`** restores the anchor and sweeps one mode.
   Axes are validated by `config.axis()`, as for the CLI and YAML. The default
   throttle runs down from the engine's own `mil_Tt4` or `max_Tt7` in four
   200 R steps. The sweep's first point is bridged from the anchor condition
   (`SweepRunner.run_sweep(start=...)`).
6. **The CLI routes through these.** `f404 design` validates its three flags
   as `DesignInputs`; `run_sweeps()` sizes from `DesignInputs` and calls
   `sweep()` per mode. `ValidationError` is formatted once, in `cli.py`.
7. **A YAML `design:` block ships now**, optional, mapping onto `DesignInputs`.
   Resolved snapshots record the full design inputs next to the sweep.
8. **`f404/__init__.py` exports eagerly**, with `__all__`.

### `DesignInputs` fields

| Group | Fields | Bound |
|---|---|---|
| Targets | `fn_target` (lbf), `mil_Tt4`, `max_Tt7` (degR) | > 0 |
| Turbomachinery | `fan_PR`, `hpc_PR` | > 1 |
| | `fan_eff`, `hpc_eff`, `hpt_eff`, `lpt_eff` | (0, 1] |
| Design spool speeds | `LP_Nmech`, `HP_Nmech` (rpm) | > 0 |
| Inlet | `ram_recovery` | (0, 1] |
| Duct losses | `inlet_duct_dPqP`, `splitter_core_duct_dPqP`, `hpt_duct_dPqP`, `lpt_duct_dPqP`, `bypass_duct_dPqP`, `mixer_duct_dPqP` | [0, 1) |
| Cooling bleeds | `hpc_cool1_frac_W`, `bld3_cool3_frac_W` | [0, 1) |

Left out for now: Newton initial guesses (solver state, not inputs), the
augmentor-loss constants (a correlation, ADR-0002), station design Mach
numbers, bleed `frac_P`/`frac_work`, and HP power extraction (`hp_shaft.HPX`),
which the shaft balances ignore until
[#60](https://github.com/Jhawk414/F404/issues/60) is fixed. A field with a default is
non-breaking to add, so each waits for a consumer.

There is no `max_Tt7 > mil_Tt4` validator. The augmentor heats mixed flow at
about 1500 R, so `max_Tt7` below `mil_Tt4` is a valid engine (a test builds one
at `mil_Tt4 − 92`). The real constraint, `max_Tt7` above the SLS-mil
augmentor inlet temperature, depends on the solved cycle and stays a
post-solve check.

## Options considered

### What `DesignInputs` holds and how it is named

| Option | Assessment |
|---|---|
| Targets only (`fn_target`, `mil_Tt4`, `max_Tt7`) | Rejected: the studio and calibration vary component values, and #47 asks for all literals |
| **Flat model of every sizing literal, named after model paths (chosen)** | Low complexity. One mechanical name↔path mapping, which `compute_totals(wrt=...)` and the studio's raw-path escape hatch reuse |
| Nested per-component models (`fan: {PR, eff}`) | Rejected: tidier YAML, but every studio column and calibration variable needs a flattening convention, and the paths stop being mechanical |
| Include Newton initial guesses | Rejected: they are solver state; changing them doesn't change the engine, only whether Newton finds it |

### What `design()` returns

| Option | Assessment |
|---|---|
| Keep `(prob, mp)` | Rejected: no place for the anchor or the inputs, so OD calls can't be history-independent |
| `NamedTuple` `Engine(prob, mp)` | Rejected: `prob, mp = engine` unpacking breaks the day a field is added, and tuple equality on an ndarray field raises |
| **Frozen dataclass `Engine(prob, inputs, anchor)` (chosen)** | Attribute access, room to grow, `eq=False`. `mp` is `prob.model`, so it is not a field |
| Keep `build_problem()` beside `design()` | Rejected: two near-identical entry points, two places to validate |

### How `run_point()` reaches its point

| Option | Assessment |
|---|---|
| Warm-start from wherever the Problem was left | Rejected: results depend on call history, so parallel studies can't match serial ones |
| **Restore the anchor, bridge from the anchor condition (chosen)** | Removes the state-vector history; one extra bridge per call. #59 added pyCycle's static-pressure guess caches to the restore |
| Re-run `design()` per point | Rejected: about 2.5 s more per point, for the same anchor |

Bridge path, settled by a throwaway spike (below):

| Option | Assessment |
|---|---|
| **A: existing linear bridge, 5 steps (chosen)** | No new code; reached all 81 in-envelope points tested |
| B: linear bridge, step count adapted to `BRIDGE_THRESHOLD` | No gain over A in the envelope |
| C: axis-by-axis legs in deck traversal order | Same accuracy, about 4× slower (≈ 42 s at M 0.95) |

### `sweep()` defaults and checks

| Option | Assessment |
|---|---|
| Fixed default throttle lists (3100 → 2500 R, 3607.68 → 3007.68 R) | Rejected: a `mil_Tt4 = 3000` engine would start its default dry sweep 100 R over mil |
| **Engine-relative defaults, `top − 200·k`, k = 0…3 (chosen)** | Equal to the fixed lists for the default engine, so decks are unchanged |
| Reject a dry throttle above `mil_Tt4` | Rejected: over-temperature is a legitimate what-if, and the start bridge removes the "starts away from the design point" hazard #17 raised |

### Exports and the YAML `design:` block

| Option | Assessment |
|---|---|
| **Eager imports in `__init__.py` (chosen)** | Every `f404` submodule already imports OpenMDAO (about 0.6 s); a lazy `__getattr__` saves nothing |
| **Ship `design:` now (chosen)** | Small: one optional `RunConfig` field, and the CLI passes it through. It completes #17's narrowed scope without a follow-up issue |
| Defer `design:` | Rejected: a follow-up for about 20 lines |

## Spike: the `run_point()` bridge

Each attempt restored the SLS max-AB anchor and reached the target from home
(static, 0 ft, dTs 0, top power), scored by convergence and the largest
relative difference from the committed deck row over Fn, TSFC, W and BPR.
Python 3.9.6, OpenMDAO 3.39.0, macOS arm64.

Home is a corner of the default grid, so the largest in-envelope jumps go to
the far corners. The second pass took the 30 converged deck points per mode
farthest from home, at 11–14 bridge-threshold lengths (summed over Mach,
altitude, dTs and power, each divided by its `BRIDGE_THRESHOLD`).

| Pass | Method | Converged | Max / median error vs deck | Mean time |
|---|---|---|---|---|
| 21 points: cold/fast, M 0.95 part power, hot/high, random | A | 21/21 | 3.6e-6 / 6.3e-8 | 3.1 s |
| | B | 21/21 | 3.6e-6 / 1.4e-7 | 2.8 s |
| | C | 21/21 | 6.1e-6 / 8.8e-8 | 12.8 s |
| 60 farthest points, 30 dry + 30 wet | A | 60/60 | 3.6e-6 / 1.0e-7 | 3.1 s |
| | B | 60/60 | 3.6e-6 / 1.0e-7 | 3.0 s |

Every error is at the ADR-0004 solver-path floor (about 3e-6): the same point
reached by a different path. Within the envelope A needs nothing B or C add.
Points beyond the default grid (15,000 and 30,000 ft) were tried and excluded:
the model isn't calibrated that high, and no method converged reliably there.

## Trade-off analysis

The API is deliberately small: one model, one dataclass, three functions.
Restoring the anchor costs one bridge per call. In exchange, a run's result
no longer depends on the state vectors earlier calls left, which parallel
studies and calibration need. The output vector alone was not enough: each
pyCycle `PsResid` caches its last Ps guess as a Python attribute, so a wet
sweep after a dry sweep differed from a wet-only sweep by up to 7e-5 relative
on the default grid. The anchor now records those caches and the restore
resets them, which makes the result history-free bit for bit
([#59](https://github.com/Jhawk414/F404/issues/59)). Leaving the Problem at the solved point, rather than
restoring it on exit, keeps `compute_totals` available. The cost is a contract
users must respect: `engine.prob` reflects the last call, and an Engine's
inputs must not be changed in place.

Field names tied to model paths make a rename in the model a breaking change
to the API. That is acceptable: the names are already the vocabulary of
pyCycle and of the decks.

## Consequences

- Python users and agents can size and run any valid engine without reading
  solver code, and invalid inputs fail before the solve with a field-level
  message.
- The CLI keeps no model logic, so the CLI and Python results are the same by
  construction.
- Error text for `f404 design` flags changes to Pydantic's field-level
  messages (e.g. `design.fn_target: Input should be greater than 0`). Units
  and defaults are now in the CLI guide and the field comments, not the error.
- A Python `sweep()` or YAML grid whose first point is away from home is now
  bridged there. Its rows can differ from before at solver-path level (≈1e-6),
  and some first points that failed now converge. The default grids start at
  home and are unchanged.

### Recorded for later

- **Snapshot migration**: resolved snapshots store `design:` by field name.
  Renaming a field, or moving `max_Tt7` into #30's schedule model, needs a
  migration for old snapshots, or they fail validation as unknown keys.

- **Schedule parameters** (dry A8 #8, PLA #30) change OD behaviour, not the
  sizing, and #48 will calibrate them. They go in a sibling model passed to
  `design()` (e.g. `design(inputs, schedules=...)`), not into `DesignInputs`,
  so the flat names never need nesting later.
- **Re-sizing on one Problem**: `design(inputs, *, warm_start=engine)` is
  reserved for the studio's phase 1 (#46); it would consume the engine it is
  given.
- **Infeasible designs**: a named error for a DESIGN solve that fails or
  clips a balance at its bound, with a diagnosis, belongs to
  [#57](https://github.com/Jhawk414/F404/issues/57) (single-source bounds).
- **Studio columns**: `fan_PR`, `hpc_PR`, `fan_eff`, `hpc_eff`, `LP_Nmech`
  and `HP_Nmech` are both `DesignInputs` fields and OD deck columns; the
  studio's tidy frame needs a prefix convention (#46).
- **Tolerance against `f404 verify`**: `run_point()` lands within the
  solver-path floor (about 3e-6) of the deck and of `verify`'s fixed solve
  path, above `verify`'s 1e-6 tolerance (ADR-0004). An `--extended` verify
  that reads OD points through `run_point()` must take its reference from
  `run_point()` itself, which is deterministic, not from the decks.
- **`max_Tt7`'s default** is calibrated to 17,700 lbf for the default sizing
  only. A re-sized engine's max AB is not calibrated.

## Action items

1. [x] `StrictModel`, `DesignInputs`; constants moved to `config.py`
2. [x] `design()`, `Engine`, `DESIGN_INPUT_PATHS`; `_validate_design_targets()` deleted
3. [x] `sweep()`, `run_point()`, `SweepRunner(start=, verbose=)`; CLI routed through them
4. [x] `f404/__init__.py` exports; YAML `design:` block and snapshots
5. [x] #17 narrowed; [#57](https://github.com/Jhawk414/F404/issues/57) filed
6. [x] Deck proof in the PR: `--mode dry/wet` byte-identical to the committed decks; `f404 run.yml` byte-identical to `main`'s `run.yml` (its wet deck differs from the committed one on `main` too, #59)
7. [x] `docs/guide/python.md`, CLI guide, README, handoff
