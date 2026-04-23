# TREND Pipeline Dashboard — Product Requirements Document

**Document owner:** TREND platform team
**Status:** Draft v1 — ready to scope and build
**Date:** 2026-04-23
**Companion docs:** `README.md` (pipeline reference), `codes/1. Instructions/TREND_pipeline_instructions.docx`, the two pseudocode markdowns under `codes/3. Post_HPC_enhancer_activity_analysis_scripts/code_by_projects/detailed_description_of_the code's_functionality/`

---

## 1. Executive Summary

The TREND dashboard is a local-first web application that **wraps — never rewrites** the existing TREND bioinformatics pipeline. It exists to solve the universal failure mode of manuscript-accessory code: published scripts that *technically run* but practically can't be re-run, re-interpreted, or re-applied by anyone outside the original lab. The dashboard converts TREND from a folder of scripts into a **navigable, runnable, auditable platform** that:

1. Lets a reviewer reproduce a published figure in under ten minutes on a laptop.
2. Lets a wet-lab biologist see what's in the Lib4 library and what each result column means without reading R.
3. Lets a new lab apply TREND to a new biological question by editing a configuration, not by find-and-replacing variable names.
4. Lets a rotation student understand the 9-step pipeline as a *state machine*, not a wall of bash.
5. Showcases TREND's generality (OvCa + T-cell from one library, one pipeline) as a first-class product narrative.

The dashboard is the manuscript's **front door**. It is *not* a re-implementation of TREND.

---

## 2. Background & Problem

### 2.1 What TREND is today
- A 9-step enhancer-screening pipeline built on the Lib4 designed library (`codes/2. HPC_cluster_scripts/required_metadata/Lib4.fasta`).
- Steps 1–8 (FASTQ → barcode counts) live in `codes/2. HPC_cluster_scripts/` and are orchestrated by `Lib4_all_steps_FINAL_111525.sbatch` (SLURM).
- Step 9 (count matrix → enhancer activity) is project-specific, with one R script per project under `codes/3. Post_HPC_enhancer_activity_analysis_scripts/code_by_projects/`.
- Two projects ship with the manuscript: **ovarian cancer** (OV8 / IOSE / ID8) and **T-cell activation** (donor 1 / donor 2).
- Pre-computed intermediate and final outputs live under `project_data/` for both projects.

### 2.2 The pain (from the user-empathy brainstorm, 2026-04-23)
A 10-person session with bioinformaticians, cancer biologists, and graduate students surfaced ten clustered pain points that any reader of a typical manuscript repo hits — all reproduced verbatim or near-verbatim in TREND today:

| # | Pain | Brief |
|---|------|-------|
| 1 | Onboarding cliff | README assumes user knows what FASTQ, RPM, demultiplexing are; no visual map of the 9 steps. |
| 2 | Environment friction | Bowtie2/SAMtools/Cutadapt/FASTX/R/Python — no pinned versions, no preflight check, no container. |
| 3 | Provenance fog | `FINAL_111525` filenames; no link from a result CSV back to the code+inputs+parameters that produced it. |
| 4 | Hard-coded contracts | Sample names (`OV8`, `IOSE`, `ID8`) and the DNA threshold vector `c(2,3,5,6,3,2,30,35)` baked into Step 9. |
| 5 | Reviewer time-to-trust | No tiny example dataset, no expected outputs, no oracle for "did my run reproduce the paper?" |
| 6 | Statistical opacity | Judgement calls (e.g., "75% active" threshold) embedded as constants with no interactive justification. |
| 7 | Project portability | The OvCa Step-9 script doesn't generalize to T-cell despite using the same library. |
| 8 | Library composition is invisible | Figure 1's library design exists only as a cartoon; `Lib4.fasta` and `Lib4_info_concise_060621.csv` are not interactively explorable. |
| 9 | Cryptic output columns | `mean_OV8_to_IOSE_RD_ratio` — definitions live only in the methods section of the paper. |
| 10 | Failure surfacing | When step 5 dies, the user gets a 4,000-line SLURM log, not a plain-language diagnosis. |

### 2.3 Why this matters beyond TREND
TREND is the vehicle, but the dashboard's design solves a class of problem affecting nearly every bioinformatics paper. Done well, it doubles as a **reference pattern for manuscript-accessory tooling**, which strengthens the publication's impact and the platform's adoption.

