# Handoff: F404 — Recommended Issue Order

Supersedes `HANDOFF_18Oct26.md` (renamed to this file; before that,
`HANDOFF_11Oct26.md` and `HANDOFF_10Oct26.md`). Everything before the 10 Oct 26 session is
deliberately **not** carried forward, to keep this file
cheap for agents to read. Only the gotchas that still bite are kept, under
[Standing gotchas](#standing-gotchas). Full history: `git log --follow -- AGENTS/`.

## Session summary (10–20 Oct 26)

### 10 Oct — #2 single-engine sizing (PR #23)

Full write-up: [ADR-0001](../docs/adr/0001-single-engine-sizing.md), the first ADR in `docs/adr/`.

**What shipped** (the two OD points, `a8_ctrl` and the 5.4 % loss are
superseded by the single OD point; see [18 Oct, PR #36](#18-oct--one-od-point-kumar-augmentor-loss-wet-a8-schedule-pr-36)):
- One `MPCycle` with one DESIGN, sized at SLS dry mil (11,000 lbf, Tt4 3100 R).
- Two OD points:
  - `OD_dry`: afterburner is a Duct; A8 frozen at the DESIGN throat area.
  - `OD_wet`: afterburner is a Combustor. A8 is a free state (`a8_ctrl`)
    holding fan `RlineMap` at its design value of 2.0.
- `SweepRunner(frozen_pts=...)` freezes the point the sweep isn't driving,
  because every `run_model()` solves all three.
- Max AB calibrated to 17,700 lbf: Tt7 = 3608 R, with a 5.4% augmentor hot
  loss on `OD_wet` only.
- New deck columns `Wf_core`, `Wf_ab`, `A8`. `f404 design` has no `--mode`;
  `--dsn-tt7` is now `--max-tt7`. Default wet grid is 3608 → 3008 R.

**Findings worth keeping:**
1. The old 5.17% dry/wet sizing gap was a cycle mismatch (augmentation ratio
   1.692 vs target 1.609), not a sizing artefact. Closing it needs a cycle knob.
2. Wet full-envelope convergence rose 89 → 100 of 132 with no regressions,
   which supports #3's frozen-A8 hypothesis. Remaining failures are all dTs < 0.
3. Dry is 118/132 (confirmed on a clean venv). The old 125 is not reproducible.
4. The near-zero-`FAR_ab` Jacobian problem from the #2 prototyping did not reproduce.
5. A single A8 can't serve dry and wet (dry flow through the wet-sized throat
   leaves the map), so a per-mode A8 is a prerequisite for any one-engine design.

**Numbers at 11 Oct:** 177 tests, 97% coverage (190 tests as of 13 Oct, below).

### 11 Oct — docs and rename (two PRs, both merged to `main`)

**[PR #28](https://github.com/Jhawk414/F404/pull/28) — public F404 performance data, converted to Obsidian markdown.**
Source PDFs moved to `docs/unclassified_perf_data/pdf/`; nine papers converted
to markdown in `md/` with figures under `md/images/<paper>/`. Start at
**[`docs/unclassified_perf_data/README.md`](../docs/unclassified_perf_data/README.md)**
(558 lines): this is the index for real-world F404 performance data, and the
place to look before calibrating anything (#25) or validating a result.
- **How to use it:** the README is ~58 KB and the nine papers total ~780 KB.
  Don't read them whole. Grep the README for the section you need:
  *Cross-Study Multi-Condition Reference Map* (one table of key parameters with
  operating condition and source), *Research Selection Guide* (which paper
  answers which question), then open only that paper.
- **Provenance tags matter.** Every number is tagged `[M-DIR]` measured,
  `[M-SPEC]` manufacturer rating, `[M-MOD]` model-derived (a GE cycle deck
  driven by test data, not a measurement), or `[M-PLOT]` read off a chart.
  Operating conditions differ per row (ground stand, altitude chamber,
  flight); don't mix them. Published thrust ratings are uninstalled.
- **Where the public data and the model differ today** (values from the index,
  *not re-verified against the papers*, and not necessarily like-for-like on
  station definitions; a starting point for #25, not findings):

  | | Published (SLS, std day) | Model |
  |---|---|---|
  | Max A/B thrust | 16,000 lbf | 17,700 (calibrated) |
  | Dry (IRP) thrust | 10,600 lbf | 11,000 |
  | Dry TSFC | 0.78–0.81 | 0.624 |
  | BPR | 0.34 | ~0.75 |
  | N1 / N2 | 13,270 / 16,810 rpm | 10,000 / 14,000 |
  | Airflow | 142–145 lbm/s | 145.1 |
  | HPT cooling bleed | 11% of CDP | 11.0% |

- Also there: customer-bleed thrust slopes (Yuhas), nozzle A8 span and
  expansion ratio (relevant to #8), and a flight-envelope
  max-A/B gross-thrust grid (Johnson). An unconverted `F404 Family Data Sheet`
  PDF sits in `pdf/`.
- **A8 span, checked 18 Oct.** The index's "~215 in² at IRP" has no source in
  the papers. Sourced values (GE-model-derived unless noted): about 400 in² at
  flight idle (Johnson, GE model), 232–249 in² at MIL (TM-4140 at 30k ft;
  TM-4538 ground), and 420 in² at max AB, 30k ft, M 1.2 (TM-4140, measured
  in flight). A9/A8 is 1.24–1.49 (TM-4538). Use these, not 215, for #8.

**[PR #29](https://github.com/Jhawk414/F404/pull/29) — package rename `src/F404_pycycle` → `src/f404`**, to match the
repo name. `python -m f404`, `f404.cli:main`, and the `filterwarnings` scope
all follow. **An existing checkout must re-run `pip install -e ".[all]"`** or
the `f404` entry point still points at the old package. Old handoffs, issue
bodies #13 and #16, and anything else written before 11 Oct still say
`F404_pycycle`; read it as `f404`.

Also: [PR #21](https://github.com/Jhawk414/F404/pull/21) (interactive browser GUI for deck interpolation) is open and
**parked on purpose**. It waits until `--mach` and `--pla` exist. Don't review or
rebase it as part of the next items.

### 13 Oct — CI split and CLI axis fixes (one PR, three commits)

- **#31:** PRs run only `pytest -m "not slow"` (Ubuntu 3.12, ~1 min). The full
  3-job matrix runs on push to `main`, `workflow_dispatch`, and PRs labelled
  `full-ci`. **Apply `full-ci` before merging**: the goldens and convergence
  regressions are all `slow`. Superseded PR runs are cancelled.
- **#22:** `cli.main()` joins `--dts -50,50,10` into `--dts=-50,50,10` before
  argparse (abbreviated flags too).
- **#24:** a single value is a constant axis (`--alt 0`); `0,0,0` now hints at it.
- **Numbers (13 Oct):** 190 tests (155 fast), 97% coverage, full suite ~2 min.

### 18 Oct — full-precision decks and `f404 compare` (PR #34)

- **Decks are now full float64 precision**, with 56 columns (the original
  22, then station data). The columns are `DECK_COLUMNS` in `sweep_utils.py`.
  The decks were regenerated from the unchanged model, with the same 118 dry
  and 100 wet points.
- **`f404 compare BASE NEW`** (`compare_decks.py`) is the standard proof for
  a model change: sweep before and after, then compare.
  - It raises on mixed or mismatched modes, duplicate keys and unknown
    `--cols`.
  - It reports zero-base points in absolute terms.
  - It flags blank or non-finite values and exits 1.
- **Filed [#35](https://github.com/Jhawk414/F404/issues/35)**: both burners
  are 100 % efficient, because pyCycle's `Combustor` has no efficiency
  input. NASA TN D-6839 (TF30) puts afterburner efficiency at 0.91 → 0.68
  from Reynolds-number index 0.80 to 0.25. The same report puts the pilot
  zone's lean limit near f/a 0.006 on unburned air, about FAR_ab 0.005 on
  the model's definition.
- **Numbers (18 Oct):** 207 tests (172 fast), 97 % coverage.

### 18 Oct — one OD point, Kumar augmentor loss, wet A8 schedule (PR #36)

Full write-up: [ADR-0002](../docs/adr/0002-single-od-topology.md). ADR-0001 is
partly superseded.

**What shipped:**
- **One `OD` point** (`mp.od_pt`). Its afterburner is always a Combustor.
  `aug_ctrl.Tt7_cmd` selects dry (0, or ≤ Tt6) or wet. FAR_ab's lower bound
  is exactly 0, and the dry root sits on it. DESIGN keeps its Duct.
  `od_pts`, `frozen_pts`, `_FROZEN_NEWTON`, `_OD_WET_BOUNDS`, `a8_ctrl` and
  the `afterburn` option are gone.
- **Augmentor loss (#33, closed by PR #36):** `q·[C_D + η(τ−1)]`, Kumar
  Eq. 13 at the flameholder Mach `k_M·MN6`. `AB_K_M` 0.5, `AB_CD` 0.65,
  `AB_ETA` 1.0 in `mp_cycle.py`. 2.1 % cold (DESIGN too), 6.6 % at SLS max AB.
- **Wet A8 (#8, wet half):** `NozzleSchedule`, choked continuity with the dry
  nozzle. It is explicit, with no Newton state. Wet keeps the gas generator
  within ~0.25 % BPR of dry at each condition. The fan follows its dry-mil
  line (Rline 1.94–2.12), not 2.0.
- **`MAX_Tt7` = 3598.35 R** (was 3608). The wet default grid is
  3598.35 → 2998.35 R. To compare a wet deck against an older one, sweep with
  `--throttle 3008,3608,200`.
- **`docs/references/`** is new: general method papers the model uses, kept
  apart from `unclassified_perf_data/` (F404 data to match). Its
  [index](../docs/references/README.md) lists, per paper, the equations and
  constants the code takes, with provenance tags including `[M-THY]`
  (analytic). Kumar (1980) is in; the NASA flameholder RMs, TN D-6839 and
  ICAS-90-5.3.4 are the next candidates.
- SLS dry mil: W 145.09 lbm/s, TSFC 0.6240 (W +0.63 %, TSFC +0.6 % from the
  cold loss in the sizing).

**Findings worth keeping:**
1. Full envelope: dry 120/132 (+2 hot-day points), wet 95/132 (−5, all at
   dTs −20 R). Every wet failure is at a condition where dry mil also fails,
   except (2500 ft, −20 R, 3398 R). #3 is now one problem for both modes.
2. Light-off moves the gas generator by < 0.02 %, and the worst excursion over
   the AB range is 0.26 % BPR, against 3.9 % under the old Rline-2.0 hold.
3. **The dry A8 schedule is blocked on #25/#30, not on the topology.** Opening
   A8 at fixed Tt4 raises BPR into the OD bound (1.0) and raises fan Rline,
   the opposite of the real engine, which commands N2 below MIL.
4. A minimum wet FAR_ab of ~0.005 (TN D-6839) is the planned floor on
   `Tt7_cmd`, in a small follow-up PR.

**Numbers (18 Oct, PR #36):** 219 tests (178 fast). `build_problem()`
raises `MaxTt7TooLowError` (a `ValueError`) if `max_Tt7` ≤ the solved Tt6.

### 19–20 Oct — failed points in the deck (#27), Mach axis (#13) (PR #39)

**What shipped:**
- **Every requested point is a deck row.**
  - Leading columns: `mode, converged, alt, dTs, MN, T4_cmd, T7_cmd`. `mode` moved to the front.
  - `T4_cmd`/`T7_cmd` are what the OD point was told: dry is `(Tt4, 0)`, wet is `(mil, Tt7)`.
  - Outputs are blank on a failed row, and the last column, `failure`, says why: an exception name, `bound:<state>` or `target`.
  - No separate failures CSV. Count convergence from the deck, never by hand.
- **`f404 compare` keys on `(mode, alt, dTs, MN, T4_cmd, T7_cmd)`.**
  - It lists points that converge in only one deck and counts those failed in both.
  - Full-envelope decks compare too.
  - Pre-#27 decks get their commands from the solved T4/T7.
- **`--mach MIN,MAX,STEP`**, default `0.001, 0.2, 0.4, 0.6, 0.8, 0.95`.
  - Mach 0 is flown at `STATIC_MN` = 0.001; exactly 0 gives NaN residuals.
  - Mach ≥ 1 is rejected (#38).
  - The grid nests power → Mach → alt → dTs, and each odd Mach step reverses the alt/dTs block. With one Mach this is the old order, so `--mach 0` reproduces the pre-Mach decks bit for bit (the PR's regression proof).
- **No model change.** DESIGN stays at SLS dry mil. Mach is off-design; the F404 is rated and published at SLS.
- Filed #37 (DESIGN at MN 0.01 vs static 0.001; SLS mil reads 11,044.7 lbf, not 11,000) and #38 (supersonic inlet recovery and the W bound).

**Findings worth keeping:**
1. **Full default sweep:** dry 642/792, wet 657/792 converged, in 2 h 5 min. A failed point costs ~20 s, a converged one ~0.4 s. Per-Mach counts are in the README.
2. **Dry part power collapses with Mach.** Tt4 2500 R converges 30 of 33 points static and 3 at M 0.95, as BPR runs into its 1.0 bound (`bound:balance.BPR`). This is #25's BPR problem, now visible across Mach.
3. **The mil cold corner (dry, and wet with it) shrinks up to M 0.6** (24 → 32 of 33), then grows again.
4. **The OD W bound (200 lbm/s) bites on cold days at M 0.95** (6 points). Mil W reaches 197.6 at M 0.8, −30 R. Raise it before any supersonic work (#38 comment).
5. **Static rows in the full deck differ from `--mach 0` at Newton tolerance (≤ 0.0024 %).** Later power levels now warm-start from M 0.95, not from 5000 ft. Use `--mach 0` for bit-identical static regressions.

**Numbers (20 Oct, PR #39):** 228 tests (187 fast).

## Open issues at a glance

Closed since the last full table: #2 (PR #23), #4, #5, #6, #12, #18, and #22, #24, #31 (13 Oct PR), #33 (PR #36), #27 and #13 (PR #39).
New since: #35 (combustion efficiency), #37 (one static Mach), #38 (supersonic envelope).

| # | Title | Type | Size / status |
|---|---|---|---|
| [#30](https://github.com/Jhawk414/F404/issues/30) | Define PLA in the cycle (blocks the `--pla` axis) | enhancement | decision first, then small; see [PLA](#pla-what-the-literature-says) |
| [#17](https://github.com/Jhawk414/F404/issues/17) | Pydantic models for inputs | enhancement | medium |
| [#8](https://github.com/Jhawk414/F404/issues/8) | PLA/T7-scheduled A8 | enhancement | 🟡 wet half done (PR #36, ADR-0002); **dry schedule open**, with #25/#30 |
| [#25](https://github.com/Jhawk414/F404/issues/25) | Define idle; calibrate dry part power to F404 data | enhancement | large; tune together with #8 |
| [#3](https://github.com/Jhawk414/F404/issues/3) | Cold / high-alt / max-AB non-convergence | bug | large; body numbers stale (now 120 dry / 95 wet; wet fails where dry mil does) |
| [#16](https://github.com/Jhawk414/F404/issues/16) | CLI entry point | enhancement | 🟡 `sweep`/`design` done; **`init-config`/YAML open** (needs #17) |
| [#37](https://github.com/Jhawk414/F404/issues/37) | One static Mach for DESIGN and OD | bug | small; moves goldens and the max-AB calibration |
| [#38](https://github.com/Jhawk414/F404/issues/38) | Supersonic envelope: inlet recovery, W bound | enhancement | medium; W bound already bites at M 0.95 cold |
| [#35](https://github.com/Jhawk414/F404/issues/35) | Combustion efficiency in both burners | enhancement | medium; vendored `Combustor` change or F404 wrapper; calibrate max AB after it |
| [#10](https://github.com/Jhawk414/F404/issues/10) | Inline creep/LCF life estimate | enhancement | exploratory |

## Recommended order

**#30 → `--pla` → #17 → #8 + #25 (+ #3, #37 re-measured) → #16 remainder → #10**

#27 and #13 are done (PR #39). Finish the sweep-axis side of the CLI with
PLA before #8 and #25, so agents working those have `--pla` to sweep.
#38 is independent and can go any time.

**Stage 1: PLA (CLI)**

1. **#30, then `--pla`.** #30 settles what PLA commands (a decision recorded as an ADR) and gives a provisional schedule. PLA then maps onto the deck's existing `T4_cmd`/`T7_cmd` commands (plus a `PLA` input column).
   - `--throttle` stays as the temperature-based throttle, for textbook T4/T7 work.
   - Findings are in [PLA](#pla-what-the-literature-says) below.

**Stage 2: inputs as data**
2. **#17 pydantic.** Not CLI, but placed before the solver cluster because #25
   edits the DESIGN defaults in `problems._apply_design_inputs`, which #17
   turns into data; #17's own text asks to land before #2/#3/#8 churn the
   same signatures. It also unblocks `init-config`/YAML (#16).

**Stage 3: coupled physics cluster (one effort)**
3. **#8 + #25 together, with #3 measured alongside.** #8 and #3 are the same
   problem from two angles (confirmed by 89 → 100/132 from #2). #25 says
   explicitly to tune with #8: a dry PLA → A8 schedule moves the fan operating
   line, BPR and spool speeds at exactly the low-Tt4 end #25 is calibrating.
   Notes for whoever starts:
   - Keep DESIGN as the MIL / minimum-A8 anchor so Tt4 = 3100 R dry rows
     don't change (cheap regression check). The dry schedule multiplies
     `a8_sched.A8_dsn` in `NozzleSchedule` (an `A8_dry(Tt4)` or `A8_dry(N2)`
     slot); keep it explicit, with no Newton state. The wet factor then scales
     the dry throat, so dry and wet meet continuously by construction.
   - **Re-check max-AB calibration** (Tt7 3598.35 R, Kumar loss) after any DESIGN
     change; **goldens in `tests/problems_test.py` and the committed decks will
     move by design**.
   - Use the published-data table above and the index README for targets
     (MIL TSFC, airflow, idle thrust, N1, N2).
   - Define idle by an observable (ground-idle thrust or N2 %), not a Tt4 floor.
   - The model's part-power BPR (~0.95 at Tt4 2500 R) is far above the
     published 0.34, and the OD `BPR` balance's upper bound of 1.0 is
     reachable there. Opening the dry A8 at a fixed Tt4 raises BPR further.
     The F404 commands N2 below MIL, not Tt4 (#30), which is part of the same
     calibration problem.
   - **#35 sits with this cluster.** It changes the augmentor's thrust and
     fuel, so max AB recalibrates after it (#33's loss is already in).

**Stage 4: the rest**
4. **#16 remainder: `init-config`/YAML**, after #17.
5. **#10 creep/LCF.** Additive and independent; last, incrementally.

### PLA: what the literature says

PLA isn't modeled: sweeps drive Tt4 (dry) or Tt7 (wet) directly. Full write-up
in [#30](https://github.com/Jhawk414/F404/issues/30); the essentials:
- Landmarks: 31° flight idle, **87° MIL** (not 90°), 130° max AB.
- Below MIL, PLA schedules `N2` and `A8`. At and above MIL it schedules AB fuel
  flow, and `A8` is a trim holding a scheduled LPT-exit temperature (`T5.6`).
  So PLA is not one cycle variable. The wet `NozzleSchedule` (gas generator
  held at its dry state) is the model's analogue of that trim.
- One PLA axis spans dry and wet, so `--pla` works with `--mode both`, unlike
  `--throttle`. `--throttle` keeps temperature semantics; `--pla` is a separate
  flag, as is a target-thrust OD mode (discussed 07 Oct, deferred).
- Open: dry commanded quantity (Tt4 vs `N2` vs thrust), light-off location,
  schedule source (Ray's measured thrust vs PLA is the best candidate).

## Standing gotchas

**Environment and process**
- **`gh` in this checkout defaults to upstream `OpenMDAO/pyCycle`.** Always
  pass `--repo Jhawk414/F404`, or `gh issue view 2` returns an unrelated issue.
- CI installs OpenMDAO latest (3.45); a local `.venv` may have 3.39. Behaviour
  differs both ways (a dry `page_viewer` crash passed CI and failed locally).
  Test fixtures use `verbose=False`, which hides verbose-print paths.
- Local `.venv` once held a stale non-editable `pycycle` copy in site-packages.
  If imports look wrong, re-run `pip install -e ".[all]"`.
- Open-issue bodies predate PR #23/#29: #3 quotes 125/132 and 89/132; #13/#16
  link `src/F404_pycycle/`. Trust the numbers in this file and the code.

**Code and tests**
- Tests live in top-level `tests/`, one `<module>_test.py` per module. Connection
  assertions match prefix + suffix, not the exact path, because OpenMDAO
  resolves promoted names into pyCycle internals.
- The `filterwarnings` rule promoting NumPy's scalar-conversion deprecation to an
  error must stay **scoped to `f404.*`** in `pyproject.toml`. Unscoped, it turns
  the vendored library's own deprecations into failures (`testpaths` doesn't
  protect against an explicit path).
- Use the `_scalar()` helper in `sweep_utils.py` for OpenMDAO length-1 arrays.
  Bare `float()` is deprecated and, inside the `except Exception` in
  `_state_at_bounds` / `_target_met`, would silently report every point
  unconverged. CI's `ruff --select NPY201` does not catch it.
- `run_sweep` seeds `_last_good_state` from the state it is handed. If the
  first grid point fails, there's nothing to restore, and everything after it
  fails too. This stays hidden only because both default grids start on a
  converging point (SLS, static), so **it matters when a new envelope
  reorders the grid** (e.g. `--mach 0.6,0.9,0.3` starts at M 0.6). A deck
  that is nearly all `converged == False` usually means this, not "the model broke".
- `printer.py` takes a `file` argument because pyCycle's `print_*` helpers
  bind `sys.stdout` at import, which defeats `capsys`.
- Decks are full float64 precision (`write_deck_csv()`), with columns
  `INPUT_COLUMNS` + `DECK_COLUMNS` + `failure` from `sweep_utils.py`, and a
  row for every requested point. Filter with `df[df.converged]`. A failed row's
  outputs are empty fields (`NaN` in pandas) by design. The decks are over
  GitHub's 512 KB CSV-render limit, so GitHub shows raw text: not a format bug. Decks written before 18 Oct 26 were
  rounded to 2–4 decimals, so they can't resolve differences below about
  0.01 %; regenerate rather than compare against one.

**CLI behaviour**
- A range flag takes `min,max,step` or a single value (constant axis). A
  negative-start range works as a separate token; `main()` rewrites it to the
  `--flag=value` form. A new range flag must be added to `_RANGE_FLAGS` in
  `cli.py` or it won't get this.
- Axis order is fixed regardless of flag order: `--dts` hot side first, then
  cold; `--throttle` high power to low. The warm-start was built around it.
  `-50,50,10`, `2500,3100,200`, `3200,3800,200` reproduce the old default
  grids exactly (pinned by tests). `--mach` is ascending; Mach steps reverse
  the alt/dTs block (`build_snake_sweep`).
- Validation fails before OpenMDAO loads (exit 2): not one or three finite
  numbers, step ≤ 0, min > max, a step that doesn't divide `max − min`,
  `--throttle` with `--mode both`, wet `--throttle` ≤ fixed Tt4, `--out` is a
  file. A non-converging `design` exits 1.
- The wet-throttle floor (`Tt7 > MIL_Tt4`) is conservative; the physical floor
  is the mixer exit temperature (~1500 R).
- `importing sweep_full_envelope` sets no logging or warning filters;
  `configure_runtime()` does, from the CLI.

## Key model parameters

- DESIGN at SLS (alt 0 ft, MN 0.01; sweeps call 0.001 static, #37), sized at dry mil: 11,000 lbf, Tt4 3100 R.
  Max AB: Tt7 3598.35 R → 17,700 lbf, with the Kumar augmentor loss
  (2.1 % cold, 6.6 % at max AB; ADR-0002).
- Thermo: TABULAR / `AIR_JETA_TAB_SPEC`.
- Fan PR 4.1 (eff 0.8948), HPC PR 6.5 (eff 0.8707), HPT eff 0.8888, LPT eff
  0.8996; BPR ≈ 0.75; low-bypass mixed-flow, no LPC (`lp_shaft` has
  `num_ports=2`: fan + LPT).
- LP 10,000 rpm, HP 14,000 rpm, 250 hp customer power extraction; bleeds
  `cool1` 5.07% (HPC interstage → LPT), `cool3` 11.0% (CDP → HPT).
- Dry MIL at SLS: W 145.1 lbm/s, TSFC 0.624 (optimistic vs published, see #25).
- Branch hygiene: one narrowly-scoped branch per issue (`IMPROVEMENTS.md` item 4).
