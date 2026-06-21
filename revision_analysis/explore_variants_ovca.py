"""Exploratory variant -> activity/specificity analysis for the OvCa screen.

Pass 1 (no dashboard code): tests the central revision hypothesis ---
  variant-driven tumor specificity comes mainly from SUPPRESSING normal-cell
  activity rather than boosting tumor activity, consistent with lower-affinity
  variants raising the TF-activation threshold.

Bakes in the design decisions agreed in the brainstorm:
  - consensus anchor = highest fraction-of-consensus-affinity variant that
    survived QC (NOT a fixed "variant 1")
  - empirical neutral center of log2(OV8/IOSE); tail asymmetry MEASURED, not
    assumed symmetric
  - decomposition reported as two medians (Dtumor, Dnormal), plus scatter
  - within-PWM affinity->specificity trend uses ALL surviving variants
  - n_repeats recorded and tested as an avidity confounder
"""
from __future__ import annotations
import csv, re, math, os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

ROOT = Path(r"C:\Dev\TREND_bioinformatics_pipeline")
PWM_FILE = ROOT / "references" / "all_ENCODE_MotifDb_ppm_no_NA_v1.txt"
CSV = ROOT / "project_data" / "final_enhancer_activity_results" / "ovarian_cancer" / "ovca_sensor_activity_result_concise.csv"
OUT = ROOT / "revision_analysis"
FIGS = OUT / "figs"
FIGS.mkdir(parents=True, exist_ok=True)

BASES = "ACGT"
BIDX = {b: i for i, b in enumerate(BASES)}
PSEUDO = 1e-3          # column pseudocount for affinity
ACT_PC = 0.01          # activity pseudocount for log ratios/deltas
ACT_FLOOR = 0.1        # min tumor activity for a variant to anchor "best specific"

# ---------------------------------------------------------------- PWM parsing
def load_pwms():
    pwms = {}
    name, rows = None, []
    with PWM_FILE.open() as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name and len(rows) == 4:
                    pwms[name] = np.array(rows, float)
                name = line[1:].split()[0]
                rows = []
            else:
                rows.append([float(x) for x in line.split()])
    if name and len(rows) == 4:
        pwms[name] = np.array(rows, float)
    # pseudocount + renormalize columns to sum 1
    for k, m in pwms.items():
        m = m + PSEUDO
        pwms[k] = m / m.sum(axis=0, keepdims=True)
    return pwms

def rel_affinity(seq, ppm):
    """Fraction-of-consensus: prod p[seq_j]/max_b p[b,j]; slide if seq longer."""
    W = ppm.shape[1]
    L = len(seq)
    if L < W:
        return np.nan
    colmax = ppm.max(axis=0)
    best = 0.0
    for off in range(0, L - W + 1):
        sub = seq[off:off + W]
        try:
            idx = [BIDX[b] for b in sub]
        except KeyError:
            continue
        p = ppm[idx, range(W)]
        best = max(best, float(np.prod(p / colmax)))
    return best if best > 0 else np.nan

# ---------------------------------------------------------------- load data
pwms = load_pwms()
df = pd.read_csv(CSV)
print(f"variants in CSV: {len(df)}   PWMs loaded: {len(pwms)}")

def pwm_key(bp):
    if not isinstance(bp, str) or bp == "NA":
        return None
    return re.sub(r"_v\d+$", "", bp)

df["pwm_key"] = df["by_ppm_name"].map(pwm_key)
df["lookup"] = df["pwm_key"].map(lambda k: k.split()[0] if k else None)

# affinity + n_repeats per variant
aff, nrep, wmm = [], [], 0
for _, r in df.iterrows():
    seq = r["TFBS_sequence"]
    ppm = pwms.get(r["lookup"]) if r["lookup"] else None
    if ppm is None or not isinstance(seq, str):
        aff.append(np.nan)
    else:
        a = rel_affinity(seq, ppm)
        aff.append(a)
        if np.isnan(a):
            wmm += 1
    vr = r["variable_region"]
    nrep.append(vr.count(seq) if isinstance(vr, str) and isinstance(seq, str) and seq else np.nan)
df["rel_affinity"] = aff
df["n_repeats"] = nrep
print(f"affinity computed: {df['rel_affinity'].notna().sum()}   unmatched/short: {wmm}")
print(f"PWM-width vs TFBS-len: len matches sample -> repeats median {np.nanmedian(df['n_repeats']):.0f} "
      f"(range {np.nanmin(df['n_repeats']):.0f}-{np.nanmax(df['n_repeats']):.0f})")

OV8, IOSE = "mean_OV8_RD_ratio", "mean_IOSE_RD_ratio"
df = df[df[OV8].notna() & df[IOSE].notna()].copy()
df["log2ratio"] = np.log2((df[OV8] + ACT_PC) / (df[IOSE] + ACT_PC))

