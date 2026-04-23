# TREND — Transcription-Factor-Responsive Enhancer Discovery

End-to-end pipeline + interactive dashboard for the TREND enhancer-screening platform described in [the manuscript](#citation). One install, one command per experiment, one folder per result. Runs on a workstation, an HPC cluster, or a Mac/PC laptop — same code, same outputs.

> **Status:** Phase 1 dashboard + v2 CLI / Snakemake workflow / conda packaging are implemented and tested. See `DASHBOARD_PRD.md` and `~/.claude/plans/now-i-want-you-quizzical-mountain.md` for the build plan and decision log.

---

## Data on Dropbox (one-time download for full data)

The repository contains all code plus a small set of bundled fixtures sufficient for verifying the manuscript's claims (28 MB Tier-2 fixtures + 6 MB Tier-3 simulated FASTQs). The **full data** (~3 GB: published alignment count tables + Lib4 reference + per-construct metadata) is hosted on Dropbox and fetched with a one-liner:

```bash
# macOS / Linux
bash scripts/download_data.sh

# Windows
pwsh scripts/download_data.ps1
```

You only need this if you want the full library viewer (2.7 M constructs vs 1,000-promoter subsample) or want to apply TREND to your own samples. **For manuscript verification, the bundled examples are sufficient.** Dropbox URL also linked in `MANUAL.md` § 2.5.

---

## TL;DR — three commands

```bash
# Install (Linux / macOS / WSL2 / HPC head node)
conda install -c bioconda trend-pipeline

# Reproduce a published figure on the bundled tiny example
trend run --example ovarian_cancer

# Visualize any run interactively
trend dashboard
# -> open http://localhost:8000
```

That's the whole product surface for a reviewer or new adopter.

---

## Reviewer's quickstart — three tiers

Three increasingly-rigorous reproducibility checks, runnable on a laptop. Pick the deepest tier whose tools you have installed; the dashboard runs them all from one button (`Verify` page) or from the CLI.

| Tier | What it verifies | Time | Tools needed | Command |
|---|---|---|---|---|
| **1 · Quick check** | Dashboard + comparator wiring | ~1 s | Python only | `trend run --example ovarian_cancer --tier smoke` |
| **2 · Activity reproduction** | Step 9 R script reproduces published OvCa numbers from a 1,000-promoter slice of the real data | ~30 s | R + tidyverse + Rsamtools | `trend run --example ovarian_cancer --tier step9` |
| **3 · Full pipeline reproduction** | Steps 1–9 reproduce expected post-alignment counts from simulated FASTQs (50 promoters × 5 barcodes × 8 samples) | ~3 min | Conda env (`bowtie2 + samtools + cutadapt + fastx-toolkit + R`) | `trend run --example ovarian_cancer --tier pipeline` |

All three emit the same green-badge oracle report (column-by-column, row-by-row CSV diff). Outputs live under `dashboard/example_data/`:

```
dashboard/example_data/
├── ovca_step9/                 # Tier 2 fixtures (~28 MB)
│   ├── inputs/                 # 1,000-promoter subsample of published alignment CSVs
│   │   ├── alignment_result_normalized_in_house_pipeline.csv
│   │   ├── alignment_result_unnormalized_in_house_pipeline.csv
│   │   └── all_enhancer_metadata_111525.csv
│   └── expected/               # 1,000-promoter subsample of published activity CSVs
│       ├── ovca_sensor_activity_result_concise.csv
│       └── ovca_sensor_activity_result_all.csv
└── ovca_pipeline/              # Tier 3 fixtures (~6 MB)
    ├── inputs/
    │   ├── fastqs/             # 8 simulated FASTQ files (~700 KB each, gzipped)
    │   ├── Lib4_tiny.fasta     # 250-construct subset of the Lib4 reference
    │   ├── Lib4_info_tiny.csv
    │   └── barcode_key.xlsx    # for Step 3 demultiplex
    └── expected/
        ├── alignment_result_normalized_in_house_pipeline.csv
        └── alignment_result_unnormalized_in_house_pipeline.csv
```

Fixtures are deterministic — `python tools/build_fixtures.py` regenerates them bit-for-bit. No HPC cluster is required for any tier; everything runs on a single CPU core in seconds (T1, T2) to a few minutes (T3) on a laptop.

---

## Architecture — three loosely-coupled pieces

```
   trend-pipeline           Installable on Linux + HPC.
        │                   Runs Steps 1–9 end-to-end.
        │
        │  emits:  runs/<id>/manifest.json + outputs/*.csv
        ▼
     run manifest           The durable artifact. Records code commit,
        ▲                   software versions, input/output SHA-256s,
        │                   per-step timings, parameters.
        │  reads:
   trend-dashboard          Mac/PC viewer. Never needs bowtie2 installed.
                            Reads runs from ./runs, --runs <dir>, or a
                            URL on a remote cluster.
```

Anyone can use just the pipeline (`conda install ...`), just the dashboard (`pip install trend-dashboard`), or both. They join on the on-disk manifest format — no API contract beyond filesystem layout.

---

## For three audiences

### A. Reviewer — verify a published figure (10 minutes)

```bash
conda install -c bioconda trend-pipeline
trend run --example ovarian_cancer       # ~2 min, dashboard-bundled tiny dataset
trend dashboard                           # browser shows the green oracle
```

Green badge = the comparator confirms your run produced the same numbers as the manuscript figure, column-by-column, within `rtol=1e-6`.

### B. Adopting lab — your own samples on a workstation

```bash
conda install -c bioconda trend-pipeline                    # one-time
trend init my-experiment --template T_cell_activation       # scaffold project
$EDITOR my-experiment/samplesheet.yaml                       # only config to touch
trend run --inputs ./fastqs/ --output runs/$(date +%F)/      # streams progress
trend dashboard --runs ./runs/                               # explore visually
```

### C. Adopting lab — HPC cluster + laptop viewer

On the cluster head node:
```bash
conda install -c bioconda trend-pipeline
trend init my-experiment --template ovarian_cancer
$EDITOR my-experiment/samplesheet.yaml

# One extra flag turns local execution into SLURM submission.
trend run --inputs /scratch/fastqs/ --output /scratch/runs/2026-04/ --profile slurm
# Snakemake submits each step as a SLURM job, handles dependencies, retries.
# Logout. Come back tomorrow.
```

On your laptop:
```bash
# Option 1: live-mount the cluster runs directory over SSH
sshfs cluster:/scratch/runs/ ~/cluster-runs/
trend dashboard --runs ~/cluster-runs/

# Option 2: rsync just the small final outputs back
rsync -av cluster:/scratch/runs/2026-04/outputs/ ./
trend dashboard --runs ./
```

The dashboard never needs bowtie2, samtools, or R installed locally — it's a *viewer* for runs produced anywhere.

---

## What you do NOT have to do

| Old workflow | After v2 |
|---|---|
| Install `bowtie2` + `samtools` + `cutadapt` + `fastx-toolkit` + R + tidyverse + Rsamtools manually | One `conda install -c bioconda trend-pipeline` |
| Hand-edit `Lib4_all_steps_FINAL_111525.sbatch` for your cluster's queue | `--profile slurm` (Snakemake handles submission) |
| Run 9 scripts in the right order, debug each one | Snakemake DAG handles ordering + resume-on-failure |
| Find-replace `OV8`/`IOSE`/`ID8` in the R script for your samples | Edit `samplesheet.yaml` |
| Move CSVs between cluster and laptop, lose track of what came from where | Either run dashboard on cluster or sshfs/rsync; manifest records provenance |
| Hope script versions match what made the paper figures | Conda-pinned versions; `manifest.json` records exact hashes per run |
| Open results in Excel and decode column names from the methods section | Hover for tooltips driven by schema YAMLs |

---

## Repository layout

```
TREND_bioinformatics_pipeline/
├── codes/                   Original manuscript scripts. UNCHANGED. Wrapped, never rewritten.
│   ├── 1. Instructions/
│   ├── 2. HPC_cluster_scripts/
│   └── 3. Post_HPC_enhancer_activity_analysis_scripts/
├── project_data/            Reference inputs and outputs the manuscript published.
├── pipeline/                trend-pipeline package — installable CLI + Snakemake workflow.
│   ├── trend/cli.py         The user-facing `trend` command.
│   ├── trend/workflow/      Snakefile + per-rule conda envs + SLURM profile.
│   ├── templates/           Project scaffolds for `trend init`.
│   ├── conda-recipe/        Bioconda submission (meta.yaml).
│   └── environment.yml      Single-shot `conda env create -f` setup for development.
├── dashboard/               Web dashboard (FastAPI + React).
│   ├── backend/             Pipeline runner, oracle comparator, library service.
│   ├── frontend/            React + Tailwind + shadcn UI (warm cream/charcoal theme).
│   └── Dockerfile           Canonical pinned container.
├── tests/                   18 tests. `pytest tests/ -v`.
│   ├── equivalence/         The C2 comparator gate.
│   ├── e2e/                 Oracle end-to-end (OvCa + T-cell).
│   └── cli/                 trend CLI tests.
├── DASHBOARD_PRD.md         Full product requirements document.
├── DESIGN.md                Visual design system (colors, typography, components).
└── README.legacy.md         Original pipeline-only README (kept for reference).
```

---

## Development

### One-shot conda env

```bash
conda env create -f pipeline/environment.yml
conda activate trend
pip install -e pipeline/
pip install -e 'pipeline/[dashboard]'    # if you want to develop the dashboard too
```

### Without conda (Python only — pipeline binaries stubbed)

```bash
pip install -e pipeline/
pip install fastapi 'uvicorn[standard]' pydantic duckdb sse-starlette pytest httpx
cd dashboard && make ingest && make backend
# in another shell:
cd dashboard/frontend && npm install && npm run dev
```

### Run all tests

```bash
pytest tests/ -v
# Expect 18 passes:
#   7  csv_compare unit tests
#   2  oracle end-to-end (OvCa + T-cell)
#   9  trend CLI tests (init, status, --example, …)
```

---

## CLI reference

```
trend --version
trend init <name> [--template ovarian_cancer|T_cell_activation]
trend run --example <project>                       # bundled reviewer oracle
trend run --inputs <dir> --output <dir>             # local execution
trend run --inputs <dir> --output <dir> --profile slurm   # HPC via Snakemake
trend dashboard [--runs <dir>] [--port 8000]
trend status <run_id> [--runs-dir <dir>]
trend preflight                                     # FR-2 environment check
```

---

## Contributing / extending

The architecture is intentionally seam-friendly. Common extensions:

- **New project type** (e.g., a third tissue context): add a template under `pipeline/templates/`, add an entry under `STEP9_SCRIPTS` in `pipeline/trend/workflow/Snakefile`, ship a project-specific R script under `codes/3. .../code_by_projects/<name>/`.
- **New cluster scheduler** (PBS, LSF, SGE): add a profile under `pipeline/trend/workflow/profiles/<scheduler>/config.yaml`. Snakemake supports all of them.
- **New result-CSV column tooltip**: edit the relevant `dashboard/backend/schemas/*.yaml`. The dashboard renders it automatically.
- **New error-classifier hint**: add a rule to `dashboard/backend/pipeline/error_hints.yaml`. First match wins.

---

## Citation

Manuscript citation will be added upon acceptance. For now, please cite the preprint and the GitHub repository.

## License

MIT.
