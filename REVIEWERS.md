# For reviewers — start here

Pick the depth of review that matches your time:

| You want to… | Time | Section |
|---|---|---|
| **Browse the code and judge whether the platform is real** | 5–10 min | **Mode A** below — no installation, browser only |
| **Hands-on verify the published claims on your own machine** | 20–60 min | **Mode B** at the bottom — clone + install + run |

Most reviewers do Mode A only; it's enough to write an informed review. Mode B is for the most rigorous reviewers who want to re-run the analysis themselves on bundled tiny example data.

You do not need an HPC cluster, GPU, or specialized hardware for either mode. Everything in Mode B runs on a 2020-era laptop.

> **Reviewers cannot access the GitHub URL during the review period** (it's private — you'll see a 404). Use the anonymized mirror you received from the journal: 🔗 **https://anonymous.4open.science/r/TREND-Bioinformatics-Pipeline**. After paper acceptance the GitHub repo becomes public and the anonymous mirror is no longer needed.

---

# Mode A — Browse-only review (5–10 minutes, no install)

You can write a solid review just by reading the anonymized repository. Open it in your browser and walk through the four checks below.

## A.1 — Verify the code is real and complete

Skim any of these files in the file tree (one click each on the anonymous page). You should see proper, working code — not skeleton fragments or TODOs:

| File | What it is | Approx. size |
|---|---|---|
| `pipeline/trend/cli.py` | The user-facing `trend` CLI with five subcommands (init / run / dashboard / status / preflight) | ~370 lines |
| `pipeline/trend/workflow/Snakefile` | The Snakemake DAG that orchestrates all 9 pipeline steps | ~250 lines |
| `dashboard/backend/library/classifications.py` | Computes the Figure 1B–E aggregates against Lambert / Reddy / D'Alessio | ~270 lines |
| `dashboard/backend/library/queries.py` | Paginated, filterable, sortable enhancer queries | ~180 lines |
| `dashboard/backend/oracle/run_example.py` | The three-tier reproducibility verifier | ~270 lines |
| `dashboard/frontend/src/pages/Library.tsx` | Main dashboard page with all Figure 1 panels wired together | ~140 lines |
| `tests/equivalence/helpers/csv_compare.py` | The C2 equivalence predicate (numerical-tolerance CSV comparator) | ~150 lines |
| `codes/3. .../code_by_projects/ovarian_cancer/ovarian_cancer_specific_enhancer_screening_analysis.R` | The unchanged Step-9 R script that produces the published activity tables | original manuscript code |

## A.2 — Verify the manuscript's published numbers against the code & docs

Without running anything, these numbers should appear (as stated text) in the README, MANUAL.md, and the relevant code/data files. Cross-check against your manuscript copy:

| Claim in manuscript | Where to find it in the repo | Expected value |
|---|---|---|
| Total constructs in Lib4 | `README.md`, `MANUAL.md` | **2,730,581** |
| Total TFs in library | `README.md`, `references/TREND_library_TF_breakdown.md` | **1,068** |
| Confirmed sequence-specific TFs | `references/TREND_library_TF_breakdown.md`; reconciliation diagram | **729** (= 695 direct + 34 alias) |
| DBD families covered | `dashboard/backend/library/classifications.py` constant `N_LAMBERT_DBD_FAMILIES_TOTAL` | **49** (Lambert taxonomy) |
| Sensors in the Homeodomain family | `dashboard/backend/library/classifications.py` (Panel C aggregate) | **11,283** |
| CaCTS cancer-MTF coverage | `references/TREND_library_TF_breakdown.md` | **204/273 = 74.7%** |
| D'Alessio identity-TF coverage | same file | **354/503 = 70.4%** (mirror computes 354/505 = 70.9% with alias resolution; difference noted in the breakdown md) |
| Top OvCa-selective enhancer | `project_data/final_enhancer_activity_results/ovarian_cancer/ovca_sensor_activity_result_concise.csv` row 1 | **E2F7 promoter (`ATTTTCCCGCCA_E2F7`), ≈26.6× OV8/IOSE selectivity** |
| Top six DBD families account for | `references/TREND_library_TF_breakdown.md` | **67% of confirmed TFs** (489 / 729) |

Click into the CSVs in the file viewer — the anonymous interface renders CSVs as tables.

## A.3 — Verify reproducibility infrastructure exists and is real

| What | Where to find it | Expected size |
|---|---|---|
| Tier-2 fixtures (1,000-promoter subsample of published OvCa run) | `dashboard/example_data/ovca_step9/inputs/` and `expected/` | ~28 MB |
| Tier-3 fixtures (50 promoters × 5 barcodes; 8 simulated FASTQ files; analytically-correct expected count matrix) | `dashboard/example_data/ovca_pipeline/inputs/` and `expected/` | ~6 MB |
| Deterministic fixture generator | `tools/build_fixtures.py` | ~290 lines |
| Tests | `tests/` (3 directories: `equivalence/`, `e2e/`, `cli/`) | 18 tests |
| Bundled published activity tables (the comparison reference for Tier 2) | `project_data/final_enhancer_activity_results/{ovarian_cancer,T_cell_activation}/*.csv` | ~78 MB |

## A.4 — Verify documentation depth and license

- **`README.md`** — project overview, architecture diagram, three-piece deployment story
- **`MANUAL.md`** — comprehensive user manual with install paths, dashboard tour, troubleshooting, glossary
- **`DASHBOARD_PRD.md`** — full product requirements (for context on the design choices)
- **`DESIGN.md`** — visual design system spec
- **`references/TREND_library_TF_breakdown.md`** — the full reconciliation of the 1,068 / 729 / 695 / 49 numbers against Lambert
- **`LICENSE`** — MIT