---

## 3. Goals & Non-Goals

### 3.1 Goals (P0)
- **G1.** A reviewer with no prior exposure to TREND can reproduce one published figure end-to-end in **under 10 minutes** on a Mac/Linux laptop, using a bundled tiny example dataset, with a pass/fail oracle.
- **G2.** Anyone — including a wet-lab biologist who does not read R — can interactively explore the composition of the Lib4 library (Figure 1, made living).
- **G3.** Every result file the dashboard produces carries a provenance record (code commit, parameter set, input hashes, timestamp) viewable in the UI.
- **G4.** Sample names, threshold vectors, and other project-specific parameters move from inside scripts to an editable per-project configuration (sample sheet + parameters file). The two existing projects ship as reference configurations.
- **G5.** When a pipeline step fails, the dashboard surfaces *which step*, *what the underlying tool said*, and *the most likely fix*, without the user opening a log file.

### 3.2 Goals (P1, after MVP)
- **G6.** Interactive parameter exploration — the DNA-abundance threshold can be moved on its diagnostic plot and Step 9 outputs recompute live.
- **G7.** Cross-project comparison view — clicking a TF or promoter in the library viewer shows its activity profile across both shipped projects.
- **G8.** Run history with side-by-side parameter-sweep comparisons.

### 3.3 Non-Goals
- **NG1.** Rewriting the pipeline scripts. Existing code is treated as immutable executable artifacts.
- **NG2.** Replacing SLURM/HPC for production runs on real (full-size) datasets. The dashboard offers a laptop-friendly path *and* delegates to HPC where available.
- **NG3.** Multi-user web service, authentication, billing, hosted deployment. The dashboard is local-first; reviewers run it on their own machine.
- **NG4.** A general-purpose MPRA toolkit. Scope is TREND / Lib4.
- **NG5.** Mobile / tablet support. Desktop browser only.
- **NG6.** Modifying the biological logic of the pipeline. The dashboard exposes parameters; it does not change defaults that produced published results.

---

## 4. Design Constraints (binding)

These constraints are non-negotiable and govern every implementation decision below.

- **C1. Existing pipeline code is immutable by default.** The dashboard invokes the existing `.sbatch`, `.py`, and `.R` files as black-box subprocesses with the same arguments and inputs they accept today.
- **C2. Any modification to existing scripts requires an equivalence test.** If a script *must* change (e.g., to accept an output-directory argument instead of a hard-coded one), the change must be paired with an automated test that runs the old and new versions on the same input and confirms byte-identical or numerically-equivalent (with documented tolerance) outputs. Test artifact lives in `tests/equivalence/`.
- **C3. New code lives in a new top-level directory.** All dashboard code goes under `dashboard/` (frontend, backend, orchestration, tests). The `codes/` and `project_data/` trees are touched only to add — never to modify or remove.
- **C4. Local-first.** The dashboard must run with `docker compose up` (or a single `make dev`) on macOS or Linux with no cloud account, no API key, and no network calls beyond optional dependency installs.
- **C5. Reproducibility-first.** Every runnable action emits a provenance record. No silent state.
- **C6. No documentation drift.** The dashboard reads from the canonical metadata files (`Lib4_info_concise_060621.csv`, `all_enhancer_metadata_111525.csv`, the per-project pseudocode markdowns); it does not re-encode that information in code.

---

## 5. Target Users & Personas

Distilled directly from the brainstorm session participants. These personas anchor every requirement.

