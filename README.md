# TREND — Transcription-Factor-Responsive Enhancer Discovery

End-to-end pipeline + interactive dashboard for the TREND enhancer-screening platform. The Lib4 designed library contains ~2.7 million barcoded enhancer-reporter constructs across 1,068 transcription factors; this software takes raw sequencing reads through demultiplexing, barcode extraction, alignment to the Lib4 reference, and per-promoter activity quantification, with a web dashboard for interactive exploration.

---

## 📋 For reviewers

The GitHub repository is private during the manuscript review period; this anonymized mirror is the read-only equivalent and requires no GitHub account or login. After paper acceptance the GitHub repo will be made public and the mirror will retire.

For an organized walkthrough of what is in the repository — source files, manuscript numbers and where they appear, bundled reproducibility examples, and the Docker-based local run path — read [`REVIEWERS.md`](REVIEWERS.md). It comes in two parts: Part A describes what is in the repository and runs in 5–10 minutes of browsing; Part B walks through a Docker install and two bundled reproducibility checks (the longer finishes in ~3 minutes on a standard laptop). No HPC cluster is required for either part.

---

## 🧬 For new users running TREND on your own data

The installation and run loop. Adapt the project name and sample sheet to your experiment.

### One-time install

Pick the path matching your environment:

#### Path A — Docker (easiest; zero dependency conflicts)

