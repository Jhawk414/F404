# Handoff: F404-pyCycle — Recommended Issue Order

Supersedes `HANDOFF_14Sep26.md` (renamed to this file). The prior handoff's
content is preserved below unchanged, under "Prior handoff (14 Sep 26)".

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
| [#5](https://github.com/Jhawk414/F404/issues/5)  | Per-module test suite convention | — | medium |
| [#6](https://github.com/Jhawk414/F404/issues/6)  | Sync vendored `pycycle/` with upstream | housekeeping | small (re-scope) |
| [#8](https://github.com/Jhawk414/F404/issues/8)  | PLA/T7-scheduled nozzle A8 area | enhancement | large |
| [#10](https://github.com/Jhawk414/F404/issues/10) | Inline creep/LCF life estimation | enhancement | large/exploratory |
| [#12](https://github.com/Jhawk414/F404/issues/12) | CSV writes full float64 precision | good first issue | trivial |
| [#13](https://github.com/Jhawk414/F404/issues/13) | CLI-configurable sweep ranges | enhancement | medium |

## Recommended order

Dependency chain, condensed:

**#12 → #5 (baseline) → #6 → [#2 measure] → #3 + #8 → #13 → #10**

### Phase 1 — Foundation (before any solver work)

1. **[#12](https://github.com/Jhawk414/F404/issues/12) — CSV precision.**
   Trivial, isolated `float_format` change. Do it *first* because it must land
   before #5 captures any golden CSV baseline — otherwise a later formatting
   change invalidates the baseline. Quick win that de-risks #5.
2. **[#5](https://github.com/Jhawk414/F404/issues/5) — test suite.** The real
   enabler. Every hard item below (#2, #3, #8) is Newton-solver surgery, and
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
