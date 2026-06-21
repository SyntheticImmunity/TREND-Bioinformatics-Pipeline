#!/usr/bin/env python
"""
Pass-2 identity scan — FULL OvCa library curation (all 37,832 variants).
========================================================================
For every variant: which TF does its sequence actually match, and is that call
functionally corroborated by the rest of the screen?

Per variant we report:
  call          retained / dual / switched / lost / ambiguous
  p_ownfam      best FIMO-style p-value among the variant's own TF family
  p_otherfam    best p-value among a DIFFERENT, motif-dissimilar TF family
  other_tf      the different-family TF (the switch/dual target)
  dual_kind     for 'dual': 'distinct' (two separate sites) vs 'shared'
                (one site read by two TFs) — from matched window positions
  functional corroboration (switch/dual only): does the target TF have its own
  tumor-ACTIVE sensors in this screen, and does THIS variant's activity fall in
  their range?  -> target_has_sensors / target_tumor_active / activity_concordant
                   / functionally_corroborated
  confidence    high / med / low  (sequence significance x functional support)

Scorer: self-contained numpy FIMO-style (log-odds PSSM, uniform bg, best window
over both strands/offsets; Gaussian-null p to rank all 6,012 PWMs, exact DP
upper-tail p for the chosen hits).  Usage:  python identity_scan_full.py [LIMIT]
"""
import re, sys, time, numpy as np, pandas as pd
from pathlib import Path
from numpy.lib.stride_tricks import sliding_window_view
from scipy import stats

ROOT = Path(r"C:\Dev\TREND_bioinformatics_pipeline")
PWM_FILE = ROOT / "references" / "all_ENCODE_MotifDb_ppm_no_NA_v1.txt"
OUT = ROOT / "revision_analysis"
BASES = "ACGT"; BIDX = {b: i for i, b in enumerate(BASES)}
BG = 0.25; PSEUDO = 1e-3; SCALE = 20
P_SIG = 1e-4; SWITCH_MARGIN = 2.0; FAM_CORR = 0.60
BONF = 0.05 / 6012

# Project config: input table + the two activity columns (on-state / off-state).
# Functional corroboration tests whether a switch/dual target TF drives the
# ON state (tumour for OvCa, stimulated for T cells).  Usage:
#   python identity_scan_full.py [ovca|tcell] [limit]
PROJECTS = {
    "ovca":  dict(csv="standalone/trend_ovca_variants.csv",
                  on="ov8", off="iose", out="identity_scan_full.csv"),
    "tcell": dict(csv="standalone_tcell/trend_tcell_variants.csv",
                  on="stim", off="rest", out="identity_scan_tcell.csv"),
}
PROJECT = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in PROJECTS else "ovca"
CFG = PROJECTS[PROJECT]
CSV = ROOT / "revision_analysis" / CFG["csv"]

# ---------------------------------------------------------------- PWM library
def load_pwms():
    pwms, names, name, rows = [], [], None, []
    with PWM_FILE.open() as fh:
        for raw in fh:
            line = raw.strip()
            if not line: continue
            if line.startswith(">"):
                if name and len(rows) == 4: pwms.append(np.array(rows, float)); names.append(name)
                name = line[1:].split()[0]; rows = []
            else: rows.append([float(x) for x in line.split()])
    if name and len(rows) == 4: pwms.append(np.array(rows, float)); names.append(name)
    los, mu, var, width, ppms = [], [], [], [], []
    for m in pwms:
        m = m + PSEUDO; m = m / m.sum(axis=0, keepdims=True)
        lo = np.log2(m / BG)
        los.append(lo); ppms.append(m); width.append(lo.shape[1])
        mu.append(lo.mean(axis=0).sum()); var.append(lo.var(axis=0).sum())
    root = [re.split(r"[_\-]", n)[0] for n in names]
    return names, root, los, ppms, np.array(mu), np.array(var), np.array(width)

NAMES, ROOT, LOS, PPMS, MU, VAR, WIDTH = load_pwms()
NP_ = len(NAMES)
name2i = {n: i for i, n in enumerate(NAMES)}
ROOTU = np.array([str(x).upper() for x in ROOT], dtype=object)
def famkey(x):
    s = str(x).upper()
    while True:
        t = re.sub(r"[-_]?\d+$", "", s)
        if t == s or not t: break
        s = t
    return s
FAM = np.array([famkey(r) for r in ROOT], dtype=object)
BYW = {}
for i, w in enumerate(WIDTH): BYW.setdefault(int(w), []).append(i)
BYW = {w: np.array(ix) for w, ix in BYW.items()}
LOW = {w: np.stack([LOS[i] for i in ix]) for w, ix in BYW.items()}
print(f"loaded {NP_} PWMs")

def encode(seq):
    try: return np.array([BIDX[b] for b in seq], dtype=int)
    except KeyError: return None
