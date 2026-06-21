#!/usr/bin/env python
"""
TREND T-cell-activation variant analysis — standalone figure reproduction.
=========================================================================
Cross-context replication of the ovarian-cancer variant analysis on the primary
human T-cell activation screen. Same logic, same definitions, same figure set;
the only difference is the biology — the two "cell states" are activated (Stim)
versus resting (Rest) T cells, and selectivity = log2(Stim / Rest).

Reads ONE self-contained data file (trend_tcell_variants.csv) and regenerates
the seven figures, each as a vector PDF (publication quality) plus a PNG preview.

Run:   python make_figures.py
Deps:  numpy  pandas  scipy  matplotlib  plotnine
       (pip install numpy pandas scipy matplotlib plotnine)

Data file — one row per quantified enhancer variant, columns:
  pwm           unique position-weight-matrix id (ENCODE/MotifDb source motif)
  tf            human-curated transcription-factor name
  promoter      unique variant id (TFBS sequence + TF)
  tfbs_sequence the variant's transcription-factor binding-site sequence
  rel_affinity  fraction-of-consensus relative affinity of the variant scored
                against its OWN source PWM:  prod_j p[j,seq_j] / max_b p[j,b];
                1.0 = consensus.  (Pre-computed so this script needs no PWM file.)
  n_repeats     number of tandem TFBS copies in the synthetic enhancer
  stim          mean activity (RNA/DNA ratio) in activated (stimulated) T cells
  rest          mean activity (RNA/DNA ratio) in resting T cells
  log2r         log2(stim / rest)  = activation selectivity (raw, no pseudocount)

Definitions used throughout:
  consensus variant = the surviving variant of a PWM with the highest rel_affinity
  best variant      = the most ACTIVATION-selective surviving variant (max log2r),
                      restricted to variants with stim >= FLOOR (real stim activity)
  performance tiers  = all PWMs ranked by their best variant's selectivity
"""
import numpy as np, pandas as pd, re, textwrap
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy import stats
from plotnine import (ggplot, aes, geom_point, geom_abline, geom_line, geom_text,
                      facet_wrap, scale_fill_cmap, scale_color_manual,
                      scale_x_continuous, coord_fixed, labs, theme_gray, theme_bw,
                      theme, element_text)

HERE = Path(__file__).resolve().parent
DATA = HERE / "trend_tcell_variants.csv"
OUT  = HERE / "figures"; OUT.mkdir(exist_ok=True)
FLOOR = 0.1
TIERS = [(0.1,"Top 0.1%"),(1,"Top 1%"),(10,"Top 10%"),(20,"Top 20%"),(40,"Top 40%"),(100,"All PWMs")]

def save(obj, name, w=None, h=None, dpi=150, gg=False):
    """Write a vector PDF (publication) and a PNG preview for one figure."""
    if gg:
        obj.save(OUT/f"{name}.pdf", width=w, height=h, verbose=False)
        obj.save(OUT/f"{name}.png", width=w, height=h, dpi=dpi, verbose=False)
    else:
        obj.savefig(OUT/f"{name}.pdf", bbox_inches="tight")
        obj.savefig(OUT/f"{name}.png", dpi=dpi, bbox_inches="tight")
        plt.close(obj)
    print(f"  wrote {name}.pdf / .png")

_DBS = ("jaspar2018","jaspar2016","jaspar","SwissRegulon","HOCOMOCOv11","HOCOMOCOv10",
        "HOCOMOCO","jolma2013","jolma","hPDI","transfac","cisbp","UniPROBE","bulyk","pazar")
def short_pwm(k):                       # -> "TF · source · accession", de-duplicated
    k = " ".join(str(k).split())
    tf = re.split(r"[_\- ]", k)[0]
    src = next((d for d in _DBS if d.lower() in k.lower()), "")
    m = re.search(r"(MA\d+\.\d+|M\d{3,}|H\w+\.\w+)", k); acc = m.group(1) if m else ""
    if acc and tf.lower() in acc.lower(): acc = ""
    return " · ".join(dict.fromkeys([p for p in (tf, src, acc) if p]))

# ----------------------------------------------------------------- load + summarise
df = pd.read_csv(DATA)
print(f"loaded {len(df)} variants across {df['pwm'].nunique()} PWMs")

rows = []
for k, g in df.groupby("pwm"):
    cons = g.loc[g.rel_affinity.idxmax()]
    elig = g[g.stim >= FLOOR]
    if elig.empty: continue
    best = elig.loc[elig.log2r.idxmax()]
    rows.append(dict(pwm=k, tf=cons.tf, nvar=len(g),
        cons_stim=cons.stim, cons_rest=cons.rest, best_stim=best.stim, best_rest=best.rest,
        cons_spec=cons.log2r, best_spec=best.log2r, cons_aff=cons.rel_affinity,
        cons_prom=cons.promoter, best_prom=best.promoter,
        dT=np.log2(best.stim/cons.stim), dN=np.log2(best.rest/cons.rest)))
