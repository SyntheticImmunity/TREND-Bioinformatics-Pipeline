# For reviewers

This document is a guide to the repository's contents. It comes in two parts:

| Section | What it covers | Time |
|---|---|---|
| **Part A — Browsing the repository** | A map of the source files, the manuscript numbers and where they appear, the bundled reproducibility examples, and the documentation set. No installation required. | 5–10 min |
| **Part B — Running the code** | A Docker-based install and two bundled reproducibility checks for reviewers who want to run the code locally. | 20–60 min |

No HPC cluster, GPU, or specialized hardware is required for either part. The bundled checks in Part B run on a standard laptop.

> The GitHub URL is private during the review period (it returns a 404 to non-collaborators). The anonymized mirror you received from the journal — 🔗 **https://anonymous.4open.science/r/TREND-Bioinformatics-Pipeline** — provides full read-only access to the same content. The GitHub repo will be made public after paper acceptance.

---

# Part A — Browsing the repository (no install)

The sections below describe what is in the repository and where to find it. Open the anonymized mirror in your browser to follow along.

## A.1 — Source files at a glance

The platform's logic lives in a small number of files. The list below is offered as a map; each file is one click away in the mirror's file tree.

| File | What it is | Approx. size |
|---|---|---|
| `pipeline/trend/cli.py` | The user-facing `trend` CLI with five subcommands (init / run / dashboard / status / preflight) | ~375 lines |
| `pipeline/trend/workflow/Snakefile` | The Snakemake DAG that orchestrates all 9 pipeline steps | ~265 lines |
| `dashboard/backend/library/classifications.py` | Computes the Figure 1B–E aggregates against Lambert / Reddy / D'Alessio | ~365 lines |
| `dashboard/backend/library/queries.py` | Paginated, filterable, sortable enhancer queries plus CSV-export streaming | ~390 lines |
| `dashboard/backend/oracle/run_example.py` | The reproducibility verifier driving the Verify tab | ~340 lines |
| `dashboard/frontend/src/pages/Library.tsx` | Main dashboard page with all Figure 1 panels wired together | ~140 lines |
| `tests/equivalence/helpers/csv_compare.py` | Numerical-tolerance CSV comparator | ~165 lines |
| `codes/3. Post_HPC_enhancer_activity_analysis_scripts/code_by_projects/ovarian_cancer/ovarian_cancer_specific_enhancer_screening_analysis.R` | The unchanged Step-9 R script that produces the published activity tables | original manuscript code |

## A.2 — Manuscript numbers and where they appear in the repository

The numbers cited in the manuscript appear in the repository at the locations listed below. The mirror's file viewer renders CSV files as browsable tables.

| Number cited in the manuscript | Location in the repository | Value |
|---|---|---|
| Total constructs in Lib4 | `README.md`, `MANUAL.md` | 2,730,581 |
| Total TFs in library | `README.md`, `references/TREND_library_TF_breakdown.md` | 1,068 |
| Confirmed sequence-specific TFs | `references/TREND_library_TF_breakdown.md`; reconciliation diagram | 729 (= 695 direct + 34 alias) |
| DBD families covered | `dashboard/backend/library/classifications.py` constant `N_LAMBERT_DBD_FAMILIES_TOTAL` | 49 (Lambert taxonomy) |
| Sensors in the Homeodomain family | `dashboard/backend/library/classifications.py` (Panel C aggregate) | 11,283 |
| CaCTS cancer-MTF coverage | `references/TREND_library_TF_breakdown.md` | 204/273 = 74.7% |
| D'Alessio identity-TF coverage | same file | 354/503 = 70.4% (mirror computes 354/505 = 70.9% with alias resolution; difference noted in the breakdown) |
| Top OvCa-selective enhancer | `project_data/final_enhancer_activity_results/ovarian_cancer/ovca_sensor_activity_result_concise.csv`, row 1 | E2F7 promoter (`ATTTTCCCGCCA_E2F7`), ≈26.6× OV8/IOSE selectivity |
| Share of confirmed TFs in the top six DBD families | `references/TREND_library_TF_breakdown.md` | 67% (489 / 729) |

## A.3 — Bundled examples for hands-on reproduction

The repository includes two example datasets that the Verify tab in the dashboard uses to reproduce the published activity tables on a reviewer's machine. Both datasets are committed to the repository and run on a standard laptop.

| Example | Location | Size |
|---|---|---|
| Analysis-only example: 1,000-promoter subsample of the published OvCa alignment count tables, with the expected Step-9 output | `dashboard/example_data/ovca_step9/inputs/` and `expected/` | ~28 MB |
| End-to-end example: 50 promoters × 5 barcodes, 8 simulated FASTQ files, and the analytically-derived expected count matrix | `dashboard/example_data/ovca_pipeline/inputs/` and `expected/` | ~6 MB |
| Deterministic fixture generator | `tools/build_fixtures.py` | ~290 lines |
| Tests | `tests/` (`equivalence/`, `e2e/`, `cli/`) | 18 tests |
| Published activity tables used as the reference for the analysis-only example | `project_data/final_enhancer_activity_results/{ovarian_cancer,T_cell_activation}/*.csv` | ~78 MB |

## A.4 — Documentation

