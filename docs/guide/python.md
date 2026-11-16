# Python guide

Size the engine and run it at off-design (OD) conditions from Python, without
the CLI. The `f404` command is built on these same functions, so they produce
the same numbers. Design decisions are in
[ADR-0005](https://github.com/Jhawk414/F404/blob/main/docs/adr/0005-public-python-api.md).

```python
from f404 import DesignInputs, design, run_point, sweep

eng = design(DesignInputs(hpc_PR=7.0, hpc_cool1_frac_W=0.04))   # ~3 s
row = run_point(eng, mode='dry', alt=5000, mach=0.8, dts=-30, throttle=2700)
row['Fn'], row['TSFC'], row['converged']

dry = sweep(eng, mode='dry', mach=[0.001, 0.4, 0.8], alt=[0, 5000], dts=0)
dry[dry.converged].to_csv('my_deck.csv', index=False)
```

## `DesignInputs`

Everything that sizes the engine at sea-level-static (SLS) dry mil. Every
field has a default; together they are the calibrated F404. Set only what
you want to change.

| Field | Default | Meaning |
|---|---|---|
| `fn_target` | 11000 | SLS dry mil thrust, lbf; sets the airflow |
| `mil_Tt4` | 3100 | Core burner exit temperature at mil, R |
| `max_Tt7` | 3607.68 | Afterburner exit temperature at max AB, R |
| `fan_PR`, `hpc_PR` | 4.1, 6.5 | Design pressure ratios |
| `fan_eff`, `hpc_eff`, `hpt_eff`, `lpt_eff` | 0.8948, 0.8707, 0.8888, 0.8996 | Design efficiencies |
| `LP_Nmech`, `HP_Nmech` | 10000, 14000 | Design spool speeds, rpm |
| `ram_recovery` | 0.999 | Inlet total-pressure recovery |
| `inlet_duct_dPqP`, `splitter_core_duct_dPqP`, `hpt_duct_dPqP`, `lpt_duct_dPqP`, `bypass_duct_dPqP`, `mixer_duct_dPqP` | 0.0107, 0.0048, 0.0051, 0.0107, 0.015, 0.0107 | Duct total-pressure loss fractions |
| `hpc_cool1_frac_W` | 0.050708 | HPC bleed to the LPT, fraction of HPC flow |
| `bld3_cool3_frac_W` | 0.11 | HPC exit bleed to the HPT, fraction of HPC flow |
| `HPX` | 250 | HP shaft power extraction, hp |

Validation happens when the model is built, before any solve. Pressure
ratios must exceed 1, efficiencies and `ram_recovery` lie in (0, 1], loss and
bleed fractions in [0, 1), and the targets must be positive. Unknown fields,
NaN, inf and strings are rejected. A `pydantic.ValidationError` (a
`ValueError`) names every bad field at once. The model is frozen: build a new
one to change a value.

`max_Tt7` may be below `mil_Tt4`; it must exceed the SLS-mil augmentor inlet
temperature (about 1500 R), which `design()` checks after the dry solve. Its
default is calibrated to 17,700 lbf for the default engine only. A re-sized
engine's max AB is uncalibrated.

Each field name is its model path with `.` and `:` replaced by `_`.
`f404.problems.DESIGN_INPUT_PATHS` maps each field to its path and units, for
`prob.get_val()` or `compute_totals()`.

## `design(inputs=DesignInputs(), *, verbose=False)`

Sizes the engine, solves OD at SLS dry mil and then at SLS max AB, and returns
an `Engine`:

- `eng.prob`: the solved `openmdao.api.Problem`; the OD point is
  `eng.prob.model.od_pt` (`'OD'`).
- `eng.inputs`: the `DesignInputs` it was sized from.
- `eng.anchor`: the OD state at SLS max AB that every OD call starts from.

`verbose=True` prints Newton iterations and the result tables, as
`f404 design` does. A solve that doesn't converge raises
`openmdao.api.AnalysisError`; a `max_Tt7` that leaves the afterburner dry
raises `f404.problems.MaxTt7TooLowError` (a `ValueError`).

Treat an `Engine` as fixed. To change the design, call `design()` again;
setting a design value on `eng.prob` directly leaves `inputs` and `anchor`
stale.

## `run_point(engine, *, mode, alt, mach, dts, throttle, verbose=False)`

Solves one OD condition and returns its deck row as a dict.

- `mode`: `'dry'` (afterburner off; `throttle` is Tt4, R) or `'wet'`
  (`throttle` is Tt7, R; Tt4 held at the engine's `mil_Tt4`).
- `alt` ft, `mach` below 1 (0 is flown at 0.001), `dts` R off ISA.

Every call restores the anchor and bridges from SLS to the point, as a sweep
reaches its first point, so earlier calls don't steer the result. (Solver
state outside the model's vectors can still carry over, moving results by
about 1e-5 after long call histories;
[#59](https://github.com/Jhawk414/F404/issues/59).) A
point that fails is returned, not raised: `converged` is False, the outputs
are NaN, and `failure` says why. When the point converged, `eng.prob` is left
solved there, so you can read any other variable or call
`eng.prob.compute_totals()`. After a failure it is not at a solution.

The keys are the deck columns: `INPUT_COLUMNS`, `DECK_COLUMNS` and `failure`
from `f404.sweep_utils`. `DECK_COLUMNS` maps each output to its OD model path
and units.

## `sweep(engine, *, mode, mach, alt, dts, throttle=None, out_dir=None, verbose=False)`

Sweeps one mode over a grid and returns a `pandas.DataFrame`, one row per
point with failed points included, in the same columns as the committed decks.

- Each axis takes a number, a list, or a `'min,max,step'` range string, with
  the same rules as the YAML run file: Mach and altitude ascending; dts
  non-negative ascending, then negative descending; throttle descending. An
  out-of-order list raises `ValueError`; a range string is put in order for
  you.
- `throttle` defaults to four levels 200 R apart down from the engine's
  `mil_Tt4` (dry) or `max_Tt7` (wet). For the default engine these are the
  committed grids.
- `mach`, `alt` and `dts` default to the committed grid.
- `out_dir` writes `cycle_deck_<mode>.csv` there; by default nothing is
  written.

The sweep visits points in snake order (throttle, then Mach, altitude and
dts), warm-starting each from the last and bridging large jumps, as the CLI
does. It starts from the anchor, so two calls with the same arguments give the
same deck, up to the solver state noted under `run_point()` (#59).

## Performance and parallel use

`design()` takes about 3 s; a point takes 1–4 s. Each `Engine` owns one
OpenMDAO Problem and isn't thread-safe. For parallel studies use processes,
one engine per process.
