# TREND — User and Reviewer Manual

This manual walks you from `git clone` to verifying the published results to running TREND on your own data. Pick the section that matches your goal:

- **Reviewing the manuscript?** Read sections 1, 2, 3, and 4. ~10 minutes for a quick check; ~1 hour for full reproducibility.
- **Adopting TREND for your own enhancer screen?** Read all sections, especially 6 and 7.
- **Just curious what the dashboard does?** Sections 1, 3, and 5.

---

## 1. What is TREND

TREND (Transcription-Factor-Responsive Enhancer Discovery) is a high-throughput platform for discovering synthetic enhancers. The Lib4 designed library contains ~2.7 million barcoded enhancer-reporter constructs across 1,068 transcription factors. By sequencing both the input library (DNA) and the cellular readout (RNA) for each construct, the platform quantifies enhancer activity across cell contexts and identifies designs with desired specificity (e.g., tumor-selective).

The software in this repository provides:

- **A 9-step bioinformatics pipeline** (`trend-pipeline`) that takes raw FASTQ reads through demultiplexing, barcode extraction, alignment to the Lib4 reference, and per-promoter activity quantification. Runs on a laptop, a workstation, or any HPC cluster.
- **An interactive web dashboard** (`trend-dashboard`) that visualizes the library composition (faithful to manuscript Figure 1), runs the pipeline, and explores results.
- **Three tiers of reviewer-facing examples** for verifying that this code reproduces the published results.

---

## 2. System requirements

| Resource | Minimum | Recommended |
|---|---|---|
| Operating system | macOS 11+ / Linux (any modern distro) / Windows 10+ via WSL2 or Docker Desktop | Linux or macOS |
| RAM | 4 GB | 8 GB |
| Disk space | 1 GB free for the repo and bundled fixtures | 4 GB free if you also pull the published full-size reference data |
| CPU | Any 64-bit CPU | Multi-core helps the alignment step |

You do **not** need an HPC cluster, GPU, or specialized hardware to verify the manuscript or run TREND on small-to-medium datasets. The bundled example dataset runs in under 5 minutes on a 2020-era laptop. A cluster only becomes useful when you process your own large FASTQ files (10+ GB).

---

## 2.5 Data: what's in git, what's downloaded separately

The repository contains all the **code** plus a small set of **bundled fixtures** sufficient for the bundled install check. The **full data** (1.0–1.2 GB of published alignment count tables per project, the 152 MB Lib4 reference, the 18 MB per-enhancer metadata is bundled in the repo) is hosted as assets on this repository's GitHub release `library-data-2026-05-04` and fetched by a one-line script:

```bash
# macOS / Linux
bash scripts/download_data.sh

# Windows
pwsh scripts/download_data.ps1
```

This downloads ~3 GB and places each file at the path the pipeline expects. The script is idempotent — safe to re-run anytime; it skips files already present.

**Release URL:** https://github.com/SyntheticImmunity/TREND-Bioinformatics-Pipeline/releases/tag/library-data-2026-05-04

**You don't need to download anything for the dashboard's install check or manuscript reproduction.** The install check uses the bundled fixtures in `dashboard/example_data/`; the *Reproduce* tab fetches the per-project count tables from the same GitHub release automatically on first click. You only need to run this script if you want to:

