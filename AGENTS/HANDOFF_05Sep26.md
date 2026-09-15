# Handoff: F404-pyCycle — Off-Design Sweep Convergence

Supersedes `HANDOFF_22Apr26.md` (stale — written before the dry/wet mode
question was resolved). Ryan is deleting that file directly.

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
   `AGENTS/HANDOFF_05Sep26.md` (committed `bc656b1`) instead of sitting
   untracked at repo root. It had been untracked long enough to almost get
   lost during the branch cleanup in step 5 — only recovered because it
   was caught in a `git stash` first. Future handoff docs should go in
   `AGENTS/` and get committed promptly, not left loose.

## Remaining loose ends

- ~~`release_notes.md` → `meta/release_notes.md` rename — still not done~~
  **Resolved differently:** deleted outright instead of moved (upstream
  `om-pycycle` release history, not F404-specific) — see the
  `refactor/src-layout` section below.
- `HANDOFF_22Apr26.md` — Ryan is deleting this directly.
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

## Branch: `refactor/src-layout` — status: open ([PR #11](https://github.com/Jhawk414/F404/pull/11))

Picks up issue #4 (`src/` restructure), deferred since this handoff was
written. Three commits so far:

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
3. **README refresh** (this commit) — updated the repo-layout table,
   mermaid data-flow diagram, install/usage commands, and roadmap checklist
   to match the `src/` layout and the `meta/`/`docs/` cleanup above.

**Repo renamed:** `Jhawk414/F404-pyCycle` → `Jhawk414/F404` (GitHub handles
the redirect from the old slug, but the remote URL and all in-repo links
have been updated to the new one going forward).

Not yet merged — Ryan is re-running the full dry+wet envelope sweep
locally to confirm the deck output is unchanged before merging PR #11.

**Next up:** work through issues #2 and #3 together rather than
sequentially — both are Newton-solver robustness problems at extreme
corners of the state space (cold/high-alt/max-AB for #3; a near-zero
`FAR_ab` Jacobian conditioning issue was hit previously when prototyping
#2's Option 2, see the comment on issue #2). Then #5 (test suite, now that
`src/` exists) and #6 (vendor sync).
