# ADR-0003: Fail fast on non-converging sweep points

**Status:** Accepted
**Date:** 2026-10-22
**Deciders:** @Jhawk414
**Issues:** [#40](https://github.com/Jhawk414/F404/issues/40). Also touches
[#3](https://github.com/Jhawk414/F404/issues/3) (the failures themselves) and
[#37](https://github.com/Jhawk414/F404/issues/37) (its deck regeneration is
the first big beneficiary).

## Context

The 6-Mach default sweep (PR #39) takes 2 h 5 min for 1,584 points (792
per mode), and most of that is spent on its 285 failures. A converged point
costs ~0.4 s. A failed one costs ~20 s, because `SweepRunner.run_sweep`
treats every failure the same way:

1. A **fast** attempt: OD Newton, `maxiter` 50 (`engine_model.py`), no line
   search.
2. On failure, restore the last good state and make a **safe** attempt:
   another 50 iterations, each with up to 5 Armijo backtracks.
3. Before a large jump in conditions, up to 5 **bridge** points, each a full
   Newton solve with `err_on_non_converge` off, keeping any partial progress
   unless the state ends at a bound.

The fix has to be deterministic. Decks are compared bit for bit
(`f404 compare`), so a wall-clock timeout, whose result would depend on the
machine and its load, is out. #40's acceptance: no point that converges
today may be lost, and converged values must agree to Newton tolerance.

### Measurement

An instrumented copy of the full default sweep (dry and wet, OpenMDAO
3.39.0) logged every Newton attempt: kind, wall time, iteration count,
residual history and outcome. The instrumentation reproduced the committed
decks bit for bit (642/792 dry, 657/792 wet; `f404 compare` shows no change).

Time spent in attempts, both modes (113 min total):

| Spent on | min | % |
|---|---|---|
| Converged points: bridges | 8.8 | 7.8 |
| Converged points: fast attempts | 10.7 | 9.5 |
| Failed points: bridges | 13.2 | 11.7 |
| Failed points: fast attempts | 18.6 | 16.5 |
| **Failed points: safe retries** | **61.7** | **54.6** |

Newton iterations of the attempts that converged:

| Attempt | n | Iterations |
|---|---|---|
| Fast | 1,298 | 1–5 (p50 3, p99 4, max 5) |
| Safe | 1 | 12 |
| Bridge | 1,039 | 0–15 |

Every attempt that did not converge in those ranges ran to the 50-iteration
limit (or failed earlier on NaN/inf or a bound). Nothing converged between
16 and 50 iterations.

Failures, by how the fast attempt failed and what the safe retry then did:

| Fast attempt | Safe retry | Points |
|---|---|---|
| hit `maxiter` | hit `maxiter` | 232 |
| hit `maxiter` | NaN/inf | 8 |
| hit `maxiter` | **converged** | **1** |
| NaN/inf | hit `maxiter` | 14 |
| NaN/inf | NaN/inf | 10 |
| bound | bound | 21 |

The safe retry rescued one point out of 286 (dry mil, 2500 ft, −10 R,
static), in 12 iterations. A failed safe retry averaged 14.5 s.

Bridges: 191 of 1,230 ran all 50 iterations (14.0 min). 128 of those ended at
a bound or on NaN and were rolled back anyway. The other 63 kept their partial
state, and every one of them was followed by a point that failed. No converged
point in the deck was preceded by a non-converged bridge whose state was
kept.

One property makes the measurement decisive: after a failed point,
`run_sweep` restores the last good state. How long a failed attempt runs
therefore cannot change any later row. A cheaper failure path changes the
deck only if it stops an attempt that would have converged.

## Decision

**Cap OD Newton at 20 iterations for every sweep solve (fast, safe and
bridge), and roll back a bridge that does not converge.**

- `SweepRunner` sets the OD Newton `maxiter` to `SWEEP_MAXITER = 20` when a
  sweep starts. The model's own default (50) is unchanged, so
  `build_problem()`'s solve from cold initial guesses keeps its headroom.
- Bridges keep `err_on_non_converge` on. A bridge that runs out of
  iterations raises like any point and is rolled back to the last good
  state. Previously it kept its partial progress.
- The fast → safe retry is kept. At 20 iterations it is cheap, and it still
  rescues the one point.

20 is 4× the slowest converged fast attempt, 1.7× the safe rescue and 1.3×
the slowest converged bridge (15). There is nothing between 15 and 50 in the
data to tune against, so the cap sits in that gap with margin on the bridge
side, where the data is closest to the limit.

### Expected effect

From the logs, scaling each over-limit attempt's time by 20/iterations: about
46.5 min saved on failed fast and safe attempts and 8.4 min on bridges, so
roughly 113 → 58 min of solver time. The default decks were expected to stay
bit-identical, but that is not guaranteed: a rolled-back bridge changes the
next point's warm start, which can change its solve path, and any point that
changes outcome changes the warm starts after it. The evidence is the
measured result (see [Result](#result)), not a general rule. Other grids, and
the same grid after a model change, need their own `f404 compare`.

## Options considered

The five options #40 lists, scored against the measurement.

### Option 1: OpenMDAO stall detection (`stall_limit` / `stall_tol`)

Stop when the relative residual norm changes by less than `stall_tol` for
`stall_limit` consecutive iterations. Replayed offline on the logged
residual histories:

| (limit, tol) | Converged attempts stopped | Of 488 maxiter failures, stopped | Mean iteration at stop |
|---|---|---|---|
| (3, 1e-1) | **12** | 479 | 8.3 |
| (3, 1e-2) | **2** | 461 | 9.8 |
| (5, 1e-2) | 0 | 459 | 12.8 |
| (5, 1e-3) | 0 | 399 | 15.1 |
| (10, 1e-2) | 0 | 443 | 18.9 |

| Dimension | Assessment |
|---|---|
| Complexity | Low: two solver options |
| Savings | About the same as the 20 cap at (5, 1e-2); less at tighter tolerances |
| Robustness | Two coupled knobs. Too loose stops converging attempts (12 at (3, 1e-1)). A slowly diverging attempt never stalls, so the cap is still needed |
| Determinism | Yes |

**Pros:** built in; stops a stalled attempt early whatever the cap.
**Cons:** the threshold is a residual-shape heuristic with no physical
meaning, it misses 6–20 % of the hopeless attempts, and it still needs a
`maxiter` behind it. It gains little over the plain cap.

### Option 2: divergence guard

Abort when the residual norm grows past a multiple of its initial value.
The data separates cleanly: converged attempts never exceed 32× their
initial norm, and failures reach 4×10⁸ (p99) to 3×10⁹.

| Dimension | Assessment |
|---|---|
| Complexity | Medium: a `NewtonSolver` subclass or hook in a vendored-library solver loop |
| Savings | Catches diverging attempts early (p50 of failures doesn't grow, so it misses the stalled half) |
| Robustness | A clean threshold today, but custom solver code to keep working across OpenMDAO versions (CI runs 3.45, local 3.39) |
| Determinism | Yes |

**Pros:** physically meaningful, a wide margin.
**Cons:** custom code inside the solver loop, and half the failures stall
rather than diverge, so it still needs a cap. Worth revisiting only if the
cap alone proves too slow.

### Option 3: lower `maxiter` (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | Lowest: one constant |
| Savings | ~55 min of 113 at 20 iterations |
| Robustness | The measured gap (nothing converges between 15 and 50) gives margin either side |
| Determinism | Yes, and the deck is predictably identical |

**Pros:** trivially explained, testable, deterministic; it keeps the
failure semantics (`AnalysisError`, then the `failure` column) unchanged.
**Cons:** a future model change (#8, #25, #37) could make some point need
more than 20 iterations. That point would then fail rather than converge
slowly. `f404 compare` lists it under "converged only in base", so the change
can't go unnoticed. The fix would be to raise the cap.

### Option 4: retry only failures that can recover

Skip the safe retry after NaN/inf or a bound. The data: retries after those
cost 2.2 min in total and rescued nothing, but the expensive retries (after
`maxiter`, 59.6 min) are exactly the ones that rescued the one point.

| Dimension | Assessment |
|---|---|
| Complexity | Low |
| Savings | ~2 min |
| Robustness | Fine, but it needs a residual-history check to tell NaN from `maxiter` in `AnalysisError` |

**Rejected:** too little gain for the extra branching once the cap makes
every retry cheap.

### Option 5: skip infeasible neighbours

Mark the next point as skipped when its neighbour fails. **Rejected:** it
records points as failed without trying them. The deck is #3's baseline, so
"failed" has to mean "tried and failed". It also wouldn't be needed after
Option 3.

### Bridges

Bridges are warm-start stepping stones; they are not deck rows. The choice
was whether they too get the cap and, if so, what happens to a bridge that
runs out of iterations:

- **Cap only, keep partial progress.** A bridge that hit a bound at 50
  iterations might stop short of it at 20 and keep a state it used to roll
  back. That would change warm starts for converged points unpredictably.
- **Cap and roll back (chosen).** Same as a bridge that ends at a bound today.
  Per the measurement, no converged point depended on a kept, non-converged
  bridge, so the converged rows are predicted unchanged.
- **No cap on bridges.** Keeps 8.4 min of waste.

## Trade-off analysis

The cap trades a small risk that a future, harder point needs 21+ iterations
for a halved sweep time and the simplest possible mechanism. Stall detection
and a divergence guard each save little beyond the cap and both still need
it, so they are left as fallbacks: **if a later model change pushes
converged attempts towards 20 iterations, consider stall detection and
raise the cap**, rather than raising the cap alone. (5, 1e-2) is only today's
candidate: its thresholds were fitted to this model's residual histories and
need fresh validation against the new ones.

## Result

The same instrumented full default sweep, before and after, dry and wet as
two parallel processes (OpenMDAO 3.39.0, one core each; times exclude
machine sleep):

| | Before | After |
|---|---|---|
| Dry wall time | 64.6 min | 33.0 min |
| Wet wall time | 48.6 min | 29.3 min |
| Solver time in attempts, both modes | 113.0 min | 62.3 min |
| Per failed point (bridges + fast + safe) | 19.7 s | 9.3 s |
| Converged | 642 dry, 657 wet | 642 dry, 657 wet |

`f404 compare` of both decks against the committed #39 decks: every value
identical, no point converged in only one deck. The expectation held with no
exception: the one safe rescue still converges (12 iterations), and no
failed point changed outcome.

A default `f404 sweep` (both modes, one after the other) therefore drops from
2 h 5 min to about 1 h.

Where the remaining time goes: converged points 18.3 min (unchanged), failed
points 44.0 min, of which safe retries are 27.7 min. Each failure still
costs two capped attempts plus its bridges.

## Consequences

### Code

- `sweep_utils.SWEEP_MAXITER = 20`, set on the OD Newton by
  `SweepRunner.run_sweep`.
- `_run_bridge` no longer turns off `err_on_non_converge`; a bridge that
  doesn't converge is rolled back like one that ends at a bound.
- The model default (`engine_model.py`, `maxiter` 50) is unchanged.

### To revisit

- After #8, #25 or #37: re-measure the iteration histogram (the spike is
  cheap: wrap `_run_point` and `_run_bridge` and log `_iter_count`). If
  converged attempts approach 20, validate stall thresholds on the new
  residual histories before raising the cap.
- The safe retry earns its keep with one point. If a future sweep shows it
  rescuing none, drop it.
