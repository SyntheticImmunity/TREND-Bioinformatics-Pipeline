# TREND ovarian-cancer variant analysis — figure reproduction bundle

Self-contained code + data to regenerate the variant-level figures for the revision.

## Contents
- `trend_ovca_variants.csv` — the only input. One row per quantified enhancer variant.
- `make_figures.py` — reads the CSV and writes all seven figures to `figures/`.
- `figures/` — output: each figure as a **vector PDF** (publication) + a **PNG** preview.

## Run
```bash
pip install numpy pandas scipy matplotlib plotnine
python make_figures.py
```
No other files are needed (the per-variant motif affinity is pre-computed into the CSV).

## Data columns (`trend_ovca_variants.csv`)
| column | meaning |
|---|---|
| `pwm` | unique position-weight-matrix id (ENCODE/MotifDb source motif) |
| `tf` | human-curated transcription-factor name |
| `promoter` | unique variant id (TFBS sequence + TF) |
| `tfbs_sequence` | the variant's TF binding-site sequence |
| `rel_affinity` | fraction-of-consensus relative affinity of the variant vs its **own** PWM: `∏ⱼ p[j,seqⱼ] / maxᵦ p[j,b]`; 1.0 = consensus |
| `n_repeats` | number of tandem TFBS copies in the synthetic enhancer |
| `ov8` | mean OV8 (tumor) RNA/DNA activity ratio |
| `iose` | mean IOSE (normal) RNA/DNA activity ratio |
| `log2r` | `log2(ov8 / iose)` = tumor-vs-normal specificity (raw, no pseudocount; matches the dashboard's OV8/IOSE) |

## Key definitions (used by every figure)
- **consensus variant** = the surviving variant of a PWM with the highest `rel_affinity`.
- **best variant** = the most **tumor**-specific surviving variant (max `log2r`), restricted to `ov8 ≥ 0.1` so it has real tumor activity.
- **performance tiers** = all PWMs ranked by their best variant's specificity (top 0.1% … all).

## Figures
1. **`fig1_per_pwm_variant_clouds`** — variant clouds for 12 representative PWMs (genuine consensus present, `cons_aff ≥ 0.8`; a non-consensus variant ≥2× more tumor-specific; ranked by absolute selectivity). Thick-edged dot = consensus, ★ = most-specific, color = affinity, below the diagonal = tumor-specific. *(illustrative; quantitative claims are in figs 2–6.)*
2. **`fig2_neutral_center`** — distribution of `log2(OV8/IOSE)`; the empirical neutral center is left of 1 and the tumor-specific (right) tail is heavier than the normal-specific (left) tail.
3. **`fig3_decomposition_by_tier`** — per-PWM Δtumor vs Δnormal (best − consensus) across performance tiers; specificity gains come mainly from lowering normal activity, with a tumor-gain component that grows in the top tiers.
4. **`fig4_tiered_slopegraph`** — median tumor and normal activity, consensus → best variant, by tier; the "both levers" pattern sharpens toward the best enhancers.
5. **`fig5_goldilocks`** — affinity rank of each PWM's most tumor-specific variant; broadly spread (no universal optimal affinity → a diverse variant library is required).
6. **`fig6_affinity_vs_specificity`** — specificity vs affinity density for all variants; the flat median line shows affinity does not predict specificity.
7. **`fig7_necessity`** — counterfactual: a consensus-only library vs the full variant library. **(A)** selectivity of the N-th best enhancer each can assemble (shaded gap = forfeited selectivity); **(B)** PWMs reaching ≥2×/≥4×/≥8× selectivity — a consensus-only design misses ~60–69% of the most tumor-selective enhancers.
