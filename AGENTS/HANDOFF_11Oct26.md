# Handoff: F404 — Recommended Issue Order

Supersedes `HANDOFF_10Oct26.md` (renamed to this file). Everything before the
10 Oct 26 session is deliberately **not** carried forward, to keep this file
cheap for agents to read. Only the gotchas that still bite are kept, under
[Standing gotchas](#standing-gotchas). Full history: `git log --follow -- AGENTS/`.

## Session summary (10–11 Oct 26)

### 10 Oct — #2 single-engine sizing (PR #23)

Full write-up: [ADR-0001](../docs/adr/0001-single-engine-sizing.md), the first ADR in `docs/adr/`.

**What shipped:**
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

**Current numbers (measured 11 Oct on `main`):** 177 tests, 97% coverage, all
pass, no xfail; the full suite takes ~2 min locally.

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
  | Dry TSFC | 0.78–0.81 | 0.62 |
  | BPR | 0.34 | ~0.75 |
  | N1 / N2 | 13,270 / 16,810 rpm | 10,000 / 14,000 |
  | Airflow | 142–145 lbm/s | 144.2 |
  | HPT cooling bleed | 11% of CDP | 11.0% |

- Also there: customer-bleed thrust slopes (Yuhas), nozzle A8 span (~215 →
  ~420 in²) and expansion ratio (relevant to #8), and a flight-envelope
  max-A/B gross-thrust grid (Johnson). An unconverted `F404 Family Data Sheet`
  PDF sits in `pdf/`.

**[PR #29](https://github.com/Jhawk414/F404/pull/29) — package rename `src/F404_pycycle` → `src/f404`**, to match the
repo name. `python -m f404`, `f404.cli:main`, and the `filterwarnings` scope
all follow. **An existing checkout must re-run `pip install -e ".[all]"`** or
the `f404` entry point still points at the old package. Old handoffs, issue
bodies #13 and #16, and anything else written before 11 Oct still say
`F404_pycycle`; read it as `f404`.

Also: [PR #21](https://github.com/Jhawk414/F404/pull/21) (interactive browser GUI for deck interpolation) is open and
**parked on purpose**. It waits until `--mach` and `--pla` exist. Don't review or
rebase it as part of the next items.

## Open issues at a glance

Closed since the last full table: #2 (PR #23), #4, #5, #6, #12, #18.

| # | Title | Type | Size / status |
|---|---|---|---|
| [#22](https://github.com/Jhawk414/F404/issues/22) | `--dts -50,50,10` parsed as a flag | bug | small |
| [#24](https://github.com/Jhawk414/F404/issues/24) | Single value = constant axis (`--alt 0`) | enhancement | small; same code as #22 |
| [#27](https://github.com/Jhawk414/F404/issues/27) | Write failed sweep points to `deck/` | enhancement | small/medium |
| [#13](https://github.com/Jhawk414/F404/issues/13) | CLI sweep ranges | enhancement | 🟡 alt/dTs/throttle done; **`--mach` open** (needs model work) |
| [#30](https://github.com/Jhawk414/F404/issues/30) | Define PLA in the cycle (blocks the `--pla` axis) | enhancement | decision first, then small; see [PLA](#pla-what-the-literature-says) |
| [#31](https://github.com/Jhawk414/F404/issues/31) | CI: fast tests on PRs, full matrix on merge | housekeeping | small; independent |
| [#17](https://github.com/Jhawk414/F404/issues/17) | Pydantic models for inputs | enhancement | medium |
| [#8](https://github.com/Jhawk414/F404/issues/8) | PLA/T7-scheduled A8 | enhancement | large; state-of-play comment 10 Oct |
| [#25](https://github.com/Jhawk414/F404/issues/25) | Define idle; calibrate dry part power to F404 data | enhancement | large; tune together with #8 |
| [#3](https://github.com/Jhawk414/F404/issues/3) | Cold / high-alt / max-AB non-convergence | bug | large; body numbers stale (now 118 dry / 100 wet) |
| [#16](https://github.com/Jhawk414/F404/issues/16) | CLI entry point | enhancement | 🟡 `sweep`/`design` done; **`init-config`/YAML open** (needs #17) |
| [#10](https://github.com/Jhawk414/F404/issues/10) | Inline creep/LCF life estimate | enhancement | large/exploratory |

## Recommended order

**#31 (any time) → #22 + #24 → #27 → #13 `--mach` → #30 → `--pla` → #17 → #8 + #25 (+ #3 re-measured) → #16 remainder → #10**

Plan: finish the sweep-axis side of the CLI before #8 and #25, so agents
working those have `--mach` and `--pla` to sweep or turn.

**Stage 1: sweep axes (CLI)**
1. **#22 + #24 together.** Both live in `cli.py` (`parse_range`/`expand_range`,
   the axis builders), and #24 notes a negative single value (`--dts -20`) hits
   #22's argparse problem. Cheap, and makes every later flag easier to type.
2. **#27, failure CSV.** Before `--mach`: a Mach sweep will surface new
   failures, and without a record of which points failed and why, a missing
   row can't be told apart from a point nobody asked for. It is also #3's
   measurable baseline and the input for the planned coverage plot.
3. **#13 `--mach`.** Not just a flag: Mach is pinned at 0.001 in `SweepRunner`;
   a Mach dimension has to go into `build_snake_sweep` / `generate_bridge_points`
   in `sweep_utils.py`. Expect new non-convergence at the envelope edge; that
   is #3's problem, not a blocker (per #13's scope note).
4. **#30, then `--pla`.** #30 settles what PLA commands (decision, ADR) and
   gives a provisional schedule; the `--pla` flag is a thin layer on top.
   Findings in [PLA](#pla-what-the-literature-says) below.

**Stage 2: inputs as data**
5. **#17 pydantic.** Not CLI, but placed before the solver cluster because #25
   edits the DESIGN defaults in `problems._apply_design_inputs`, which #17
   turns into data; #17's own text asks to land before #2/#3/#8 churn the
   same signatures. It also unblocks `init-config`/YAML (#16).

**Stage 3: coupled physics cluster (one effort)**
6. **#8 + #25 together, with #3 measured alongside.** #8 and #3 are the same
   problem from two angles (confirmed by 89 → 100/132 from #2). #25 says
   explicitly to tune with #8: a dry PLA → A8 schedule moves the fan operating
   line, BPR and spool speeds at exactly the low-Tt4 end #25 is calibrating.
   Notes for whoever starts:
   - Keep DESIGN as the MIL / minimum-A8 anchor so Tt4 = 3100 R dry rows
     don't change (cheap regression check). Schedule goes inside `OD_dry`,
     replacing the direct A8 connection; make it an explicit function of a
     sweep input so it adds no Newton state (see the 10 Oct comment on #8).
   - The dry-MIL and wet-min-AB A8 must meet continuously (ADR-0001 has the
     continuity table); today's fixed Rline 2.0 leaves BPR −3.9…+1.7% off SLS.
   - **Re-check max-AB calibration** (Tt7 3608 R, 5.4% loss) after any DESIGN
     change; **goldens in `tests/problems_test.py` and the committed decks will
     move by design**.
   - Use the published-data table above and the index README for targets
     (MIL TSFC, airflow, idle thrust, N1, N2).
   - Define idle by an observable (ground-idle thrust or N2 %), not a Tt4 floor.

**Stage 4: the rest**
7. **#16 remainder: `init-config`/YAML**, after #17.
8. **#10 creep/LCF.** Additive and independent; last, incrementally.

### PLA: what the literature says

PLA isn't modeled: sweeps drive Tt4 (dry) or Tt7 (wet) directly. Full write-up
in [#30](https://github.com/Jhawk414/F404/issues/30); the essentials:
- Landmarks: 31° flight idle, **87° MIL** (not 90°), 130° max AB.
- Below MIL, PLA schedules `N2` and `A8`. At and above MIL it schedules AB fuel
  flow, and `A8` is a trim holding a scheduled LPT-exit temperature (`T5.6`).
  So PLA is not one cycle variable, and `OD_wet`'s `a8_ctrl` (Rline hold) is
  the model's analogue of that trim.
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
  converging point, so **it matters when `--mach` or a new envelope reorders
  the grid.** A near-empty deck usually means this, not "the model broke".
- `printer.py` takes a `file` argument because pyCycle's `print_*` helpers
  bind `sys.stdout` at import, which defeats `capsys`.
- Don't reformat a reduced-precision deck to raise precision; the digits are
  gone. Regenerate from the model (`write_deck_csv()` sets per-column
  precision: `%.4e` for the fuel-air ratios, 4 decimals for dimensionless
  quantities, 2 for thrust and temperatures).

**CLI behaviour**
- Axis order is fixed regardless of flag order: `--dts` hot side first, then
  cold; `--throttle` high power to low. The warm-start was built around it.
  `-50,50,10`, `2500,3100,200`, `3200,3800,200` reproduce the old default
  grids exactly (pinned by tests). A `--mach` axis needs an equivalent rule.
- Validation fails before OpenMDAO loads (exit 2): not exactly three finite
  numbers, step ≤ 0, min > max, a step that doesn't divide `max − min`,
  `--throttle` with `--mode both`, wet `--throttle` ≤ fixed Tt4, `--out` is a
  file. A non-converging `design` exits 1.
- The wet-throttle floor (`Tt7 > MIL_Tt4`) is conservative; the physical floor
  is the mixer exit temperature (~1500 R).
- `importing sweep_full_envelope` sets no logging or warning filters;
  `configure_runtime()` does, from the CLI.

## Key model parameters

- DESIGN at SLS (alt 0 ft, MN ≈ 0.001), sized at dry mil: 11,000 lbf, Tt4 3100 R.
  Max AB: Tt7 3608 R → 17,700 lbf, 5.4% augmentor hot loss on `OD_wet` only.
- Thermo: TABULAR / `AIR_JETA_TAB_SPEC`.
- Fan PR 4.1 (eff 0.8948), HPC PR 6.5 (eff 0.8707), HPT eff 0.8888, LPT eff
  0.8996; BPR ≈ 0.75; low-bypass mixed-flow, no LPC (`lp_shaft` has
  `num_ports=2`: fan + LPT).
- LP 10,000 rpm, HP 14,000 rpm, 250 hp customer power extraction; bleeds
  `cool1` 5.07% (HPC interstage → LPT), `cool3` 11.0% (CDP → HPT).
- Dry MIL at SLS: W 144.2 lbm/s, TSFC 0.62 (optimistic vs published, see #25).
- Branch hygiene: one narrowly-scoped branch per issue (`IMPROVEMENTS.md` item 4).
