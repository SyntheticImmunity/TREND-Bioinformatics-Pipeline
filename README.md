# TREND — Transcription-Factor-Responsive Enhancer Discovery

End-to-end pipeline + interactive dashboard for the TREND enhancer-screening platform. The Lib4 designed library contains ~2.7 million barcoded enhancer-reporter constructs across 1,068 transcription factors; this software takes raw sequencing reads through demultiplexing, barcode extraction, alignment to the Lib4 reference, and per-promoter activity quantification, with a web dashboard for interactive exploration.

## Try the dashboard in 30 seconds

**Prerequisite:** install [Docker Desktop](https://docker.com/products/docker-desktop) (macOS / Windows) or the `docker` engine (Linux), and **launch it** — Docker Desktop must be running before the commands below will work.

> **Windows users — install as administrator.** Right-click the downloaded Docker Desktop installer and choose **Run as administrator** for the first install. Docker Desktop writes into protected system directories during setup, and the standard double-click path will fail with a permission error like `For security reasons C:\ProgramData\DockerDesktop must be owned by an elevated account`.

**Open a terminal:**
- **Windows** — **PowerShell** or **Windows Terminal** (no WSL or bash setup needed).
- **macOS** — **Terminal** (Applications → Utilities → Terminal).
- **Linux** — any shell.

In the terminal, run the first command to download the image (~6.6 GB; runs once and is cached):

```bash
docker pull ghcr.io/syntheticimmunity/trend-dashboard:latest
```

When that finishes, run the second command to start the dashboard:

```bash
docker run -p 8000:8000 ghcr.io/syntheticimmunity/trend-dashboard:latest
```

The terminal will print `Uvicorn running on http://0.0.0.0:8000` when it's ready. **At that point, open [http://localhost:8000](http://localhost:8000) in your web browser.** Leave the terminal window open while you're using the dashboard; closing it stops the container.

The image bundles bowtie2, samtools, cutadapt, fastx-toolkit, R + tidyverse + Rsamtools, Python, all dependencies, the Lib4 alignment reference, and the pre-built dashboard frontend. Runs against the bundled OvCa + T-cell results immediately.

## Where to start

| If you're a... | Start at | Time budget |
|---|---|---|
| **Reviewer** verifying the manuscript | [`REVIEWERS.md`](REVIEWERS.md) — repo tour, manuscript-number cross-reference, one-click reproducibility checks | 5–10 min browsing; ~30 sec for the bundled analysis check |
| **Adopter** running TREND on your own FASTQs | [Quickstart for adopters](#-for-new-users-running-trend-on-your-own-data) below + [`MANUAL.md`](MANUAL.md) | ~5 min install; alignment hours; per-iteration minutes |
| **Developer** extending or self-hosting the dashboard | [`dashboard/README.md`](dashboard/README.md) | Varies |

## Repository tour

| Path | What it is |
|---|---|
| **[`REVIEWERS.md`](REVIEWERS.md)** | Reviewer-first walkthrough — repo map, manuscript-number cross-references, reproducibility procedures |
| **[`MANUAL.md`](MANUAL.md)** | Comprehensive adopter manual — install paths, dashboard tour, troubleshooting, glossary |
| `pipeline/` | Snakemake workflow + the `trend` CLI (`init` / `run` / `dashboard` / `preflight`) |
| `dashboard/` | FastAPI backend + React/Tailwind frontend |
| `project_data/` | Bundled published outputs — OvCa & T-cell activity tables |
| `codes/` | Manuscript's original analysis scripts |
| `references/` | Library metadata, TF taxonomy tables (Lambert / D'Alessio), curated breakdowns |
| `scripts/` | Data-download helpers (`download_data.{sh,ps1}`) |
| `tests/` · `tools/` | Automated equivalence tests, fixture builders, audit utilities |

---

## 📋 For reviewers

For an organized walkthrough of what is in the repository — source files, manuscript numbers and where they appear, bundled reproducibility examples, and the Docker-based local run path — read [`REVIEWERS.md`](REVIEWERS.md). It comes in two parts: Part A describes what is in the repository and runs in 5–10 minutes of browsing; Part B walks through a Docker install and the bundled reproducibility checks. No HPC cluster is required for either part.

---

## 🧬 For new users running TREND on your own data

The installation and run loop. Adapt the project name and sample sheet to your experiment.

### One-time install

Pick the path matching your environment:

#### Path A — Docker (easiest; zero dependency conflicts)

**Prerequisite:** [Docker Desktop](https://docker.com/products/docker-desktop) installed and running on macOS or Windows (one-click installer); on Linux, the `docker` engine.

> **Windows users — install as administrator.** Right-click the downloaded Docker Desktop installer and choose **Run as administrator** for the first install. Docker Desktop writes into protected system directories during setup, and the standard double-click path will fail with a permission error.

**Where to run the commands below:**
- **Windows** — open **PowerShell** or **Windows Terminal** (no WSL or bash setup required).
- **macOS** — open **Terminal**.
- **Linux** — any shell.

Download the image (~6.6 GB; cached after the first pull):

```bash
docker pull ghcr.io/syntheticimmunity/trend-dashboard:latest
```

Start the dashboard:

```bash
docker run -p 8000:8000 ghcr.io/syntheticimmunity/trend-dashboard:latest
```

When the terminal shows `Uvicorn running on http://0.0.0.0:8000`, open [http://localhost:8000](http://localhost:8000) in your web browser.

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

For Path B (Conda) and Path C (Manual) installs, the bowtie2 alignment reference (`Lib4.fasta`) and per-construct metadata (`Lib4_info_concise_060621.csv`) exceed GitHub's per-file size limit and live as assets on this repository's GitHub release `library-data-2026-05-04`. One command pulls them and places each file at the path the pipeline expects:

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
# 1. Scaffold a project from one of the bundled templates.
trend init my-experiment --template ovarian_cancer     # or: T_cell_activation
cd my-experiment

# 2. Edit samplesheet.yaml — one row per (cell_line, replicate) pair, with
# dna_fastq + rna_fastq filenames matching your FASTQs (without .fastq.gz).
# Leave dna_threshold blank for the first run; you'll come back after step 4.
$EDITOR samplesheet.yaml

# 3. First run: alignment (~hours) + Step 9 with default thresholds.
# Outputs include a DNA_threshold_for_samples.pdf for inspection.
trend run --inputs ./fastqs/ --output runs/$(date +%F)/ \
  --samplesheet ./samplesheet.yaml --profile snakemake

# 4. Inspect runs/<date>/DNA_threshold_for_samples.pdf, decide thresholds.

# 5. Edit dna_threshold values in runs/<date>/samplesheet.yaml (the copy in
# the run dir, not your input), then re-run only Step 9 (~minutes):
trend run --resume runs/<date> --rerun-from step9

# 6. Browse results in the dashboard.
trend dashboard --runs ./runs/

# HPC cluster: replace --profile snakemake with --profile slurm in step 3.
```

For the full step-by-step walkthrough with Docker volume-mount commands for both bash/zsh and PowerShell, the inspect-and-tune iteration explained in detail, and the *For bioinformaticians: direct R control* path (open `step9_rendered.R` in RStudio), see [`REVIEWERS.md`](REVIEWERS.md) *Running TREND on your own data* or [`MANUAL.md`](MANUAL.md) § 7.

Open `http://localhost:8000` to see the library composition panels (Figure 1A–E faithfully reproduced as interactive plots), the cancer-selectivity scatter (Figure 1F), and a sortable enhancer table.

The full user manual is in [`MANUAL.md`](MANUAL.md). For HPC-specific configuration see `pipeline/trend/workflow/profiles/slurm/`.

---

The dashboard wraps — but never modifies — the existing manuscript scripts in `codes/`. The Snakemake workflow shells out to those same scripts, so any verification you do via this software exercises the original published code.

---

## Data: what's in git, what's downloaded separately

The repository contains all code plus a small set of bundled fixtures (~36 MB) sufficient for the bundled reproducibility checks. The **full data** (~3 GB: published per-barcode count tables for all screens + the 152 MB Lib4 reference + the 445 MB per-construct metadata) is hosted as assets on this repository's GitHub release `library-data-2026-05-04` and fetched by a one-line script:

```bash
# macOS / Linux
bash scripts/download_data.sh

# Windows
pwsh scripts/download_data.ps1
```

You only need this for full library exploration (2.7 M constructs vs the bundled 1,000-promoter subsample) or to apply TREND to your own samples (the Lib4 reference is needed for bowtie2 alignment). **For manuscript verification, the bundled examples are sufficient.**

After paper acceptance, the full dataset will be migrated to a Zenodo deposit with a citable DOI.

---

## Reproducing the manuscript's results

The repository supports manuscript reproduction at two levels of stringency:

**Install check (~3–4 minutes, in the dashboard).** Click *Install check → Run install check*. Phase 1 runs the bioinformatics pipeline (FASTQ → adapter trim → UMI collapse → barcode extract → bowtie2 → count matrix) on a small simulated FASTQ fixture and verifies the count matrix matches analytically-computed expected values. Phase 2 runs the per-project Step 9 R script on a 1,000-promoter slice of real OvCa alignment data and verifies the activity table matches the published values row-for-row. A green "all match" report confirms every tool in the stack — bowtie2, cutadapt, samtools, fastx-toolkit, R + tidyverse, and the per-project Step 9 script — is functional in your install.

**Reproduce key results (~5–7 minutes per project, in the dashboard).** Click *Reproduce* in the navigation, then *Reproduce this analysis* on either project card. The dashboard fetches the full post-alignment count tables from this repository's GitHub release on first click (~1.0–1.2 GB per project; cached afterwards), runs the manuscript's unmodified Step 9 R script against them, and exposes both the produced CSV and the deposited reference CSV for download. The two files should be byte-identical when produced by the bundled Docker image.

The same reproduction is available on the command line — see [`REVIEWERS.md`](REVIEWERS.md) § *Reproducing the manuscript's results* for the four-step procedure (download → place → `Rscript` → diff). Verified bit-for-bit (zero numeric mismatches across 3.8 million cells, both projects) when run inside the bundled Docker image.

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

Questions, bug reports, and feature requests: open an issue on the GitHub repository.