**Prerequisite:** [Docker Desktop](https://docker.com/products/docker-desktop) installed on macOS or Windows (one-click installer); on Linux, the `docker` engine.

```bash
docker pull ghcr.io/syntheticimmunity/trend-dashboard:latest
docker run -p 8000:8000 ghcr.io/syntheticimmunity/trend-dashboard:latest
# → open http://localhost:8000
```

The image bundles bowtie2, samtools, cutadapt, fastx-toolkit, R + tidyverse + Rsamtools, Python, all dependencies, and the pre-built dashboard frontend. ~5 min from clean machine to running dashboard.

The same image runs your own data — mount your FASTQs, output dir, and your project scaffold; then override the default command. The Lib4 alignment reference is already in the image, so no separate download is needed:

```bash
docker run --rm \
  -v /path/to/fastqs:/data/fastqs \
  -v /path/to/runs:/data/runs \
  -v "$(pwd)/my-experiment:/app/my-experiment" \
  ghcr.io/syntheticimmunity/trend-dashboard:latest \
  trend run --inputs /data/fastqs --output /data/runs/$(date +%F)
```

For HPC clusters that disallow Docker, convert once to Singularity:

```bash
singularity build trend.sif docker://ghcr.io/syntheticimmunity/trend-dashboard:latest
singularity run -B /scratch:/scratch trend.sif trend run --profile slurm --inputs /scratch/fastqs --output /scratch/runs
```

#### Path B — Conda environment

```bash
git clone https://github.com/syntheticimmunity/TREND-Bioinformatics-Pipeline.git
cd TREND-Bioinformatics-Pipeline
conda env create -f pipeline/environment.yml
conda activate trend
pip install -e ./pipeline
trend preflight    # verify every required tool is installed
```

#### Path C — Manual install

See [`MANUAL.md`](MANUAL.md) § 3 for OS-specific commands to install bowtie2, samtools, cutadapt, fastx-toolkit, and R + tidyverse + Rsamtools system-wide, then `pip install -e ./pipeline`.

### Get the Lib4 reference data (Path B / Path C only)

The Docker image (Path A) already bakes in the Lib4 alignment reference, so Path A users can skip this step.

For Path B (Conda) and Path C (Manual) installs, the bowtie2 alignment reference (`Lib4.fasta`) and per-construct metadata (`Lib4_info_concise_060621.csv`) exceed GitHub's per-file size limit and live on Dropbox. One command pulls them and places each file at the path the pipeline expects:

```bash
# macOS / Linux
bash scripts/download_data.sh

# Windows (PowerShell)
pwsh scripts/download_data.ps1
```

This downloads ~3 GB total (the Lib4 reference plus the published alignment count tables for full Step 9 reproducibility). Idempotent — safe to re-run; skips files already present.

You don't need this download for the bundled reproducibility checks under `trend run --example` — only for `trend run` against your own FASTQs.

### Per-experiment loop

```bash
# Scaffold a project from one of the bundled templates
trend init my-experiment --template ovarian_cancer     # or: T_cell_activation
cd my-experiment

# Edit the ONLY configuration you need to touch.
# Per sample: id (must match FASTQ filename), fastq path, role (DNA|RNA),
# condition, replicate_group, dna_threshold. Plus an analysis: block at the
# bottom defining bc_threshold and the contrasts to compute.
$EDITOR samplesheet.yaml

# Run the 9-step pipeline (workstation, ~hours per 16 samples on 8 cores)
trend run --inputs ./fastqs/ --output runs/$(date +%F)/

# Or on an HPC cluster — Snakemake handles SLURM submission for you
trend run --inputs /scratch/fastqs/ --output runs/2026-04/ --profile slurm

# Browse results in the dashboard (any computer; doesn't need bowtie2 installed)
trend dashboard --runs ./runs/
```

For the full sample-sheet field reference, plus how to surface your own activity table on the Results page (strip plot, drill-downs, CSV export), see [`MANUAL.md`](MANUAL.md) § 7.

Open `http://localhost:8000` to see the library composition panels (Figure 1A–E faithfully reproduced as interactive plots), the cancer-selectivity scatter (Figure 1F), and a sortable enhancer table.

The full user manual is in [`MANUAL.md`](MANUAL.md). For HPC-specific configuration see `pipeline/trend/workflow/profiles/slurm/`.

---

## What's in the box

```
TREND-Bioinformatics-Pipeline/
├── pipeline/                trend CLI + Snakemake workflow + Bioconda recipe
│   ├── trend/cli.py         The user-facing `trend` command
│   ├── trend/workflow/      Snakemake DAG with per-rule conda envs
│   ├── templates/           Project scaffolds for `trend init`
│   └── conda-recipe/        Bioconda submission (planned)
├── dashboard/               FastAPI backend + React/Tailwind frontend
│   ├── backend/             Library service, pipeline runner, oracle, preflight
│   ├── frontend/            Interactive UI (Recharts, TanStack Table, shadcn/ui)
│   └── example_data/        Bundled tiny datasets for reviewer verification
├── codes/                   Original manuscript scripts (UNCHANGED)
│   ├── 2. HPC_cluster_scripts/
│   └── 3. Post_HPC_enhancer_activity_analysis_scripts/
├── project_data/            Published analysis outputs (small CSVs only)
├── tests/                   18 tests — pytest tests/ -v
├── tools/                   build_fixtures.py — deterministic fixture generator
├── scripts/                 download_data.{sh,ps1} for the Dropbox-hosted full data
└── references/              Lambert/Reddy/D'Alessio derived tables + breakdown md
```

The dashboard wraps — but never modifies — the existing manuscript scripts in `codes/`. The Snakemake workflow shells out to those same scripts, so any verification you do via this software exercises the original published code.

---

## Data: what's in git, what's downloaded separately

The repository contains all code plus a small set of bundled fixtures (~36 MB) sufficient for the bundled reproducibility checks. The **full data** (~3 GB: published per-barcode count tables for all screens + the 152 MB Lib4 reference + the 445 MB per-construct metadata) is hosted on Dropbox and fetched by a one-line script:

```bash
# macOS / Linux
bash scripts/download_data.sh

# Windows
pwsh scripts/download_data.ps1
```

You only need this for full library exploration (2.7 M constructs vs the bundled 1,000-promoter subsample) or to apply TREND to your own samples (the Lib4 reference is needed for bowtie2 alignment). **For manuscript verification, the bundled examples are sufficient.**

After paper acceptance, the full dataset will be migrated to a Zenodo deposit with a citable DOI.

---

## Verifying the manuscript's claims

The dashboard's Verify tab exposes two reproducibility checks against bundled example datasets, both also runnable from the CLI:

```bash
trend run --example ovarian_cancer --tier step9      # ~30 s   needs R; reproduces the published activity numbers from a 1,000-promoter slice of real OvCa alignment data
trend run --example ovarian_cancer --tier pipeline   # ~3 min  needs the full conda env; runs the full FASTQ-to-counts pipeline on simulated reads
```

Each prints a self-contained report ending in `overall_pass: True` plus per-file column-by-column match results. The dashboard exposes the same checks as click-to-run cards on the Verify tab, with a green "match" badge and per-file diff if anything differs.

---

## Documentation map

| Document | Audience | Length |
|---|---|---|
| [`README.md`](README.md) | Everyone — first impression | This file |
| [`REVIEWERS.md`](REVIEWERS.md) | Journal reviewers | Two parts: Part A (browsing) and Part B (running the code via Docker) |
| [`MANUAL.md`](MANUAL.md) | New users / adopters | Comprehensive install, dashboard tour, troubleshooting, glossary |
| [`references/TREND_library_TF_breakdown.md`](references/TREND_library_TF_breakdown.md) | Reviewers + curious adopters | Reconciliation of the 1,068 / 729 / 695 / 49 numbers against Lambert |
| [`CHANGELOG.md`](CHANGELOG.md) | Anyone tracking releases | Release notes per version |

---

## License

MIT — see [`LICENSE`](LICENSE).

## Citation

Citation will be added upon manuscript acceptance. For now, please cite the preprint and link to this repository.

## Contact

Questions, bug reports, and feature requests: open an issue on the GitHub repository (after publication; private during review).
