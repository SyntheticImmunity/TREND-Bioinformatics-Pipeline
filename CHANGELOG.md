# Changelog

## v0.1.0 — 2026-04-23

Initial release. Three artifacts in one repository:

### `pipeline/` — `trend-pipeline` CLI
- `trend init` — scaffold a project from `ovarian_cancer` or `T_cell_activation` templates
- `trend run` — execute the 9-step pipeline locally or via Snakemake on SLURM (`--profile slurm`)
- `trend run --example {smoke,step9,pipeline}` — three reviewer-facing reproducibility tiers
- `trend dashboard` — launch the web UI pointed at any runs directory
- `trend status` — one-screen run summary
- `trend preflight` — environment check with per-OS install hints
- Bundled Snakemake workflow with conda env definitions and SLURM profile
- Bioconda recipe at `pipeline/conda-recipe/meta.yaml` ready for submission

### `dashboard/` — interactive web dashboard
- Library composition view faithful to manuscript Figure 1 (panels A, B, C, D, E, F)
  - Library target composition pyramid (1,068 → 729 / 91 / 248 decomposition)
  - DBD family composition bar chart (49 Lambert families; 28 named bars + Other)
  - Sensors per DBD family bar chart
  - TREND coverage of CaCTS cancer master TFs across 34 TCGA tumor types
  - TREND coverage of D'Alessio cell identity TFs across 15 anatomical systems
  - Cancer-selectivity scatter for the OvCa project
- Enhancer table with sortable columns, free-text search, Lambert taxonomy badges, and click-to-filter from any panel
- Pipeline runner with 9-step state machine visualization
- Three-tier reproducibility check with green/red oracle badges
- Published-results browser with column-by-column tooltips
- System status page with FR-2 environment preflight
- Lovable-inspired warm cream / charcoal visual system (shadcn/ui + Tailwind)

### `tools/`
- `build_fixtures.py` — deterministic fixture generator for the three reviewer tiers (subsamples real OvCa data + simulates FASTQs with planted activity profiles)

### Reproducibility tiers
- **Tier 1 — Quick check** (1 s, no external tools): comparator validates against bundled published outputs
- **Tier 2 — Activity reproduction** (~30 s, requires R + tidyverse + Rsamtools): unchanged Step 9 R script reproduces published activity from a 1,000-promoter slice of real OvCa data
- **Tier 3 — Full pipeline** (~3 min, requires conda env): Steps 1-9 end-to-end on simulated FASTQs (50 promoters x 5 barcodes x 8 samples) with analytically-correct expected count matrix

### Tests
- 18 passing tests under `tests/` (`pytest tests/ -v`)
  - 7 csv-comparator unit tests (the C2 equivalence predicate)
  - 2 oracle E2E tests (OvCa + T-cell)
  - 9 trend CLI tests

### Documentation
- `README.md` — short overview, install summary
- `MANUAL.md` — comprehensive user + reviewer manual (install, three-tier verification, dashboard tour, adopter walkthrough, troubleshooting, glossary)
- `DASHBOARD_PRD.md` — product requirements
- `DESIGN.md` — visual system specification
- `references/TREND_library_TF_breakdown.md` — TF composition reconciliation against Lambert / Reddy / D'Alessio

### Data hosting
- Code + bundled fixtures: GitHub
- Full data (~3 GB: published alignment count tables + Lib4 reference + per-construct metadata): Dropbox, fetched by `scripts/download_data.{sh,ps1}`
- Post-acceptance: planned migration of full data to Zenodo with citable DOI
