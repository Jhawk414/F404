# ADR-0004: `f404 verify`, a tolerance-based install check

**Status:** Proposed
**Date:** 2026-11-15
**Deciders:** @Jhawk414
**Issue:** [#53](https://github.com/Jhawk414/F404/issues/53). Also serves
[#47](https://github.com/Jhawk414/F404/issues/47), whose refactor must keep
results unchanged.

## Context

A user or agent who clones the repo or downloads the DOI release zip has no
quick way to confirm the install reproduces the model. The full suite takes
about 3 min and needs the repo's `tests/`; the decks take hours. #53 asks for a
command that solves DESIGN, OD at SLS dry mil and OD at SLS max AB, compares a
few outputs with committed values, prints the library versions, and exits
non-zero on a mismatch. Four questions follow: how to compare, how tight, how
to read the dry-mil point that `build_problem()` overwrites when it goes wet,
and where the reference lives. #53 also leaves three options open: `--json`,
`--extended` and a SHA-256 fingerprint.

Two forces shape the tolerance. Too loose, and a real change to the cycle
passes. The existing goldens in `tests/problems_test.py` use 1e-4, which on a
100,000 lbf engine is ±10 lbf. Too tight, and the check fails on a platform
where the solver lands on a slightly different point inside its own
convergence tolerance (OD Newton `atol` 1e-5, `rtol` 1e-9, `engine_model.py`).

### Measurement

A throwaway spike ran `build_problem()` (DESIGN, dry mil, max AB) and read 17
deck quantities at each point. Reference environment: Python 3.9.6, OpenMDAO
3.39.0, NumPy 2.0.2, SciPy 1.13.1, macOS arm64.

| Comparison | Max relative difference |
|---|---|
| 3 separate processes and 3 repeats in one process | 0 (bit-identical) |
| Python 3.12, OpenMDAO 3.45.2, NumPy 2.5.5, SciPy 1.18.1, same machine | 5e-14 |
| DESIGN vs OD dry mil (same SLS condition) | 1.4e-8 |
| OD dry mil re-solved warm from max AB vs dry mil inside `build_problem()` | 3.3e-6 (OPR), 2.1e-6 (Fn), 1.8e-6 (BPR) |

The last row is the solver-path floor: the same point reached from a different
starting state differs at the size of Newton's tolerance. Library versions
barely move the answer; the solve path does.

What each tolerance can see, from perturbing the three design targets:

| Perturbation | Response |
|---|---|
| `fn_target` +1e-4 (+1.1 lbf) | Fn, Fg, W, A8, fuel flow +1e-4 exactly; TSFC, BPR, FAR, PRs unchanged (≤ 4e-14) |
| `mil_Tt4` +1e-6 (+0.003 R) | BPR 5.9e-6, FAR_core 2.1e-6, hpt/lpt PR 1.2e-6, TSFC 2.7e-7 |
| `max_Tt7` +1e-4 (+0.36 R) | max-AB FAR_ab 2.1e-4, TSFC 9.6e-5, A8 7.3e-5, Fn 6.0e-5 |

Thrust, airflow, A8 and fuel flow scale together with engine size, so a
tolerance on them is a tolerance on size; BPR is the most sensitive single
indicator of a change inside the cycle. `build_problem()` takes 2.5 s.

## Decision

Add `f404 verify [--json]`:

- It runs `build_problem(verbose=False)` and reads OD at SLS dry mil through a
  new optional `on_mil(prob, od)` callback, called after the dry solve and
  before going wet.
- It checks Fn, TSFC, BPR, W, A8, T4 and T7 at DESIGN, SLS dry mil and SLS max
  AB (21 checks) against `src/f404/verify_reference.json`, shipped as package
  data, with relative tolerance **1e-6**.
- It prints Python, OpenMDAO, NumPy, SciPy and platform, one row per check
  (value, expected, relative difference, PASS/FAIL) and a summary. `--json`
  prints `{passed, rel_tol, versions, checks: [{point, quantity, value,
  expected, rel_diff, ok}]}` instead.
- Exit 0 when every check passes; 1 when any fails or the solve does not
  converge (as `f404 design`); 2 for usage errors.
- The fast PR CI job runs `f404 verify`; a `slow` test runs it on the full
  matrix (Ubuntu 3.9/3.12, macOS 3.12).

At 1e-6 the bands are Fn ±0.011 lbf at 11,000 lbf and ±0.018 lbf at 17,700
lbf (±0.1 lbf on a future 100,000 lbf engine), A8 ±0.0003 in², T7 ±0.004 R and
W ±0.00015 lbm/s. That is more than 1e7 above the version drift measured, and
below the 2e-6 solver-path floor, so a change in solve path (#47) shows up
rather than hiding.

### Checks

| Quantity | Why |
|---|---|
| Fn | #53; a balance target at DESIGN, an output at max AB |
| TSFC | #53; fuel and thrust together |
| BPR | #53; most sensitive to a change inside the cycle |
| W | #53; engine size and airflow |
| A8 | #53; the DESIGN throat and the wet A8 law |
| T4 | combustor exit; a balance target, so it checks the balance |
| T7 | aft: mixer exit (dry), afterburner exit target (max AB) |

Left out: Fg (Fn plus a ram drag of about 0 at Mach 0.001), and FAR_ab and
Wf_ab, which are 0 when dry and so can't be tested with a relative tolerance.

### #53 open options

| Option | Answer |
|---|---|
| `--json` | Included. The exit code alone carries no detail for an agent. |
| `--extended` | Deferred. See "To revisit". |
| SHA-256 fingerprint | Deferred, and never the pass/fail test. Rounding to 6 significant figures can still flip a digit at a rounding boundary on a 1e-14 difference, so a correct install could report a different hash. |

## Options considered

### How to compare

#### Option A: committed reference values with a relative tolerance (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | Low: one JSON file and a comparison |
| Cost | 2.5 s solve |
| Robustness | Survives last-digit platform differences |
| Familiarity | Same idea as the golden tests |

**Pros:** works after a plain `pip install`; diagnoses which quantity moved
and by how much. **Cons:** the tolerance is a judgment, revisited with data.

#### Option B: SHA-256 of rounded outputs

**Pros:** one citable string per release. **Cons:** rounding-boundary flips
make it fail on correct installs; a mismatch says nothing about what moved.

#### Option C: run the golden tests

**Pros:** no new reference. **Cons:** `tests/` does not ship in the package;
needs pytest; the goldens' 1e-4 is too loose for this purpose.

#### Option D: a mini-deck compared with `f404 compare`

**Pros:** reuses the comparison code. **Cons:** a sweep is slower and pulls in
warm-start order; #53 asks for expected values, not a deck.

### Tolerance

| Option | Assessment |
|---|---|
| Relative 1e-4, as the goldens | Rejected: passes a 1.1 lbf sizing shift; ±10 lbf at 100,000 lbf |
| Relative 1e-6, uniform (chosen) | 1e7 margin over measured drift; catches a 0.003 R Tt4 shift via BPR |
| Relative 1e-8 or tighter | Rejected: below the 1.4e-8 DESIGN/OD agreement; no margin if a platform takes one more Newton step |
| Relative plus absolute | Rejected: every checked value is far from 0 |
| Per-quantity tolerances | Not needed today; the file format allows one later if CI data demands it |

### Reading SLS dry mil

| Option | Assessment |
|---|---|
| `on_mil` callback in `build_problem()` (chosen) | One optional argument; reads the point on the solve path the model already uses, which #47 can keep |
| Re-solve dry mil after `build_problem()` | Rejected: differs by 3e-6 from the dry mil solved on the way, so the reference would encode a warm-start path |
| Use DESIGN for dry mil | Rejected: skips the DESIGN-to-OD hand-off #53 asks to check |

### Reference format

| Option | Assessment |
|---|---|
| JSON package data, read with `importlib.resources` (chosen) | Language-neutral; agents can read it; as #53 asks |
| Python constants module | Rejected: #53 asks for package data, and values are data |
| YAML | Rejected: no gain over JSON, which needs no dependency |

## Trade-off analysis

The tolerance trades false failures against missed changes. The spike puts
version drift at 5e-14 and the solver-path floor at 2e-6, so 1e-6 sits in a
wide gap: tight enough that a material change to the cycle fails, loose enough
for bit-level platform noise. The one unmeasured case is Linux x86_64, whose
BLAS/LAPACK differ; if it took a different number of Newton steps, it could
land near the path floor. The full CI matrix measures that before this ADR is
accepted, and only the affected quantities would be loosened, to 1e-5.

The `on_mil` callback adds one argument to `build_problem()`. Re-solving
afterwards would need no model change, but the reference would then depend on
the warm-start path, which #47 is free to change.

## Consequences

- Anyone can check an install in about 3 s, and bug reports carry versions.
- #47 gets a quick check that its refactor keeps results unchanged.
- A deliberate change to the model's results also needs a regenerated
  `verify_reference.json`, in the same PR, explaining why the numbers moved.
  Regenerate from the `value` fields of `f404 verify --json`.

### To revisit

- `--extended`: 5–10 OD points across Mach and altitude, dry and wet, kept
  away from the cold side (dTs < 0), M 0.95 and Tt4 2500 R, which fail today
  (#3, #25), so the check is not flaky.
- A release fingerprint, if a DOI release wants one, as information only.
- The tolerance, if a platform outside the CI matrix fails at 1e-6.

## Action items

1. [ ] `on_mil` callback in `build_problem()`
2. [ ] `src/f404/verify.py`, `verify_reference.json`, `package_data`
3. [ ] `f404 verify [--json]`, listed in `f404 --help`
4. [ ] Tests: perturbed reference fails with exit 1; slow end-to-end run
5. [ ] `f404 verify` in the fast CI job
6. [ ] README "Verify your install", CLI guide
7. [ ] Record the CI matrix differences here and mark Accepted
