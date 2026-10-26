# F404 handoff — 25 Oct 2026

Current state and next work only. Earlier session history is in
`git log --follow -- AGENTS/`; architecture decisions are in `docs/adr/`.

## Current model and verification

- One engine, sized at sea-level-static dry MIL: DESIGN Mach 0.001, thrust
  11,000 lbf, Tt4 3100 R. One `OD` point handles dry and wet operation.
- Max AB is Tt7 **3607.68 R**, calibrated to 17,700 lbf. Afterburner loss is
  Kumar flameholder drag plus Rayleigh heat-addition loss: 2.1% cold, 6.6% at
  SLS max AB. DESIGN includes the cold loss.
- Dry A8 is the DESIGN throat. Wet A8 uses explicit choked-flow continuity,
  holding the gas generator near its dry state. Dry PLA/A8 scheduling is open.
- Default grids: 6 Mach levels, 3 altitudes, 11 temperature offsets, 4 power
  levels: **792 points per mode**. Dry **643/792**, wet **663/792** converge.
  The README holds the per-Mach counts; decks are committed under `deck/`.
- Current local reference environment: Python 3.9.6, OpenMDAO 3.39.0,
  NumPy 2.0.2. CI also tests newer OpenMDAO releases; results can differ.
- The full local suite passes **325 tests (281 fast), 97% coverage**. It covers
  sizing goldens, convergence regressions, CLI behavior, and validation. Fast PR CI excludes tests marked `slow`; the full
  matrix runs on `main`, manual dispatch, or the user-applied `full-ci` label.
  **Agents must not add `full-ci`.**

Architecture records:

- [ADR-0001](../docs/adr/0001-single-engine-sizing.md): one engine sized dry;
  its old two-OD topology is superseded by ADR-0002.
- [ADR-0002](../docs/adr/0002-single-od-topology.md): single OD, Kumar loss,
  explicit wet A8 law.
- [ADR-0003](../docs/adr/0003-fail-fast-sweep.md): 20-iteration sweep cap and
  rollback of unsuccessful bridges. Model/cold-solve default remains 50.

## Latest work: YAML config and thin Pydantic validation

