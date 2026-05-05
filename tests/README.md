# tests/

Automated test suite. Run the full set with:

```bash
pytest tests/ -v
```

Subdirectories:

- **`equivalence/`** — equivalence tests. Each test re-runs a step (or the end-to-end pipeline) on a bundled fixture and asserts the produced output is numerically equivalent to the deposited reference. Backed by the shared `csv_compare` predicate at `tests/equivalence/helpers/csv_compare.py`, which is the same predicate used by the dashboard's *Install check* tab.
- **`contracts/`** — schema and contract tests for the dashboard's API surface (request/response shape, error cases). Catch regressions when the FastAPI handlers drift.
- **`cli/`** — `trend` CLI smoke tests. Verify `trend init`, `trend run --example`, and `trend dashboard` invocations do not regress.
- **`e2e/`** — end-to-end orchestration: spin up a dry-run pipeline, inspect the produced manifest, validate state transitions.

Most tests run in seconds; a few of the equivalence tests run R or snakemake and take ~30 sec to ~3 min. `pytest -m "not slow"` skips those.