| Persona | Role | Primary need | Success looks like |
|---------|------|--------------|--------------------|
| **Hyun-woo (the Reviewer)** | PhD reviewer with 2 weeks and 4 papers | Verify a published figure quickly | One-click example run in <10 min produces the published numbers within tolerance. |
| **Sofia (the Wet-Lab PI)** | Cancer biologist, designed Lib4 | See library + results without reading code | Library viewer + annotated results explorer; can answer "how many constructs per TF?" in 30 seconds. |
| **Tomás (the Adopting Postdoc)** | Wants to apply TREND to a new biology | Configure the pipeline for new samples | Edits a sample sheet and parameters file; does not touch R or Python. |
| **Aisha (the Wet-Lab Grad Student)** | Learning bioinformatics on the side | Run the pipeline on her own data | Preflight check tells her exactly what's missing; pipeline state view tells her where she is. |
| **Ben (the Rotation Student)** | First exposure to bioinformatics | Build a mental model of what TREND does | Library viewer + step-by-step state machine + glossary tooltips. |
| **Priya (the Statistician)** | Validates analytical choices | Justify or change threshold-style parameters | Diagnostic plots are interactive; can sweep parameters and compare runs. |
| **Marco (the Reproducibility Reviewer)** | Open-science focused | Audit the trail from code to figure | Run history with code commit, inputs, parameters, outputs for every run. |
| **Lena (the HPC Engineer)** | Operates pipelines at scale | Trust the wrapper over the scripts | Same scripts, same args; dashboard is a thin shim, not a fork. |
| **Raj (the Computational Biologist)** | Power user, writes adapters | Plug in his own pipeline variants | Step contracts are documented; can swap an executable while keeping the wrapper. |
| **Maya (the Core-Facility Lead)** | Supports many users | Reduce support tickets | Plain-language failure surfacing + glossary cuts onboarding questions. |

---

## 6. Key User Journeys

### 6.1 Reviewer's golden path (P0)
1. Reviewer clones the repo and runs `make dev` (or `docker compose up`).
2. Browser opens to the dashboard home, which shows three on-ramps: **Explore the Library**, **Run the Example**, **Browse Published Results**.
3. Reviewer clicks **Run the Example**. The dashboard:
   - Runs preflight (verifies tools or falls back to the bundled container).
   - Executes Steps 1–9 on the bundled tiny example dataset (~1k reads/sample).
   - Streams plain-language progress (`Step 5 of 9: collapsing UMIs (≈30s)`).
   - Presents the resulting `ovca_sensor_activity_result_concise.csv` rendered as an interactive table, alongside the published `project_data/final_enhancer_activity_results/ovarian_cancer/ovca_sensor_activity_result_concise.csv`, with a numeric-tolerance diff.
4. Reviewer sees a green "Match" badge, reads the data dictionary inline, exits.

**Success metric:** Time from `make dev` to green badge ≤ 10 min on a 2022 MacBook Pro.

### 6.2 Wet-lab PI overview (P0)
1. Sofia opens the dashboard, lands on **Explore the Library**.
2. Sees: total constructs, # TFs covered, distribution of barcodes-per-promoter, breakdown by variable-region category, searchable construct table.
3. Clicks **SOX2** → sees all SOX2 constructs and (P1) their activity in OvCa and T-cell.
4. Opens **Browse Published Results** → sees the OvCa activity table with column tooltips ("RD ratio = RNA reads ÷ DNA reads, normalized within sample, median across barcodes for the same promoter").

### 6.3 Adopting postdoc (P1)
1. Tomás creates a new project from the **+ New Project** button.
2. Dashboard duplicates the T-cell config as a template.
3. Tomás edits the sample sheet (sample names, role: DNA/RNA, condition, replicate group), sets DNA thresholds *interactively* by dragging on the diagnostic plots, saves.
4. Runs Step 9 against his existing alignment outputs. Result CSV is exported to a new folder under `project_data/final_enhancer_activity_results/<his_project>/` with a provenance sidecar.

### 6.4 Rotation student onboarding (P0)
1. Ben opens the dashboard. Lands on **Explore the Library**, gets a concrete artifact first.
2. Hovers any term he doesn't know — tooltip explains. Glossary page accessible from header.
3. Clicks through to **Run the Example**, watches the state-machine view fill in step by step.

---

## 7. Functional Requirements

Each requirement carries a priority (P0 = MVP, P1 = next, P2 = later) and acceptance criteria. Numbering matches the ten dashboard responsibilities surfaced in the brainstorm.

### FR-1. Guided pipeline view (P0)
**What.** A persistent left-rail or top-row visualization of the 9 pipeline steps as a state machine, with status (not started / running / done / stale / failed) and a one-sentence description per step.

**Acceptance criteria**
- Each step shows: name, one-line purpose, primary tool used (e.g., "Cutadapt"), and current status.
- Clicking a step opens its detail pane: inputs, outputs, parameters, last run timestamp, log excerpt.
- A step is marked **stale** if any of its declared inputs has changed since its last successful run.
- The view is identical when running locally (subprocess) or on a cluster (SLURM job state polled).

