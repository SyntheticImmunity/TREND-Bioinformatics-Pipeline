# TF mRNA does not predict enhancer activity — standalone figure bundle

Self-contained code + data to regenerate the seven figures showing that
differential TF mRNA expression does not predict TREND synthetic-enhancer
selectivity (ovarian cancer, OV8 vs IOSE).

## Contents
- `mrna_vs_activity_data.csv` — the only input. One row per quantified enhancer
  sensor: `tf`, `sensor_log2_selectivity` (log2 OV8/IOSE), `tf_mrna_log10_ratio`
  (log10 OV8/IOSE TPM, constant per TF). 28,645 sensors across 755 TFs.
- `plot_mrna_vs_activity.py` — reads the CSV and writes all seven figures to
  `figures/` as vector PDF + PNG. All derived quantities (per-TF best/median
  selectivity, ranks, the three reference TF categories, recovery curve, ROC,
  variance decomposition) are computed in the script.
- `make_mrna_docs.py` — writes the two Word documents below.
- `TREND_mRNA_figure_legends.docx` — manuscript-ready figure legends.
- `TREND_mRNA_figure_descriptions.docx` — plain-language descriptions (author use).
- `figures/` — output.

## Run
```bash
pip install numpy pandas scipy matplotlib adjustText python-docx
python plot_mrna_vs_activity.py
python make_mrna_docs.py
```

## Figures
- `fig0_reference` — current view: per-TF mRNA vs median enhancer selectivity (r = −0.02).
- `figA_recovery` — mRNA-ranked TF selection recovers the best enhancers no better than chance (0/50).
- `figB_variance` — within-TF sensor variance ≈ 1.9× between-TF: the signal mRNA cannot see.
- `figC_roc` — mRNA as a classifier of selective TFs: AUC = 0.54 (chance 0.50).
- `figD_quadrant` — best-sensor selectivity vs mRNA, with three reference TF groups
  (screen-best / field-acknowledged ovarian-cancer / most over-expressed).
- `figE_top_overexpressed` — the 20 most over-expressed TFs are unremarkable sensors (1.87× vs 1.76×).
- `figF_rank_rank` — TF rank by mRNA vs by best sensor is a scramble (Spearman ρ = 0.10).

## Data provenance
Built by joining per-TF tumour-vs-normal mRNA (RNA-seq TPM, OV8 and IOSE) to the
ovarian-cancer TREND sensor screen on TF symbol, keeping the 755 TFs expressed in
either cell type (max TPM > 1) that also have sensors.
