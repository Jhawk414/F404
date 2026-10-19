# ADR-0002: One off-design topology from dry to max afterburner

**Status:** Accepted
**Date:** 2026-10-18
**Deciders:** @Jhawk414
**Supersedes:** part of [ADR-0001](0001-single-engine-sizing.md): its two OD
points (`OD_dry` with a Duct, `OD_wet` with a Combustor), the Rline-2.0 A8
law, the fixed 5.4 % augmentor loss and its light-off growth-path note.
ADR-0001's single dry-mil DESIGN and its max-AB thrust calibration stand.
**Issues:** [#33](https://github.com/Jhawk414/F404/issues/33),
[#8](https://github.com/Jhawk414/F404/issues/8) (wet half). Also touches
[#3](https://github.com/Jhawk414/F404/issues/3),
[#25](https://github.com/Jhawk414/F404/issues/25),
[#30](https://github.com/Jhawk414/F404/issues/30),
[#35](https://github.com/Jhawk414/F404/issues/35).

## Context

ADR-0001 (A3b) ran the sized engine on two OD points. `OD_dry`'s afterburner
was a `Duct`. `OD_wet`'s was a `Combustor`, with A8 a Newton state
(`a8_ctrl`) holding fan Rline at 2.0. Light-off was a hand-off between two
models.

Transient work is next: one time-marched run from sub-mil to max AB. That
needs one constant topology. It also needs physics that do not step at
light-off. A3b had three steps:

1. **The topology.** Duct to Combustor.
2. **The augmentor loss.** 0 dry, 0.054 wet, from upstream pyCycle's
   example. Nothing scaled with Mach or heat addition, and there was no cold
   (flameholder) loss (#33).
3. **A8.** The DESIGN throat dry, the Rline-2.0 hold wet. Off SLS, dry mil
   is not at Rline 2.0. Lighting the AB therefore moved the gas generator, by
   up to 3.9 % BPR at 2500 ft / −20 R (#8).

Three facts made one OD point plausible:

- **At zero fuel a Combustor is a Duct.** In pyCycle a Combustor is ideal
  fuel mixing plus a constant dPqP. A FAR_ab = 0 Combustor matched the Duct
  dry OD to about 1e-7 %, with identical iteration counts.
- **ADR-0001's A2 already ran an always-present Combustor.** With the FAR_ab
  balance bounded below at exactly 0, it converged 117/132 dry against
  118/132, with no rank-deficiency errors. The failure that put the Duct in
  (51c9bb6) came from FAR *fixed* at 0, with no balance state.
- **The decks are now full precision** (`DECK_COLUMNS`, 56 columns,
  `f404 compare`). Differences below 0.01 % no longer round away, so every
  comparison below is exact.

## Decision

Adopt **C3 with a neutral dry schedule**:

- **One `OD` point** (`MPMixedFlowTurbofan.od_pt`). Its afterburner is a
  `pyc.Combustor` at every power setting. DESIGN keeps its `Duct`, because
  it never lights.
- **`AugmentorControl` (`aug_ctrl`)** takes one command, `Tt7_cmd`, and the
  augmentor inlet state (station 6, `mixer_duct.Fl_O`). Any command at or
  below Tt6 is dry, so 0 is the usual dry command. It outputs:
  - **The FAR_ab target**, `Tt7 = max(Tt7_cmd, Tt6)`. The FAR_ab balance's
    lower bound is exactly 0. When dry, its root sits on that bound.
  - **The augmentor loss** (#33), `dPqP = q·[C_D + η(τ − 1)]`, with
    `τ = Tt7/Tt6`. Here `q` is the approach dynamic head over Pt at the
    flameholder plane (Kumar 1980, Eq. 13),
    `q = (γ/2)·M_fh²·(1 + (γ−1)/2·M_fh²)^(−γ/(γ−1))`, and the flameholder
    Mach is `M_fh = k_M·MN6`. The constants are `k_M` 0.5, `C_D` 0.65 and
    `η` 1.0 (`AB_K_M`, `AB_CD`, `AB_ETA` in `mp_cycle.py`). DESIGN's Duct
    carries the same cold loss through its own `aug_ctrl`: 2.10 % at
    MN6 = 0.446.
- **`NozzleSchedule` (`a8_sched`)** sets A8 explicitly. There is no Newton
  state and no blend. It uses choked-throat continuity with the dry nozzle
  (#8, wet half):

  `A8 = A8_dsn·(W7/W6)·√(R7Tt7/R6Tt6)·Γ(γ6)/Γ(γ7)·(1 − dPqP_dry)/(1 − dPqP)`

  `Γ(γ)` is the choked flow function. The factor is exactly 1 dry.
  Lighting the AB leaves W and Pt6, and therefore the gas generator, where
  dry put them at that flight condition. That is the model's analogue of the
  F404 holding N1 and T5.6 through the AB range.
- **No dry A8 opening yet.** The dry half of #8 waits for #25 and #30 (see
  [Dry schedule](#the-dry-a8-schedule-is-blocked-on-calibration)). The OD
  BPR upper bound stays at 1.0.
- **Calibration.** `MAX_Tt7` = 3598.35 R gives 17,700 lbf at SLS max AB,
  down from 3608 R. The wet sweep's default grid moves with it, to
  3598.35 − 200k R. Combustion efficiency (#35) will move it again:
  pyCycle's Combustor burns all the fuel it is given.
- **The sweep sets the mode by command.** A dry sweep sets `Tt7_cmd = 0` and
  throttles Tt4. A wet sweep holds Tt4 at mil and throttles `Tt7_cmd`.
  `run_sweeps` restarts each mode from the SLS max-AB state that
  `build_problem()` leaves.

## Options considered

Two rounds of spikes ran on 17–18 Oct 26. The first (B) fixed the topology
and kept A3b's physics as far as possible. The second (C) replaced the loss
and the A8 law on that topology.

| | Topology | Augmentor dPqP | A8 law | Dry schedule |
|---|---|---|---|---|
| A0 | ADR-0001 A3b: `OD_dry` Duct, `OD_wet` Combustor | 0 dry / 0.054 wet | DESIGN A8 dry; Rline 2.0 wet, on separate points | — |
| B1 | One `OD`, Combustor, FAR_ab ≥ 0 | `K_hot(τ−1)`, `K_hot` = 0.0385 fitted to 0.054 at max AB | hard switch at `Tt7_cmd > Tt6`: DESIGN A8 → Rline 2.0 | — |
| B2 | as B1 | as B1 | `a8_ctrl` residual blended over 100 R: DESIGN A8 → Rline 2.0 | — |
| B3 | as B1 | as B1 | as B2, from A8_dsn·√τ | — |
| C1 | as B1 | Kumar | as B3 | — |
| C2a | as B1 | as B1 | choked continuity, explicit | none (f_open = 1) |
| C2b | as B1 | as B1 | as C2a | dry A8 opened to 1.6× toward idle |
| **C3** | as B1 | **Kumar** | **choked continuity, explicit** | **none** (f_open = 1, adopted) |

### Round B: the topology

**B1 has no solution just above light-off** wherever dry-mil Rline is not
2.0. The hard switch moves the gas generator, and with it Tt6. At
2500 ft / −20 R it raises Tt6 from 1501.6 to 1516.2 R. For any command
between the two, "wet" puts Tt6 above the command and "dry" puts it below,
so Newton hits its 50-iteration limit. B2 blends the two laws, but holding
the bare DESIGN throat while heat is added dips the fan (Rline 1.975, BPR
−1.0 % mid-blend at SLS). B3's √τ term opens A8 for the hotter gas and cuts
that excursion by about 6×.

Study grid: alt {0, 2500, 5000} ft × dTs {0, ±20} R × 4 throttles, 36 points
per mode, MN 0.001.

| | A0 | B1 | B3 |
|---|---|---|---|
| Dry converged / 36 | 35 | 35 | 34¹ |
| Wet converged / 36 | 36 | 36 | 36 |
| OD points | 2 | 1 | 1 |

¹ B3 loses dry 2500 ft / −20 R / 3100 R. Its residuals are identical to
B1's, because at s = 0 the extra `a8_ctrl` partials are exact zeros.
Removing only those declarations recovers the point. The cause is SuperLU's
pivot order, not physics. The corner sits at fan Rline 2.15 on a cold day
and is marginal (#3).

**B3 against A0, full envelope (132 points per mode):** the same 118 dry and
100 wet points converged. The dry deck was unchanged to 2.7e-5 %. In the wet
deck, Fn moved −0.05…+0.61 % and A8 −1.71…+0.12 %, all from the continuous
loss; the gas generator stayed within 8e-4 %. B3 proved the topology. Its
physics were still A3b's: a fitted loss and an Rline target that moves the
gas generator at light-off.

### Round C: the loss and the nozzle law

#### Augmentor-loss constants (literature)

The sources are collected under #33.

| | Value | Basis |
|---|---|---|
| Flameholder approach Mach | 0.20–0.36 | RM12 rig (ICAS-90-5.3.4, Fig. 5, graph read) |
| C_D | 0.6–0.7 at 29–31 % blockage | Kumar 1980 Eq. 5 (K = 4, n = 0.5); NASA RM E54C30 / E53J14 cold losses of 1–3 % at M 0.2–0.3 |
| η (momentum) | ≈ 1–1.3 | NASA RM E57C01 Fig. 12 (inferred); small-M Rayleigh gives 1 |
| Cold loss, model | 2.10 % (DESIGN), 2.09–2.13 % across the envelope | |
| Hot loss at SLS max AB, model | 6.6 % (against the fixed 5.4 %) | |

The model's station Mach numbers are not the flameholder Mach. MN6 = 0.446
is the mixer-duct exit, and 0.1025 is the augmentor *exit* station. Using
either directly gives a cold loss of about 6 % or about 0.3 %, which is why
the formula needs `k_M`. With literature constants and no tuning, SLS max AB
came out at 17,732 lbf at 3608 R: +0.18 %, which the 10 R recalibration
removes.

#### Study grid (full precision)

| | A0 | B3 | C1 | C2a | C2b | C3 |
|---|---|---|---|---|---|---|
| Dry / 36 | 35 | 34 | 35 | 35 | 35² | 35² |
| Wet / 36 | 36 | 36 | 36 | 32³ | 32³ | 32³ |

² With the OD BPR upper bound raised to 2.0 for the dry schedule (see below).
³ All four lost points are at 5000 ft / −20 R. Dry mil itself fails at that
corner in every variant, A0 included. The choked law keeps the wet gas
generator at the dry operating point, so wet inherits the failure. A0 and B3
converge there only because the Rline-2.0 hold moves the gas generator to a
different operating point.

**% vs A0, max |%| over matched points:**

| | Dry Fn | Dry TSFC | Dry W | Wet Fn | Wet BPR | Wet A8 | Wet fan Rline |
|---|---|---|---|---|---|---|---|
| B3 | 1.8e-5 | 2.2e-6 | 1.1e-5 | 0.57 | 3.9e-6 | 1.71 | 0 |
| C1 | 0.59 | 1.27 | 0.63 | 0.75 | 1.9e-4 | 2.21 | 0 |
| C2a | 1.6e-5 | 1.9e-6 | 1.0e-5 | 0.55 | 3.89 | 2.85 | 7.05 |
| C3 (f_open 1.6) | 2.25 | 1.84 | 9.63 | 0.68 | 3.43 | 4.1 | 6.2 |

- C2a's dry deck is A0's (≤ 2.4e-5 %). It also recovers the dry point that
  B3 lost, because dry no longer carries an `a8_ctrl` state.
- C2a/C3 wet BPR and Rline move because A0's Rline 2.0 is gone. When wet, the fan
  now sits on the dry-mil line for that condition: Rline 1.96–2.14, with fan
  SMN 15.8–22.5 against A0's 12.1–23.5. Max-AB A8 becomes nearly
  independent of flight condition (327–333 in²).

#### Light-off continuity (spike walks)

Each walk is warm-started at MN 0.001 at three conditions. Dry runs
Tt4 2500 → 3100 R. The wet walk runs `Tt7_cmd` = Tt6 + {0.5 … 150} R, then up to max
AB. Values are % vs dry mil at that condition.

| | Light-off step (Tt6 + 0.5 R) | Worst within Tt6…Tt6 + 150 R: W / BPR / N1 / Rline | Max AB at 2500 ft / −20 R: BPR / N1 |
|---|---|---|---|
| B3 | ≤ 0.02 % | 0.42 % / 3.90 % / 0.78 % / 0.148 | −3.90 % / −0.78 % |
| C1 | ≤ 0.02 % | 0.38 / 3.56 / 0.71 / 0.134 | −3.56 / −0.71 |
| C2a | ≤ 0.02 % | 0.03 / 0.13 / 0.02 / 0.004 | −0.16 / −0.03 |
| C3 | ≤ 0.02 % | 0.03 / 0.15 / 0.03 / 0.006 | −0.25 / −0.05 |

No variant had a wet failure at any condition. Every step took at most 4
Newton iterations, and Fn rose monotonically in both Tt4 and `Tt7_cmd`. The
choked law takes the gas-generator shift through light-off from 3.9 % BPR
to 0.15 %. What remains comes from the ideal-gas Γ(γ) in the formula, not
from the topology.

### The dry A8 schedule is blocked on calibration

C2b/C3 opened the dry A8 with Tt4/Tt4_mil, by a smoothstep from 1 at
r = 0.9 to `f_open` = 1.6 at r = 0.6. The 1.6 comes from F404 data: about
400 in² at idle (GE model) against about 249 in² at mil (GE IFT). Three
findings:

1. **It failed at Tt4 = 2500 R on the OD BPR bound (1.0), not on physics.**
   Opening A8 at a fixed Tt4 raises BPR (0.946 → 1.121 at f_open 1.6, SLS).
   With the bound raised to 2.0 the full opening converges.
2. **The model's part-power BPR (~0.95) is nearly 3× the published F404's
   (0.34).** Any dry A8 opening amplifies that error: W +9.6 %, BPR +20 % and
   Fn +3.6 % at 2500 R on the grid.
3. **Opening A8 at a fixed Tt4 *raises* fan Rline here (2.02 → 2.17).** The
   real schedule does the opposite. Below mil the F404 commands N2, not Tt4,
   so the model's dry throttle variable is the wrong one for this question.

The dry half of #8 therefore belongs with #25 (part-power and BPR
calibration) and #30 (dry command = N2), not with this refactor.

## Result

The adopted model, as merged, against ADR-0001's (A0). Full default envelope:
132 points per mode, MN 0.001.

| | A0 | C3, adopted |
|---|---|---|
| Dry converged / 132 | 118 | **120** (+2: 2500 ft / +40 R and 5000 ft / +50 R at Tt4 2500 R; none lost) |
| Wet converged / 132 | 100 | **95** (−5, all at dTs −20 R: the four 5000 ft points and 2500 ft at the third T7 level) |
| SLS dry mil W / TSFC | 144.18 lbm/s / 0.6200 | 145.09 lbm/s / 0.6240 |
| SLS max AB Tt7 / dPqP / A8 | 3608 R / 0.054 / 326.9 in² | 3598.35 R / 0.066 / 332.1 in² |

**Dry deck vs A0, % (118 matched points):** Fn −0.63…+0.14, TSFC
+0.59…+1.30, W +0.35…+0.63, BPR −0.67…0, A8 +2.55 at every point (the DESIGN
throat grows with the cold loss), LP spool −0.14…0. The augmentor cold loss
is 2.09–2.13 % everywhere.

**Wet deck vs A0, at A0's T7 grid (3008–3608 R, 95 matched points), %:** Fn
−0.99…+0.68, BPR −4.2…+3.4, A8 −2.8…+4.1, W −1.1…+1.0, fan SMN −9.8…+13.6.
Fan Rline is now 1.94–2.12, where A0 held 2.000 everywhere. The fan follows
its dry-mil line at each condition instead.

**Light-off walks** (warm-started at MN 0.001; % vs dry mil at that
condition):

| Condition (dry-mil Rline) | Step at Tt6 + 0.5 R: W / BPR / N1 / A8 | Worst within Tt6…Tt6 + 150 R: W / BPR / N1 / ΔRline | Max AB: Fn / BPR / N1 / A8 | Failures / max Newton iterations |
|---|---|---|---|---|
| SLS, std day (2.000) | 0 / 0 / 0 / +0.02 | 0.03 / 0.11 / 0.01 / 0.003 | +60.7 / −0.24 / −0.03 / +72.5 | 0 / 4 |
| 5000 ft, +20 R (1.986) | 0 / 0 / 0 / +0.02 | 0.03 / 0.12 / 0.01 / 0.003 | +60.7 / −0.07 / −0.01 / +72.5 | 0 wet / 4 |
| 2500 ft, −20 R (2.133) | 0 / 0 / 0 / +0.02 | 0.02 / 0.15 / 0.03 / 0.006 | +61.0 / −0.26 / −0.05 / +72.4 | 0 / 4 |

B3, for reference, at 2500 ft / −20 R: worst 0.42 / 3.90 / 0.78 / 0.148 and
max-AB BPR −3.90 %. Fn rises monotonically through the dry walk and through
light-off to max AB at all three conditions.

**Why the counts moved.** Both changes are warm-start path effects at
marginal corners, not new physics limits. A 12-point hot-day dry probe
(0/2500 ft, dTs +30…+50 R, Tt4 2500/2700 R) converged 12/12 for B3, C1
and C2a alike: the topology, the Kumar loss and the nozzle law each solve
there. The full-envelope counts, ±5 points,
measure the snake path as much as the model (#3, #27). The wet cold corner
is different. Dry mil fails at 5000 ft / −20 R in every variant, A0
included. The nozzle law keeps the wet gas generator at that dry operating
point, so wet now inherits the failure. A0 converged there only because the
Rline-2.0 hold moved the gas generator to a different operating point.

## Trade-off analysis

- **C3 against A0.** One OD point and one topology, which is what a
  time-marched transient needs. A0's light-off is a state hand-off between
  two models. The machinery for freezing the inactive OD point goes:
  `SweepRunner(frozen_pts=...)`, `_FROZEN_NEWTON`, `_OD_WET_BOUNDS`, and the
  `afterburn` switch in `extract_od_results`. So does the `a8_ctrl` Newton
  state.
- **C3 against B3.** Same topology. C3 has no blend width to choose and no
  extra Newton state. The gas generator ignores the afterburner at every
  condition, where B3 still moved it by up to 3.9 % BPR. The loss constants
  come from the literature, where B3's was fitted.
- **What C3 costs.** The cold loss applies to DESIGN, so the sizing and the
  dry deck move: W +0.63 % and TSFC +0.6 % at SLS mil (0.6200 → 0.6240, in
  the right direction for the published 0.78). Wet loses the cold corner
  where dry mil has no solution. That corner is #3's to fix, and it is now
  one problem rather than two.
- **ADR-0001's light-off growth-path note is reversed.** ADR-0001 modelled
  light-off as a discrete switch because real ignition needs a minimum stable
  FAR. Here, a minimum stable FAR or a blow-out limit becomes a constraint on
  `Tt7_cmd` (a floor on wet FAR_ab), set by the controller. It is no longer
  a topology change.

### Minimum stable augmentor fuel-air ratio

No published F404 value turned up in the papers collected for #33 or in
`docs/unclassified_perf_data/`.

- 1950s single-zone afterburners on JP-4 blow out lean at an overall f/a of
  about 0.03–0.06. The limit rises as pressure falls and velocity rises
  (NASA RM E53J14, E54C30).
- The F404 is piloted and zoned: pilot spraybars feed a vaporizer-fed gutter
  ring, and the RM12 CFD set local f/a stoichiometric. It therefore lights and
  holds at a leaner *overall* f/a than those rigs.
- NASA TN D-6839 (the TF30's zone-1 pilot) gives f/a ≈ 0.006 on unburned
  air, which is the basis for a later floor of about 0.005.
- The model's lowest default wet point (Tt7 ≈ 3000 R) runs FAR_ab ≈ 0.025 at
  every condition tested.

## Consequences

### Code
- `MixedFlowTurbofan`: the afterburner type follows `design`, so the
  `afterburn` option is gone. Both points get `aug_ctrl`. OD also gets
  `a8_sched`, whose `A8` feeds `balance.rhs:W`, and a FAR_ab balance with
  lower bound 0 and target `aug_ctrl.Tt7`.
- `MPMixedFlowTurbofan.od_pts` becomes `od_pt = 'OD'`. The DESIGN throat
  feeds `OD.a8_sched.A8_dsn`. The loss constants are cycle parameters on
  both points.
- `build_problem()` solves OD at SLS mil (`Tt7_cmd = 0`), then at SLS max AB
  warm-started from it, and returns the problem at max AB.
- `SweepRunner` sets `aug_ctrl.Tt7_cmd` (0 dry). `_OD_BOUNDS` carries FAR_ab
  with no lower check: 0 is the dry solution, and a wet point pinned at 0
  fails `_target_met`.
- Both components have analytic partials, checked against complex step.

### Decks
- Both decks are regenerated (see [Result](#result)). The wet deck's T7
  levels move with `MAX_Tt7`, to 3598.35 − 200k R, so a wet `f404 compare`
  against an older deck needs a sweep on the old grid
  (`--throttle 3008,3608,200`).

### To revisit
- **`k_M` and `C_D`**, against F404 data if any surfaces.
- **The Γ(γ) approximation** in the nozzle law. Using the nozzle's own
  throat state, or a real-gas Γ, would take the residual 0.1–0.25 % BPR to 0.
- **A minimum wet FAR_ab** (~0.005, TN D-6839) as a floor on `Tt7_cmd`.
- **Combustion efficiency (#35).** It will move the `MAX_Tt7` calibration.
- **The dry A8 schedule** with #25 and #30, including the OD BPR bound
  (1.0), which any dry A8 opening reaches at part power.
- **The cold corner** (5000 ft / −20 R), where dry mil and now wet fail (#3).