S = pd.DataFrame(rows)
S["gain"] = 2 ** (S.best_spec - S.cons_spec)
S = S.sort_values("best_spec", ascending=False).reset_index(drop=True)

def tier_df(pct):
    return S.head(max(3, int(len(S) * pct / 100)))

# =========================================================== Fig 1 — variant clouds (ggplot)
print("Fig 1 — per-PWM variant clouds (ggplot/plotnine)")
top = S[(S.nvar >= 8) & (S.cons_aff >= 0.8) & (S.gain >= 2)].head(12)   # genuine consensus + real gain
gmax = max(max(df[df.pwm==r.pwm].stim.max(), df[df.pwm==r.pwm].rest.max())
           for _, r in top.iterrows()) * 1.05
V, M, Tx = [], [], []
for _, row in top.iterrows():
    gp = df[df.pwm == row.pwm].copy()
    lab = "\n".join(textwrap.wrap(short_pwm(row.pwm), 26)); gp["lab"] = lab
    V.append(gp[["stim","rest","rel_affinity","lab"]])
    c  = gp[gp.promoter == row.cons_prom].iloc[0]; b = gp[gp.promoter == row.best_prom].iloc[0]
    M.append(dict(stim=c.stim, rest=c.rest, aff=c.rel_affinity, lab=lab, role="consensus"))
    M.append(dict(stim=b.stim, rest=b.rest, aff=b.rel_affinity, lab=lab, role="most-selective"))
    Tx.append(dict(lab=lab, x=gmax*0.03, y=gmax*0.97, txt=f"Gain {row.gain:.1f}×"))
V = pd.concat(V); M = pd.DataFrame(M); Tx = pd.DataFrame(Tx)
order = ["\n".join(textwrap.wrap(short_pwm(r.pwm), 26)) for _, r in top.iterrows()]
for d in (V, M, Tx): d["lab"] = pd.Categorical(d.lab, categories=order, ordered=True)
p1 = (ggplot(V, aes("stim","rest"))
      + geom_abline(slope=1, intercept=0, linetype="dashed", color="grey")
      + geom_point(aes(fill="rel_affinity"), shape="o", color="black", size=2.6, stroke=.2)
      + geom_point(M[M.role=="consensus"], aes("stim","rest",fill="aff"), shape="o", color="black", size=3.4, stroke=1.7)
      + geom_point(M[M.role=="most-selective"], aes("stim","rest"), shape="*", color="red", size=6)
      + geom_text(Tx, aes(x="x", y="y", label="txt"), ha="left", va="top", size=8)
      + facet_wrap("lab", ncol=4)
      + scale_fill_cmap(cmap_name="viridis", name="Motif affinity\n(1 = consensus)")
      + coord_fixed(ratio=1, xlim=(0,gmax), ylim=(0,gmax))
      + labs(x="Stim (activated) RD ratio", y="Rest (resting) RD ratio",
             title="Per-PWM variant clouds — thick-edged dot = consensus, ★ = most-selective, below diagonal = stim-selective")
      + theme_gray() + theme(strip_text=element_text(size=7), plot_title=element_text(size=11)))
save(p1, "fig1_per_pwm_variant_clouds", w=15, h=11, gg=True)

# =========================================================== Fig 2 — neutral center (matplotlib)
print("Fig 2 — neutral center & tail asymmetry")
lr = df.log2r.values
kde = stats.gaussian_kde(lr); grid = np.linspace(lr.min(), lr.max(), 2000)
center = grid[np.argmax(kde(grid))]
fig, a = plt.subplots(figsize=(7.5, 3.4))
a.hist(lr, bins=120, color="#8b949e")
a.plot(grid, kde(grid)*len(lr)*(grid[1]-grid[0]), color="#d29922", lw=1.5)
a.axvline(center, color="crimson", lw=1.6, label=f"Empirical center = {center:+.2f}")
a.axvline(0, color="k", ls=":", lw=1, label="Ratio = 1")
a.set_xlabel("Selectivity, log2(Stim / Rest)"); a.set_ylabel("Number of variants")
a.set_title("Neutral center & tail asymmetry"); a.legend(fontsize=8)
save(fig, "fig2_neutral_center")

