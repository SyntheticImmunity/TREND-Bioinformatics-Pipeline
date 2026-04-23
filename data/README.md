# Data layout

This directory exists as a placeholder. The TREND pipeline reads its inputs from a few well-defined locations under the repo root:

| Path | What lives there | Where it comes from |
|---|---|---|
| `codes/2. HPC_cluster_scripts/required_metadata/Lib4.fasta` | The Lib4 reference library (152 MB) | Dropbox — see download script |
| `codes/2. HPC_cluster_scripts/required_metadata/Lib4_info_concise_060621.csv` | Per-construct metadata (445 MB) | Dropbox |
| `codes/3. .../required_metadata/all_enhancer_metadata_111525.csv` | Per-enhancer annotations | Bundled in the repo (under 1 MB) |
| `project_data/alignment_results/ovarian_cancer/*.csv` | Full per-barcode count tables (1.2 GB) | Dropbox |
| `project_data/alignment_results/T_cell_activation/*.csv` | Same for T-cell project (1.0 GB) | Dropbox |
| `project_data/final_enhancer_activity_results/**/*.csv` | Published activity tables | Bundled in the repo (~78 MB) |
| `dashboard/example_data/ovca_step9/**/*` | 1,000-promoter subsamples for Tier-2 verification | Bundled in the repo (~28 MB) |
| `dashboard/example_data/ovca_pipeline/**/*` | Simulated FASTQs for Tier-3 verification | Bundled in the repo (~6 MB) |

**To fetch the Dropbox-hosted files:**

```bash
# macOS / Linux
bash scripts/download_data.sh

# Windows PowerShell
pwsh scripts/download_data.ps1
```

The script is idempotent — running it twice is safe; it only downloads what's missing.

**You don't need the Dropbox files for tier-1/2/3 verification** — the bundled examples in `dashboard/example_data/` are sufficient. The Dropbox files are only needed for:
- Browsing the full library viewer (all 2.7 M barcoded constructs vs the 1,000-promoter subsample)
- Re-running Step 9 against the FULL published alignment data (vs the 1,000-promoter subsample)
- Adopting TREND for your own data (the Lib4 reference is needed for bowtie2 alignment of new samples)
