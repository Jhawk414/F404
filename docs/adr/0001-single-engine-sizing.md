# ADR-0001: Single-engine sizing for dry and wet modes

**Status:** Accepted
**Date:** 2026-10-10
**Deciders:** @Jhawk414
**Issue:** [#2](https://github.com/Jhawk414/F404/issues/2) (also touches [#3](https://github.com/Jhawk414/F404/issues/3), [#8](https://github.com/Jhawk414/F404/issues/8))

## Context

Dry and wet are two `om.Problem`s, each with its own DESIGN solve: 11,000 lbf
dry mil and 17,700 lbf max AB at Tt7 = 3800 R. The two DESIGNs agree on every
dimensionless quantity but differ by 5.17% in mass flow, so they describe one
cycle at two sizes. Two less obvious forces shape the decision.

1. **The thrust targets and the cycle don't agree.** For a fixed cycle, the
   ratio of max-AB to dry-mil thrust is a property of the cycle. The model
   gives 1.692. The targets imply 17,700 / 11,000 = 1.609. No single sizing
   meets both thrusts at Tt7 = 3800 R, so the 5.17% can only be closed by
   changing the cycle, not by choosing a different sizing point.
2. **A frozen nozzle throat couples the modes.** Every OD point holds the
   throat (A8) at the DESIGN area (`mp_cycle.py`, `balance.rhs:W`). A
   wet-sized throat is 1.70× the dry throat at equal mass flow. Options 1 and
   2 in `single_engine_mode.md` would run dry points through that wet throat.
   Continuation shows dry mil leaves the model's envelope at A8 ≈ 217 in²,
   a third of the way from the dry throat (178.5) to the wet throat (303.9):
   BPR hits its 1.0 bound and fan Rline passes 2.9. **As written, Options 1
   and 2 have no dry solution.** Both need a per-mode A8. #8's scheduled A8
   is therefore a prerequisite for #2, not a separate feature.

## Decision

Adopt **A3b**:

- **One `MPCycle`, one DESIGN point**, sized at dry mil (11,000 lbf,
  Tt4 = 3100 R).
- **Two OD points**:
  - `OD_dry`, with the afterburner as a `Duct`. It is today's dry OD,
    unchanged.
  - `OD_wet`, with the afterburner as a `Combustor`.
- **In `OD_wet`, A8 is a free state** that holds the fan operating line
  (`RlineMap`) at its design value. This is the standard augmentor nozzle
  control law: lighting the afterburner should be invisible to the gas
  generator.
- **The sweep drives one OD point and freezes the other.**
- **Calibration** of the max-AB thrust to 17,700 lbf is a separate
  parameter choice. See [Calibration](#calibration).

## Options considered

All sweeps use the study grid: alt {0, 2500, 5000} ft × dTs {0, +20, −20} R
× 4 throttle levels, giving 36 points per mode, all at MN 0.001. Decks are
joined to the status quo (A0) on (alt, dTs, throttle rank). Values are %
difference vs A0. A single number means the difference is uniform; a range
gives min…max.

| | Architecture | Sizes | Dry AB | Wet A8 |
|---|---|---|---|---|
| A0 | Status quo: two Problems | dry 11k and wet 17.7k, separately | Duct | frozen at wet DESIGN |
| A1 | Option 1, snapshot and inject (wet DESIGN feeds a dry OD point); repaired with dry A8 = wet A8 / 1.7024 | wet 17.7k | Duct | frozen |
| A2 | Option 2, always-AB: Combustor everywhere, dry T7 target = mixer exit T via a runtime selector, FAR_ab lower bound 0; repaired with a runtime A8 multiplier | wet 17.7k | Combustor, FAR_ab → 0 | frozen, switched per mode |
| A3a | One DESIGN (dry), `OD_dry` + `OD_wet`; wet A8 = DESIGN A8 × 1.7024 | dry 11k | Duct | fixed ratio |
| **A3b** | A3 with wet A8 as a state holding fan Rline = 2.0 | dry 11k | Duct | control law |
| A3b+cal | A3b with Tt7_max = 3607.8 R and AB dPqP = 0.054 | dry 11k | Duct | control law |

### Convergence and cost (study grid)

| | A0 | A1 | A2 | A3a | A3b | A3b+cal |
|---|---|---|---|---|---|---|
| Dry converged / 36 | 35 | 35 | 35 | 35 | 35 | 35 |
| Wet converged / 36 | 30 | 30 | 30 | 30 | **35** | **36** |
| Wall time, both modes (s)¹ | 303 | 291 | 272 | 288 | 180 | 162 |
| DESIGN solves per run | 2 | 1 | 1 | 1 | 1 | 1 |
| Dry deck byte-identical to A0 | — | no | no | **yes** | **yes** | **yes** |

¹ Sweeps ran 2–4 at a time on one laptop, so wall times are indicative
only. A3b's lower time comes from fewer failed points (each failure costs a
retry). It is not caused by the architecture itself.

### % difference vs A0: dry deck

| metric | A1 | A2 | A3a | A3b | A3b+cal |
|---|---|---|---|---|---|
| W, Fn, Fg, Wf_core, A8 | −4.92 | −4.92 | 0 | 0 | 0 |
| TSFC, BPR, FAR_core, PRs, T4, T7, spool speeds | 0 | 0 | 0 | 0 | 0 |
| FAR_ab, Wf_ab | 0 | ≤1e-18 | 0 | 0 | 0 |

### % difference vs A0: wet deck (30 matched points)

| metric | A1 / A2 | A3a | A3b | A3b+cal |
|---|---|---|---|---|
| W (air) | 0 | +5.17 | +2.02…+5.85 | +2.02…+5.85 |
| Fn | 0 | +5.17 | +4.22…+6.32 | **−1.35…+0.89** |
| Fg | 0 | +5.17 | +4.22…+6.32 | −1.35…+0.89 |
| TSFC | 0 | 0 | −3.04…+0.23 | −6.80…−2.76 |
| Wf_core (fuel) | 0 | +5.17…+5.18 | +4.98…+10.83 | +4.98…+10.83 |
| Wf_ab (fuel) | 0 | +5.17 | −0.39…+6.13 | −13.15…−4.73 |
| A8 | 0 | +5.17 | −6.59…+6.54 | −4.85…+8.97 |
| BPR | 0 | 0 | −15.82…+1.97 | −15.82…+1.97 |
| FAR_core | 0 | 0 | −0.36…+0.02 | −0.36…+0.02 |
| FAR_ab | 0 | 0 | −3.17…+0.26 | −15.67…−10.00 |
| OPR | 0 | 0 | −0.21…+5.72 | −0.21…+5.72 |
| fan PR | 0 | 0 | −0.26…+6.57 | −0.26…+6.57 |
| HPC PR | 0 | 0 | −0.80…+0.05 | −0.80…+0.05 |
| HPT PR | 0 | 0 | −0.02…+0.29 | −0.02…+0.29 |
| LPT PR | 0 | 0 | −5.92…+0.62 | −5.92…+0.62 |
| T4 | 0 | 0 | 0 | 0 |
| T7 | 0 | 0 | 0 | −6.01…−5.06 (by design) |
| LP / HP spool speed | 0 | 0 | −3.32…+0.24 / −0.02…+0.22 | same |

How to read the wet table:

- **A3a is a pure 5.17% rescale.** All extensive quantities move by 5.17%;
  nothing dimensionless moves.
- **A3b's spread comes from A8 no longer being frozen.** At part AB, A0's
  fixed throat lets the fan unload: fan PR drops 4.10 → 3.90 and BPR rises
  0.75 → 0.88 at SLS, Tt7 = 3200 R. A3b holds fan PR at 4.10 and closes A8
  from 320 to 288 in² instead.
- **The −15.8% BPR outliers are all minimum-AB points.** They measure A0's
  frozen-A8 artifact rather than an error in A3b.

### Continuity from dry mil to minimum AB

This is the step in the gas-generator state when the afterburner lights, on
the same (alt, dTs), from dry Tt4 = 3100 R to wet Tt7 = 3200 R:

| | W | BPR | fan PR | LP spool |
|---|---|---|---|---|
| A0 | −3.3…−1.4% | **+15…+17%** | −5.6…−3.1% | +1.4…+3.1% |
| A3b | −0.4…+0.6% | −3.9…+1.7% | −0.2…+1.5% | −0.8…+0.2% |

In A0, two different engines with a frozen throat produce a large, unphysical
jump. A3b is close to the "transparent light-off" that a real A8 schedule
aims for. The residual step off SLS exists because Rline is held at 2.0
rather than at the dry-mil Rline for that flight condition. That refinement
belongs with #8.

## Calibration

Can the 5.17% be minimised? Yes: one knob closes it exactly. The table shows
the SLS max-AB point on the dry-sized engine (W = 144.18 lbm/s) for each
knob:

| Knob | Tt7_max (R) | AB dPqP | A8/A8_dry | Fn (lbf) | TSFC | Physically |
|---|---|---|---|---|---|---|
| none | 3800 | 0 | 1.702 | 18,615 | 1.5245 | 5.17% over the target |
| Tt7 only | 3501.7 | 0 | 1.617 | 17,700 | 1.4123 | plausible, but a lossless AB is optimistic |
| **Tt7 + AB loss** | **3607.8** | **0.054** | 1.741 | 17,700 | 1.4786 | **recommended**: upstream pyCycle's AB loss, credible max-AB T7 |
| AB loss only | 3800 | 0.138 | 1.975 | 17,700 | 1.6042 | implausible (13.8% loss) |

The calibrated deck keeps wet Fn within −1.35…+0.89% of today's deck over the
grid. It does so with 2–6% more air and 3–7% lower TSFC, because the same
thrust comes from a larger, cooler-burning engine.

**TSFC is not a target in this study.** Dry-mil TSFC of 0.62 is already low
compared with published F404 figures. Fitting TSFC is validation work and
out of scope for #2.

**Not done here:** a dry-mode afterburner cold loss. It would change the dry
deck and the DESIGN sizing, and it belongs with validation.

## Trade-off analysis

**A1 vs A3a.** Once repaired, A1 and A3a are the same model sized at opposite
corners. A1 keeps today's wet deck and shrinks dry by 4.92%. A3a keeps today's
dry deck and grows wet by 5.17%. A1 also costs more:

- `mp_cycle` needs either an OD-only mode or a DESIGN copy carrying wet
  inputs.
- The snapshot list exists twice.

**A2 works on the study grid.** With a selector component and a FAR_ab lower
bound of exactly 0, there were no rank-deficiency errors. Dry FAR_ab
converged to ≤1e-18 and matched A1 exactly. The ill-conditioning reported in
the #2 comment was not reproduced here. A variant that pins FAR near the
reported 1e-5 also ran cleanly: a 2 R "pilot" above the mixer temperature gave
FAR_ab ≈ 2.8e-5 and 35/36 converged. That pilot fuel adds a spurious
+0.16…+0.28% to dry TSFC, so the exact-zero form is the better of the two. The
earlier problem may have come from FAR being fixed as an input, with no balance
state, which is the case the `engine_model.py` comment describes. On the full default dry envelope (132 points),
A2 converged 117/132 against A0's 118/132:

- No rank-deficiency errors.
- The 5 NaN failures sit at the same cold, 5000 ft corners where A0 fails
  (A0 has 3).
- So the near-zero-FAR Jacobian is not a blocker for Option 2.

A2 also carries costs the others don't:

- A Combustor state that is meaningless in dry mode.
- A selector input that changes what `rhs` means.
- An A8 multiplier that must be switched in step with it.
- A per-mode bounds check (FAR_ab legitimately sits at 0 on every dry point).

**A3 vs A1/A2.**

- A3 keeps the dry deck byte-identical, so its blast radius on dry is zero.
- A3's wet topology is isolated: per-mode elements, controls and fidelity
  never leak into the dry point.
- The cost is a third point evaluated on every `run_model`. Freezing the
  inactive point makes that a single residual evaluation, and wall time
  doesn't measurably change.

**A3b vs A3a.** A3b is physically better (A8 is a control, not a frozen
area), converges more (+5 wet points; it gained 6 and lost 1, at
2500 ft / −20 R / 3600 R), and is faster. Its cost is real wet-deck movement
at part AB versus today.

## Consequences

### CLI and data structures
- One `build_problem()` replaces `build_dry_problem` / `build_wet_problem`.
  `MPMixedFlowTurbofan` exposes `od_pts = {'dry': 'OD_dry', 'wet': 'OD_wet'}`
  instead of `od_pt`, and its `afterburn` option goes away.
- `f404 sweep --mode both` builds once and runs both sweeps on the same
  problem.
- `f404 design` no longer needs `--mode`: there is one DESIGN.
  - `--fn-target` is the single sizing thrust (dry mil).
  - `--dsn-tt7` is replaced by `--max-tt7`, the max-AB Tt7 of `OD_wet`.
  - The "fn-target can't be used with both" rule goes away.
- The default wet throttle grid follows Tt7_max: 3608 → 3008 R in 200 R
  steps. The calibration is rounded to 3608 R (17,700.6 lbf).
- Deck CSVs gain `Wf_core`, `Wf_ab` (lbm/s) and `A8` (in²). A8 is now a
  per-point output, not a constant per mode.
- `_OD_BOUNDS` gains the A8 state.

### Blast radius on the decks
- **Dry:** none. Byte-identical.
- **Wet:** thrust within ±1.4% once calibrated. W +2…+6%. TSFC, fuel flows,
  BPR, fan PR and LPT PR shift at part AB, as tabulated above. The committed
  `deck/cycle_deck_wet.csv` is regenerated.
- **Golden test baselines:** dry unchanged. The wet DESIGN golden values are
  replaced by OD_wet values.

### Growth paths

| Future feature | How A3b accommodates it |
|---|---|
| Dry throttle-up, overspeed, startup | Dry point unchanged. Transients need shaft inertia (`dN/dt = ΔP / (I·N)`) replacing the shaft-power balances. That is a per-point change, and per-point topology is exactly what A3 enables. |
| AB light-off / blow-out | Modelled as a discrete switch `OD_dry` → `OD_wet` with state hand-off, which matches real AB ignition (a minimum stable FAR, not a continuous ramp from 0). The control-law A8 already makes the step nearly transparent. A continuous FAR ramp from 0 would need A2's always-live combustor; the study shows that path is numerically viable if ever needed. |
| Compressor stall / surge | Fan and HPC maps already carry stall-margin outputs. A3b fixes the fan operating line in AB, so fan surge margin there is a direct output, and A8 becomes the lever for margin studies. |
| Cantera AB combustion | Replace the `Combustor` in `OD_wet` only. The dry point and DESIGN never see it, so the Cantera dependency stays opt-in and wet-only. |
| Method-of-characteristics CD nozzle | A8 is now a per-point state and the nozzle inlet station is in the deck, so a MoC tool can post-process `mixed_nozz` inlet conditions and throat area for each point, or later replace the `Nozzle` element per mode. |
| #8 scheduled A8 | Swap the A8 control residual (Rline = 2.0) for a PLA/T7 schedule or a per-condition dry-Rline target. The structure is unchanged. |
| #3 convergence | A3b recovers 5 of 6 failed wet points on the study grid. On the full default envelope (with calibration), wet goes from 89/132 to 100/132 and keeps every point the old deck converged. That is strong evidence for the frozen-A8 hypothesis in #3. |

### Needs revisiting
- The Rline target (2.0 everywhere vs dry-mil Rline per condition) is a #8
  decision.
- The calibration knob is a modelling decision. Validating TSFC against
  published F404 data is separate work.
- `_validate_design_targets` and the CLI's wet-throttle check
  (`Tt7 > MIL_Tt4`) assume the old semantics. The physical lower limit for
  Tt7 is the mixer exit temperature (~1500 R), not Tt4.

## Action items
1. [x] Implement A3b in `engine_model.py`, `mp_cycle.py`, `problems.py`,
   `sweep_utils.py`, `sweep_full_envelope.py` and `cli.py`.
2. [x] Decide on calibration: adopted Tt7_max 3608 R + AB dPqP 0.054,
   applied to `OD_wet` only.
3. [x] Turn the strict xfail into a pass and re-baseline the wet goldens.
4. [x] Regenerate `deck/cycle_deck_wet.csv` and add `deck/cycle_deck_dry.csv`.
5. [ ] Follow-ups: #8 (A8 schedule / Rline target), #3 (re-measure full-envelope wet convergence).
