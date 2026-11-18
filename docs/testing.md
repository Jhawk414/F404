# Testing

```bash
pytest tests                    # full suite, ~3 min
pytest tests -m "not slow"      # structural and unit tests only, ~7 s
```

`pytest` needs no prior install. `pythonpath` in `pyproject.toml` puts `src/`
on the path.

## Layout

Each module has one `tests/<module>_test.py` ([#5](https://github.com/Jhawk414/F404/issues/5)).
Tests marked `slow` build and solve a full `om.Problem`. The rest call pure
functions or build a model without solving it. The golden baselines and the
convergence regressions are all `slow`.

## CI

CI is defined in [`.github/workflows/f404_test_workflow.yml`](../.github/workflows/f404_test_workflow.yml)
([#31](https://github.com/Jhawk414/F404/issues/31)).

| Trigger | What runs |
|---|---|
| Pull request to `main` | `f404 verify` and the fast tests (`-m "not slow"`) on Ubuntu, Python 3.12, about a minute |
| Push to `main`, manual dispatch, or a PR with the `full-ci` label | The full suite on Ubuntu (3.9, 3.12) and macOS (3.12) |

The maintainer adds the `full-ci` label when a PR is about to merge. Labelling a
PR skips the fast job and starts the full suite.

The driver and CLI are importable and covered. The remaining gaps are mostly
uncommon input and I/O errors, solver-failure paths and the one-line `__main__`
shims.
