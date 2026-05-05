# references/

External taxonomy resources and the derived tables we built from them. The dashboard's library composition panels (Figure 1B–E) join enhancer constructs against these resources to produce the Lambert DBD families, the CaCTS cancer-MTF coverage, and the D'Alessio identity-TF coverage breakdowns.

Files committed here:

- **`Table_S1_Lambert_alias_mapping.csv`** — alias resolution for the Lambert TF taxonomy. Resolves the manuscript's 695 direct + 34 alias matches against the 1,068 Lib4 TFs.
- **`Table_S2_DAlessio_tissue_system_mapping.csv`** — tissue/system mapping derived from D'Alessio Table S1. Drives the dashboard's per-system identity-TF coverage.
- **`all_ENCODE_MotifDb_ppm_no_NA_v1.txt`** — position probability matrices keyed by PPM name, used by the dashboard to render sequence logos and rank-distribution plots.
- **`TREND_library_TF_breakdown.md`** — narrative reconciliation of the manuscript's 1,068 / 729 / 695 / 49 numbers, with the per-step joins explicit.

The third-party source PDFs and supplementary tables (Lambert / D'Alessio / Reddy original publications) are excluded from git as copyrighted material — see `.gitignore`.
