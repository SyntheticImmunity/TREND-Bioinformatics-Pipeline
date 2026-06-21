#!/usr/bin/env python
"""Shared data prep + computed quantities for the 'mRNA does not predict enhancer
activity' figures. Imported by the matplotlib / seaborn / plotnine renderers so
all three draw exactly the same numbers."""
import numpy as np, pandas as pd
from types import SimpleNamespace
from pathlib import Path
from scipy import stats

HERE = Path(__file__).resolve().parent
RNA = Path(r"d:\Dropbox (Personal)\paper writing working folder\ovarian cancer"
           r"\restructure for Cell resource\TREND Cell revision 061526\data for figures"
           r"\RNAseq_TPM_OV8_and_IOSE_050724.csv")
SEN = HERE.parent / "project_data" / "final_enhancer_activity_results" / "ovarian_cancer" / "ovca_sensor_activity_result_concise.csv"
EPS = 0.1
K = 50            # size of the "most selective" target set for the recovery curve

# colors shared across engines
RED, BLUE, GREY, GREEN, GREEN2 = "#d1495b", "#1f6feb", "#8b949e", "#2da44e", "#198754"

# the three labelled categories on figs D / F: (color, legend label)
CAT_STYLE = {
    "screen-best": ("#198754", "Most tumour-selective sensors (screen)"),
    "literature":  ("#1f6feb", "Field-acknowledged ovarian-cancer TFs"),
    "mRNA-top":    ("#d1495b", "Most over-expressed (OV8/IOSE mRNA)"),
}
CAT_ORDER = ["screen-best", "literature", "mRNA-top"]