def rc(e): return (3 - e)[::-1]

def best_scores(e):
    """best-window log-odds of encoded seq vs every PWM -> (NP_,)."""
    out = np.full(NP_, -np.inf); L = len(e)
    fwd, rev = e, rc(e)
    for w, lo_w in LOW.items():
        if w > L: continue
        W = np.concatenate([sliding_window_view(fwd, w), sliding_window_view(rev, w)])  # (k,w)
        sc = lo_w[:, W, np.arange(w)].sum(axis=2).max(axis=1)                            # (n_w,)
        out[BYW[w]] = sc
    return out

def exact_p(lo, score):
    q = np.rint(lo * SCALE).astype(int)
    dist = np.array([1.0]); base = 0
    for j in range(q.shape[1]):
        vals = q[:, j]; lo_v, hi_v = vals.min(), vals.max()
        col = np.zeros(hi_v - lo_v + 1)
        for v in vals: col[v - lo_v] += BG
        dist = np.convolve(dist, col); base += lo_v
    thr = int(np.ceil(score * SCALE)) - base
    if thr <= 0: return 1.0
    if thr >= len(dist): return 1.0 / 4 ** q.shape[1]
    return float(dist[thr:].sum())

def best_pos(e, lo):
    """(start_on_fwd, width) of the best-scoring window; None if unplaceable."""
    w, L = lo.shape[1], len(e)
    if w > L: return None
    col = np.arange(w); best = (-np.inf, 0)
    for strand, s in enumerate((e, rc(e))):
        sc = lo[sliding_window_view(s, w), col].sum(axis=1)
        k = int(sc.argmax())
        if sc[k] > best[0]:
            start = (L - w - k) if strand else k
            best = (sc[k], start)
    return (best[1], w)

def motif_corr(a, b):
    def one(x, y):
        wx, wy, best = x.shape[1], y.shape[1], -1.0
        for off in range(0, wy - wx + 1):
            ov = min(wx, y[:, off:off + wx].shape[1])
            if ov < 4: continue
            c = np.corrcoef(x[:, :ov].ravel(), y[:, off:off + ov].ravel())[0, 1]
            best = max(best, c)
        return best
    brc = b[[3, 2, 1, 0], ::-1]
    return max(one(a, b), one(a, brc)) if a.shape[1] <= b.shape[1] else max(one(b, a), one(brc, a))

def classify_sequence(seq, pwm_alias, tf):
    """Context-independent identity call for one binding site (no activity used).

    Returns the sequence-only fields shared by the full scan and the library
    coverage scan: call (retained/switched/dual/lost/ambiguous), the best own-
    and different-family p-values, the margin, the dual sub-type, and length."""
    # First alias, with any trailing _vN library-version suffix stripped so the
    # construct-DB form ('TF_..._v8') resolves the same as the standalone form.
    aname = re.sub(r"_v\d+$", "", str(pwm_alias).split()[0])
    e = encode(seq)
    if e is None:
        return dict(ok=False, length=0, aname=aname, call="ambiguous",
                    dual_kind="", other_tf="", p_ownfam=1.0, p_otherfam=1.0, margin=0.0)
    ai = name2i.get(aname); appm = PPMS[ai] if ai is not None else None
    own_root = ROOTU[ai] if ai is not None else str(tf).upper()
    fams = {famkey(own_root), famkey(tf)}
    sc = best_scores(e); finite = np.isfinite(sc)
    papprox = stats.norm.sf((sc - MU) / np.sqrt(VAR)); papprox[~finite] = 1.0
    samefam = np.isin(FAM, list(fams)) | (ROOTU == own_root)
    own_c = np.where(samefam & finite)[0]
    own_idx = own_c[np.argmin(papprox[own_c])] if len(own_c) else None
    p_own = exact_p(LOS[own_idx], sc[own_idx]) if own_idx is not None else 1.0
    oth_idx = None
    for i in np.argsort(papprox)[:60]:
        if not finite[i] or samefam[i]: continue
        if appm is not None and motif_corr(appm, PPMS[i]) >= FAM_CORR: continue
        oth_idx = int(i); break
    p_oth = exact_p(LOS[oth_idx], sc[oth_idx]) if oth_idx is not None else 1.0
    other_tf = ROOTU[oth_idx] if oth_idx is not None else ""
    margin = np.log10(max(p_own, 1e-300)) - np.log10(max(p_oth, 1e-300))
    own_sig, oth_sig = p_own < P_SIG, p_oth < P_SIG
    if own_sig and oth_sig: call = "switched" if margin >= SWITCH_MARGIN else "dual"
    elif own_sig: call = "retained"
    elif oth_sig: call = "switched"
    elif p_own >= 1e-3 and p_oth >= 1e-3: call = "lost"
    else: call = "ambiguous"
    dual_kind = ""
    if call == "dual" and own_idx is not None and oth_idx is not None:
        po, px = best_pos(e, LOS[own_idx]), best_pos(e, LOS[oth_idx])
        if po and px:
            ov = max(0, min(po[0] + po[1], px[0] + px[1]) - max(po[0], px[0]))
            dual_kind = "shared" if ov >= 0.5 * min(po[1], px[1]) else "distinct"
    return dict(ok=True, length=len(e), aname=aname, call=call, dual_kind=dual_kind,
                other_tf=other_tf, p_ownfam=p_own, p_otherfam=p_oth, margin=float(margin))