**Notes for implementation**
- Step contracts (inputs/outputs) live in `dashboard/backend/pipeline/steps.yaml`. This is metadata about existing scripts — the scripts themselves are unchanged.
- Status persistence: `dashboard/state/runs.sqlite` (or JSON files; SQLite preferred for run history queries).

### FR-2. Preflight environment check (P0)
**What.** On first launch and on demand, verify that all external tools and language packages required by the pipeline are present, and clearly explain what to do if not.

**Acceptance criteria**
- Detects: `python` (≥3.7), `R` (≥4.0), `bowtie2`, `samtools`, `fastx_collapser`, `cutadapt`, plus Python packages (`biopython`, `pandas`, `numpy`) and R packages (`tidyverse`, `data.table`, `Rsamtools`).
- For each missing item, displays: (a) what it is in one sentence, (b) recommended install command for the user's OS, (c) the option "Use the bundled Docker container instead."
- Container fallback: a `dashboard/Dockerfile` produces an image with all deps pinned. The dashboard can launch pipeline subprocesses inside that container transparently.
- Re-runs in <5 seconds.

### FR-3. Project & sample-sheet configuration (P0 for read, P1 for write)
**What.** Replace hard-coded sample names and threshold vectors in Step 9 with an editable per-project configuration. The two existing projects ship as reference configs.

**Acceptance criteria**
- Each project has a `project.yaml` (sample sheet + parameters) under `dashboard/projects/<project_name>/`.
- The OvCa and T-cell configs are reverse-engineered from the existing R scripts and shipped on day one. Equivalence test confirms that running Step 9 driven by the config produces identical output to running the original R script unchanged. *If full equivalence requires script edits, those edits are gated by C2.*
- **P0:** UI displays the config read-only with explanations.
- **P1:** UI allows editing and saving a new project config without touching code.
- Sample sheet columns: `sample_id`, `fastq_path` (or `count_column_name` for post-alignment runs), `role` (`DNA`|`RNA`), `condition`, `replicate_group`, `dna_threshold`.

### FR-4. Tiny example dataset & one-click test run (P0)
**What.** A bundled small dataset (~1k reads per sample, ~10 representative library constructs) with expected outputs, runnable end-to-end in under 10 minutes on a laptop.

**Acceptance criteria**
- Lives under `dashboard/example_data/`. Includes raw FASTQs (or starts at the post-alignment step if FASTQ is too large), the barcode key, and an `expected/` folder with reference outputs.
- One-click run executes Steps 1–9 (or the chosen subset) and compares results to `expected/` with documented numeric tolerances.
- Outputs a green/red oracle badge plus a column-by-column diff for any failures.
- Bundled data is small enough to commit to git (target <20 MB total).

### FR-5. Run provenance & history (P0 for capture, P1 for UI history view)
**What.** Every dashboard-initiated run is recorded with sufficient metadata to identify, audit, and re-run it.

**Acceptance criteria**
- Each run produces a `run_<id>/manifest.json` containing: ISO timestamp, git commit of `codes/` and `dashboard/`, software versions (from preflight), input file paths + SHA-256 hashes, full parameter set, output file paths + hashes, exit code per step, total runtime.
- Manifest is co-located with outputs (sidecar) and indexed in `dashboard/state/runs.sqlite`.
- The published-figure run is shipped with the repo as `dashboard/runs/published_v1/manifest.json` so reviewers can see exactly which run generated paper figures.
- **P1:** UI page lists all runs, allows filtering, and supports side-by-side comparison of two runs (parameter diff + output diff).

### FR-6. Library composition viewer (P0)
**What.** Make the TREND library (Figure 1 in the manuscript) interactively explorable. This is both a UX win and a platform-credibility showcase.

**Acceptance criteria**
- Reads `codes/2. HPC_cluster_scripts/required_metadata/Lib4_info_concise_060621.csv` and (optionally) `Lib4.fasta` directly. Never duplicates this data.
- Renders, at minimum:
  - Summary cards: total constructs, # TFs, # promoters, # variable regions, mean barcodes per promoter.
  - Histogram: barcodes per promoter.
  - Stacked bar: constructs per TF.
  - Distribution: variable-region length / category.
  - Searchable, filterable construct table with download-as-CSV.
