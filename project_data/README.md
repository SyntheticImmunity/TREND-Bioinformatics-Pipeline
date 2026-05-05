# project_data/

Bundled outputs from the published TREND analyses. Two projects are included:

- **`final_enhancer_activity_results/{ovarian_cancer,T_cell_activation}/`** — the per-promoter activity tables that appear in the manuscript's figures and supplementary tables. Committed in this repository (~50 MB total). These are the *deposited reference outputs* you compare against when reproducing.

- **`alignment_results/{ovarian_cancer,T_cell_activation}/`** — post-alignment count tables (the inputs to Step 9). Each pair is ~1.0–1.2 GB and exceeds GitHub's 100 MB per-file limit, so they are not committed here. Two ways to obtain them:
  - Run `scripts/download_data.{sh,ps1}` to fetch from this repository's GitHub release (`library-data-2026-05-04`).
  - Click *Reproduce this analysis* on the dashboard's Reproduce tab, which fetches them from the same release on first use.

For the manuscript-reproduction workflow that uses both directories together, see [`REVIEWERS.md`](../REVIEWERS.md) § *Reproducing the manuscript's results*.
