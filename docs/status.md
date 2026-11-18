# Convergence status

Latest full-envelope sweep (`--mode both`, OpenMDAO 3.39.0): 792 points per mode
on the one sized engine, with DESIGN and OD at the same static Mach 0.001
([#37](https://github.com/Jhawk414/F404/issues/37)). Each mode takes about 35
min, and dry and wet run in parallel.

| Mode | Converged | Throttle sweep |
|---|---|---|
| Dry | 643 / 792 | Tt4 3100 → 2500 R |
| Wet | 663 / 792 | Tt7 3607.68 → 3007.68 R (Tt4 fixed at 3100 R MIL) |

Converged by Mach, out of 132 points per cell:

| MN | 0.001 | 0.2 | 0.4 | 0.6 | 0.8 | 0.95 |
|---|---|---|---|---|---|---|
| Dry | 120 | 118 | 120 | 115 | 97 | 73 |
| Wet | 95 | 100 | 120 | 128 | 120 | 100 |

At SLS standard day, static to M 0.95, dry mil Fn falls from 11,000 to 9,224 lbf.
Max AB Fn runs from 17,700 to 18,792 lbf, with a minimum of 16,899 lbf at M 0.4.

## Decks

[`deck/cycle_deck_dry.csv`](../deck/cycle_deck_dry.csv) and
[`deck/cycle_deck_wet.csv`](../deck/cycle_deck_wet.csv) hold one row per requested
point at full float64 precision. A failed row has blank outputs (`NaN` in pandas),
so the counts above are `df.groupby(['mode', 'MN']).converged.sum()`. The columns
are `INPUT_COLUMNS` and `DECK_COLUMNS` (both in `sweep_utils.py`), then `failure`.

## Where the failures are

Tracked in [issue #3](https://github.com/Jhawk414/F404/issues/3) and readable from
the `failure` column:

- **Dry part power (Tt4 2500 R) gets worse with Mach.** BPR climbs toward its 1.0
  bound ([#25](https://github.com/Jhawk414/F404/issues/25)). Only 3 of 33 points
  converge at M 0.95.
- **Dry and wet mil fail on the cold side (dTs < 0).** Wet fails where dry mil
  does, because the A8 law holds the wet gas generator at the dry-mil operating
  point. The one exception is 2500 ft, static, dTs −20 R, T7 3007.68 R, where dry
  mil converges.
- **Airflow ceiling.** One cold-day point at M 0.95 hits the 200 lbm/s OD airflow
  bound. Six did before #37 sized the engine 0.4% smaller
  ([#38](https://github.com/Jhawk414/F404/issues/38)).

## Change from the pre-#37 decks

Those decks were sized at Mach 0.01. Against them, dry points and wet points at the
same T7 have thrust, airflow and A8 0.40% lower. TSFC and BPR move by under 0.01%.
The default wet grid also moved up 9.33 R, so its levels compare at 0.16–0.26%
lower thrust and 0.20–0.30% higher TSFC.