[PR #45](https://github.com/Jhawk414/F404/pull/45) closes
[#16](https://github.com/Jhawk414/F404/issues/16) and starts the thin sweep-run
slice of [#17](https://github.com/Jhawk414/F404/issues/17). `f404 run.yml` runs
the committed full grid; `--example-yaml` replaces the proposed `init-config`
and prints a runnable example with inline descriptions. The complete schema,
axis order/10,000-point limit, and snapshot rules live in the
[CLI guide](../docs/guide/cli.md#yaml-run-configuration).

- `RunConfig`/`SweepConfig` and nested `ThrottleConfig` share axis validation
  with CLI flags. Range strings expand into traversal order; explicit lists
  must already be in that order or fail before output/solver work.
- Dry, wet, and combined decks have corresponding `run_dry.resolved.yml`,
  `run_wet.resolved.yml`, and `run_both.resolved.yml` snapshots. Single-mode
  runs preserve the other mode and combined snapshots.
- Physics, default grids, and solver settings are unchanged. CLI behavior does
  change: help now eagerly imports OpenMDAO, and every sweep writes snapshots
  before solving, exiting 2 if output setup or snapshot writing fails.
- Full-deck SHA-256 proof and current validation results are in the PR's
  **Proof of function / behavior** section. Review regressions reject ambiguous
  lists before starting a run and preserve snapshots across successive modes.

Still deferred under #17: design/component inputs, individual sweep points,
shared solver bounds, and better DESIGN feasibility diagnostics. Existing
`problems._validate_design_targets()` stays until that design-input slice.
Deck writing and comparison retain plain validation rather than Pydantic.

## Next work

**#30 → PLA axis → remainder of #17 → #8 + #25 + #35, measuring #3 → #10.**
[#38](https://github.com/Jhawk414/F404/issues/38) is independent.

| Issue | Remaining scope |
|---|---|
| [#30](https://github.com/Jhawk414/F404/issues/30) | Decide what PLA commands, record an ADR and provisional schedule; add the PLA axis afterward |
| [#17](https://github.com/Jhawk414/F404/issues/17) | Extend input validation beyond sweep-run settings; consolidate bounds |
| [#8](https://github.com/Jhawk414/F404/issues/8) + [#25](https://github.com/Jhawk414/F404/issues/25) | Dry A8 scheduling and idle/part-power calibration, together |
| [#35](https://github.com/Jhawk414/F404/issues/35) | Combustion efficiency in both burners; recalibrate max AB afterward |
| [#3](https://github.com/Jhawk414/F404/issues/3) | Cold/high-Mach convergence; measure alongside calibration |
| [#38](https://github.com/Jhawk414/F404/issues/38) | Supersonic inlet recovery and OD airflow ceiling |
| [#10](https://github.com/Jhawk414/F404/issues/10) | Incremental creep/LCF estimate |

### PLA and calibration constraints

- PLA is currently absent: dry sweeps command Tt4 and wet sweeps Tt7.
  Landmarks from the literature: 31° flight idle, **87° MIL**, 130° max AB.
- Below MIL, the real engine schedules N2 and A8. Above MIL it schedules AB
  fuel, with A8 trimmed to a scheduled LPT-exit temperature (T5.6). PLA is
  therefore not a single existing model variable. #30 must settle the
  provisional dry command, light-off, and schedule source.
- Preserve temperature-based `--throttle`; PLA is a separate axis spanning
  dry/wet operation. Ray's measured thrust-vs-PLA data is a schedule candidate.
- Tune dry A8 and idle together. Opening A8 at fixed Tt4 raises BPR, already
  near its 1.0 bound at part power; the real engine commands N2 below MIL.
- Keep DESIGN/MIL as the minimum-A8 anchor. Prefer an explicit dry schedule
  multiplying `a8_sched.A8_dsn`, with no new Newton state; the wet factor then
  scales it continuously. Re-check max-AB calibration after any DESIGN change.
- Define idle from observed thrust or N2, rather than a Tt4 floor. Model BPR
  (~0.75 MIL, ~0.95 at 2500 R) is above published ~0.34; MIL TSFC ~0.621 is
  optimistic against published ~0.78–0.81. Compare operating conditions and
  station definitions before treating a literature value as a target.
- A minimum wet FAR_ab around 0.005 is a proposed follow-up, not implemented.
- PR #21's deck-interpolation GUI is deliberately parked pending PLA. Do not
  review/rebase it as part of the above tasks.

## Data and references

Start at [`docs/unclassified_perf_data/README.md`](../docs/unclassified_perf_data/README.md).
Search its *Cross-Study Multi-Condition Reference Map* and *Research Selection
Guide*, then read only the relevant paper. The collection is large; delegate
PDF searches when available.

- Provenance tags matter: `[M-DIR]` measured, `[M-SPEC]` manufacturer rating,
  `[M-MOD]` GE/model-derived, `[M-PLOT]` chart reading. Published thrust is
  generally uninstalled. Do not mix test conditions or station definitions.
- Sourced A8 anchors: ~400 in² flight idle (Johnson GE model), 232–249 in² MIL
  (TM-4140/TM-4538), 420 in² max AB at 30k ft/M1.2 (TM-4140 measured). A9/A8
  is 1.24–1.49 (TM-4538). The old “215 in² at IRP” has no verified source.
- MCAS Iwakuni 2017 telemetry, merged in PR #44, anchors ground idle at PLA
  18.1°, N1 4089 rpm, N2 10933 rpm, PS3 36.2 psia, A8 75.7% open. T5 444°C
  has an unverified station label. Relevant to #25 and dry #8; see the report
  indexed in the performance-data README for provenance and uncertainties.
- [`docs/references/README.md`](../docs/references/README.md) holds general
  aerothermal methods separately from F404 validation data. Kumar (1980) is
  the augmentor-loss source; `[M-THY]` denotes analytic results.

## Standing gotchas

**Environment and process**

- `gh` defaults to upstream `OpenMDAO/pyCycle` in this checkout. Always pass
  `--repo Jhawk414/F404`. Older issue bodies use `src/F404_pycycle/` and stale
  convergence counts; use current code and decks.
- Re-run `pip install -e ".[all]"` after pulling package/dependency changes.
  A stale non-editable pyCycle install once shadowed the checkout.
- Test fixtures often use `verbose=False`; exercise printing paths when
  changing them. `printer.py` passes `file` because pyCycle helpers bind
  stdout at import, otherwise defeating `capsys`.
- Keep the machine awake with `caffeinate -i` for sweeps. Each mode takes
  roughly 30–35 minutes in the reference environment; run modes in separate
  processes for parallel proof. OS thread count alone does not measure useful
  solver parallelism. Do not change thread caps without measuring.

**Model and solver**

- One `OD` point: `mp.od_pt`. Removed names include `OD_dry`, `OD_wet`,
  `od_pts`, `frozen_pts`, `a8_ctrl`, and `_OD_WET_BOUNDS`.
- `SweepRunner` seeds its last-good state from the problem it receives
  (normally SLS max AB). A remote first point can fail where the same point
  midway through the default traversal converges. Traversal order matters.
- Sweeps leave OD Newton capped at 20. Before raising that cap after a model
  change, re-measure iteration histories and consider ADR-0003's stall
  detection alternative. Known failed bridges roll back to the last good state.
- The two wet points lost on the pre-#37 throttle grid were replayed at caps
  20 and 50: one stalled at residual 1.76e7; the other started with NaN.
  They are warm-start/convergence problems, not slow convergers.
- Dry low-power failures grow with Mach as BPR reaches 1.0. Wet cold-corner
  failures mostly follow dry MIL failures. One cold M0.95 point reaches the
  200 lbm/s OD airflow ceiling (#38).
- Use `_scalar()` for OpenMDAO length-1 arrays. Bare `float(array)` can be
  caught by broad failure guards and silently mark every point unconverged.
  Keep NumPy's scalar-deprecation-as-error filter scoped to `f404.*`; unscoped
  it also fails vendored pyCycle. `ruff NPY201` does not catch this conversion.

**CLI, decks, and tests**

- Detailed usage belongs in `docs/guide/cli.md`; README keeps short examples.
  The guide mirrors read-only to the GitHub wiki; edit the repo copy.
- Negative-start ranges are joined to their flags before argparse, including
  abbreviations. Add any new range flag to `_RANGE_FLAGS` in `cli.py`.
- Validation exits 2 before solving. A non-converging design exits 1. There
  is no CLI wet-throttle floor beyond positivity: the physical floor is the
  solved augmentor inlet temperature, and a missed target is a failed row.
- Decks are full float64 CSVs: `INPUT_COLUMNS` + `DECK_COLUMNS` + `failure`,
  one row per request. Failed outputs are blank. Filter `df[df.converged]`.
  `f404 compare --changed-only` is the normal numeric regression proof;
  SHA-256 equality also proves identical row order/failures/formatting.
- Decks older than 18 Oct were rounded; regenerate for precision comparisons.
  GitHub's raw-text display of current ~650 KB CSVs is its size limit.
- Tests are `tests/<module>_test.py`. Connection assertions match path prefix
  and suffix because promoted OpenMDAO paths can change internally.
- Known unrelated gap: a CSV without the required deck command/temperature
  columns can still produce a bare `KeyError` in `f404 compare`. It remains
  outside this run-config change; deck-boundary validation belongs separately.
