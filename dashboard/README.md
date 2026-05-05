# TREND Dashboard

Local-first web dashboard that wraps the TREND bioinformatics pipeline. Built to solve the universal pain points of manuscript-accessory bioinformatics code: opaque onboarding, hard-coded constants, no provenance, no tiny-example oracle, invisible library composition.

## Quick start (canonical: Docker)

```bash
cd dashboard
docker compose up
# open http://localhost:8000
```

First launch ingests the Lib4 library metadata into SQLite (~30s). Subsequent launches are instant.

## Native development (no Docker)

```bash
cd dashboard
make install          # installs Python backend in editable mode
make ingest           # builds backend/state/library.sqlite from metadata CSVs
make backend          # FastAPI on http://localhost:8000
# in another terminal:
make frontend         # Vite dev server on http://localhost:5173
```

Native dev is best-effort. The container is the canonical runtime — it pins R 3.5.1 to match the manuscript SLURM script (`Lib4_all_steps_FINAL_111525.sbatch:62`).

## Architecture

- `backend/` - FastAPI app + pipeline runner + library service + provenance writer
- `frontend/` - React + TypeScript + Vite + Tailwind + shadcn/ui
- `projects/` - Per-project sample sheets and parameters (ovarian_cancer, T_cell_activation)
- `example_data/` - Bundled fixtures for the install-check oracle
- `runs/` - Run history (provenance manifests)
- `state/` - Generated runtime artifacts (library.sqlite, runs.sqlite, library_summary.json)
