# ADR-0006: Power Lever Angle (PLA) definition and provisional schedule

**Status:** Accepted
**Date:** 2026-11-28
**Deciders:** @Jhawk414
**Issues:** [#30](https://github.com/Jhawk414/F404/issues/30). Unblocks dry $A_8$ scheduling ([#8](https://github.com/Jhawk414/F404/issues/8)), idle and dry part-power calibration ([#25](https://github.com/Jhawk414/F404/issues/25)), and gradient-assisted calibration ([#48](https://github.com/Jhawk414/F404/issues/48)). Builds on [ADR-0002](0002-single-od-topology.md) and [ADR-0005](0005-public-python-api.md).

## Context

Until this change, power lever angle (PLA) was absent from the cycle model. Sweeps commanded cycle temperatures directly: `Tt4` in dry mode and `Tt7` in wet mode (`--throttle`). That forced callers to run dry and wet as separate sweeps and left three open efforts without a shared power coordinate:

- a single `--pla` / `pla=` sweep axis spanning dry and wet operation;
- the dry half of the variable exhaust nozzle throat schedule ([#8](https://github.com/Jhawk414/F404/issues/8));
- idle definition and dry part-power calibration ([#25](https://github.com/Jhawk414/F404/issues/25), [#48](https://github.com/Jhawk414/F404/issues/48)).

### Published F404 PLA landmarks and control laws

From the unclassified F404 corpus indexed in [`docs/unclassified_perf_data/README.md`](../unclassified_perf_data/README.md):

| PLA (deg) | Regime / Landmark | Provenance & Sources |
|---|---|---|
| `18.1` | Ground idle (`N2 = 65.0%`, `N1 = 30.8%`, `A8 = 75.7%` open) | `[M-DIR]` MCAS Iwakuni (2017); `[M-SPEC]` Frith (1985, `ADA164562` Fig. 28: `18°`) |
| `31.0` | Flight idle (`A8 ≈ 400 in²`) | `[M-MOD]` Johnson (1990, `NASA TM-4240`); `[M-DIR]` Ray (1990, `NASA TP-3001` Table 6); `[M-MOD]` Conners (1989, `NASA TM-4140`); `[M-SPEC]` Frith Fig. 28; `[M-DIR]` Yuhas & Ray (1992, Fig. 5) |
| `87.0` | Intermediate / MIL (max non-afterburning) | Unanimous across Frith, Ray, Conners, Johnson, Yuhas & Ray |
| `92.5` | Minimum AB / light-off gate | `[M-MOD]` Conners (`TM-4140` L261: `92.5°`); `[M-MOD]` Johnson (`TM-4240` Fig. 8: `~92°`); `[M-DIR]` Yuhas & Ray (Fig. 5: `~92–97°`); `[M-SPEC]` Frith (Fig. 28: `~87–90°` transition band) |
| `130.0` | Maximum AB | Unanimous across Frith, Ray, Conners, Johnson, Yuhas & Ray |

*Convention note:* Ennix et al. (`NASA TM-4538`) reports `35°` idle and `102°` MIL from the F-18 maintenance data recorder (airframe/cockpit rigging convention; Hadzic 2010 and Henry 1988 show similar CF-18 airframe scaling). This model standardizes on the **GE engine-level PLA convention** (`31° / 87° / 92.5° / 130°`).

*Data-source note:* Ray (`NASA TP-3001`) does not tabulate an absolute thrust-vs-PLA curve; it tabulates thrust-calculation uncertainties and $2\sigma$ bands grouped by PLA bins (`31°`, `40–87°`, `90–130°`). Multi-PLA performance tables in the corpus are model-derived: Johnson's 4-point table (`31°`, `87°`, `~92°`, `130°`, linearly interpolated) and Conners' Table 2 (`70°`, `87°`, `92.5°`, `109°`, `130°`).

In the physical F404 (Frith Fig. 28; Yuhas & Ray):
- **Below MIL (`< 87°`)**: hydromechanical control schedules corrected core speed $N_2$ (trimmed with $T_{2.5}$) and exhaust throat area $A_8$; $N_1$ and $T_{5.6}$ float.
- **At MIL and above (`87°–130°`)**: the ECU holds scheduled $N_1$ (vs. $T_1$) and schedules afterburner fuel flow with PLA, modulating $A_8$ to hold scheduled LPT exit temperature $T_{5.6}$.

In the current uncalibrated cycle model, however, dry BPR sits at `0.75` at MIL and climbs to `0.94` at `Tt4 = 2500 R` against a `1.0` balance bound, and dry $A_8$ is frozen at the DESIGN throat (ADR-0002). Reaching physical idle $N_2$ (`65%` ground idle, `~70–75%` flight idle) requires joint BPR, spool-speed, and dry-$A_8$ calibration under `#8`, `#25`, and `#48`.

## Decision

1. **Standardize on GE engine-level PLA (`deg`) with a provisional piecewise-linear schedule (`PlaSchedule`)** in `config.py`, as a sibling frozen `StrictModel` to `DesignInputs` (per ADR-0005):

   | Field | Default | Meaning |
   |---|---|---|
   | `idle_pla` | `31.0` deg | Flight idle landmark (lower PLA bound until `#25`) |
   | `mil_pla` | `87.0` deg | Intermediate / MIL landmark |
   | `min_ab_pla` | `92.5` deg | Afterburner light-off gate (`Conners TM-4140` / `Johnson TM-4240`) |
   | `max_ab_pla` | `130.0` deg | Maximum afterburner landmark |
   | `idle_Tt4` | `2500.0` degR | Provisional dry `Tt4` at `idle_pla` (Spike 001) |
   | `min_ab_Tt7` | `1900.0` degR | Provisional wet `Tt7` at `min_ab_pla` (Spike 002) |

   `PlaSchedule.resolve(pla, inputs)` maps a scalar `pla` in `[idle_pla, max_ab_pla]` to `(mode, Tt4_cmd, Tt7_cmd)`:
   - **Dry ramp** (`idle_pla <= pla <= mil_pla`): `mode = 'dry'`, linear interpolation of `Tt4_cmd` from `idle_Tt4` to `inputs.mil_Tt4`, `Tt7_cmd = 0.0`.
   - **AB gate detent** (`mil_pla < pla < min_ab_pla`): `mode = 'dry'`, `Tt4_cmd = inputs.mil_Tt4`, `Tt7_cmd = 0.0`. Setting `min_ab_pla == mil_pla` collapses the detent if a caller wants immediate light-off above MIL.
   - **Wet ramp** (`min_ab_pla <= pla <= max_ab_pla`): `mode = 'wet'`, `Tt4_cmd = inputs.mil_Tt4`, linear interpolation of `Tt7_cmd` from `min_ab_Tt7` to `inputs.max_Tt7`.
   - **Below `idle_pla` (`< 31°`) and above `max_ab_pla` (`> 130°`):** rejected with `ValueError`. Ground idle (`18.1°`) is intentionally excluded until `#25`/`#8` calibrate idle with dry $A_8$ opening.

2. **Keep the single OD topology and existing `Tt4`/`Tt7` balances untouched.**
   - No new Newton state and no dry $A_8$ opening yet; DESIGN/MIL stays the minimum-$A_8$ anchor (`f_open = 1.0`). When `#8` adds dry $A_8$ opening, it will multiply `a8_sched.A8_dsn` explicitly as a function of PLA.
   - All existing `f404 verify` checks, sizing goldens, and `--throttle` decks remain bit-for-bit identical.

3. **Public Python API (`f404`):**
   - Export `PlaSchedule` from `f404`.
   - `design(inputs=DesignInputs(), *, schedules=PlaSchedule(), verbose=False) -> Engine`: attaches `schedules` to `Engine`; schedule temperature bounds (`idle_Tt4 < inputs.mil_Tt4`, `min_ab_Tt7 < inputs.max_Tt7`) are validated when PLA is actually used (`sweep(..., pla=...)`, `run_point(..., pla=...)`, and PLA `RunConfig`) so temperature-only designs keep `MaxTt7TooLowError` intact.
   - `run_point(engine, *, mode=None, alt, mach, dts, throttle=None, pla=None, verbose=False) -> dict` and `sweep(engine, *, mode=None, mach=..., alt=..., dts=..., throttle=None, pla=None, out_dir=None, verbose=False) -> DataFrame`:
     - `throttle` and `pla` are strictly mutually exclusive.
     - `throttle` retains its existing temperature semantics and requires `mode` (`'dry'` or `'wet'`).
     - `pla` spans dry and wet in a single descending sweep starting from the SLS max-AB anchor (`engine.home('pla')`), resolving per-point `mode` (`'wet'` / `'dry'`) and recording a `PLA` column in the returned deck (`PLA_INPUT_COLUMNS`).

4. **CLI and YAML:**
   - `f404 sweep --pla MIN,MAX,STEP` is mutually exclusive with both `--throttle` and `--mode` (exits 2). It runs one unified descending PLA sweep and writes `cycle_deck_pla.csv` + `run_pla.resolved.yml`.
   - Existing `f404 sweep --throttle` and `run.yml` keep their exact behavior and CSV schema (no `PLA` column added to temperature-driven decks).
   - YAML `RunConfig` accepts an optional `schedules:` block (`PlaSchedule`), and `SweepConfig` accepts either `throttle:` + `mode:` or `pla:` (mutually exclusive).
   - `f404 compare` treats `PLA` as an input/metadata column rather than a compared performance output.

## Options Considered

### Dry commanded variable

| Option | Assessment |
|---|---|
| **Provisional `Tt4` schedule via `PlaSchedule` (chosen)** | Low complexity. Zero OD balance changes; preserves `--throttle`, `verify`, and committed decks bit-for-bit; unblocks `#8`/`#25`/`#48` immediately |
| Direct corrected-$N_2$ balance on OD | Rejected for `#30`: conflicts with `--throttle` (`Tt4` command), touches `_OD_BOUNDS` (before `#57`), and hits `BPR = 1.0` before real idle $N_2$ on the uncalibrated cycle |
| Direct thrust target (`Fn`) | Rejected: non-physical control law; thrust varies strongly with altitude/Mach at fixed PLA |

### Wet light-off representation

| Option | Assessment |
|---|---|
| **`Tt7` ramp with `min_ab_pla = 92.5°` detent and `min_ab_Tt7 = 1900 R` (chosen)** | Matches F404 AB gate in Conners/Johnson and NASA TN D-6839 lean pilot floor (`FAR_ab ≈ 0.006`); configurable (`min_ab_pla = 87.0` collapses detent) |
| Continuous `Tt7` ramp from `Tt6` at `87°` | Rejected as default: `Tt6` depends on flight condition and real AB ignition requires a minimum stable fuel-air ratio |
| Command `FAR_ab` directly | Rejected: breaks symmetry with `max_Tt7` calibration and `AugmentorControl`'s `Tt7_cmd` interface |

### Schedule flight-condition dependence

| Option | Assessment |
|---|---|
| **SLS-style fixed `(Tt4, Tt7)` vs. PLA (chosen, provisional)** | Pure function of `(PLA, DesignInputs, PlaSchedule)`, transparent, matches current flat-rated `mil_Tt4` sweeps, and bridges cleanly in PLA |
| Corrected $T_{t4}/\theta$ or $N_2/\sqrt{\theta}$ schedule | Deferred to `#25`/`#48` once BPR, spool speeds, and dry $A_8$ are calibrated |

### Deck schema for `PLA`

| Option | Assessment |
|---|---|
| **`PLA` column on PLA-driven decks only (`PLA_INPUT_COLUMNS`, chosen)** | Existing `--throttle` decks and `run.yml` stay 100% byte-identical; `compare_decks` ignores `PLA` as metadata |
| Add blank `PLA` column to all decks | Rejected: churns committed dry/wet CSVs without new physics |

## Spike Results

Two throwaway spikes were run on the default engine (Python 3.9.6, OpenMDAO 3.39.0, macOS arm64) to anchor the provisional defaults.

### Spike 001: Dry part-power envelope (`idle_Tt4`)

SLS (`MN = 0.001`, `alt = 0 ft`, `dTs = 0 R`) dry walk from `3100 R` to `2100 R`:

| `T4_cmd` (R) | Converged | `Fn` (lbf) | `W` (lbm/s) | `BPR` | `N1` (%) | `N2` (%) | `Tt6` (R) |
|---:|:---:|---:|---:|---:|---:|---:|---:|
| 3100 | Yes | 11,000.0 | 144.50 | 0.753 | 100.0 | 100.0 | 1502.4 |
| 2900 | Yes | 9,180.2 | 131.56 | 0.808 | 95.5 | 97.3 | 1389.6 |
| 2700 | Yes | 7,390.9 | 117.42 | 0.869 | 91.1 | 94.6 | 1281.5 |
| **2500** | **Yes** | **5,853.2** | **104.67** | **0.944** | **87.1** | **92.0** | **1175.9** |
| 2400 | Yes | 5,154.8 | 98.49 | 0.979 | 85.3 | 90.7 | 1126.9 |
| 2300 | No | — | — | — | — | — | — |

Off-SLS check (`MN ∈ {0.001, 0.4, 0.8, 0.95}`, `alt ∈ {0, 5000} ft`, `dTs = 0 R`): `2500 R` converges `4/8` (`max BPR = 0.967`), `2400 R` drops to `3/8` (`max BPR = 0.979`), and `2300 R` drops to `1/8`. **`idle_Tt4 = 2500.0 R`** matches the existing default dry grid floor and avoids immediate BPR-bound failure at SLS while making clear why `#25`/`#8` must calibrate BPR before physical idle $N_2$ is reachable.

### Spike 002: AB light-off (`min_ab_Tt7`) and envelope `Tt6` ceiling

Across dry MIL (`MN ∈ {0.001, 0.4, 0.8, 0.95}`, `alt ∈ {0, 5000} ft`, `dTs ∈ {0, ±50} R`, `18/24` converged), augmentor inlet temperature `Tt6` stays tightly bounded at **`1498.9–1504.7 R`**.

SLS wet walk (`MN = 0.001`, `alt = 0`, `dTs = 0`) and off-SLS hot/fast check (`16` points across `MN 0.001..0.95`, `alt 0..5000 ft`, `dTs 0, +50 R`):

| `T7_cmd` (R) | SLS `Fn` (lbf) | SLS `FAR_ab` | SLS `A8` (in²) | Off-SLS converged | Off-SLS `FAR_ab` range |
|---:|---:|---:|---:|:---:|---|
| 3607.68 | 17,700.0 | 0.03727 | 331.4 | 16/16 | — |
| 2400.0 | 14,120.1 | 0.01421 | 253.7 | 16/16 | 0.01411–0.01424 |
| 2200.0 | 13,478.0 | 0.01085 | 240.5 | 16/16 | 0.01077–0.01088 |
| 2000.0 | 12,805.3 | 0.00761 | 227.0 | 16/16 | 0.00753–0.00764 |
| **1900.0** | **12,459.4** | **0.00602** | **220.1** | **16/16** | **0.00596–0.00605** |
| 1800.0 | 12,107.2 | 0.00447 | 213.2 | — | — |

**`min_ab_Tt7 = 1900.0 R`** lands at `FAR_ab ≈ 0.0060` across all 16 tested corners (matching ADR-0002's NASA TN D-6839 zone-1 pilot floor of `~0.006`), sits ~400 R above `Tt6` everywhere, and gives a `+13.3%` SLS thrust step above dry MIL (`12,459` vs. `11,000 lbf`).

## Trade-off Analysis

- **What we gain:** A single validated, mode-spanning PLA axis across Python, CLI, and YAML, with zero risk to existing goldens, `f404 verify`, or `--throttle` decks, and a clean Pydantic schedule object ready for `#8`, `#25`, and `#48`.
- **What we defer:** True physical idle (`18.1°` ground idle at `65% N2`, `31°` flight idle at `~70–75% N2`), corrected-speed dry governing, and dry $A_8$ opening. Attempting those before `#25`/`#48` recalibrates BPR (`0.75` vs. `0.34`) would fight the `BPR = 1.0` bound on an uncalibrated cycle.

## Consequences

- Callers can sweep dry through wet in one pass (`sweep(eng, pla=...)` or `f404 sweep --pla 31,130,...`) without managing separate dry/wet runs.
- `PLA < 31°` (including `18.1°` ground idle) is intentionally rejected until `#25`/`#8` calibrate idle.
- Temperature-based `--throttle` and `--mode` remain intact and byte-identical for engineering trade studies and `#46`/`#48`.

### Recorded for later

- **Dry $A_8$ schedule ([#8](https://github.com/Jhawk414/F404/issues/8)):** Add dry nozzle opening parameters to `PlaSchedule` (or a sibling schedule model) and apply an explicit multiplier `f_open(PLA) >= 1.0` on `a8_sched.A8_dsn` with no new Newton state, keeping `87°` MIL as the minimum-$A_8$ anchor.
- **Idle and part-power calibration ([#25](https://github.com/Jhawk414/F404/issues/25), [#48](https://github.com/Jhawk414/F404/issues/48)):** Calibrate idle to observed $N_2$ / thrust (`18.1°` ground idle `65% N2` from MCAS Iwakuni; `31°` flight idle from Johnson/Ray) rather than a `Tt4` floor, and lower the `idle_pla` bound once ground idle converges. Because `PlaSchedule` lives outside the OpenMDAO model, `compute_totals` cannot differentiate directly with respect to `idle_Tt4` or `min_ab_Tt7`; `#48` will either use finite differences over schedule parameters or move the schedule into the model.
- **Flag naming:** Consider renaming `--throttle` to `--temp` in a follow-up issue so temperature-commanded and PLA-commanded sweeps are unmistakably distinct.

## Action Items

1. [x] Run Spike 001 (dry part-power envelope) and Spike 002 (AB light-off / `Tt6` ceiling)
2. [x] Record ADR-0006 (`docs/adr/0006-pla-definition.md`)
3. [x] Add `PlaSchedule`, `pla_axis`, and `SweepConfig`/`RunConfig` updates in `config.py`
4. [x] Attach `PlaSchedule` to `Engine` / `design()` and support PLA sweeps in `SweepRunner`, `sweep()`, and `run_point()`
5. [x] Wire `--pla` into `cli.py` and key `compare_decks.py` on `PLA` when present
6. [x] Add proportionate tests, verify with `f404 verify`, `pytest`, and a PLA proof sweep
7. [x] Update `README.md`, CLI/Python guides, `docs/architecture.md`, and `AGENTS/` handoff
