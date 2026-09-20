# Handoff: F404-pyCycle — Recommended Issue Order

Supersedes `HANDOFF_14Sep26.md` (renamed to this file). The prior handoff's
content is preserved below unchanged, under "Prior handoff (14 Sep 26)".

## Session summary (19 Sep 26) — #5 test suite (PR #15)

Implemented Phase 1 item #2 below. [#5](https://github.com/Jhawk414/F404/issues/5)
is done via [PR #15](https://github.com/Jhawk414/F404/pull/15) (branch
`test/module-test-suite`). **98 tests, ~25 s, 86% coverage.**

### Restructuring the suite required first

Three things made a test suite impossible to write, all fixed in the PR:

1. **The package wasn't importable.** Modules imported each other by bare
   name (`from mp_cycle import ...`), which only resolves when the
   interpreter's cwd is `src/F404_pycycle/` — i.e. only when a file in it
   runs as a script. Now absolute imports, with `F404_pycycle` registered in
   `setup.py` (`package_dir` mapping, sharing the vendored distribution
   rather than carrying a second `setup.py`). **Entry points are now invoked
   as `python -m F404_pycycle.sweep_full_envelope`.**
2. **`test_modes.py` would have detonated on collection** — 181 lines, zero
   assertions, a 4-point solve at import time, and named such that pytest
   collects it. Deleted, along with `run_design_od.py`, whose docstring
   pinned it to the `MFTF_od_CRZ.py` monolith deleted back in `b96c02e`.
3. **Problem setup existed in three near-identical copies.** Consolidated
   into `problems.py` as `build_dry_problem()` / `build_wet_problem()`, which
   also buys `verbose=False`, parameterised targets, and a home for
   fail-fast validation. Also dropped a redundant second `run_model()` per
   builder — the "verify OD at design conditions" block re-set values that
   were already set and re-solved an already-converged point purely to print
   it.

### Two findings

- **#2's divergence is 5.17%, not the 1–2% the issue estimates.** Dry and
  wet agree *exactly* on everything dimensionless — same PRs, same Tt4, same
  BPR 0.7528 — but land on different DESIGN mass flows (144.1825 vs 137.0927
  lbm/s). The handoff below lists measuring this as #2's first step; it is
  now a labelled characterisation test that should fail and be deleted when
  a single sizing serves both modes.
- **A latent NumPy 2 break in `sweep_utils.py`.** `float()` on OpenMDAO's
  length-1 arrays, ~18 times per sweep point, deprecated since NumPy 1.25
  and slated to raise. The nasty part: in `_state_at_bounds` and
  `_target_met` the surrounding `except Exception` would swallow the eventual
  `TypeError` and silently report *every* point as unconverged. Fixed via a
  `_scalar()` helper; pytest now promotes that deprecation to an error. Note
  the CI's existing `ruff --select NPY201` gate does **not** catch this
  pattern.

### Golden baseline (captured at 1e-4 relative tolerance)

| | Fn (lbf) | W (lbm/s) | BPR | TSFC |
|---|---|---|---|---|
| dry DESIGN | 11,000 | 144.1825 | 0.7528 | 0.6201 |
| wet DESIGN | 17,700 | 137.0927 | 0.7528 | 1.5245 |

Wet also: FAR_ab 0.0415, T7 3800 R. Both OD points reproduce their DESIGN
solve exactly at design conditions.

### Decisions worth knowing

- **Tests live in top-level `tests/`, not as `src/` siblings.** #5 and
  `IMPROVEMENTS.md` item 2 specified siblings; the naming convention is kept
  but the location isn't, so `src/` stays model code only.
