# scripts/

Helpers for first-time setup. Currently only the data-download wrapper:

- **`download_data.sh`** (macOS / Linux) and **`download_data.ps1`** (Windows PowerShell) — fetch the ~3 GB of large data files (Lib4 reference, per-construct metadata, full alignment count tables) from this repository's GitHub release (`library-data-2026-05-04`) and place them at the canonical paths the pipeline and R scripts expect. Idempotent: safe to re-run; skips files already in place.

Adopters running TREND on their own data via Path B (Conda) or Path C (Manual install) need to run this once. **Path A (Docker) users do not need this** — the Docker image bakes the Lib4 reference in, and the dashboard's *Reproduce this analysis* button fetches the per-project count tables on demand from the same GitHub release.

For the full install paths and what each one needs, see the top-level [`README.md`](../README.md) and [`MANUAL.md`](../MANUAL.md).
