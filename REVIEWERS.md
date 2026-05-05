# For reviewers

This document is a guide to the repository's contents. It comes in two parts:

| Section | What it covers | Time |
|---|---|---|
| **Part A — Browsing the repository** | A map of the source files, the manuscript numbers and where they appear, the bundled reproducibility examples, and the documentation set. No installation required. | 5–10 min |
| **Part B — Running the code** | A Docker-based install and two bundled reproducibility checks for reviewers who want to run the code locally. | 20–60 min |

No HPC cluster, GPU, or specialized hardware is required for either part. The bundled checks in Part B run on a standard laptop.

> The repository lives at 🔗 **https://github.com/SyntheticImmunity/TREND-Bioinformatics-Pipeline** (MIT-licensed, public read-only). All sections below link directly into the GitHub source tree.

---

# Part A — Browsing the repository (no install)

The sections below describe what is in the repository and where to find it. Open the GitHub repository in your browser to follow along.

## A.1 — Source files at a glance

The platform's logic lives in a small number of files. The list below is offered as a map; each file is one click away in GitHub's file tree.

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

The numbers cited in the manuscript appear in the repository at the locations listed below. GitHub renders CSV files as browsable tables in its file viewer.

| Number cited in the manuscript | Location in the repository | Value |
|---|---|---|
| Total constructs in Lib4 | `README.md`, `MANUAL.md` | 2,730,581 |
| Total TFs in library | `README.md`, `references/TREND_library_TF_breakdown.md` | 1,068 |
| Confirmed sequence-specific TFs | `references/TREND_library_TF_breakdown.md`; reconciliation diagram | 729 (= 695 direct + 34 alias) |
| DBD families covered | `dashboard/backend/library/classifications.py` constant `N_LAMBERT_DBD_FAMILIES_TOTAL` | 49 (Lambert taxonomy) |
| Sensors in the Homeodomain family | `dashboard/backend/library/classifications.py` (Panel C aggregate) | 11,283 |
| CaCTS cancer-MTF coverage | `references/TREND_library_TF_breakdown.md` | 204/273 = 74.7% |
| D'Alessio identity-TF coverage | same file | 354/503 = 70.4% (the breakdown computes 354/505 = 70.9% with alias resolution; difference noted there) |
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

Clone the repository, or click the green **"Code"** button on GitHub and choose **"Download ZIP"**:

```bash
git clone https://github.com/SyntheticImmunity/TREND-Bioinformatics-Pipeline.git
cd TREND-Bioinformatics-Pipeline
```

## B.2 — Install via Docker

The fastest way to run the platform is the bundled Docker image. It includes bowtie2, samtools, cutadapt, fastx-toolkit, R and all R packages, Python, and the pre-built dashboard frontend — nothing else needs to be installed.

