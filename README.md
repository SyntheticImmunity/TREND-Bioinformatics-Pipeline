# TREND — Transcription-Factor-Responsive Enhancer Discovery

End-to-end pipeline + interactive dashboard for the TREND enhancer-screening platform. The Lib4 designed library contains ~2.7 million barcoded enhancer-reporter constructs across 1,068 transcription factors; this software takes raw sequencing reads through demultiplexing, barcode extraction, alignment to the Lib4 reference, and per-promoter activity quantification, with a web dashboard for interactive exploration.

---

## 📋 For reviewers

The GitHub repository is **private during the manuscript review period** — you will see a 404 if you try to access it. Use the anonymized mirror the journal forwarded with your review assignment:

> 🔗 **https://anonymous.4open.science/r/TREND-Bioinformatics-Pipeline**

This mirror serves the same code with author identities stripped from commits and identifying terms replaced with `XXXX-N` placeholders. No GitHub account or login is required.

**Most reviewers verify this work in 5–10 minutes by browsing alone.** Open the anonymous URL, then read [`REVIEWERS.md`](REVIEWERS.md) — its "Mode A" section walks you through spot-checking the published numbers (e.g., *204/273 = 74.7% CaCTS coverage*, *11,283 Homeodomain sensors*, *top OvCa hit `ATTTTCCCGCCA_E2F7` at 26.6× selectivity*) directly against the source files. No installation needed.

**Rigorous reviewers can run the verification end-to-end in 20–60 minutes** with the three-tier reproducibility check ([`REVIEWERS.md`](REVIEWERS.md) → Mode B). The repository ships with bundled tiny example datasets so the full pipeline runs on a laptop in minutes — no HPC cluster required.

After paper acceptance the GitHub URL above becomes public and the anonymous mirror is no longer needed.

---

## 🧬 For new users running TREND on your own data

The installation and run loop. Adapt the project name and sample sheet to your experiment.

### One-time install

Pick the path matching your environment:

#### Path A — Docker (easiest, zero dependency conflicts)

```bash
docker pull ghcr.io/syntheticimmunity/trend-dashboard:latest
docker run -p 8000:8000 ghcr.io/syntheticimmunity/trend-dashboard:latest
```

Open `http://localhost:8000`. The same image runs the full pipeline on your own data via volume mounts:

```bash
docker run -v /path/to/fastqs:/data -v /path/to/output:/runs \
  ghcr.io/syntheticimmunity/trend-dashboard:latest \
  trend run --inputs /data --output /runs/$(date +%F)
```

For HPC clusters, convert once to Singularity:

```bash
singularity build trend.sif docker://ghcr.io/syntheticimmunity/trend-dashboard:latest
singularity run -B /scratch:/scratch trend.sif trend run --profile slurm --inputs /scratch/fastqs --output /scratch/runs
```

#### Path B — Conda environment (recommended; fully working today)

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

### Per-experiment loop

```bash
# Scaffold a project from one of the bundled templates
trend init my-experiment --template T_cell_activation     # or: ovarian_cancer
cd my-experiment

# Edit the ONLY configuration you need to touch
$EDITOR samplesheet.yaml      # sample IDs, FASTQ paths, conditions, replicate groups

# Run the 9-step pipeline (workstation)
trend run --inputs ./fastqs/ --output runs/$(date +%F)/

# Or on an HPC cluster — Snakemake handles SLURM submission for you
trend run --inputs /scratch/fastqs/ --output runs/2026-04/ --profile slurm

# Browse results in the dashboard (any computer; doesn't need bowtie2 installed)
trend dashboard --runs ./runs/
```

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

The repository contains all code plus a small set of bundled fixtures (~36 MB) sufficient for the three-tier reviewer reproducibility check. The **full data** (~3 GB: published per-barcode count tables for all screens + the 152 MB Lib4 reference + the 445 MB per-construct metadata) is hosted on Dropbox and fetched by a one-line script:

```bash
# macOS / Linux
bash scripts/download_data.sh

# Windows
pwsh scripts/download_data.ps1
```

You only need this for full library exploration (2.7 M constructs vs the bundled 1,000-promoter subsample) or to apply TREND to your own samples (the Lib4 reference is needed for bowtie2 alignment). **For manuscript verification, the bundled examples are sufficient.**

After paper acceptance, the full dataset will be migrated to a Zenodo deposit with a citable DOI.

---

## Verifying the manuscript's claims (the three reviewer tiers)

Every install path supports the same three reproducibility checks. Run any tier from the dashboard's Verify page or via the CLI:

```bash
trend run --example ovarian_cancer --tier smoke      # ~1 s   no tools needed
trend run --example ovarian_cancer --tier step9      # ~30 s  needs R
trend run --example ovarian_cancer --tier pipeline   # ~3 min needs the full conda env
```

Each prints a self-contained report ending in `overall_pass: True` plus per-file column-by-column match results. Tier 2 is the load-bearing reproducibility check — it confirms the unchanged Step-9 R script reproduces the published activity numbers row-for-row from the bundled subsample of real OvCa alignment data. Tier 3 confirms the full FASTQ-to-counts plumbing on simulated reads.

The dashboard's `/run/example` page exposes the same tiers as click-to-run buttons, with a green "all match" badge and per-file diff if anything differs.

---

## Documentation map

| Document | Audience | Length |
|---|---|---|
| [`README.md`](README.md) | Everyone — first impression | This file |
| [`REVIEWERS.md`](REVIEWERS.md) | Journal reviewers | ~10 min read; ships a 5-min Mode A path and a 30-min Mode B path |
| [`MANUAL.md`](MANUAL.md) | New users / adopters | Comprehensive install, dashboard tour, troubleshooting, glossary |
| [`DASHBOARD_PRD.md`](DASHBOARD_PRD.md) | Engineers extending the platform | Full product requirements |
| [`DESIGN.md`](DESIGN.md) | UI contributors | Visual design system spec |
| [`references/TREND_library_TF_breakdown.md`](references/TREND_library_TF_breakdown.md) | Reviewers + curious adopters | Reconciliation of the 1,068 / 729 / 695 / 49 numbers against Lambert |
| [`CHANGELOG.md`](CHANGELOG.md) | Anyone tracking releases | Release notes per version |

---

## License

MIT — see [`LICENSE`](LICENSE).

## Citation

Citation will be added upon manuscript acceptance. For now, please cite the preprint and link to this repository.

## Contact

Questions, bug reports, and feature requests: open an issue on the GitHub repository (after publication; private during review).