# ---------------------------------------------------- (2) neutral center + asymmetry
lr = df["log2ratio"].to_numpy()
center_med = float(np.median(lr))
kde = stats.gaussian_kde(lr)
grid = np.linspace(lr.min(), lr.max(), 2000)
center_mode = float(grid[np.argmax(kde(grid))])
print("\n=== (2) NEUTRAL CENTER & TAIL ASYMMETRY ===")
print(f"n variants (both expressed): {len(lr)}")
print(f"center: median={center_med:+.3f}  KDE-mode={center_mode:+.3f}  (log2; 0 == ratio 1)")
for T in (1, 2, 3):
    up = int(np.sum(lr - center_mode >= T))
    dn = int(np.sum(lr - center_mode <= -T))
    print(f"  |dev|>={T} log2 from center:  tumor-specific={up:5d}   normal-specific={dn:5d}   "
          f"tumor/normal={up/max(dn,1):.2f}")

# ---------------------------------------------------- (3-4) per-PWM decomposition
rows = []
for key, g in df.groupby("pwm_key"):
    g = g.dropna(subset=["rel_affinity"])
    if len(g) < 2:
        continue
    cons = g.loc[g["rel_affinity"].idxmax()]
    elig = g[g[OV8] >= ACT_FLOOR]
    if elig.empty:
        continue
    best = elig.loc[elig["log2ratio"].idxmax()]
    dT = math.log2((best[OV8] + ACT_PC) / (cons[OV8] + ACT_PC))
    dN = math.log2((best[IOSE] + ACT_PC) / (cons[IOSE] + ACT_PC))
    dS = dT - dN
    # within-PWM affinity->specificity trend
    rho = np.nan
    if len(g) >= 4 and g["rel_affinity"].nunique() >= 3:
        rho, _ = stats.spearmanr(g["rel_affinity"], g["log2ratio"])
    rows.append(dict(pwm=key, tf=cons["TF_name_human_curated"], nvar=len(g),
                     cons_aff=cons["rel_affinity"], best_aff=best["rel_affinity"],
                     dT=dT, dN=dN, dS=dS,
                     d_rep=(best["n_repeats"] - cons["n_repeats"]),
                     same=bool(best["promoter_name"] == cons["promoter_name"]),
                     rho=rho))
res = pd.DataFrame(rows)
print(f"\n=== (3-4) DECOMPOSITION across {len(res)} PWMs ===")
gain = res[res["dS"] >= 1]          # >=2-fold specificity gain from a non-consensus variant
print(f"median Dtumor  (best-consensus): {res['dT'].median():+.3f} log2  ({2**res['dT'].median():.2f}x)")
print(f"median Dnormal (best-consensus): {res['dN'].median():+.3f} log2  ({2**res['dN'].median():.2f}x)")
print(f"median Dspecificity:             {res['dS'].median():+.3f} log2  ({2**res['dS'].median():.2f}x)")
print(f"\n'consensus is not enough': non-consensus variant >=2x more specific: "
      f"{(~gain['same']).sum()}/{len(res)} = {100*(~res['same'] & (res['dS']>=1)).mean():.0f}% of PWMs"
      f"   (median fold among them {2**gain['dS'].median():.2f}x)")
# mechanism buckets among specificity-gaining PWMs
def bucket(r):
    if r["dS"] < 0.5: return "neutral"
    if r["dT"] >= 0.5: return "tumor-gain"
    if r["dN"] <= -0.5 and abs(r["dT"]) < 0.5: return "normal-suppression"
    if r["dN"] <= -0.5 and r["dT"] <= -0.5: return "divergent"
    return "other"
res["bucket"] = res.apply(bucket, axis=1)
print("\nmechanism buckets:")
print(res["bucket"].value_counts().to_string())
print(f"\nwithin-PWM affinity->specificity Spearman (n={res['rho'].notna().sum()} PWMs w/>=4 var): "
      f"median rho={res['rho'].median():+.3f}; "
      f"negative={100*(res['rho']<0).mean():.0f}%  (negative == lower affinity -> higher specificity)")
# n_repeats confounder
sub = res.dropna(subset=["d_rep"])
if len(sub) > 10:
    cr, cp = stats.spearmanr(sub["d_rep"], sub["dS"])
    print(f"\nn_repeats confounder: corr(Drepeats, Dspecificity) rho={cr:+.3f} p={cp:.1e}; "
          f"best==consensus repeats in {100*(sub['d_rep']==0).mean():.0f}% of PWMs")

