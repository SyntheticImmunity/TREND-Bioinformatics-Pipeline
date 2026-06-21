# TREND T-cell-activation variant analysis — figure reproduction bundle

Self-contained code + data to regenerate the variant-level figures for the
**T-cell activation** screen. This is a cross-context **replication** of the
ovarian-cancer bundle (`../standalone/`): identical analysis logic, definitions,
and figure set — only the data and the two cell states differ (activated *Stim*
vs resting *Rest* T cells; selectivity = `log2(Stim/Rest)`). The two figure sets
are therefore directly comparable.

## Contents
- `trend_tcell_variants.csv` — the only input. One row per quantified enhancer variant.
- `make_figures.py` — reads the CSV and writes all seven figures to `figures/`.
- `make_docs.py` — writes the figure legends + conclusions as Word documents.
- `figures/` — output: each figure as a **vector PDF** (publication) + a **PNG** preview.

## Run
```bash
pip install numpy pandas scipy matplotlib plotnine python-docx
python make_figures.py
python make_docs.py
```
No other files are needed (the per-variant motif affinity is pre-computed into the CSV).
The CSV was built from `project_data/.../T_cell_activation/activation_responsive_enhancer_screening_result_donor1.csv`
and `references/all_ENCODE_MotifDb_ppm_no_NA_v1.txt` by `../_build_tcell.py`.

## Data columns (`trend_tcell_variants.csv`)
| column | meaning |
|---|---|
| `pwm` | unique position-weight-matrix id (ENCODE/MotifDb source motif) |
| `tf` | human-curated transcription-factor name |
| `promoter` | unique variant id (TFBS sequence + TF) |
| `tfbs_sequence` | the variant's TF binding-site sequence |
| `rel_affinity` | fraction-of-consensus relative affinity of the variant vs its **own** PWM; 1.0 = consensus |
| `n_repeats` | number of tandem TFBS copies in the synthetic enhancer |
| `stim` | mean activity (RNA/DNA ratio) in activated (stimulated) T cells |
| `rest` | mean activity (RNA/DNA ratio) in resting T cells |
| `log2r` | `log2(stim / rest)` = activation selectivity (raw, no pseudocount) |

## Key definitions (used by every figure)
- **consensus variant** = the surviving variant of a PWM with the highest `rel_affinity`.
- **best variant** = the most **activation**-selective surviving variant (max `log2r`), restricted to `stim ≥ 0.1`.
- **performance tiers** = all PWMs ranked by their best variant's selectivity (top 0.1% … all).

## Figures (same seven as the OvCa bundle)
1. **`fig1_per_pwm_variant_clouds`** — variant clouds for 12 representative PWMs; ★ = most activation-selective, below the diagonal = stim-selective.
2. **`fig2_neutral_center`** — distribution of `log2(Stim/Rest)`; empirical neutral center ≈ −0.19 (essentially identical to OvCa), asymmetric toward activation-selective variants.
3. **`fig3_decomposition_by_tier`** — per-PWM Δstim vs Δrest; selectivity gains come mainly from **suppressing resting-cell activity** (median Δstim ≈ 0; Δrest strongly negative in the top tiers) — the OvCa normal-suppression mechanism reproduced.
4. **`fig4_tiered_slopegraph`** — median Stim and Rest activity, consensus → best variant, by tier.
5. **`fig5_goldilocks`** — affinity rank of each PWM's most activation-selective variant; broadly spread (no universal optimal affinity).
6. **`fig6_affinity_vs_specificity`** — selectivity vs affinity density; flat median = affinity does not predict selectivity.
7. **`fig7_necessity`** — counterfactual consensus-only vs full variant library; a consensus-only design misses ~60% of the most activation-selective enhancers (−60 / −59 / −62 % at ≥2× / ≥4× / ≥8×).

## Cross-context summary (why this matters)
The same variant-tuning principle recurs in two unrelated cell systems:

| | Ovarian cancer (OV8/IOSE) | T-cell activation (Stim/Rest) |
|---|---|---|
| Empirical neutral center | −0.19 log2 | −0.19 log2 |
| % PWMs needing a non-consensus variant (≥2×) | 22.9% | 24.4% |
| Consensus-only misses (≥2× / ≥4× / ≥8×) | 64 / 60 / 69 % | 60 / 59 / 62 % |
| Mechanism (top tiers) | suppress normal (IOSE) | suppress resting (Rest) |
| Goldilocks affinity | no universal optimum | no universal optimum |