def compute():
    rna = pd.read_csv(RNA)
    rna["OV8_TPM"] = pd.to_numeric(rna.OV8_TPM, errors="coerce")
    rna["IOSE_TPM"] = pd.to_numeric(rna.IOSE_TPM, errors="coerce")
    rna = rna.dropna(subset=["OV8_TPM", "IOSE_TPM"])
    rna["mrna_l10"] = np.log10((rna.OV8_TPM + EPS) / (rna.IOSE_TPM + EPS))
    rna = rna[rna[["OV8_TPM", "IOSE_TPM"]].max(axis=1) > 1]

    sen = pd.read_csv(SEN).dropna(subset=["mean_OV8_RD_ratio", "mean_IOSE_RD_ratio"])
    sen = sen[(sen.mean_OV8_RD_ratio > 0) & (sen.mean_IOSE_RD_ratio > 0)].copy()
    sen["log2spec"] = np.log2(sen.mean_OV8_RD_ratio / sen.mean_IOSE_RD_ratio)

    per_tf = (sen.groupby("TF_name_human_curated")
              .agg(n=("log2spec", "size"), med_log2=("log2spec", "median"), best_log2=("log2spec", "max"))
              .reset_index().rename(columns={"TF_name_human_curated": "tf"}))
    M = per_tf.merge(rna[["hgnc_symbol", "mrna_l10"]], left_on="tf", right_on="hgnc_symbol", how="inner")
    M["good"] = M.best_log2 >= 1
    M["rank_mrna"] = M.mrna_l10.rank(ascending=False)
    M["rank_sensor"] = M.best_log2.rank(ascending=False)
    N = len(M)

    # per-sensor frame with the TF's mRNA differential attached (fig B)
    sm = sen.merge(M[["tf", "mrna_l10"]], left_on="TF_name_human_curated", right_on="tf", how="inner")

    # reference correlation (current S3A)
    r_ref = stats.pearsonr(M.mrna_l10, M.med_log2)[0]

    # recovery curve
    order = M.sort_values("mrna_l10", ascending=False).reset_index(drop=True)
    target = set(M.sort_values("best_log2", ascending=False).head(K).tf)
    xs = np.arange(1, N + 1)
    mrna_rec = np.cumsum([1 if tf in target else 0 for tf in order.tf]) / K
    rand_rec = xs / N
    screen_rec = np.minimum(xs, K) / K
    nrec = int(mrna_rec[K - 1] * K)

    # ROC of mRNA differential -> "good" TF
    score, label = M.mrna_l10.values, M.good.values
    thr = np.sort(np.unique(score))[::-1]
    P, Nn = label.sum(), (~label).sum()
    tpr, fpr = [0.0], [0.0]
    for t in thr:
        pred = score >= t
        tpr.append((pred & label).sum() / P); fpr.append((pred & ~label).sum() / Nn)
    pos, neg = score[label], score[~label]
    auc = stats.mannwhitneyu(pos, neg, alternative="two-sided").statistic / (len(pos) * len(neg))

    # variance decomposition
    # variance decomposition over the SAME joined TF set shown in the figures
    _senj = sen[sen.TF_name_human_curated.isin(set(M.tf))]
    within = _senj.groupby("TF_name_human_curated").log2spec.var().mean()
    between = M.med_log2.var()

    # quadrant thresholds + counts
    xthr, ythr = np.log10(2), 1.0
    hi_m, hi_s = M.mrna_l10 >= xthr, M.best_log2 >= ythr
    wasted = int((hi_m & ~hi_s).sum()); missed = int((~hi_m & hi_s).sum())

    # curated discordant labels for figF / figD:
    #   missed = excellent sensor but flat/low mRNA (RNA-seq would skip it)
    #   wasted = strongly overexpressed mRNA but no usable sensor
    missed_tfs = (M[M.mrna_l10 < 0.1].sort_values("best_log2", ascending=False).head(3))
    wasted_tfs = (M[M.best_log2 < 0.5].sort_values("mrna_l10", ascending=False).head(3))

    topm = M.sort_values("mrna_l10", ascending=False).head(20)

    # Three label categories for figs D / F (priority: literature > screen-best > mRNA-top):
    #   literature  = field-acknowledged ovarian-cancer (HGSOC) TFs
    #   screen-best = TFs whose best sensor is most tumour-selective (TREND's wins)
    #   mRNA-top    = TFs most over-expressed in tumour mRNA (the RNA-seq shortcut)
    tfset = set(M.tf)
    LIT = [t for t in ["PAX8", "WT1", "SOX17", "MECOM", "FOXM1"] if t in tfset]
    screen_best = [t for t in M.sort_values("best_log2", ascending=False).tf if t not in LIT][:6]
    mrna_top = [t for t in M.sort_values("mrna_l10", ascending=False).tf
                if t not in LIT and t not in screen_best][:6]
    cat = {}
    for t in mrna_top: cat[t] = "mRNA-top"
    for t in screen_best: cat[t] = "screen-best"
    for t in LIT: cat[t] = "literature"
    M["category"] = M.tf.map(cat).fillna("")

    return SimpleNamespace(
        M=M, sm=sm, sen=sen, N=N, K=K, r_ref=r_ref,
        xs=xs, mrna_rec=mrna_rec, rand_rec=rand_rec, screen_rec=screen_rec, nrec=nrec,
        fpr=np.array(fpr), tpr=np.array(tpr), auc=auc,
        within=within, between=between,
        xthr=xthr, ythr=ythr, wasted=wasted, missed=missed,
        missed_tfs=missed_tfs, wasted_tfs=wasted_tfs, topm=topm,
        cat_style=CAT_STYLE, cat_order=CAT_ORDER,
        colors=SimpleNamespace(RED=RED, BLUE=BLUE, GREY=GREY, GREEN=GREEN, GREEN2=GREEN2),
    )


if __name__ == "__main__":
    d = compute()
    print(f"TFs={d.N}  r_ref={d.r_ref:.2f}  AUC={d.auc:.2f}  within/between={d.within/d.between:.1f}x  "
          f"recovery@{d.K}={d.nrec}/{d.K}  wasted={d.wasted} missed={d.missed}")
    print("missed labels:", list(d.missed_tfs.tf))
    print("wasted labels:", list(d.wasted_tfs.tf))
