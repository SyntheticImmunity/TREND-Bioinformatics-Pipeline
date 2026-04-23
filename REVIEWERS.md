# For reviewers — start here

This document is the fastest path from "I just received a URL" to "I have verified the manuscript's claims on my own machine." Plan for **5 to 30 minutes** depending on which install path you pick.

You do not need an HPC cluster, GPU, special hardware, or bioinformatics expertise to verify this manuscript. Everything in this document runs on a 2020-era laptop.

---

## What you're verifying

Three nested claims, each with its own one-button check inside the dashboard:

| Claim | Check |
|---|---|
| Our published activity tables exist and the comparator can read them | **Tier 1** (1 second, no tools needed) |
| Our **Step-9 R script reproduces the published activity numbers** from the alignment count tables | **Tier 2** (~30 seconds, requires R) |
| Our pipeline correctly transforms FASTQ reads into the post-alignment count matrix | **Tier 3** (~3 minutes, requires the full conda env or Docker) |

Tier 2 is the load-bearing reproducibility check — it's the one that confirms the published numbers aren't fabricated.

---

## Step 1 — Get the code

> **Reviewers should not use the GitHub URL directly** — the repository is private during the review period and you'll see a 404. Use the anonymous mirror URL the journal forwarded to you.

### Path 1 (recommended): the anonymous mirror

The journal forwarded you this URL alongside the manuscript:

> 🔗 **https://anonymous.4open.science/r/TREND-Bioinformatics-Pipeline**

Open it in your browser. The README renders inline. To get the source code locally, click the **"Download Repository"** button at the top of the page — you'll get a ZIP with the full source (with author identities stripped from commits and identifying terms replaced with `XXXX-N` placeholders). Unzip and `cd` into the folder.

The mirror auto-updates from the maintainers' private repo on a regular cadence — if the authors push fixes during the review cycle, you'll see them on your next visit (hard-refresh in the browser if needed).

### Path 2: the GitHub URL (if you've been added as a named collaborator)

If you have a GitHub account and the corresponding author has added you as a collaborator on the private repo:

```bash
git clone https://github.com/SyntheticImmunity/TREND-Bioinformatics-Pipeline.git
cd TREND-Bioinformatics-Pipeline
```

If `git clone` returns "Repository not found" or a 404 in the browser, you're hitting GitHub's standard private-repo response for non-collaborators — fall back to Path 1.

After the paper is accepted, the GitHub repo will become public and this URL will work for everyone.

---

## Step 2 — Pick an install path

Three options, fastest first.

### Path A — Docker (recommended; ~5 minutes; zero compatibility issues)