- Each row links to a construct detail panel (sequence, design rationale from metadata, neighboring barcodes).
- **P1:** Clicking a TF or promoter pivots to that entity's activity profile across both shipped projects (cross-project view).

### FR-7. Interactive parameter exploration (P1)
**What.** Promote the most consequential hard-coded parameter — the per-sample DNA-abundance threshold — from a constant to an interactive control.

**Acceptance criteria**
- Renders the equivalent of `DNA_threshold_for_samples.pdf` as an interactive plot per sample.
- A draggable vertical line per sample selects the threshold; the displayed `c(...)` vector updates live.
- "Recompute downstream" button re-runs Step 9 with the chosen vector and produces a new run with provenance (FR-5). Original published thresholds remain a one-click reset.
- Side-by-side comparison of two runs (e.g., published thresholds vs. user's chosen thresholds): shows promoters that crossed the activity ranking cutoff.

### FR-8. Output explorer with data dictionary (P0)
**What.** Render result CSVs as first-class objects with column-level documentation, filtering, sorting, and links back to library entries.

**Acceptance criteria**
- Each known result CSV (`alignment_result_*_in_house_pipeline.csv`, `ovca_sensor_activity_result_*.csv`, `activation_responsive_enhancer_screening_result_donor*.csv`) has a registered schema in `dashboard/backend/schemas/`.
- Each column carries: name, type, units, one-sentence definition, link to the methods section if applicable.
- Tooltips on column headers display definitions on hover.
- Promoter-ID and barcode-ID columns link to the library viewer (FR-6).
- An export button copies the current filtered view to CSV.
- **Robustness:** the dashboard tolerates real-world filename quirks already present in the data (e.g., `alignment_result_normalized_in_house_pipeline..csv` with the double dot) without requiring rename. Fix is loader-side, not data-side.

### FR-9. Plain-language failure surfacing (P0)
**What.** When any pipeline step fails, the user sees a human-readable explanation and a recommended next action — not raw logs.

**Acceptance criteria**
- Each step's wrapper captures stdout/stderr and runs a small classifier (regex rules + a curated mapping in `dashboard/backend/pipeline/error_hints.yaml`) to identify common failure modes (e.g., "Cutadapt: no adapter matched in any read" → "Check that the adapter sequence in `Step 6` matches your construct.").
- UI shows: failed step, plain-language headline, recommended action, and a collapsible "Show full log" disclosure.
- A "Copy diagnostic bundle" button packages the failed step's manifest, log, and config into a single zip for support.

### FR-10. Construct & adapter parameter visibility (P1)
**What.** Surface the biological parameters embedded in the pipeline (constant regions, BamHI site, RT-handle2, barcode coordinates, adapter sequences) so a wet-lab user can confirm they match their construct.

**Acceptance criteria**
- A "Construct & parameters" view renders an annotated diagram of the Lib4 read structure (5′ adapter — UMI — flanking — 20-bp barcode — flanking — 3′ adapter), with each segment's expected sequence pulled from the pipeline scripts at load time (parsed once, cached).
- Editable in **P2**; read-only in **P1** with explicit "to change, edit `<script>` line N" pointer.

---

## 8. Information Architecture

Proposed page structure (single-page app with five primary views):

```
/                       Home — three on-ramps + status banner
/library                Library composition viewer (FR-6)
/run                    Pipeline runner — state machine (FR-1) + step detail
/run/example            One-click example with oracle (FR-4)
/run/history            Run history & comparisons (FR-5, P1)
/results                Output explorer with data dictionary (FR-8)
/results/<run_id>       Specific run's outputs
/project                Project & sample-sheet configuration (FR-3)
/project/<name>         Specific project config (read-only P0, editable P1)
/construct              Construct & adapter parameter view (FR-10, P1)
/glossary               Plain-language glossary of every term in the UI
/health                 Preflight environment check (FR-2)
```

Persistent UI elements: top nav with the seven main views, a status pill showing preflight result, a "Failures" badge that appears when a recent run errored.

---

## 9. Technical Architecture

### 9.1 Recommended stack
- **Backend:** Python 3.11 + FastAPI. Reasons: the audience is Python-fluent; FastAPI's typed interfaces make step contracts and run manifests pleasant; integrates trivially with subprocess orchestration of existing `.py`, `.R`, and `.sbatch` scripts.
- **Frontend:** React + TypeScript + Vite, Tailwind for styling, TanStack Table for the data-heavy views, Recharts (or Plotly for the interactive threshold plots in FR-7). React is overkill for v1 but pays back at FR-6/FR-7/FR-8.
- **Alternative for v1:** Streamlit single-file app. Faster to ship, weaker UX ceiling. Recommended only if the team wants a visible MVP within 2 weeks. **The PRD assumes FastAPI + React.** A decision to use Streamlit affects acceptance criteria (no real state machine, weaker provenance UI) and should be explicitly logged.
- **State store:** SQLite for run history (single-file, zero ops). JSON sidecars for per-run manifests (greppable, diffable).
- **Job execution:** subprocess for local; thin SLURM submitter for cluster. A shared `Runner` interface in `dashboard/backend/pipeline/runner.py` abstracts the two.
- **Containerization:** `dashboard/Dockerfile` produces an image with bowtie2, samtools, cutadapt, fastx-toolkit, pinned Python and R, and the dashboard itself. `docker-compose.yml` orchestrates the dashboard container alongside (optionally) a worker container.
- **Testing:**
  - **Equivalence tests** (`tests/equivalence/`): for any change to existing scripts or any new wrapper, prove output equivalence. This is the C2 enforcement layer.
  - **Contract tests** (`tests/contracts/`): every step's declared inputs/outputs match what the script actually consumes/produces.
  - **End-to-end** (`tests/e2e/`): the example dataset run produces the expected outputs.

### 9.2 How the dashboard talks to existing code
- Each pipeline step is invoked as a subprocess with the **same command and arguments** the existing `.sbatch` uses today. The wrapper captures stdout/stderr, exit code, and timing.
- Where existing scripts hard-code paths or sample identifiers, the wrapper renders a temporary config file or uses environment variables — **without modifying the script** wherever possible.
- Where modification is unavoidable (e.g., to externalize the threshold vector for FR-7), the modification is paired with an equivalence test (C2) and the original script is preserved as `<name>.original.R` until the test passes in CI.

### 9.3 New code layout
```
dashboard/
  backend/
    main.py                 FastAPI entrypoint
    pipeline/
      runner.py             Local + SLURM execution
      steps.yaml            Step contracts (metadata, not code)
      error_hints.yaml      Plain-language failure mapping
    schemas/                Result-CSV column definitions
    provenance/             Manifest writer
  frontend/
    src/                    React app
  example_data/             Tiny bundled dataset + expected outputs
  projects/
    ovarian_cancer/project.yaml
    T_cell_activation/project.yaml
  runs/
    published_v1/manifest.json   Reference run for the manuscript
  state/runs.sqlite
  Dockerfile
  docker-compose.yml
tests/
  equivalence/
  contracts/
  e2e/
Makefile                    `make dev`, `make test`, `make build`
```

### 9.4 Data flow at a glance
```
                       ┌────────────────────────┐
                       │  React UI (browser)    │
                       └────────────┬───────────┘
                                    │ REST + SSE
                       ┌────────────▼───────────┐
                       │  FastAPI backend       │
                       └──┬───────────┬─────────┘
                          │           │
              ┌───────────▼──┐   ┌────▼────────────┐
              │  Runner      │   │  Provenance     │
              │  (subproc /  │   │  + run history  │
              │   SLURM)     │   │  (SQLite + JSON)│
              └───────┬──────┘   └─────────────────┘
                      │
        ┌─────────────▼──────────────────────────────┐
        │  Existing TREND scripts (UNCHANGED)         │
        │  codes/2. HPC_cluster_scripts/*.py *.R      │
        │  codes/3. .../code_by_projects/*.R          │
        └────────────────────────────────────────────┘
```

---

## 10. Phased Roadmap

The brainstorm explicitly warned against scope sprawl. Sequencing below reflects highest reviewer-and-newcomer impact per week of work.

### Phase 1 — MVP (target: 4–6 weeks)
**Goal: a reviewer can verify a published figure in 10 minutes; a newcomer can grok the platform.**
- FR-1 Guided pipeline view (status only; no fancy DAG)
- FR-2 Preflight environment check
- FR-4 Tiny example dataset & one-click run
- FR-5 Run provenance capture (UI history view deferred)
- FR-6 Library composition viewer
- FR-8 Output explorer + data dictionary
- FR-9 Plain-language failure surfacing
- Glossary page
- Dockerfile + `make dev`

**Exit criteria:** Hyun-woo's golden path (§6.1) and Ben's onboarding path (§6.4) both succeed end-to-end on a fresh laptop.

### Phase 2 — Adopters & Auditors (target: +3–4 weeks)
**Goal: a new lab can use TREND without forking; a reproducibility reviewer has a complete trail.**
- FR-3 Project & sample-sheet configuration (write path)
- FR-5 Run history UI + side-by-side comparison
- FR-7 Interactive parameter exploration (DNA threshold)
- FR-10 Construct & adapter parameter visibility (read-only)
- Cross-project library → activity linking (FR-6 P1 facet)

**Exit criteria:** Tomás's adopter path (§6.3) and Marco's audit path succeed without writing R or Python.

### Phase 3 — Power features (target: +4 weeks)
- Parameter sweeps with multi-run comparison
- HPC submission UI (real cluster integration)
- FR-10 P2 (editable construct parameters with equivalence tests)
- "Publish your run" — bundle a run manifest + outputs as a citable artifact

---

## 11. Success Metrics

Quantitative targets validated post-launch with a small cohort (5–10 external testers).

| Metric | Target | How measured |
|--------|--------|--------------|
| Time-to-first-result for a new reviewer | ≤ 10 min | Cohort timing study |
| Preflight-resolved env issues | ≥ 90% of common cases | Telemetry on `error_hints.yaml` hit rate |
| Cross-project portability | T-cell project runnable from config alone | FR-3 acceptance test |
| Reviewer reproducibility | 1:1 match on example dataset for 100% of cohort | E2E test + manual cohort run |
| Pain-point coverage | ≥ 8 of 10 brainstorm pain points addressed in MVP | This PRD §2.2 mapped to FRs (current: 9 of 10 in Phase 1) |
| Repo issue rate per new user | ≤ 1 setup-related issue per 10 users | GitHub issues post-launch |

---

## 12. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Equivalence tests are hard to satisfy (e.g., R script writes to working dir, not a configurable path) | Medium | High | Wrap with a directory-shim (run in a temp cwd, copy outputs out). Modify script only as last resort. |
| FASTQ-stage example dataset is too big to bundle | Medium | Medium | Bundle a post-alignment dataset starting at Step 9 as the "fast path"; ship a separate "full pipeline" example outside git (S3 link or zenodo). Both paths produce a green oracle. |
| R/Python env conflicts on macOS | High | Medium | Container is the default recommended path; native install is documented but not the primary route. |
| Scope creep (the brainstorm produced 10 great features) | High | High | Roadmap is explicit; Phase 1 scope is fixed; Phase 2/3 only after Phase 1 ships. Phase boundaries are review gates. |
| Streamlit-vs-React decision relitigated mid-build | Medium | Medium | Decision recorded in §9.1; revisit only if Phase 1 demo reveals UX ceiling problems. |
| Reviewer's machine cannot run Docker | Low | Medium | Native install path remains supported; preflight detects Docker absence and falls back. |
| Library metadata file changes (new Lib version) | Medium | Low | FR-6 reads metadata at runtime, never hard-codes; schema is versioned. |
| Hard-coded thresholds in Step 9 differ subtly from what's published | Medium | High | Shipped reference configs are reverse-engineered with equivalence tests against the original scripts; any divergence is a release blocker. |

---

## 13. Open Questions / Decisions to Make Before Building

1. **Frontend choice.** FastAPI + React (recommended) vs. Streamlit (faster to ship). Decide before Phase 1 kickoff.
2. **Example dataset shape.** Synthetic FASTQs (full pipeline, slower) vs. real subsampled FASTQs (full pipeline, licensing OK?) vs. start at Step 9 (fast, doesn't exercise alignment). Recommendation: ship both — fast path as default, full path opt-in.
3. **HPC integration scope in Phase 1.** Local-only in Phase 1 (recommended) vs. include SLURM submission. Recommendation: local-only; add SLURM in Phase 3.
4. **Where does the reference manuscript run live?** A `dashboard/runs/published_v1/` directory with manifest only (outputs already in `project_data/`) vs. duplicating outputs. Recommendation: manifest-only, point to existing `project_data/` paths.
5. **Authentication.** None (local-first, recommended) vs. lightweight token if anyone wants to host. Recommendation: none.
6. **Telemetry.** Off by default; opt-in only for the post-launch metrics study. Anonymized error-hint hit rates only.
7. **Naming/branding.** "TREND Dashboard" vs. "TREND Explorer" vs. "TREND Studio." Recommendation: defer to corresponding author.

---

## 14. Appendix

### 14.1 File inventory the dashboard depends on
| Path | Role |
|------|------|
| `codes/2. HPC_cluster_scripts/Lib4_all_steps_FINAL_111525.sbatch` | SLURM driver for Steps 1–8 (read for reference; not invoked verbatim outside HPC) |
| `codes/2. HPC_cluster_scripts/requred_codes/check_sample_barcode_consistency_v3.py` | Step 1 |
| `codes/2. HPC_cluster_scripts/requred_codes/correct_read_orientation_for_Lib4_mbcf.py` | Step 2 |
| `codes/2. HPC_cluster_scripts/requred_codes/demultiplex_fastq_for_Lib4_FINAL.py` | Step 3 |
| `codes/2. HPC_cluster_scripts/requred_codes/extract_counts_from_samfiles_Lib4.R` | Step 8 |
| `codes/2. HPC_cluster_scripts/required_metadata/Lib4.fasta` | Bowtie2 reference |
| `codes/2. HPC_cluster_scripts/required_metadata/Lib4_info_concise_060621.csv` | Library design metadata — **primary input for FR-6** |
| `codes/3. .../code_by_projects/ovarian_cancer/ovarian_cancer_specific_enhancer_screening_analysis.R` | OvCa Step 9 |
| `codes/3. .../code_by_projects/T_cell_activation/T_cell_activation_responsive_enhancer_screening_analysis.R` | T-cell Step 9 |
| `codes/3. .../code_by_projects/detailed_description_of_the code's_functionality/*.md` | Pseudocode — primary source for step descriptions in FR-1 |
| `codes/3. .../required_metadata/all_enhancer_metadata_111525.csv` | Enhancer metadata for Step 9 |
| `project_data/alignment_results/{ovarian_cancer,T_cell_activation}/` | Step 8 outputs (reference) |
| `project_data/final_enhancer_activity_results/{ovarian_cancer,T_cell_activation}/` | Step 9 outputs (reference for the oracle in FR-4) |

**Known data quirks the loader must handle:**
- `requred_codes` (typo, do not rename — would break existing references).
- `alignment_result_normalized_in_house_pipeline..csv` in the T-cell folder has a double dot.
- A folder name contains an apostrophe and a space (`detailed_description_of_the code's_functionality`).

The dashboard tolerates these; it does not "fix" them.

### 14.2 Pain-point → requirement traceability
| Pain (§2.2) | Addressed by |
|-------------|--------------|
| 1 Onboarding cliff | FR-1, FR-6, Glossary |
| 2 Environment friction | FR-2, Container |
| 3 Provenance fog | FR-5 |
| 4 Hard-coded contracts | FR-3, FR-7 |
| 5 Reviewer time-to-trust | FR-4, FR-5 |
| 6 Statistical opacity | FR-7, FR-8 (data dictionary) |
| 7 Project portability | FR-3 |
| 8 Library composition invisible | FR-6 |
| 9 Cryptic outputs | FR-8 |
| 10 Failure surfacing | FR-9 |

### 14.3 Glossary (seed; lives in the app at `/glossary`)
- **TREND** — Transcription-Factor-Responsive Enhancer Discovery; the platform.
- **Lib4** — The current designed enhancer library.
- **Construct** — One designed library member (TF binding site + variable region + barcode + flanks).
- **Barcode** — 20-bp identifier sequence used to count construct abundance.
- **UMI** — Unique Molecular Identifier; collapsed to remove PCR duplicates.
- **RPM** — Reads Per Million; normalization for sequencing depth.
- **RD ratio** — RNA-to-DNA reads, normalized; the per-construct activity readout.
- **Sample role** — Whether a sample is the DNA (input) or RNA (output) measurement.
- **DNA threshold** — Minimum DNA abundance below which a construct is excluded.
- **Promoter-level score** — Median RD ratio across the barcodes that share a promoter.

---

**End of PRD.**