**Prerequisites:** Docker Desktop (https://docker.com/products/docker-desktop). One-click install on macOS.

> **Windows:** right-click the downloaded installer and choose **Run as administrator** before the first install. Docker Desktop writes into protected system directories during setup, and the standard double-click path will fail with `For security reasons C:\ProgramData\DockerDesktop must be owned by an elevated account`. Installing as administrator from the start avoids the error.

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

## Reproducing the manuscript's results

The repository supports manuscript reproduction at two levels of stringency. Both validate against the deposited activity tables in `project_data/final_enhancer_activity_results/`.

### Fast verification (~30 seconds)

Click *Install check → Analysis-only check* in the dashboard. The dashboard re-runs the published Step 9 R script against a 1,000-promoter slice of the OvCa count tables (bundled under `dashboard/example_data/ovca_step9/`) and compares the resulting activity values to the deposited table row-for-row. A green "all match" badge confirms the analysis stack — R + tidyverse + the per-project Step 9 script — is functional in your install.

This is sufficient to confirm the dashboard's machinery works end-to-end. It is *not* a full-data check — only 1,000 of the ~57,000 promoters are exercised.

### Full-data reproduction (~5–7 minutes)

For row-for-row verification of the full deposited activity tables, run the manuscript's unmodified Step 9 R script against the full deposited count tables. Two equivalent paths.

#### Path 1 — One-click in the dashboard

On the Projects page, each project card has a *Reproduce this analysis* button. Click → confirm the download → the dashboard fetches the count tables from this repository's GitHub release on first use, runs the R script, and exposes both the just-produced CSV and the deposited reference CSV for download. Compare them with your tool of choice. The dashboard does not assert a match — you decide.

#### Path 2 — Command line

If you prefer to run R yourself:

```bash
# 1. Fetch the count tables (and Lib4 reference, ~3 GB total) from Dropbox.
bash scripts/download_data.sh                    # macOS / Linux
pwsh scripts/download_data.ps1                   # Windows PowerShell

# 2. The script places the count tables at the canonical paths the R script expects:
#    project_data/alignment_results/{ovarian_cancer,T_cell_activation}/

# 3. From a directory containing the count tables and the metadata file
#    `all_enhancer_metadata_111525.csv`, run the manuscript's Step 9 script.
#    Easiest is via the bundled Docker image so the R + tidyverse versions match
#    the ones we used:
docker run --rm \
  -v "$(pwd)/project_data/alignment_results/ovarian_cancer:/work" \
  -v "$(pwd)/codes/3. Post_HPC_enhancer_activity_analysis_scripts/required_metadata/all_enhancer_metadata_111525.csv:/work/all_enhancer_metadata_111525.csv:ro" \
  -v "$(pwd)/codes/3. Post_HPC_enhancer_activity_analysis_scripts/code_by_projects/ovarian_cancer/ovarian_cancer_specific_enhancer_screening_analysis.R:/work/script.R:ro" \
  -w /work \
  ghcr.io/syntheticimmunity/trend-dashboard:latest \
  Rscript script.R

# 4. Diff against the deposited reference (also in this repo).
diff project_data/alignment_results/ovarian_cancer/ovca_sensor_activity_result_concise.csv \
     project_data/final_enhancer_activity_results/ovarian_cancer/ovca_sensor_activity_result_concise.csv
```

For T-cell, swap `ovarian_cancer` → `T_cell_activation` and the script name to `T_cell_activation_responsive_enhancer_screening_analysis.R`.

### About numerical exactness

We have verified, end-to-end via the bundled Docker image, that running the manuscript's published Step 9 R scripts against the full deposited count tables produces output that matches the deposited activity tables **bit-for-bit**: zero numeric mismatches across **3.8 million numeric cells** combined (OvCa + both T-cell donors), at the strictest possible tolerance (`rtol=0`, `atol=0`). This is the most stringent reproducibility guarantee a reviewer can ask for: bit-equivalent, not merely scientifically equivalent.

---

## Running TREND on your own data

This section takes you from raw FASTQs to a published-style activity table. It uses an **iterative threshold-tuning loop** because picking DNA thresholds is a human-in-the-loop decision: you have to look at per-sample DNA-coverage distributions before you can choose them sensibly. The flow:

1. Scaffold a project from a template.
2. Fill in the sample sheet (filenames + experimental design — leave thresholds blank).
3. Run the pipeline once → get alignment + preliminary results + a PDF of DNA distributions.
4. Open the PDF, decide thresholds per sample.
5. Edit the sample sheet, re-run Step 9 only (~minutes — not the hours that re-alignment would take).
6. Repeat step 5 until satisfied.

A separate path for bioinformaticians who want direct R control is at the bottom.

### Prerequisites

- The Docker image already pulled (or the conda env activated). See § B.2 if neither.
- A directory of demultiplexed `.fastq.gz` files — one per sample.

### A note on the multi-line commands below

Several `docker run` commands in this section span multiple lines. Each non-final line ends in `\` (on macOS/Linux) or `` ` `` (on Windows PowerShell). That trailing character is your shell's **line-continuation marker** — it tells the shell "this command continues on the next line." Two practical consequences:

- **Paste the entire block at once**, not line by line. Selecting all lines together and pasting works in Terminal (macOS), iTerm, GNOME Terminal (Linux), PowerShell, and Windows Terminal.
- **The line-continuation character is shell-specific.** bash and zsh use `\`; PowerShell uses the backtick `` ` ``. Each multi-line command is shown in two versions — pick the one for your shell.

### Step 1 — Scaffold the project

```bash
trend init my-experiment --template ovarian_cancer
cd my-experiment
```

You now have:

```
my-experiment/
├── samplesheet.yaml      ← the only file you'll edit
├── project.yaml
└── README.md
```

The template is pre-filled with the published OvCa example (3 cell lines, 8 samples). Replace it in the next step.

### Step 2 — Edit `samplesheet.yaml` (filenames + design only)

Open `samplesheet.yaml` in any text editor. Each row is one experimental sample = one (cell_line, replicate) pair, with a DNA FASTQ + RNA FASTQ. **Don't fill in `dna_threshold` yet** — leave it out. You'll come back after step 4.

```yaml
project: ovarian_cancer

samples:
  # OV8 (tumor cell line) — 3 biological replicates
  - { cell_line: OV8,  replicate: 1, dna_fastq: OV8_Lib4_DNA_r1,  rna_fastq: OV8_Lib4_RNA_r1  }
  - { cell_line: OV8,  replicate: 2, dna_fastq: OV8_Lib4_DNA_r2,  rna_fastq: OV8_Lib4_RNA_r2  }
  - { cell_line: OV8,  replicate: 3, dna_fastq: OV8_Lib4_DNA_r3,  rna_fastq: OV8_Lib4_RNA_r3  }
  # IOSE (normal control)
  - { cell_line: IOSE, replicate: 1, dna_fastq: IOSE_Lib4_DNA_r1, rna_fastq: IOSE_Lib4_RNA_r1 }
  - { cell_line: IOSE, replicate: 2, dna_fastq: IOSE_Lib4_DNA_r2, rna_fastq: IOSE_Lib4_RNA_r2 }
  - { cell_line: IOSE, replicate: 3, dna_fastq: IOSE_Lib4_DNA_r3, rna_fastq: IOSE_Lib4_RNA_r3 }

analysis:
  bc_threshold: 3
  contrasts:
    - { name: OV8_vs_IOSE, experimental: OV8, control: IOSE }
```

**Per-row fields:**

| Field | What to put |
|---|---|
| `cell_line` | Your cell-line name (e.g. `OV8`, `MCF7`) |
| `replicate` | Integer (1, 2, 3, …) |
| `dna_fastq` | Filename of your DNA FASTQ **without `.fastq.gz`** |
| `rna_fastq` | Same, for the RNA FASTQ |
| `dna_threshold` | **Leave out for now.** Will be filled in step 5. |

**Per-analysis fields:**

| Field | What to put |
|---|---|
| `bc_threshold` | Min supporting barcodes per promoter. Published OvCa used `3`. Higher = stricter. |
| `contrasts` | One entry per ratio you want computed. `experimental` and `control` must match cell-line names from your `samples:` rows. |

### Step 3 — First run

This kicks off Steps 1-8 (alignment, ~hours) plus Step 9 with default thresholds (`dna_threshold: 3` everywhere) so you have *something* to look at right away.

**macOS / Linux (bash or zsh):**

```bash
docker run --rm \
  -v "$(pwd)/fastqs:/data/fastqs" \
  -v "$(pwd)/runs:/data/runs" \
  -v "$(pwd):/app/my-experiment" \
  ghcr.io/syntheticimmunity/trend-dashboard:latest \
  trend run --inputs /data/fastqs --output /data/runs/$(date +%F)/ \
    --samplesheet /app/my-experiment/samplesheet.yaml --profile snakemake
```

**Windows PowerShell:**

```powershell
$today = Get-Date -Format yyyy-MM-dd
docker run --rm `
  -v "${PWD}/fastqs:/data/fastqs" `
  -v "${PWD}/runs:/data/runs" `
  -v "${PWD}:/app/my-experiment" `
  ghcr.io/syntheticimmunity/trend-dashboard:latest `
  trend run --inputs /data/fastqs --output /data/runs/$today/ `
    --samplesheet /app/my-experiment/samplesheet.yaml --profile snakemake
```

When it finishes, you'll see this in `runs/<date>/`:

```
alignment_result_normalized_in_house_pipeline.csv         ← Step 8 output
alignment_result_unnormalized_in_house_pipeline.csv
DNA_threshold_for_samples.pdf                             ← inspect this in step 4
samplesheet.yaml                                          ← copy of your input; edit in step 5
step9_rendered.R                                          ← the actual R that ran (for the bioinformatician path)
ovca_sensor_activity_result_concise.csv                   ← preliminary activity table
ovca_sensor_activity_result_all.csv
THRESHOLDS_DEFAULT                                        ← marker file (deleted automatically once you tune)
```

The `THRESHOLDS_DEFAULT` marker is your reminder: this run used defaults — treat the activity table as preliminary.

### Step 4 — Inspect the DNA distribution PDF

Open `runs/<date>/DNA_threshold_for_samples.pdf`. You'll see one small plot per sample:

- **X-axis**: DNA abundance (in units of the smallest DNA count for that sample)
- **Y-axis**: fraction of barcodes that have any RNA reads at that DNA level

For each sample, look for the X value where the curve **plateaus near 1.0**. That's your DNA threshold for that sample — the point at which DNA coverage is consistently high enough that absent RNA signal is meaningful (rather than just under-sequencing).

Write down a threshold per sample. Typical published values range from 2 (high-coverage) to 30+ (low-coverage).

### Step 5 — Tune thresholds and re-run Step 9 only

Open `runs/<date>/samplesheet.yaml` (the **copy in the run dir**, not your input). Add `dna_threshold` to each row using the values you decided in step 4. Save.

Then re-run Step 9 — replace `2026-05-04` with your actual date dir name:

**macOS / Linux:**

```bash
docker run --rm \
  -v "$(pwd)/runs:/data/runs" \
  ghcr.io/syntheticimmunity/trend-dashboard:latest \
  trend run --resume /data/runs/2026-05-04 --rerun-from step9
```

**Windows PowerShell:**

```powershell
docker run --rm `
  -v "${PWD}/runs:/data/runs" `
  ghcr.io/syntheticimmunity/trend-dashboard:latest `
  trend run --resume /data/runs/2026-05-04 --rerun-from step9
```

This re-renders the R script with your new thresholds and runs Step 9 only — typically **~30 seconds to a few minutes** on full Lib4 data, depending on your machine. Vastly faster than re-running Steps 1-8 (the bowtie2 alignment, which is hours) — that's the whole point of the resume flow. **You can iterate this step as many times as you want** — change a threshold, re-run, inspect, change again. The runner removes the `THRESHOLDS_DEFAULT` marker automatically once every sample has an explicit threshold.

Open the dashboard (`trend dashboard --runs ./runs/`) — your tuned activity table now appears in the Results page next to the bundled OvCa and T-cell projects.

### For bioinformaticians: direct R control

If you'd rather work in R interactively (RStudio, VS Code, or any R session) — perhaps because you want to tweak the contrast logic, add custom QC plots, or simply prefer the cell-by-cell flow the manuscript script was designed for — **skip step 5 entirely**.

Open `runs/<date>/step9_rendered.R` in your R IDE. This file is the manuscript's Step-9 analysis script with **your sample names, your thresholds, your contrasts** already inlined as R variables at the top. It reads `alignment_result_*.csv` from the same directory and writes the activity tables there too.

Run it line by line. Modify any line. Re-run any chunk. The same workflow the original manuscript author used in RStudio, applied to your experiment.

### Common mistakes

- **Editing the input `samplesheet.yaml` in step 5 instead of the copy in the run dir.** The runner uses the per-run copy. Edit the wrong one and your re-run will use the old defaults.
- **Mismatched FASTQ basenames.** If `dna_fastq: OV8_Lib4_DNA_r1` is in your samplesheet but the actual file is `OV8_DNA_r1.fastq.gz` (no `_Lib4_`), the runner errors out at parse time. Rename the file or correct the samplesheet.
- **Forgetting `--rerun-from step9` on iteration.** Without it, the runner triggers a full Steps 1-8 re-alignment (hours). The flag tells the runner "intermediate results are still valid; only redo Step 9."

### HPC / SLURM

If your data is on a cluster, add `--profile slurm` instead of `--profile snakemake` on the first run. The cluster config lives in `pipeline/trend/workflow/profiles/slurm/`.

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