# =========================================================== Fig 3 — decomposition by tier (matplotlib)
print("Fig 3 — decomposition by tier")
L = 3.2
fig, axs = plt.subplots(2, 3, figsize=(13, 8.4)); axs = axs.ravel()
for ax, (pct, lab) in zip(axs, TIERS):
    s = tier_df(pct)
    ax.scatter(s.dT.clip(-L,L), s.dN.clip(-L,L), s=14, alpha=.45, c="#1f6feb", edgecolors="none")
    ax.plot([-L,L], [-L,L], "--", color="k", lw=1); ax.axhline(0, color="gray", lw=.6); ax.axvline(0, color="gray", lw=.6)
    ax.set_xlim(-L,L); ax.set_ylim(-L,L); ax.set_aspect("equal")
    ax.set_title(f"{lab}  (n={len(s)})", fontsize=10)
    ax.set_xlabel("Δ stim (log2, best−consensus)", fontsize=8); ax.set_ylabel("Δ rest (log2, best−consensus)", fontsize=8)
    ax.text(.04, .96, f"Median Δstim {s.dT.median():+.2f}\nMedian Δrest {s.dN.median():+.2f}", transform=ax.transAxes,
            fontsize=8, va="top", ha="left", bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=.85))
fig.suptitle("Best variant vs its consensus, by performance tier  (bottom-right = stim↑ & rest↓; below diagonal = selectivity gained)", fontsize=11)
fig.tight_layout(rect=[0,0,1,.95]); save(fig, "fig3_decomposition_by_tier")

# =========================================================== Fig 4 — tiered slopegraph (ggplot)
print("Fig 4 — tiered slopegraph (ggplot/plotnine)")
recs = []
for pct, lab in TIERS:
    s = tier_df(pct); n = f"{lab} (n={len(s)})"
    for cell, cV, bV in [("Stim (activated)", s.cons_stim.median(), s.best_stim.median()),
                         ("Rest (resting)", s.cons_rest.median(), s.best_rest.median())]:
        recs += [dict(tier=n, x=0, cell=cell, val=cV), dict(tier=n, x=1, cell=cell, val=bV)]
D = pd.DataFrame(recs); D["lbl"] = D.val.map(lambda v: f"{v:.2f}")
D["tier"] = pd.Categorical(D.tier, categories=[f"{l} (n={len(tier_df(pc))})" for pc, l in TIERS], ordered=True)
p4 = (ggplot(D, aes("x","val", color="cell", group="cell"))
      + geom_line(size=1.1) + geom_point(size=3)
      + geom_text(aes(label="lbl"), va="bottom", size=8, nudge_y=0.02, show_legend=False)
      + facet_wrap("tier", ncol=3, scales="free_y")
      + scale_x_continuous(breaks=[0,1], labels=["Consensus","Best"], limits=(-.3,1.3))
      + scale_color_manual(values={"Stim (activated)":"#d1495b","Rest (resting)":"#3a7ca5"})
      + labs(x="", y="Median activity (RD ratio)", color="",
             title="Activity shift consensus → most-selective variant, by performance tier")
      + theme_bw() + theme(legend_position="top"))
save(p4, "fig4_tiered_slopegraph", w=12, h=7, gg=True)

# =========================================================== Fig 5 — Goldilocks (matplotlib)
print("Fig 5 — Goldilocks affinity")
pcts = []
for k, g in df.groupby("pwm"):
    g = g[g.stim >= FLOOR]
    if len(g) < 4: continue
    pcts.append(100 * (g.rel_affinity < g.loc[g.log2r.idxmax(), "rel_affinity"]).mean())
pcts = np.array(pcts)
edges = np.arange(0, 101, 10); centers = (edges[:-1]+edges[1:]) / 2
counts, _ = np.histogram(pcts, bins=edges)
colors = ["#cf222e" if c < 20 else ("#2da44e" if c >= 80 else "#8b949e") for c in centers]
low = (pcts<20).mean()*100; mid = ((pcts>=20)&(pcts<80)).mean()*100; high = (pcts>=80).mean()*100
fig, ax = plt.subplots(figsize=(8.4, 3.8))
ax.bar(centers, counts, width=9, color=colors, zorder=3)
ax.axvline(20, color="gray", ls=":", lw=1); ax.axvline(80, color="gray", ls=":", lw=1)
ax.set_xlim(0, 100); ax.set_xticks(np.arange(0, 101, 20))
ax.set_xlabel("Affinity rank of the most stim-selective variant within its PWM\n(0 = weakest motif match  →  100 = consensus)")
ax.set_ylabel("Number of PWMs"); ax.set_title("Where the best variant sits in affinity — no universal optimum")
ax.legend(handles=[Patch(color="#cf222e", label=f"Low affinity (bottom fifth) — {low:.0f}% of PWMs"),
                   Patch(color="#8b949e", label=f"Intermediate — {mid:.0f}% of PWMs"),
                   Patch(color="#2da44e", label=f"Near-consensus (top fifth) — {high:.0f}% of PWMs")],
          loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False, fontsize=9, title="Best variant's affinity")
save(fig, "fig5_goldilocks")

