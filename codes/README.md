# codes/

The manuscript's original analysis scripts, **unchanged from publication**. Subdirectories follow the order of the manuscript's methods:

- **`1. Instructions/`** — the original setup and run instructions distributed with the manuscript.
- **`2. HPC_cluster_scripts/`** — Steps 1–8: demultiplexing, orientation flip, adapter trimming, UMI collapse, barcode extraction, alignment to Lib4, and count-table generation. Includes the SLURM driver `Lib4_all_steps_FINAL_111525.sbatch` and per-step Python helpers.
- **`3. Post_HPC_enhancer_activity_analysis_scripts/`** — Step 9: the per-project enhancer-activity R analyses (one script per project, e.g. ovarian cancer and T-cell activation).

These scripts are the source of truth for the published numbers. The `pipeline/` and `dashboard/` trees in this repository wrap and orchestrate these scripts but never modify them — running TREND via the modern CLI or the dashboard exercises this same code.

The `Lib4.fasta` reference and the per-construct metadata CSV are not committed (each exceeds GitHub's 100 MB per-file limit) — fetch them with `scripts/download_data.{sh,ps1}` or use the bundled Docker image, which bakes them in.