# ---------------------------------------------------------------- figures
# Fig 1: Dtumor vs Dnormal scatter with marginals
fig = plt.figure(figsize=(6.2, 6.2))
gs = fig.add_gridspec(4, 4, hspace=.05, wspace=.05)
ax = fig.add_subplot(gs[1:, :3]); axx = fig.add_subplot(gs[0, :3], sharex=ax); axy = fig.add_subplot(gs[1:, 3], sharey=ax)
ax.scatter(res["dT"], res["dN"], s=7, alpha=.35, c="#1f6feb", edgecolors="none")
lim = np.nanpercentile(np.abs(np.r_[res["dT"], res["dN"]]), 99)
ax.plot([-lim, lim], [-lim, lim], "k--", lw=1, label="y=x (no specificity change)")
ax.axhline(0, color="gray", lw=.6); ax.axvline(0, color="gray", lw=.6)
ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
ax.set_xlabel("Δ tumor activity  (best − consensus, log2)")
ax.set_ylabel("Δ normal activity  (best − consensus, log2)")
ax.legend(loc="upper left", fontsize=8)
axx.hist(res["dT"].clip(-lim, lim), bins=60, color="#1f6feb"); axx.axvline(res["dT"].median(), color="k")
axy.hist(res["dN"].clip(-lim, lim), bins=60, orientation="horizontal", color="#1f6feb"); axy.axhline(res["dN"].median(), color="k")
axx.tick_params(labelbottom=False); axy.tick_params(labelleft=False)
axx.set_title("Where does variant-driven specificity come from?", fontsize=10)
fig.savefig(FIGS / "fig1_decomposition_scatter.png", dpi=130, bbox_inches="tight")

# Fig 2: log2ratio distribution with center
fig, a = plt.subplots(figsize=(7, 3.2))
a.hist(lr, bins=120, color="#8b949e")
a.plot(grid, kde(grid) * len(lr) * (grid[1]-grid[0]), color="#d29922", lw=1.5)
a.axvline(center_mode, color="crimson", lw=1.5, label=f"empirical center={center_mode:+.2f}")
a.axvline(0, color="k", ls=":", lw=1, label="ratio = 1")
a.set_xlabel("log2(OV8 / IOSE)"); a.set_ylabel("variants"); a.legend(fontsize=8)
a.set_title("Neutral center & tail asymmetry"); fig.savefig(FIGS / "fig2_neutral_center.png", dpi=130, bbox_inches="tight")

# Fig 3: slopegraph (population medians consensus->best)
fig, a = plt.subplots(figsize=(4.2, 4.4))
import numpy as _np
cons_T = df.groupby("pwm_key").apply(lambda g: g.loc[g["rel_affinity"].idxmax(), OV8] if g["rel_affinity"].notna().any() else _np.nan)
for col, lab, color in [(OV8, "tumor (OV8)", "#cf222e"), (IOSE, "normal (IOSE)", "#1f6feb")]:
    c = res["pwm"].map(lambda k: df[df["pwm_key"]==k].loc[df[df["pwm_key"]==k]["rel_affinity"].idxmax(), col] if df[df["pwm_key"]==k]["rel_affinity"].notna().any() else _np.nan)
    b = res["pwm"].map(lambda k: (lambda e: e.loc[e["log2ratio"].idxmax(), col] if not e.empty else _np.nan)(df[(df["pwm_key"]==k)&(df[OV8]>=ACT_FLOOR)]))
    a.plot([0, 1], [_np.nanmedian(c), _np.nanmedian(b)], "-o", color=color, label=lab, lw=2)
a.set_xticks([0, 1]); a.set_xticklabels(["consensus", "best-specific\nvariant"])
a.set_ylabel("median activity (RD ratio)"); a.legend(fontsize=8); a.set_title("Activity shift, consensus → best variant")
fig.savefig(FIGS / "fig3_slopegraph.png", dpi=130, bbox_inches="tight")

# Fig 4: within-PWM affinity-specificity correlation histogram
fig, a = plt.subplots(figsize=(6, 3.2))
a.hist(res["rho"].dropna(), bins=40, color="#2da44e")
a.axvline(0, color="k"); a.axvline(res["rho"].median(), color="crimson", lw=1.5, label=f"median={res['rho'].median():+.2f}")
a.set_xlabel("per-PWM Spearman(affinity, log2 specificity)"); a.set_ylabel("PWMs"); a.legend(fontsize=8)
a.set_title("Affinity → specificity trend (negative supports threshold model)")
fig.savefig(FIGS / "fig4_affinity_specificity.png", dpi=130, bbox_inches="tight")

res.to_csv(OUT / "per_pwm_decomposition_ovca.csv", index=False)
df.to_csv(OUT / "per_variant_ovca.csv", index=False)
print(f"\nwrote figs to {FIGS} and tables to {OUT}")
