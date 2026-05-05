# Data layout

This directory exists as a placeholder. The TREND pipeline reads its inputs from a few well-defined locations under the repo root:

| Path | What lives there | Where it comes from |
|---|---|---|
| `codes/2. HPC_cluster_scripts/required_metadata/Lib4.fasta` | The Lib4 reference library (152 MB) | GitHub release `library-data-2026-05-04` — see download script |
| `codes/2. HPC_cluster_scripts/required_metadata/Lib4_info_concise_060621.csv` | Per-construct metadata (445 MB) | GitHub release `library-data-2026-05-04` |
| `codes/3. .../required_metadata/all_enhancer_metadata_111525.csv` | Per-enhancer annotations | Bundled in the repo (under 1 MB) |
| `project_data/alignment_results/ovarian_cancer/*.csv` | Full per-barcode count tables (1.2 GB) | GitHub release `library-data-2026-05-04` |
| `project_data/alignment_results/T_cell_activation/*.csv` | Same for T-cell project (1.0 GB) | GitHub release `library-data-2026-05-04` |
| `project_data/final_enhancer_activity_results/**/*.csv` | Published activity tables | Bundled in the repo (~78 MB) |
| `dashboard/example_data/ovca_step9/**/*` | 1,000-promoter subsamples for the Step 9 install-check phase | Bundled in the repo (~28 MB) |
| `dashboard/example_data/ovca_pipeline/**/*` | Simulated FASTQs for the alignment install-check phase | Bundled in the repo (~6 MB) |

**To fetch the release-hosted files:**

```bash
# macOS / Linux
bash scripts/download_data.sh

# Windows PowerShell
pwsh scripts/download_data.ps1
```

The script is idempotent — running it twice is safe; it only downloads what's missing.

**You don't need these files for the bundled install check** — the fixtures in `dashboard/example_data/` are sufficient. The release-hosted files are only needed for:
- Browsing the full library viewer (all 2.7 M barcoded constructs vs the 1,000-promoter subsample)
- Re-running Step 9 against the FULL published alignment data outside the dashboard (the dashboard's *Reproduce* tab fetches them automatically on first click)
- Adopting TREND for your own data (the Lib4 reference is needed for bowtie2 alignment of new samples)