- **No pydantic in this branch.** `IMPROVEMENTS.md` item 3 already scoped it
  as its own branch. Filed as
  [#17](https://github.com/Jhawk414/F404/issues/17); PR #15's three
  hand-written checks in `problems._validate_design_targets()` are a stopgap
  that #17 should absorb and delete.
- **Connection assertions match on prefix+suffix, not exact path.** OpenMDAO
  resolves `pyc_connect_des_od` down to pyCycle-internal subcomponents
  (`DESIGN.fan.map.scalars.s_PR`); pinning to those would break on an
  upstream refactor that changed nothing here.
- **`printer.py` gained a `file` parameter.** pyCycle's `print_*` helpers
  bind `sys.stdout` as a *default argument*, evaluated at import, so their
  output escapes both `capsys` and `capfd`. Untestable without threading
  `file` through.

### Coverage, and where the ceiling is

| Module | | |
|---|---|---|
| `mp_cycle.py` | 100% | |
| `printer.py` | 100% | |
| `engine_model.py` | 98% | dead `USE_TABULAR=False` branch |
| `problems.py` | 93% | verbose print path |
| `sweep_utils.py` | 83% | |
| `sweep_full_envelope.py` | 37% | **all of it inside `if __name__ == "__main__"`** |

That last row caps the total. An uncallable `__main__` block can't be
tested — extracting it behind a real entry point is
[#16](https://github.com/Jhawk414/F404/issues/16).

### Three more bugs, surfaced by CI

The new workflow was the first thing to install this repo from scratch
*and* import the application code, and the first to run it on a platform
other than the author's. All three are pre-existing; none were test bugs.

1. **`pandas` was never a declared dependency.** `install_requires` has
   only ever listed `openmdao`, while `sweep_utils.py` has always imported
   pandas directly. A clean `pip install -e .[all]` has therefore never
   produced a working sweep — it only ever worked because pandas happened to
   be in the environment already. `numpy` is now declared too (it resolved
   transitively through openmdao).
2. **One bad point could abort an entire sweep.** `_run_point` caught only
   `om.AnalysisError`. A sufficiently degenerate point doesn't fail in Newton
   at all — it fails underneath it, where `DirectSolver` raises
   `RuntimeError: Jacobian in 'OD' is not full rank`, which propagated
   straight out of `run_sweep`. Platform-dependent: locally the same point
   fails cleanly through Newton, so this only appeared on CI.
3. **A failure before the first success poisoned everything after it.** With
   (2) fixed the sweep survived but every later point failed —
   `_last_good_state` is only populated after a point *converges*, so an
   early failure had nothing to restore from and subsequent points
   warm-started from the state Newton abandoned. `run_sweep` now seeds the
   fallback from the state it is handed (OD converged at design conditions).

**(3) is latent, not theoretical.** It stays hidden only because the first
point of both the dry and wet grids happens to converge. Reorder the grid,
or widen the envelope via #16/#13, and it presents as a near-empty deck with
no obvious cause — it looks like "the model broke", not "point 1 failed".
Worth remembering when #3/#8 start changing which corners converge.

Neither (2) nor (3) was reachable before a test deliberately failed a point.

Also note: the `filterwarnings` rule promoting NumPy's scalar-conversion
deprecation to an error must stay **scoped to `F404_pycycle.*`**. Unscoped,
it applies to the whole pytest session and turns the vendored library's own
deprecations into hard failures the moment anyone runs
`pytest pycycle/...`. `testpaths` doesn't protect against this — an explicit
path argument overrides it.

### The vendored test_bleed_out failure — fixed by cherry-pick

`pycycle/elements/test/test_bleed_out.py` failed on all three Baseline
jobs with an ambiguous-promoted-units `ValueError` under OpenMDAO 3.45.1
(what CI installs; the workflow pins `OPENMDAO: 'latest'`). It does **not**
reproduce on 3.39.0, which is what a local checkout is likely to have —
`BleedOut` promotes four inputs to `bleed.Fl_I:tot:T` with mismatched units
and newer OpenMDAO refuses to guess.

Upstream had already fixed it in `OpenMDAO/pyCycle@da3b5e3` ("fix tests to
pass with more recent OM"), so the resolution was a cherry-pick of that one
test file, taken whole so the vendored copy matches upstream byte for byte.
Test-only; no vendored production code moved. Filed and closed as
[#18](https://github.com/Jhawk414/F404/issues/18).

**Worth noting for a future vendor sync:** that workflow had never run
before — it triggers on `main` pushes and PRs targeting `main`, and PR #15
is the first PR since the default-branch rename and the trigger fix in
`3caa85b`. So this had been broken unobserved, and finding that upstream
already had the fix is direct evidence the vendored tree is behind in ways
nobody is currently watching. #6 was closed on the strength of one spot
check (the NumPy 2 `.item()` fix being present); this suggests a real
file-by-file diff against upstream is still worth doing.

### New issues filed

- [#16](https://github.com/Jhawk414/F404/issues/16) — proper CLI entry point
  (`design` / `sweep` / `init-config`), absorbing #13's `min,max,step`
  alt/Mach/throttle flags. Either land #13 inside it or land #13 first
  against the current argparse block.
- [#17](https://github.com/Jhawk414/F404/issues/17) — pydantic refactor.
  Biggest prize is `_OD_BOUNDS`: a hand-maintained duplicate of
  `engine_model.py`'s declared bounds. PR #15 added a test holding the two
  together, but a structure that can't drift beats a test that detects drift.

**Next per the order below:** #5 is done, so #6 (vendor sync, re-scope
first) is next in Phase 1 — then the #2 measurement is already in hand
above, leaving the #3 + #8 solver cluster, now with a regression net.

## Session summary (19 Sep 26) — #12 CSV precision (PR #14)

Implemented Phase 1 item #1 below. [#12](https://github.com/Jhawk414/F404/issues/12)
is done via [PR #14](https://github.com/Jhawk414/F404/pull/14) (branch
`fix/csv-deck-precision`).

- Consolidated the three `to_csv()` call sites (dry/wet/combined) in
  `src/F404_pycycle/sweep_full_envelope.py` behind one `write_deck_csv()`
  helper, then serialized each numeric column at a precision matched to how
  it's read:
  - **scientific `%.4e`** for the fuel-air ratios (`FAR_core`, `FAR_ab`,
    `DECK_SCI_COLS`) — they sit around 0.03–0.04, so fixed decimals waste
    their shown digits on leading zeros and flatten the small dTs-driven
    fueling change; scientific keeps every shown digit significant;
  - **4 decimals** for `MN`, `TSFC`, `W`, `BPR`, the pressure ratios and the
    LP/HP spool speeds (`DECK_HI_PRECISION_COLS`) — the continuous quantities
    a downstream optimizer would ingest;
  - **2 decimals** for thrust, temperatures and flight conditions.
  - (pandas' `float_format` is global, hence the per-column loop in the helper.)
- Regenerated `deck/cycle_deck_wet.csv` from the full-precision original on
  `main` — converged values unchanged (89/132 wet rows), only formatting
  differs. NB: don't reformat an already-reduced deck to *raise* precision;
  the discarded digits are gone. Pull the full-precision source instead.

Physics note surfaced while picking the FAR format (not addressed by #12, may
be worth its own look): across power levels `FAR_ab` moves as expected
(0.0415→0.0374→0.0334→0.0297 as commanded T7 drops), but at a *fixed* T7 the
dTs sweep barely perturbs `FAR_ab` (5th–6th decimal only). Real result, now
readable in the deck.

**Next per the order below:** #12 gated #5's golden baseline, so #5 (test
suite) is now unblocked and is the recommended next pickup.

## Session summary (19 Sep 26)

No code changed this session — this was a read-only investigation to advise on
which open issues to tackle first, given that several have logical
dependencies. Two findings materially reshaped the ordering:

1. **#6 (vendor sync) looks partly stale.** The issue's concrete example — the
   missing NumPy 2.x `.item()` fix in
   `pycycle/thermo/tabular/thermo_add.py` — is *already present* at
   `thermo_add.py:120-121`. So #6 needs a quick re-scope ("is anything
   actually out of sync with upstream today?") before it becomes real work,
   rather than a blind rebase against upstream.
2. **#8 is a lever on #3, not just a feature.** The comment on
   [#8](https://github.com/Jhawk414/F404/issues/8) already shows the frozen
   design-point A8 wiring (`pyc_connect_des_od('mixed_nozz.Throat:stat:area',
   'balance.rhs:W')`, `mp_cycle.py:94`) is what makes
   `mixed_nozz.staticMN.ps_resid` thrash at the wet corners — the exact
   failures [#3](https://github.com/Jhawk414/F404/issues/3) is about. #3 and #8
   are physically the same problem viewed from two angles: solver-tuning vs.
   fixing the underlying frozen-A8 physics.

Also confirmed: no F404-specific test suite exists yet (only `test_modes.py`,
a smoke test with no assertions), which is why #5 is treated as a foundational
enabler below rather than just another feature.

## Open issues at a glance

| # | Title | Label | Size |
|---|---|---|---|
| [#2](https://github.com/Jhawk414/F404/issues/2)  | Dry/wet size two different engines (~1–2%) | enhancement/question | investigate first |
| [#3](https://github.com/Jhawk414/F404/issues/3)  | OD non-convergence at cold/high-alt/max-AB | bug | large |
| [#5](https://github.com/Jhawk414/F404/issues/5)  | Per-module test suite convention | — | ✅ done (PR #15) |
| [#6](https://github.com/Jhawk414/F404/issues/6)  | Sync vendored `pycycle/` with upstream | housekeeping | small (re-scope) |
| [#8](https://github.com/Jhawk414/F404/issues/8)  | PLA/T7-scheduled nozzle A8 area | enhancement | large |
| [#10](https://github.com/Jhawk414/F404/issues/10) | Inline creep/LCF life estimation | enhancement | large/exploratory |
| [#12](https://github.com/Jhawk414/F404/issues/12) | CSV writes full float64 precision | good first issue | ✅ done (PR #14) |
| [#13](https://github.com/Jhawk414/F404/issues/13) | CLI-configurable sweep ranges | enhancement | medium |
| [#16](https://github.com/Jhawk414/F404/issues/16) | Proper CLI entry point (absorbs #13) | enhancement | medium |
| [#17](https://github.com/Jhawk414/F404/issues/17) | Pydantic models for validated inputs | enhancement | medium |

## Recommended order

Dependency chain, condensed:

**#12 ✅ → #5 ✅ (baseline) → #6 → [#2 measure ✅] → #3 + #8 → #17 → #16/#13 → #10**

### Phase 1 — Foundation (before any solver work)

1. **[#12](https://github.com/Jhawk414/F404/issues/12) — CSV precision.**
   ✅ **Done — [PR #14](https://github.com/Jhawk414/F404/pull/14)** (see the
   19 Sep 26 session summary above). Landed *first* because it had to precede
   #5's golden CSV baseline — otherwise a later formatting change would
   invalidate the baseline. Grew slightly past the filed "isolated
   `float_format` change" into per-column precision (scientific FAR), but stayed
   contained to the deck writer.
2. **[#5](https://github.com/Jhawk414/F404/issues/5) — test suite.**
   ✅ **Done — [PR #15](https://github.com/Jhawk414/F404/pull/15)** (see the
   session summary above). The real enabler. Every hard item below (#2, #3, #8) is Newton-solver surgery, and
   the prior handoff notes a regression test would have caught the false
   "converged" bug immediately. Capture a golden dry/wet baseline now
   (125/132 dry, 89/132 wet) while behavior is known-good, so the solver work
   has a safety net.
3. **[#6](https://github.com/Jhawk414/F404/issues/6) — vendor sync.** Cheap,
   and worth a known-clean environment before debugging convergence (so a
   solver "ghost" isn't actually a stale-vendor bug). **Re-scope first** given
   the `.item()` finding above — confirm what, if anything, is actually behind
   upstream before doing the work.

### Phase 2 — Coupled solver cluster (the heart of the work)

4. **[#2](https://github.com/Jhawk414/F404/issues/2) — quantify the variance.**
   The issue itself says to start by measuring the dry-vs-wet DESIGN delta.
   Cheap investigation; if the delta is negligible, #2 stays deferred and
   everything downstream simplifies. Do this as measurement, not a fix.
5. **[#3](https://github.com/Jhawk414/F404/issues/3) +
   [#8](https://github.com/Jhawk414/F404/issues/8) together.** Treat as one
   effort. #8's T7-scheduled A8 is likely the principled fix for a chunk of
   #3's wet-corner failures; the cheaper #3 knobs (relax `RlineMap`, widen
   `_OD_BOUNDS`, denser bridge points, per-corner solver tuning) cover the
   rest. Solving #3 by tuning alone, without #8, risks fighting the frozen-A8
   physics.

### Phase 3 — Additive features (any time after Phase 1's test net)

6. **[#13](https://github.com/Jhawk414/F404/issues/13) — CLI sweep ranges.**
   Independent, but sequence it *after* #3 is healthier: opening the altitude
   band and enabling a real Mach sweep will surface more non-convergence. Also
   do it after #12, since both touch the CSV/CLI path in
   `sweep_full_envelope.py`.
7. **[#10](https://github.com/Jhawk414/F404/issues/10) — creep/LCF lifing.**
   Purely additive to the per-point results dict, depends on nothing, but it's
   large and exploratory. Last, and incrementally.

### Non-obvious calls, restated

- #12 gates #5's baseline (formatting must be final before the golden file).
- #5 gates all the solver work (#2/#3/#8) — it's the regression net.
- #8 is the physics fix hiding inside the #3 bug, not a separable feature.
- #6 is smaller than filed — verify before touching it.

---

# Prior handoff (14 Sep 26)

# Handoff: F404-pyCycle — Off-Design Sweep Convergence

Supersedes `HANDOFF_22Apr26.md` (stale — written before the dry/wet mode
question was resolved). That file has been deleted.

## Branch: `feature/alt-mach-sweep` — status: merged & deleted

Merged to `main` via [PR #1](https://github.com/Jhawk414/F404/pull/1)
(merge commit `576a7b9`). Both the local and remote copies of the branch
have since been deleted — the commits below live on permanently through
`main`'s history. What shipped, oldest to newest:

1. **`026467f`** — Refactored the monolithic `MFTF_od_CRZ.py` into a modular
   architecture: `engine_model.py` (single-point cycle), `mp_cycle.py`
   (DESIGN+OD multi-point), `sweep_utils.py` (sweep infrastructure),
   `sweep_full_envelope.py` (driver script).
2. **`0950011` → `bb952b7` → `dd3badc`** — Fixed cycle balance convergence
   (BPR/ER targets, initial conditions), widened DESIGN BPR bounds, anchored
   the wet DESIGN point at Tt7=3800 R (max AB — the correct F404 sizing
   corner instead of an arbitrary mid-AB point).
3. **`51c9bb6`** — Fixed a family of convergence-detection bugs that
   were producing cycle-deck CSVs full of garbage "converged" rows
   (Fn > 100,000 lbf, BPR clipped to 1.0, LP_Nmech at its 500 rpm floor):
   - Dry-mode afterburner is now a `pyc.Duct`, not a zero-FAR `Combustor`
     (the latter produces a rank-deficient Jacobian at part power).
   - Convergence check replaced: `_iter_count < maxiter` (which silently
     accepted bound-clipped/false-positive solutions) → `err_on_non_converge
     =True` + explicit bound-saturation check + burner/AB exit-temperature
     target-met check.
   - State snapshot/restore now captures the **entire OD output vector**
     (`_outputs.asarray()`), not ~12 named primary balance variables. The
     partial-key approach left nested implicit states (e.g.
     `staticMN.ps_resid`'s internal `Ps`) uncaptured, so a restore after one
     bad cold-corner point left the model in an inconsistent state that
     degraded to non-physical gamma within a few iterations and cascaded
     through every point after it. Full-vector restore fixed the cascade.
   - Hybrid linesearch: `ArmijoGoldsteinLS` with `maxiter=0` by default
     (behaves like `BoundsEnforceLS`, fast), bumped to `maxiter=5` Armijo
     backtracks on a per-point retry.
   - `sweep_full_envelope.py` gained a `--mode dry|wet|both` flag.
   - Silenced a debug `print()` in pyCycle's `static_ps_resid.py` that fired
     on every Newton iteration touching negative gamma — was burying sweep
     status under thousands of lines of terminal spam.
4. Housekeeping commits moving upstream scaffolding into `meta/`
   (`LICENSE.txt`) and planning docs into `improvements/`
   (`IMPROVEMENTS.md`, `single_engine_mode.md`), plus several
   roadmap-only commits adding new items to `IMPROVEMENTS.md` (sweep
   coverage plot, YAML run config, CLI entry point — none implemented yet).

### Current convergence results

Full envelope: alt ∈ {0, 2500, 5000} ft, dTs ∈ {0,±10,±20,±30,±40,±50} R,
MN=0.001 (static/runway), 4 power levels per mode.

| Mode | Converged | Notes |
|------|-----------|-------|
| Dry  | 125 / 132 | Tt4 sweep 3100→2500 R |
| Wet  | 89 / 132  | Tt7 sweep 3800→3200 R (fixed Tt4=3100 R mil) |

Both modes: every point with dTs ≥ 0 R converges. Failures are
concentrated at cold (dTs < 0 R) + high-altitude + max-AB corners — these
appear to be genuinely hard for Newton from any warm-start tried so far,
not an artifact of the convergence-detection bugs above. Tracked as
[issue #3](https://github.com/Jhawk414/F404/issues/3).

## What happened after this branch closed

1. Opened [PR #1](https://github.com/Jhawk414/F404/pull/1) against
   `master`, with a summary + an "Approaches and alternatives" section
   pointing back at this handoff and at `improvements/single_engine_mode.md`.
2. Filed the deferred/roadmap items as real GitHub issues instead of only
   living in `IMPROVEMENTS.md` prose (issues were enabled on the repo for
   this purpose):
   - [#2](https://github.com/Jhawk414/F404/issues/2) — dry/wet
     modes size two slightly different engines (~1-2% variance).
   - [#3](https://github.com/Jhawk414/F404/issues/3) — OD sweep
     non-convergence at cold/high-alt/max-AB corners (includes possible
     fixes: relax the fixed `RlineMap` target, widen `_OD_BOUNDS`, denser
     bridge points, per-corner solver tuning).
   - [#4](https://github.com/Jhawk414/F404/issues/4) — move F404
     app code into `/src/`. Has a follow-up comment flagging that
     `release_notes.md` still needs its planned `git mv` to `meta/`
     (staged once, never committed — the commit was lost with the branch
     cleanup below; it's back at repo root on `main`, still pending).
   - [#5](https://github.com/Jhawk414/F404/issues/5) — add a
     per-module `<module>_test.py` regression/test suite convention.
   - [#6](https://github.com/Jhawk414/F404/issues/6) — sync vendored
     `pycycle/` against upstream `OpenMDAO/pyCycle`; concretely, this
     fork's `thermo_add.py` is missing the NumPy 2.x `.item()` fix from
     upstream [pyCycle#117](https://github.com/OpenMDAO/pyCycle/pull/117)
     (authored from this fork's now-deleted `fix/thermo-add-numpy2-compat`
     branch, merged upstream 2026-05-20).
3. Merged PR #1 into `master` (merge commit `576a7b9`).
4. Renamed the repo's default branch `master` → `main` (via GitHub repo
   settings) and fixed the one hardcoded reference to the old name:
   `.github/workflows/pycycle_test_workflow.yml`'s push/PR triggers
   (commit `3caa85b`).
5. Branch cleanup: deleted `feature/alt-mach-sweep` (fully merged into
   `main`, safe) and `fix/thermo-add-numpy2-compat` (its fix is preserved
   permanently via the merged upstream PR) — both locally and on the
   remote.
6. Set the repo description ("GE F404 mixed-flow turbofan cycle deck —
   design-point sizing and altitude/Mach/dTs off-design sweeps, built on
   OpenMDAO's pyCycle.") and added GitHub topics (`openmdao`, `pycycle`,
   `turbofan`, `jet-engine`, `propulsion`, `gas-turbine`, `thermodynamics`,
   `afterburner`, `f404`, `mdao`, `python`).
7. Started tracking handoff docs properly: this file now lives at
   `AGENTS/HANDOFF_14Sep26.md` instead of sitting
   untracked at repo root. It had been untracked long enough to almost get
   lost during the branch cleanup in step 5 — only recovered because it
   was caught in a `git stash` first. Future handoff docs should go in
   `AGENTS/` and get committed promptly, not left loose.

## Remaining loose ends

- ~~`release_notes.md` → `meta/release_notes.md` rename — still not done~~
  **Resolved differently:** deleted outright instead of moved (upstream
  `om-pycycle` release history, not F404-specific) — see the
  `refactor/src-layout` section below.
- `HANDOFF_22Apr26.md` — deleted.
- Everything else from the branch's original "uncommitted/untracked items"
  list (`single_engine_mode.md`, `cycle_deck_wet.csv`, the `*_out/` sweep
  artifact directories, the `test_modes` `.rtf` note) was resolved by the
  time the branch merged — either committed to a permanent home or
  cleared out.

## Next up

- New branch `docs/handoff-and-readme-refresh` (this one) — README rewrite
  is next, in a separate chat/context.
- After that: work through issues #2–#6 above, likely each in its own
  narrowly-scoped branch per the branch-hygiene note in
  `improvements/IMPROVEMENTS.md` item 4.

## Key F404 model parameters (for reference)

- Design point: SLS (alt = 0 ft, MN ≈ 0.001–0.01)
- Dry design thrust target: 11,000 lbf (mil power, Tt4 = 3100 R)
- Wet design thrust target: 17,700 lbf (max AB, Tt7 = 3800 R)
- Thermodynamics: TABULAR / `AIR_JETA_TAB_SPEC`
- Fan PR = 4.1, HPC PR = 6.5, OPR ≈ 26.65 (wet DESIGN)
- BPR ≈ 0.75 (bounds 0.25–0.80), low-bypass mixed-flow
- No LPC (F404 architecture); `lp_shaft` has `num_ports=2` (fan + LPT only)
- Afterburner max T7 ≈ 3800 R (F404 historical max)

## Branch: `refactor/src-layout` — status: merged & deleted ([PR #11](https://github.com/Jhawk414/F404/pull/11))

Completed issue #4 (`src/` restructure), deferred since the prior handoff.
Merged to `main` via PR #11 (merge commit `8dab15b`). Both the local and
remote copies of the branch have since been deleted. Three commits shipped:

1. **`c932036`** — Moved F404 app code (`engine_model.py`, `mp_cycle.py`,
   `sweep_utils.py`, `sweep_full_envelope.py`, `run_design_od.py`,
   `printer.py`, `test_modes.py`) into `src/F404_pycycle/`, out of the repo
   root, as pure `git mv` renames — no import changes needed since the
   moved files stay siblings of each other and the entry scripts are still
   invoked directly. Verified byte-for-byte identical `cycle_deck_wet.csv`
   output before/after the move (diffed against the committed
   `deck/cycle_deck_wet.csv` baseline, which matches the documented 89/132
   wet convergence count). `test_modes.py` wasn't in the issue's file list
   but moved along with the others since it imports `mp_cycle`/`printer`
   and would've broken otherwise.
2. **`b96c02e`** (a separate agent session) — Deleted `MFTF_od_CRZ.py` (the
   pre-refactor monolith, left alone in commit 1 pending confirmation it
   was fully superseded — confirmed, since nothing imports it anymore),
   `release_notes.md`, `.travis.yml`, `.bumpversion.cfg`, and the
   `test_modes` `.rtf` transcript. Moved `Unclassified_Perf_Data/` →
   `docs/unclassified_perf_data/`.
3. **`d19b4b6` — README refresh** — updated the repo-layout table,
   mermaid data-flow diagram, install/usage commands, and roadmap checklist
   to match the `src/` layout and the `meta/`/`docs/` cleanup above.

**Repo renamed:** `Jhawk414/F404-pyCycle` → `Jhawk414/F404` (GitHub handles
the redirect from the old slug, but the remote URL and all in-repo links
have been updated to the new one going forward).

## Next up

Work through issues #2 and #3 together rather than sequentially — both are
Newton-solver robustness problems at extreme corners of the state space
(cold/high-alt/max-AB for #3; a near-zero `FAR_ab` Jacobian conditioning
issue was hit previously when prototyping #2's Option 2, see the comment on
issue #2). Then #5 (test suite, now that `src/` exists) and #6 (vendor
sync).