- **`README.md`** — project overview, architecture diagram, three-piece deployment story
- **`MANUAL.md`** — comprehensive user manual with install paths, dashboard tour, troubleshooting, glossary
- **`references/TREND_library_TF_breakdown.md`** — full reconciliation of the 1,068 / 729 / 695 / 49 numbers against Lambert
- **`LICENSE`** — MIT

---

# Part B — Running the code locally

This part walks through a Docker install and the two bundled reproducibility checks.

## B.1 — Get the code

Click **"Download Repository"** at the top of the anonymized mirror to download a ZIP of the source code. Unzip and `cd` into the folder.

```bash
unzip TREND-Bioinformatics-Pipeline.zip
cd TREND-Bioinformatics-Pipeline
```

## B.2 — Install via Docker

The fastest way to run the platform is the bundled Docker image. It includes bowtie2, samtools, cutadapt, fastx-toolkit, R and all R packages, Python, and the pre-built dashboard frontend — nothing else needs to be installed.

**Prerequisites:** Docker Desktop (https://docker.com/products/docker-desktop). One-click install on Mac and Windows.

> **Windows note:** if the installer reports `For security reasons C:\ProgramData\DockerDesktop must be owned by an elevated account`, right-click the installer and choose **Run as administrator**.

**After installing, launch Docker Desktop and wait for it to be ready.** Installing the application is not the same as running it — the `docker` commands below talk to a background service that only starts when the app is open. Look for the whale icon in the Windows system tray (bottom-right) or the macOS menu bar (top-right): when the icon is solid and stops animating, the service is up. Until then, `docker pull` will fail with `error during connect: ... pipe/docker_engine` (Windows) or `Cannot connect to the Docker daemon` (macOS / Linux).

**Where to run the commands below.** They are not pasted into the Docker Desktop window itself; they go into a terminal application:

- **Windows** — open **PowerShell** (Start menu → type `PowerShell` → Enter) or Windows Terminal.
- **macOS** — open **Terminal** (Applications → Utilities → Terminal, or press `⌘ Space` and type `Terminal`).
- **Linux** — any shell you already use (bash, zsh).

```bash
docker pull ghcr.io/syntheticimmunity/trend-dashboard:latest
docker run -p 8000:8000 ghcr.io/syntheticimmunity/trend-dashboard:latest
```

The first command downloads the image (~1.3 GB compressed transfer; expands to ~6 GB on disk after extraction — the conda environment with R, bowtie2, samtools, cutadapt, fastx-toolkit and the prebuilt library state accounts for most of it). The pull runs once and is cached afterwards. The second command starts the container and prints `Uvicorn running on http://0.0.0.0:8000` when ready. Leave the terminal window open — closing it stops the container. To stop the container manually, return to the terminal and press `Ctrl+C`.

Open **http://localhost:8000** in your browser.

> If you'd rather use Conda or a native install instead of Docker, both are documented in **MANUAL.md** § 3.

## B.3 — Run the reproducibility checks

Once the container is running and the dashboard is open in your browser, the Verify tab is the entire interface — clicking a card runs the corresponding check inside the container. No terminal commands needed.

In the dashboard at `http://localhost:8000`, click **"Verify"** in the top navigation. You'll see two cards.

### End-to-end install check (~3 minutes; recommended)

Click the recommended card → **"Run end-to-end install check"**. Snakemake invokes Steps 1–9 on simulated FASTQs at `dashboard/example_data/ovca_pipeline/inputs/fastqs/` and validates that the post-alignment count matrix matches the analytically-computed expected values. Validates the entire alignment + analysis stack inside your install: bowtie2, cutadapt, samtools, fastx-toolkit, and R. If this passes, your install is complete and you can trust the image on your own FASTQs.

### Analysis-only check (~30 seconds; requires R + tidyverse + Rsamtools)

Click the second card → **"Run analysis-only check"**. Re-runs the unchanged Step-9 R script (`codes/3. Post_HPC_enhancer_activity_analysis_scripts/code_by_projects/ovarian_cancer/ovarian_cancer_specific_enhancer_screening_analysis.R`) against a 1,000-promoter slice of the published OvCa alignment data and verifies every output column row-for-row against the published activity tables (numerical tolerance: `rtol=1e-6`). Use this if you only plan to re-analyze existing count tables — it skips the upstream alignment stack.

### Or run via the CLI

```bash
trend run --example ovarian_cancer --tier pipeline    # end-to-end install check
trend run --example ovarian_cancer --tier step9       # analysis-only check
```

Each prints a self-contained report ending in `overall_pass: True`.

---

## Running TREND on your own data

For reviewers who also wear the adopter hat. See **MANUAL.md** § 7 for the walkthrough. The short form:

```bash
trend init my-experiment --template T_cell_activation
$EDITOR my-experiment/samplesheet.yaml
trend run --inputs ./fastqs/ --output runs/$(date +%F)/
trend dashboard --runs runs/
```

---

## Reference

| File | What's in it |
|---|---|
| `MANUAL.md` | Comprehensive user manual (install, dashboard tour, troubleshooting, glossary) |
| `README.md` | Project overview, three-piece architecture diagram |
| `references/TREND_library_TF_breakdown.md` | TF composition reconciliation (1,068 / 729 / 695 numbers) |
| `pipeline/trend/workflow/Snakefile` | The Snakemake workflow definition |
| `pipeline/conda-recipe/meta.yaml` | Bioconda submission recipe |
| `tools/build_fixtures.py` | Deterministic fixture generator for the bundled examples |

Thank you for reviewing.