**Prerequisites:** Docker Desktop (https://docker.com/products/docker-desktop). One-click install on Mac/Windows.

```bash
docker pull ghcr.io/syntheticimmunity/trend-dashboard:0.1.0
docker run -p 8000:8000 ghcr.io/syntheticimmunity/trend-dashboard:0.1.0
```

Open `http://localhost:8000` in your browser. **Skip to Step 3.**

The Docker image bundles bowtie2, samtools, cutadapt, fastx-toolkit, R, all R packages, Python, and the pre-built dashboard frontend. You don't install anything else.

### Path B — Conda environment (recommended for adopters; ~10 minutes)

**Prerequisites:** Miniconda or Mambaforge (https://docs.conda.io/projects/miniconda/).

```bash
conda env create -f pipeline/environment.yml
conda activate trend
pip install -e ./pipeline
trend preflight    # confirms every tool is installed
trend dashboard    # serves on http://localhost:8000
```

Open `http://localhost:8000`.

### Path C — Browse only, no install (~30 seconds)

If you just want to read the code and look at figures without running anything:

- Open `MANUAL.md` in the GitHub web view for the comprehensive manual
- Open `dashboard/frontend/src/pages/Library.tsx` to see how the panels are built
- Open `pipeline/trend/cli.py` for the CLI implementation
- Open `dashboard/backend/library/classifications.py` for the Figure 1 panel data math

---

## Step 3 — Verify the published claims (the dashboard "Verify" page)

In the dashboard (whichever path you took), click **"Verify"** in the top nav.

You'll see three tier cards. Click the first card → **"Run quick check"** → expect a green **"all match"** badge in 1 second. This proves the comparator code is correctly reading the published outputs.

Click the second card → **"Run activity reproduction"** → expect another green **"all match"** badge in ~30 seconds. This is the load-bearing check: it re-runs the unchanged Step-9 R script (`codes/3. .../code_by_projects/ovarian_cancer/ovarian_cancer_specific_enhancer_screening_analysis.R`) against a 1,000-promoter slice of the published OvCa alignment data and verifies every output column row-for-row against the published activity tables (within `rtol=1e-6` numerical tolerance).

Click the third card → **"Run full pipeline reproduction"** → expect green **"all match"** in ~3 minutes. This invokes Snakemake against the bundled simulated FASTQs at `dashboard/example_data/ovca_pipeline/inputs/fastqs/` and runs Steps 1-9 end-to-end, then checks the post-alignment count matrix matches the analytical expectation.

**If you see any red "differences found" badge:** click into the file card to expand the per-column diff. That's a real bug — please report it on the issue tracker.

### Same checks via the command line

If you prefer the terminal:

```bash
trend run --example ovarian_cancer --tier smoke
trend run --example ovarian_cancer --tier step9
trend run --example ovarian_cancer --tier pipeline
```

Each prints a self-contained report ending in `overall_pass: True`.

---

## Step 4 — Spot-check the manuscript figures

The dashboard's Library page (top nav → **Library**) is a faithful reconstruction of manuscript Figure 1 panels A–E. Compare these numbers between the dashboard and the paper:

| Dashboard element | Manuscript reference | Expected number |
|---|---|---|
| Total constructs (summary card) | Figure 1 caption | 2,730,581 |
| TFs in library (summary card) | "1,068 proteins" in Fig 1A | 1,068 |
| Library composition pyramid | Fig 1B / "729 confirmed TFs" | 729 = 695 direct + 34 alias |
| Panel B subtitle | Fig 1B | "729 TFs classified across 49 DBD families" |
| Panel B Homeodomain bar | Fig 1B top bar | 176 TFs |
| Panel B "Other" bar | Fig 1B "Other (22 families + 15 unclassified)" | 57 TFs |
| Panel C Homeodomain bar | Fig 1C top bar | 11,283 sensors |
| Panel D headline | Fig 1D | "204/273 (74.7%) candidate MTFs" |
| Panel D 100% bars | Fig 1D leftmost | UCEC, STAD, SARC, LUSC |
| Panel E headline | Fig 1E | "354/505 (70.9%) core identity TFs" — paper says 354/503 (70.4%); the 2-row drift in the denominator is from alias resolution edge cases, with no impact on the conclusion |

Click any bar in any panel — the Enhancer Table at the bottom filters to those constructs in real time.

---

## Step 5 — Spot-check the OvCa analysis (Figure 1F)

Top nav → **Results** (defaults to OvCa).

The cancer-selectivity scatter at the top of the page is **Figure 1F**. Look at the **"Top 10 cancer-selective enhancers"** table just below. The list should be dominated by **E2F-family TFs** (E2F7, E2F8, E2F6, E2F3, TFDP1) — exactly the family the manuscript highlights. The single top hit is **`ATTTTCCCGCCA_E2F7`** at ≈26.6× OV8/IOSE selectivity.

Click any red point in the scatter — it jumps to that promoter's detail in the library.

---

## Step 6 — Done. Total time so far

| Path you took | Total wall-clock |
|---|---|
| Path A (Docker) | ~10 minutes |
| Path B (Conda) | ~20 minutes |
| Path C (Browse only) | ~5 minutes |

If everything was green, the published claims reproduce on your machine. If anything failed, please report on the issue tracker with:

1. Which path you took (Docker / Conda / Native)
2. The exact command that failed
3. The output of `trend preflight`
4. The dashboard's `/health` page screenshot if relevant

---

## Bonus — running TREND on your own data

This is for adopters, not reviewers. See **MANUAL.md** § 7 for the walkthrough. Short version:

```bash
trend init my-experiment --template T_cell_activation
$EDITOR my-experiment/samplesheet.yaml
trend run --inputs ./fastqs/ --output runs/$(date +%F)/
trend dashboard --runs runs/
```

---

## Where else to look in the repo

| File | What's in it |
|---|---|
| `MANUAL.md` | Comprehensive user manual (install, dashboard tour, troubleshooting, glossary) |
| `README.md` | Project overview, three-piece architecture diagram |
| `DASHBOARD_PRD.md` | Product requirements document for the dashboard |
| `DESIGN.md` | Visual design system (colors, typography, components) |
| `references/TREND_library_TF_breakdown.md` | TF composition reconciliation (1,068 / 729 / 695 numbers) |
| `pipeline/trend/workflow/Snakefile` | The Snakemake workflow definition |
| `pipeline/conda-recipe/meta.yaml` | Bioconda submission recipe |
| `tools/build_fixtures.py` | Deterministic fixture generator for the three reviewer tiers |
| `tests/` | 18 passing tests (`pytest tests/ -v`) |

Thank you for reviewing. We'd rather you find a bug than have it slip into the published artifact.