## ✅ Mode A review checklist

If you can answer "yes" to all of these, your review is well-supported:

- [ ] At least three of the source files in §A.1 contain real, working code
- [ ] The manuscript numbers in §A.2 match what's in the docs/code
- [ ] The fixture data in §A.3 exists and is non-trivial
- [ ] The documentation in §A.4 is substantial, not perfunctory
- [ ] You have no concerns about code quality, organization, or licensing

If you have any concerns, run Mode B to investigate further.

---

# Mode B — Hands-on verification (20–60 minutes)

For reviewers who want to actually run the code and see green oracle badges.

## B.1 — Get the code

Click **"Download Repository"** at the top of the anonymous page. You get a ZIP with the full source code (with author identities stripped from commits and identifying terms replaced with `XXXX-N` placeholders). Unzip and `cd` into the folder.

```bash
unzip TREND-Bioinformatics-Pipeline.zip
cd TREND-Bioinformatics-Pipeline
```

## B.2 — Pick an install path

Three options, fastest first.

### Path A — Docker (recommended; ~5 minutes; zero compatibility issues)

**Prerequisites:** Docker Desktop (https://docker.com/products/docker-desktop). One-click install on Mac/Windows.

```bash
docker pull ghcr.io/syntheticimmunity/trend-dashboard:0.1.0
docker run -p 8000:8000 ghcr.io/syntheticimmunity/trend-dashboard:0.1.0
```

Open **http://localhost:8000** in your browser. Skip to §B.3.

The Docker image bundles bowtie2, samtools, cutadapt, fastx-toolkit, R, all R packages, Python, and the pre-built dashboard frontend. You don't install anything else.

### Path B — Conda environment (~10 minutes)

**Prerequisites:** Miniconda or Mambaforge (https://docs.conda.io/projects/miniconda/).

```bash
conda env create -f pipeline/environment.yml
conda activate trend
pip install -e ./pipeline
trend preflight    # confirms every tool is installed
trend dashboard    # serves on http://localhost:8000
```

Open **http://localhost:8000**.

### Path C — Native (manual install, advanced)

You install the bioinformatics tools system-wide (`brew install bowtie2 samtools cutadapt fastx_toolkit r`, etc.) and then `pip install -e ./pipeline`. Run `trend preflight` to confirm. See `MANUAL.md` § 3 for OS-specific instructions.

## B.3 — Run the three reproducibility tiers

In the dashboard at `http://localhost:8000`, click **"Verify"** in the top navigation. You'll see three tier cards.

### Tier 1 — Quick check (~1 second)

Click the first card → **"Run quick check"**. Expect a green **"all match"** badge in 1 second. This proves the comparator code can read and validate the bundled published outputs.

### Tier 2 — Activity reproduction (~30 seconds)

Click the second card → **"Run activity reproduction"**. Expect a green badge in ~30 seconds. **This is the load-bearing reproducibility check.** It re-runs the unchanged Step-9 R script (`codes/3. .../code_by_projects/ovarian_cancer/ovarian_cancer_specific_enhancer_screening_analysis.R`) against a 1,000-promoter slice of the published OvCa alignment data and verifies every output column row-for-row against the published activity tables (numerical tolerance: `rtol=1e-6`).

### Tier 3 — Full pipeline (~3 minutes)

Click the third card → **"Run full pipeline reproduction"**. Expect a green badge in ~3 minutes. Snakemake invokes Steps 1–9 end-to-end on simulated FASTQs at `dashboard/example_data/ovca_pipeline/inputs/fastqs/` and validates that the post-alignment count matrix matches the analytically-computed expected counts.

### Or run via the CLI

```bash
trend run --example ovarian_cancer --tier smoke
trend run --example ovarian_cancer --tier step9
trend run --example ovarian_cancer --tier pipeline
```

Each prints a self-contained report ending in `overall_pass: True`.

## B.4 — Spot-check the dashboard against manuscript Figure 1

Click **"Library"** in the top nav and verify the live numbers match Figure 1:

| Dashboard element | Figure 1 panel | Expected number |
|---|---|---|
| Library composition pyramid | Fig 1B reconciliation | 1,068 = 729 + 91 + 248 |
| Panel B subtitle | Fig 1B | "729 TFs classified across 49 DBD families" |
| Panel B Homeodomain bar | Fig 1B top | 176 TFs |
| Panel B "Other" bar | Fig 1B "Other (22 families + 15 unclassified)" | 57 TFs |
| Panel C Homeodomain bar | Fig 1C top | 11,283 sensors |
| Panel D headline | Fig 1D | "204/273 (74.7%) candidate MTFs" |
| Panel D 100% bars | Fig 1D leftmost | UCEC, STAD, SARC, LUSC |
| Panel E headline | Fig 1E | "354/505 (70.9%) core identity TFs" |
| Selectivity scatter on /results | Fig 1F | E2F-family TFs at top of "most selective" list |

Click any bar in any panel — the Enhancer Table at the bottom filters in real time.

## B.5 — Done

If every tier was green and the panel numbers matched, the published claims reproduce on your machine. If anything failed, please report on the issue tracker with:

1. Which install path you took (Docker / Conda / Native)
2. The exact command that failed
3. The output of `trend preflight`

---

## Bonus — running TREND on your own data

For reviewers who also wear the adopter hat. See **MANUAL.md** § 7 for the walkthrough. Short version:

```bash
trend init my-experiment --template T_cell_activation
$EDITOR my-experiment/samplesheet.yaml
trend run --inputs ./fastqs/ --output runs/$(date +%F)/
trend dashboard --runs runs/
```

---

## Where else to look

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

Thank you for reviewing. We'd rather you find a bug than have it slip into the published artifact.