- Browse the full library viewer at all 2.7 million barcoded constructs (the bundled view shows a 1,000-promoter subsample)
- Re-run Step 9 against the **full** published alignment data outside the dashboard (e.g., on a cluster, or in your own R session)
- Apply TREND to your own samples (you'll need `Lib4.fasta` for bowtie2 alignment)

After paper acceptance, this dataset will be migrated to a Zenodo deposit with a citable DOI.

---

## 3. Installation — three paths

Pick the one that matches your situation. Path A is fastest if you just want to verify the manuscript; Path B is the standard if you're adopting TREND for your own work; Path C is for users who already have the bioinformatics tools installed.

### Path A — Docker (easiest, no terminal expertise required)

Best for reviewers who want a guaranteed-working setup with zero compatibility issues.

**Prerequisites:** Docker Desktop installed (download from https://docker.com/products/docker-desktop). On Windows this is one click; on macOS it's a drag-to-Applications.

**Install + run (one command):**

```bash
docker run -p 8000:8000 ghcr.io/<owner>/trend-dashboard:0.1.0
```

That's it. The container bundles bowtie2, samtools, cutadapt, fastx-toolkit, R, all required R packages, Python, and the pre-built dashboard frontend. Open `http://localhost:8000` in your browser.

**Notes:**
- First-time pull is ~2 GB and takes a few minutes; subsequent runs are instant.
- The dashboard runs at `http://localhost:8000`.
- To stop: press Ctrl-C in the terminal, or `docker stop <container-id>`.

### Path B — Conda environment (recommended for adopters)

Best if you'll modify the pipeline, run it on your own data, or work with it long-term.

**Prerequisites:** Miniconda or Mambaforge installed (https://docs.conda.io/projects/miniconda/). If you've used Bioconda before, you already have this.

**Install:**

```bash
git clone https://github.com/<owner>/TREND.git
cd TREND
conda env create -f pipeline/environment.yml
conda activate trend
pip install -e ./pipeline
```

The conda step takes ~5 minutes and pulls bowtie2 2.3.4.3, samtools, cutadapt, fastx-toolkit, R + tidyverse + Rsamtools, plus all Python dependencies. The `pip install -e ./pipeline` step makes the `trend` command-line tool available globally inside the conda environment.

**Verify the install:**

```bash
trend --version       # should print: trend 0.1.0
trend preflight       # checks every tool; should report "ok" or "degraded"
```

### Path C — Native (manual install, advanced)

Best if you already have R and the bioinformatics tools installed system-wide.

**Prerequisites:** Python 3.10+, Node.js 20+, and the pipeline tools available via your system package manager (`brew`, `apt`, etc.).

**Install:**

```bash
git clone https://github.com/<owner>/TREND.git
cd TREND
pip install -e ./pipeline
cd dashboard/frontend && npm install && cd -
```

**Install bioinformatics tools (macOS shown; adjust for your OS):**

```bash
brew install bowtie2 samtools cutadapt fastx_toolkit r
R -e 'install.packages(c("tidyverse", "BiocManager"))'
R -e 'BiocManager::install("Rsamtools")'
```

`trend preflight` will tell you exactly which pieces are missing.

---

## 4. Verifying the published results — three tiers

The dashboard ships with three reproducibility checks, each verifying a different layer of the manuscript's claims. Pick the deepest one your install supports.

### Tier 1 — Quick check (1 second, no tools required)

Confirms the dashboard's comparison machinery is wired up. Compares the bundled published activity tables against themselves — passes trivially, but proves the comparator code is reading and processing the published outputs correctly.

```bash
trend run --example ovarian_cancer --tier smoke
```

You should see:
```
  project:      ovarian_cancer
  tier:         smoke
  mode:         stub
  overall_pass: True
  runtime:      ~1.0s
  [MATCH] ovca_sensor_activity_result_concise.csv: all 13 columns equivalent across 57715 rows
  [MATCH] ovca_sensor_activity_result_all.csv:     all 53 columns equivalent across 57715 rows
```

Or run from the dashboard: open `http://localhost:8000/run/example`, click the "Quick check" tier card, then "Run quick check".

### Tier 2 — Activity reproduction (30 seconds, requires R)

Verifies the central claim of the manuscript: that the unchanged Step 9 R script reproduces the published per-promoter activity numbers. Re-runs the script against a 1,000-promoter slice of the published OvCa alignment data and checks every output column row-for-row against the published activity tables (within `rtol=1e-6` numerical tolerance).

```bash
trend run --example ovarian_cancer --tier step9
```

Expected output (with R installed):
```
  tier:         step9
  mode:         real
  overall_pass: True
  [MATCH] ovca_sensor_activity_result_concise.csv: all 13 columns equivalent across 1000 rows
  [MATCH] ovca_sensor_activity_result_all.csv:     all 53 columns equivalent across 1000 rows
```

Without R, the tier falls back to "stub" mode (compares the bundled outputs to themselves so you can see what the report looks like).

### Tier 3 — Full pipeline reproduction (3 minutes, requires conda env)

Verifies the end-to-end plumbing: starts from simulated FASTQ files, runs Steps 1–9 (orientation correction, demultiplexing, adapter trimming, UMI collapse, barcode extraction, bowtie2 alignment, count tabulation, activity quantification), and confirms the post-alignment count matrix matches the analytically-computed expected counts.

```bash
trend run --example ovarian_cancer --tier pipeline
```

The bundled FASTQs (`dashboard/example_data/ovca_pipeline/inputs/fastqs/`) contain 8 samples × ~30,000 reads each, designed to exercise every step of the pipeline at trivial compute cost. The expected count matrix is deterministic — every read knows which barcode it's for, so the post-Step-8 counts are exactly predictable.

### How to choose a tier

| You have… | Use Tier |
|---|---|
| Just Python (no R, no bioinformatics tools) | 1 |
| Python + R | 1, 2 |
| Full conda env (or Docker) | 1, 2, 3 |

For manuscript verification, **Tier 2 is the load-bearing check** — it confirms the published numbers are reproducible. Tier 3 confirms the pipeline plumbing works end-to-end on a real-shaped FASTQ workload.

---

## 5. Using the dashboard

Open `http://localhost:8000` after starting the dashboard (Path A: it's already running; Path B/C: `trend dashboard`). Seven main pages, accessible from the top nav.

### Home (`/`)
Three on-ramp cards (Library, Verify, Results) plus the "How TREND works" three-step workflow schematic from Figure 1A.

### Library (`/library`)
The most-visited page. Eight sections, top to bottom:

1. **Five summary cards** — total constructs (2,730,581), unique promoters (54,193), median barcodes per promoter (30.0), human-curated TFs (1,068), variable regions (57,715).
2. **Library target composition** — three-level horizontal pyramid breaking the 1,068 library targets into confirmed sequence-specific TFs (729 = 695 direct + 34 alias), Lambert non-TFs (91), and proteins outside the Lambert census (248). Reproduces the manuscript's TF reconciliation in one glance.
3. **Panel B** — DNA-binding domain family composition, horizontal bar chart of all 49 Lambert DBD families with the 22 smallest folded into "Other (22 families + 15 unclassified)". Click any bar to filter the enhancer table below.
4. **Panel C** — Sensors per DBD family, same family ordering with sensor counts (Homeodomain tops at 11,283).
5. **Panel D** — TREND coverage of cancer master TFs across 34 TCGA tumor types. Stacked bars: red = in TREND, grey = absent. Click a bar to filter the enhancer table to TFs that are CaCTS MTFs for that tumor type.
6. **Panel E** — TREND coverage of cell identity TFs across 15 anatomical systems (D'Alessio). Same interactions as Panel D.
7. **Two histograms** — barcodes-per-promoter distribution and variable-region length distribution.
8. **Enhancer table** — paginated, sortable table of all 57,715 designed enhancers. Search box matches across TF, TFBS sequence, PPM name, or variable region. Sortable columns include `# Barcodes` (most-covered enhancers) and `Variable region` (longest-first). Lambert columns (DBD family, assessment) are shown as compact badges.

The active filter from any panel is shown as a pill next to the page title with a ✕ to clear.

### Verify (`/run/example`)
Three tier cards (Quick check / Activity reproduction / Full pipeline reproduction) — see section 4. Click a card to select, then "Run …" to execute. Result renders as a green-or-red oracle badge with per-file column-by-column diffs.

### Pipeline (`/run`)
Visualizes the 9 steps of the TREND pipeline as a state machine. "Simulate a run" button steps through all 9 in dry-run mode (no tools required) so you can see the orchestration UI. Recent runs appear in a table below.

### Results (`/results`)
Browses the published activity CSVs for both projects (ovarian cancer + T-cell activation) with column-by-column tooltips. The OvCa view also includes a **cancer-selectivity scatter** (Figure 1F): each point is one promoter, x-axis is log2(OV8/IOSE), y-axis is log10(OV8 RD ratio). Cancer-selective enhancers are highlighted in red. Click any red point to jump to that promoter in the library.

### Projects (`/project`)
Describes the two bundled projects (OvCa, T-cell) with cell lines, replicates, threshold parameters, and a `trend init` example for scaffolding your own.

### Glossary (`/glossary`)
Definitions for every domain term used in the dashboard (RD ratio, UMI, RPM, barcode, etc.).

### System (`/health`)
Backend status + the FR-2 environment check (which pipeline tools are installed, with per-OS install hints for any that are missing).

---

## 6. Using the command-line interface

The `trend` command is the canonical entry point for both reviewers and adopters. All subcommands accept `--help` for detailed flags.

```bash
trend --version            # version banner
trend --help               # list of subcommands
trend preflight            # check installed tools, print install hints
trend init <name>          # scaffold a new project from a template
trend run --example …      # reviewer oracle (see section 4)
trend run --inputs … --output …    # run pipeline on your own data
trend dashboard            # launch the web dashboard
trend status <run_id>      # one-screen summary of a finished run
```

### `trend init`

Scaffolds a new project directory from a template, ready to edit:

```bash
trend init my-experiment --template ovarian_cancer
ls my-experiment/
# samplesheet.yaml   project.yaml   README.md
```

`samplesheet.yaml` is the **only file you need to edit** — it lists samples, FASTQ paths, sample roles (DNA / RNA), conditions, replicate groups, and per-sample DNA thresholds.

### `trend run` modes

```bash
# Reviewer oracle (bundled example)
trend run --example ovarian_cancer --tier {smoke,step9,pipeline}

# Run on your own data, locally
trend run --inputs ./fastqs/ --output ./runs/$(date +%F)/

# Run on an HPC cluster via SLURM
trend run --inputs /scratch/fastqs/ --output /scratch/runs/2026-04/ --profile slurm

# Dry-run preview of which steps would execute
trend run --inputs ./fastqs/ --output ./runs/test/ --dry-run
```

### `trend dashboard`

Launches the web dashboard pointed at a runs directory (defaults to `./runs/`):

```bash
trend dashboard --runs ./runs/                 # local
trend dashboard --runs ~/cluster-runs/         # SSHFS-mounted cluster outputs
```

The dashboard never needs the bioinformatics tools installed — it's a viewer for runs produced anywhere.

---

## 7. Running on your own data

For adopters who want to apply TREND to a new biology.

### Step 1: Scaffold a project

```bash
conda activate trend     # if you used Path B
trend init my-tcell-experiment --template T_cell_activation
cd my-tcell-experiment
```

### Step 2: Edit the sample sheet

Open `samplesheet.yaml` in any text editor. Replace the example sample IDs and FASTQ paths with your own:

```yaml
project: T_cell_activation
samples:
  - { id: donor3_rest, fastq: fastqs/donor3_rest.fastq.gz, role: RNA, condition: rest, donor: 3, replicate_group: 1, dna_threshold: 2 }
  - { id: donor3_stim, fastq: fastqs/donor3_stim.fastq.gz, role: RNA, condition: stim, donor: 3, replicate_group: 1, dna_threshold: 3 }
  # add more samples...
analysis:
  bc_threshold: 8
  contrasts:
    - { name: stim_vs_rest_donor3, stim: donor3_stim, rest: donor3_rest }
```

### Step 3: Run the pipeline

```bash
# Workstation
trend run --inputs ./fastqs/ --output runs/2026-04-23/

# HPC (one extra flag — Snakemake handles SLURM submission)
trend run --inputs /scratch/fastqs/ --output runs/2026-04-23/ --profile slurm
```

The runner streams per-step progress. On a workstation with 8 cores, a typical 16-sample run takes hours-to-overnight depending on read depth.

### Step 4: Explore the results

```bash
trend dashboard --runs runs/
```

Open `http://localhost:8000` — the new run appears in `/run/history`. To also surface your activity table on the **Results** page (with the strip plot, sortable selective-enhancer table, drill-down to PWM and construct pages, and CSV download — the same machinery the bundled OvCa and T-cell projects use), see the next step.

### Step 4a: Visualize your own results in the dashboard

The Results page is project-agnostic. Two pieces are needed: a CSV with the right shape, and a one-block config entry that points the dashboard at it. After that, the page works the same as for the bundled projects — sequence logos, sort/filter, drill-downs, and CSV download all come for free.

**1. Drop your CSV at the expected path**

```
data/final_enhancer_activity_results/<your_project_name>/<your_file>.csv
```

**2. Required columns**

The CSV must contain the columns below. Names marked *configurable* are mapped via the config entry in step 3 — they don't have to match the OvCa names; you tell the dashboard what your column is called.

| Column | Type | Required? | Notes |
|---|---|---|---|
| `promoter_name` | string | yes | Must match a `promoter_name` in the bundled `library.sqlite`. Drives the construct drill-down. |
| `by_ppm_name` | string | yes | PPM identifier — drives the sequence-logo display and the PWM drill-down. Tab-separated and `_v\d+` suffix forms are tolerated. |
| `rank` | int | yes | Rank of this enhancer within the PPM (smaller = better-scoring). |
| (experimental activity) | float | yes (configurable) | Per-promoter activity in your experimental condition. e.g. `stim_activity`. |
| (control activity) | float | yes (configurable) | Per-promoter activity in your control condition. e.g. `rest_activity`. |
| (selectivity ratio) | float | yes (configurable) | Experimental / control ratio (in linear or log space — the dashboard plots it as-is on a log2 axis). |
| (TF name) | string | yes (configurable) | The per-row TF label shown in the table. |

Any additional columns are silently ignored.

**3. Add a config entry**

Append a block to `_SELECTIVITY_PROJECTS` in `dashboard/backend/main.py`:

```python
"my_project": {
    "csv": "my_activity_table.csv",     # filename inside the project folder
    "exp_col": "stim_activity",         # your experimental-condition column
    "ctrl_col": "rest_activity",        # your control-condition column
    "ratio_col": "stim_over_rest",      # your selectivity-ratio column
    "tf_col": "tf_name",                # your TF-name column
    "title": "Stim/Rest",               # drives column headers in the table:
                                        # "Stim Activity", "Rest Activity", "Stim/Rest"
},
```

Restart the dashboard backend (`trend dashboard` or the bare `uvicorn` command in §3 Path C). Your project appears in the Results page's project dropdown automatically.

**What you get for free**

- Strip plot of every enhancer (log2 ratio vs. log10 experimental activity), with selective enhancers highlighted.
- Sortable, filterable selective-enhancer table — click a header to sort, shift+click for secondary sort, type in any column to filter.
- Drill-down from any row to a per-construct page (with cross-project performance comparison) and to a per-PWM page (with sequence logo and activity histogram).
- Download CSV button that exports the currently filtered, sorted set.
- Project-aware column labels everywhere ("Stim Activity" instead of the OvCa "OV8 Activity", etc.) — driven entirely by your `title` value.

### Step 5: Share with collaborators

A run is a single folder containing a manifest and outputs:

```bash
tar czf my-trend-run.tgz runs/2026-04-23/
# Send the tarball to a collaborator. They unpack it and:
trend dashboard --runs ./runs/
# Same dashboard, same data.
```

The manifest (`manifest.json`) records the code commit, software versions, input file hashes, parameters, and per-step timings — so anyone running it later can verify exactly what was run.

---

## 8. Troubleshooting

### `trend preflight` reports missing tools

The preflight output lists every missing piece with an install hint. Common cases:

| Missing | Fix |
|---|---|
| `Rscript` | `conda install -c bioconda r-base r-tidyverse bioconductor-rsamtools` (or use Docker) |
| `bowtie2` | macOS: `brew install bowtie2`; Linux: `sudo apt install bowtie2`; Windows: use Docker |
| `cutadapt` | `pip install cutadapt` (works on all platforms) |
| `fastx_collapser` | macOS: `brew install fastx_toolkit`; Linux: `sudo apt install fastx-toolkit`; Windows: use Docker (no native build) |
| Python packages | `pip install biopython pandas numpy duckdb` |

If many tools are missing, switch to Path A (Docker) — it bundles everything pre-built.

### Dashboard says "Library data not loaded"

The library SQLite database hasn't been built yet. Run:

```bash
cd dashboard
make ingest
```

Takes ~20 seconds the first time; idempotent thereafter.

### A pipeline step fails with a long stderr

The dashboard's failure classifier converts common stderr patterns into plain-language hints. If you see one, follow its "Recommended action". Otherwise, the full log lives in the run manifest:

```bash
trend status <run_id>
# Or open dashboard/runs/<run_id>/manifest.json directly
```

If you need help, the manifest has everything a maintainer needs to diagnose: code commit, tool versions, exact stderr tail, and input file hashes.

### Port 8000 or 5173 is already in use

The dashboard backend defaults to port 8000; the dev frontend defaults to 5173. To use different ports:

```bash
trend dashboard --port 8080
# or for the dev frontend:
cd dashboard/frontend && npm run dev -- --port 5174
```

### `make ingest` is slow on first run

Ingesting the 2.7M-row Lib4 metadata into SQLite via DuckDB takes ~20 seconds. It's idempotent — only runs again if you change the source CSV. The resulting SQLite is ~835 MB and is mounted as a Docker volume so it survives container restarts.

### Tier 3 says "Tools not installed: snakemake, bowtie2"

You're running outside the conda environment or Docker container. Tier 3 requires the full pipeline stack:

```bash
conda activate trend     # if using Path B
# or use Docker (Path A) which has everything pre-installed
```

### Frontend won't build (`npm run build` fails)

Ensure Node 20+ is installed (`node --version`). If using Path B, conda's Node should suffice. If you see TypeScript errors after editing source files, they're real — fix the offending file.

---

## 9. Getting help

- **Documentation:** This manual + `README.md` + `DASHBOARD_PRD.md` (full product spec) + `DESIGN.md` (visual system) all live in the repo root.
- **Issue tracker:** GitHub issues at `https://github.com/<owner>/TREND/issues` — please attach the run's `manifest.json` so the maintainers have the full reproducible context.
- **Discussion:** GitHub Discussions for usage questions that aren't bugs.
- **Contact:** Corresponding author of the manuscript.

When filing an issue, include:
1. The output of `trend --version`
2. The output of `trend preflight`
3. Your install path (Docker / Conda / Native)
4. The exact command that produced the error
5. The full stderr or, ideally, the offending run's `manifest.json`

---

## Appendix: glossary of terms used in this manual

| Term | Meaning |
|---|---|
| Lib4 | The current designed enhancer library — ~2.7 million barcoded constructs across 1,068 TFs. |
| Construct (sensor) | One barcoded library member: a TF binding site + variable region + flanking constants + a unique 20-bp barcode. |
| Promoter | An enhancer design (TFBS variant + TF), backed by multiple barcoded constructs. ~54,000 unique promoters in Lib4. |
| Enhancer | Same as promoter in this codebase; the term used in the manuscript. |
| RD ratio | RNA / DNA reads per construct, normalized; the per-construct activity readout. |
| DNA threshold | Minimum DNA abundance below which a construct is excluded from analysis (filters out poorly-represented designs). |
| bc_threshold | Minimum number of supporting barcodes per promoter for the promoter to be reported in Step-9 outputs. |
| Manifest | Per-run JSON sidecar capturing code commit, tool versions, input/output hashes, parameters, and per-step timings. |
| Tier (1/2/3) | The three reviewer-facing reproducibility checks; see section 4. |
| Stub mode | When a required tool isn't installed, the oracle compares bundled expected outputs to themselves so the report shape is visible without actually running the tool. |
| CaCTS | Algorithm from Reddy et al. 2021 that identifies candidate cancer master transcription factors per tumor type. |
| Lambert taxonomy | The Lambert et al. 2018 census of human transcription factors, classified into 49 DNA-binding domain families. |