def main():
    # ------------------------------------------------------------ functional atlas
    print(f"project={PROJECT}  on={CFG['on']}  off={CFG['off']}  -> {CFG['out']}")
    df = pd.read_csv(CSV).rename(columns={CFG["on"]: "act_on", CFG["off"]: "act_off"})
    df["famk"] = df.tf.map(famkey)
    # Per-TF-family activity in the ON state, from the screen itself: lets a switch/dual
    # target be corroborated by whether that TF's own sensors actually fire here.
    ATLAS = df.groupby("famk").agg(n=("act_on", "size"), med_on=("act_on", "median"),
                                   max_on=("act_on", "max"), best_sel=("log2r", "max"))
    def corroborate(target_root, var_on):
        fk = famkey(target_root)
        if fk not in ATLAS.index: return (0, False, False, False)
        a = ATLAS.loc[fk]
        active = bool(a.med_on >= 0.5 or a.max_on >= 2.0)
        concord = bool(a.med_on * 0.5 <= var_on <= a.max_on * 1.5)
        return (int(a.n), active, concord, active and concord)

    # ------------------------------------------------------------ scan all variants
    LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else len(df)
    sub = df.iloc[:LIMIT]
    recs = []; t0 = time.time()
    for n, (_, r) in enumerate(sub.iterrows()):
        c = classify_sequence(r.tfbs_sequence, r.pwm, r.tf)
        if not c["ok"]:
            recs.append(dict(tf=r.tf, seq=r.tfbs_sequence, call="ambiguous", confidence="low")); continue
        p_own, p_oth, call, other_tf = c["p_ownfam"], c["p_otherfam"], c["call"], c["other_tf"]
        # functional corroboration for switch/dual targets
        tn, tact, tcon, fcorr = (0, False, False, False)
        if call in ("switched", "dual") and other_tf:
            tn, tact, tcon, fcorr = corroborate(other_tf, r.act_on)
        seq_bonf = min(p_own, p_oth) < BONF      # genome-wide significant
        seq_nom = min(p_own, p_oth) < P_SIG      # nominally significant
        if call in ("switched", "dual"):
            # functional corroboration can lift a nominally-significant call one tier
            if seq_bonf and fcorr: confidence = "high"
            elif seq_bonf or (seq_nom and fcorr): confidence = "med"
            else: confidence = "low"
        elif call == "retained":
            confidence = "high" if p_own < BONF else ("low" if c["length"] <= 6 else "med")
        else:
            confidence = "low" if c["length"] <= 6 else "med"
        recs.append(dict(tf=r.tf, assigned=c["aname"], seq=r.tfbs_sequence, len=c["length"],
                         act_on=round(r.act_on, 3), act_off=round(r.act_off, 3), log2r=round(r.log2r, 3),
                         call=call, dual_kind=c["dual_kind"], other_tf=other_tf,
                         p_ownfam=p_own, p_otherfam=p_oth, margin=round(c["margin"], 2),
                         target_n_sensors=tn, target_tumor_active=tact,
                         activity_concordant=tcon, functionally_corroborated=fcorr,
                         confidence=confidence))
        if (n + 1) % 2000 == 0:
            dt = time.time() - t0
            print(f"  {n+1}/{len(sub)}  ({dt:.0f}s, {1000*dt/(n+1):.1f} ms/variant)")
    res = pd.DataFrame(recs)
    res.to_csv(OUT / CFG["out"], index=False)
    print(f"\nscanned {len(res)} variants in {time.time()-t0:.0f}s -> {CFG['out']}")
    print("\n=== call distribution ===")
    print(res.call.value_counts().to_string())
    print("\n=== confidence ===")
    print(res.confidence.value_counts().to_string())
    sw = res[res.call.isin(["switched", "dual"])]
    if len(sw):
        print(f"\nswitch/dual: {len(sw)}  functionally corroborated: "
              f"{int(sw.functionally_corroborated.sum())} "
              f"({100*sw.functionally_corroborated.mean():.0f}%)")
        print("dual_kind:"); print(res[res.call == "dual"].dual_kind.value_counts().to_string())


if __name__ == "__main__":
    main()