# =========================================================== Fig 6 — specificity vs affinity (matplotlib)
print("Fig 6 — specificity vs affinity density")
fig, ax = plt.subplots(figsize=(7, 4.4))
hb = ax.hexbin(df.rel_affinity, df.log2r, gridsize=40, cmap="magma")
b = np.linspace(0, 1, 21); idx = np.clip(np.digitize(df.rel_affinity, b)-1, 0, 19)
med = [np.median(df.log2r[idx==i]) if (idx==i).any() else np.nan for i in range(20)]
ax.plot((b[:-1]+b[1:])/2, med, color="cyan", lw=2.5, label="Median selectivity (flat = no trend)")
ax.axhline(np.median(df.log2r), color="white", ls=":", lw=1)
ax.set_xlabel("Relative affinity (1 = consensus motif)"); ax.set_ylabel("Selectivity, log2(Stim/Rest)")
ax.set_title("Selectivity vs affinity — flat median = affinity doesn't predict selectivity")
ax.legend(loc="upper right", fontsize=8)
cb = fig.colorbar(hb); cb.set_label("Number of variants per hexagon")
save(fig, "fig6_affinity_vs_specificity")

# =========================================================== Fig 7 — necessity of variants (matplotlib)
print("Fig 7 — necessity of the variant dimension")
RED, GREY = "#d1495b", "#8b949e"
full = np.sort(S.best_spec.values)[::-1]
cons = np.sort(S.loc[S.cons_stim >= FLOOR, "cons_spec"].values)[::-1]
rf = np.arange(1, len(full) + 1); rc = np.arange(1, len(cons) + 1)
fig, (axA, axB) = plt.subplots(1, 2, figsize=(12.5, 4.6), gridspec_kw=dict(width_ratios=[1.45, 1]))
# Panel A — selectivity forfeited by a consensus-only design
axA.fill_between(rf, 2 ** full, np.interp(rf, rc, 2 ** cons), color=RED, alpha=.12, zorder=1)
axA.plot(rf, 2 ** full, color=RED, lw=2.2, label="Full variant library (best variant / PWM)", zorder=3)
axA.plot(rc, 2 ** cons, color=GREY, lw=2.2, label="Consensus-only library", zorder=3)
for thr in (2, 4):
    axA.axhline(thr, color="k", ls=":", lw=.8, zorder=2)
    nf = int((full >= np.log2(thr)).sum()); nc = int((cons >= np.log2(thr)).sum())
    axA.annotate(f"≥{thr}×: {nf} vs {nc} enhancers", (1.05, thr), fontsize=8, va="bottom", ha="left", color="#444")
axA.set_xscale("log"); axA.set_yscale("log")
axA.set_xlim(1, len(full)); axA.set_ylim(1, max(2 ** full) * 1.1)
axA.set_yticks([1, 2, 4, 8, 16]); axA.set_yticklabels(["1×", "2×", "4×", "8×", "16×"])
axA.set_xlabel("Enhancers selected (ranked by activation selectivity)")
axA.set_ylabel("Activation selectivity, Stim / Rest")
axA.set_title("Selectivity forfeited by a consensus-only design")
axA.legend(fontsize=8, loc="upper right", frameon=False)
# Panel B — selective enhancers missed without variants (threshold counterfactual)
thrs = [2, 4, 8]
nfull = [int((S.best_spec >= np.log2(t)).sum()) for t in thrs]
ncons = [int(((S.cons_stim >= FLOOR) & (S.cons_spec >= np.log2(t))).sum()) for t in thrs]
x = np.arange(len(thrs)); w = .38
axB.bar(x - w / 2, nfull, w, color=RED, label="Full variant library", zorder=3)
axB.bar(x + w / 2, ncons, w, color=GREY, label="Consensus-only library", zorder=3)
for i, (nf, nc) in enumerate(zip(nfull, ncons)):
    axB.text(i - w / 2, nf, f"{nf}", ha="center", va="bottom", fontsize=8, color=RED)
    axB.text(i + w / 2, nc, f"{nc}", ha="center", va="bottom", fontsize=8, color="#555")
    axB.text(i, nf * 1.28, f"−{100*(nf-nc)/nf:.0f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")
axB.set_yscale("log"); axB.set_ylim(8, max(nfull) * 2.6)
axB.set_xticks(x); axB.set_xticklabels([f"≥{t}×" for t in thrs])
axB.set_xlabel("Activation-selectivity threshold"); axB.set_ylabel("Stim-selective enhancers (PWMs)")
axB.set_title("Selective enhancers missed without variants")
axB.legend(fontsize=8, loc="upper right", frameon=False)
fig.tight_layout(); save(fig, "fig7_necessity")

print(f"\nDone — 7 figures (PDF + PNG) in {OUT}")
