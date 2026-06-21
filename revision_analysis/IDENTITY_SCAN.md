# Variant TF-identity scan — methods, decision logic, and results

For every synthetic-enhancer sequence variant in TREND we ask a single, precise
question: **does this variant's binding site still match the transcription factor
(TF) it was designed from, or has the sequence change made it match a different TF —
or no TF at all?** This document describes the algorithm, the exact decision rule
("stay vs swap"), worked examples for each outcome, and two result framings (a
project-agnostic *global* view and the *ovarian-cancer-specific* view).

Code: [`identity_scan_full.py`](identity_scan_full.py) (full library) and
[`identity_scan_pilot.py`](identity_scan_pilot.py) (validation pilot).
Output: `identity_scan_full.csv` (one row per variant).

---

## 1. Inputs

| input | description |
|---|---|
| variant binding sites | the `TFBS_sequence` of each variant (4–30 bp; median 12) and its assigned source PWM / curated TF |
| PWM library | `references/all_ENCODE_MotifDb_ppm_no_NA_v1.txt` — **6,012** position-probability matrices spanning **1,370** TFs (heavily redundant: MYC ×42, E2F ×38, …) |
| activity | per-variant mean RNA/DNA reporter ratios (OV8 tumour, IOSE normal) — used only for *functional corroboration*, not for the sequence call |

## 2. Scoring a sequence against a motif (FIMO-style)

We use a calibrated log-odds model, **not** the fraction-of-consensus affinity used
elsewhere in the project, because fraction-of-consensus is not comparable across
motifs of different width and information content (a 4-bp and a 20-bp motif cannot be
ranked by it). Calibrated p-values normalise for both.

1. **Log-odds PSSM.** Each PWM column is pseudocounted (`+1e-3`, renormalised) and
   converted to base-2 log-odds against a uniform background:
   `LO[base, j] = log2( p[base, j] / 0.25 )`.
2. **Best window.** The variant is scanned on **both strands** at **all offsets**;
   the score against a PWM is the maximum window sum. A PWM wider than the variant
   cannot be placed (correctly leaving very short variants unscorable against long
   motifs).
3. **Calibrated p-value.** The score is converted to an upper-tail p-value under the
   background — *the probability a random site scores at least this well*:
   - **Ranking (all 6,012 PWMs):** a fast Gaussian approximation using each PWM's
     exact null score mean/variance.
   - **Final call (the chosen hits):** the **exact** null distribution by dynamic
     programming — each column contributes a 4-value score pmf (each base prob 0.25);
     these are convolved across columns (`numpy.convolve`) to the exact score
     distribution, and the p-value is the tail mass at or above the observed score.
   This is the FIMO algorithm (Grant, Bailey & Noble 2011), reimplemented in numpy so
   the pipeline has **no external motif-tool dependency** (MOODS/MEME do not build on
   the project's Python).

## 3. Collapsing motif redundancy into families

A "switch" must mean a *genuinely different* motif, not one of MYC's 42 near-identical
PWMs. Two PWMs are treated as the **same family** if **either**:
- their TF-name roots collapse to the same key — trailing `-/_`+digit groups stripped
  *repeatedly* so `NKX6-1 → NKX6 → NKX` and `E2F3 → E2F`; **or**
- their motifs are highly similar — max Pearson correlation of the two
  position-probability matrices over all offsets and both orientations ≥ **0.60**.

The name rule is fast; the correlation rule catches cross-named families that share a
motif (e.g. the AP-1 bZIP group FOS/JUN/ATF reading `TGAC TCA`).

## 4. The decision rule — *stay or swap?*

For a variant assigned to TF *X* we compute two calibrated p-values:
- **`p_ownfam`** — best hit among PWMs in *X*'s family.
- **`p_otherfam`** — best hit among PWMs that are a *different* family **and**
  motif-dissimilar to *X* (correlation < 0.60), so shared-motif relatives never count
  as a switch.
- **`margin = log10(p_ownfam) − log10(p_otherfam)`** (>0 ⇒ the other TF matches better).

With `P_SIG = 1e-4` (nominal) and `SWITCH_MARGIN = 2` (the other TF must beat the own
family by ≥100× in p-value):

| call | condition | meaning |
|---|---|---|
| **retained** | own significant, other not (or margin < 2) | still the assigned TF |
| **switched** | other significant **and** margin ≥ 2 (or own not significant) | a different TF replaced it |
| **dual** | own **and** other both significant, margin < 2 | both motifs match |
| **lost** | neither significant (both p ≥ 1e-3) | no recognisable TF site |
| **ambiguous** | weak/borderline, no clear winner | unresolvable (usually short/low-information) |

### 4a. Splitting `dual` by site position
For each `dual` we record the best-scoring window position of the own and other
matches. If the two windows overlap ≥ 50% it is a **shared** site (one location read
by two TFs — i.e. assignment ambiguity at that site); if they are separated it is a
**distinct** dual (two genuinely different sites in one variant — rare, and only
possible in the longer variants).

## 5. Functional corroboration (using the screen as a TF-activity atlas)

A motif match is only *potential* binding. But TREND measures, in the same assay, the
activity of every TF that has its own designed sensors — an internal functional
TF-activity atlas. For each **switch/dual** target *Y* we therefore ask:
- **`target_has_sensors`** — does *Y* have its own sensors in the library?
- **`target_tumor_active`** — are *Y*'s sensors tumour-active (family median OV8 ≥ 0.5
  or max ≥ 2.0)?
- **`activity_concordant`** — does *this* variant's OV8 fall within *Y*'s sensor
  activity range (≈ 0.5× median to 1.5× max)?
- **`functionally_corroborated`** = active **and** concordant.

This both **strengthens** true switches (the destination TF is independently shown to
drive activity here, and the variant behaves like its sensors) and **rejects** false
ones (if *Y*'s own sensors are dead, a switch to *Y* cannot explain the variant's
activity).

## 6. Confidence tier

- **retained:** `high` if `p_ownfam` clears Bonferroni (0.05 / 6012 ≈ 8.3e-6), else `med`.
- **switched / dual:** `high` if Bonferroni-significant **and** functionally
  corroborated; `med` if Bonferroni-significant **or** (nominally significant **and**
  corroborated); else `low`. Functional corroboration can lift a nominally-significant
  call one tier but never manufactures a high call from weak sequence evidence.
- **lost / ambiguous:** `low` if ≤ 6 bp, else `med`.

## 7. Worked examples (one or two per outcome)

All values are from `identity_scan_full.csv`; the motif core is marked in the site.

**RETAINED — the change tunes the same TF.**
- `MYC` `AAAC`**`CACGTG`**`TTTT` — canonical E-box; own-family p = 4e-9 (≫ Bonferroni),
  no different-family competitor. Tumour-selective (log2 OV8/IOSE = +1.30). The variant
  is unambiguously still MYC.
- `ESRRA` `GGCC`**`AAGGTCA`**`CAG` — ESRRE/nuclear-receptor half-site; own p = 4e-9.

**SWITCHED — a few-nt change moves a different TF in.**
- `PAX8 → FOSL2` `TT`**`GACTCA`**`CGCGTA` — a paired-domain variant that gained a
  canonical AP-1 (bZIP) site; other-family p = 7e-6 (Bonferroni), margin 2.2, and
  FOSL2/AP-1 has 222 tumour-active sensors with concordant activity → **corroborated,
  high**. (Normal-selective: switching is bidirectional.)
- `XBP1 → MAF` `GAATAACGCAA`**`CGTCAGCA`**`CATTT` — bZIP-to-bZIP onto a MARE element;
  other-family p = 1.4e-7 (the strongest switch in the set), corroborated.

**DUAL (distinct) — two real sites in one long variant.**
- `NFIC + GATA` `AGCT`**`TGTT`**`ATCTGGCA`**`GGTAGC`**`CAAGA` (29 bp) — an NFI half-site
  and a GATA site at *separate* positions; own p = 2.5e-7, other p = 7e-6, GATA
  corroborated → high. Only ~10 variants in the whole library are true distinct duals,
  all long (median 22 bp), because a single ~12-bp repeat unit rarely fits two motifs.

**DUAL (shared) — one site, two candidate TFs.**
- `MYOD1 + CTCF` `CAC`**`CACCAGGTG`**`GCGTCT` — the same window scores for an E-box
  (MYOD1) and an unrelated motif (CTCF-like); the two best windows overlap, so this is
  *ambiguity about which TF reads the one site*, not two bound factors. 4,221 of the
  4,231 duals are of this shared type.

**LOST — the site no longer matches any motif.**
- `HOXA6` `TAAT` (4 bp) — too short/degenerate to reach significance against anything
  (own p = 4e-3). Lost calls are dominated by 4–5 bp sites.

**AMBIGUOUS — functionally strong but too short to assign.**
- `MYC` `CACGTGC` (7 bp) — a minimal E-box that is highly active and very tumour-
  selective (log2 = +3.5) yet only nominally significant (own p = 2e-4), with several
  unrelated motifs competing. A useful caution: a variant can be a strong functional
  element while its TF identity remains sequence-ambiguous.

## 8. Results — GLOBAL (project-agnostic): how variant introduction affects identity

The *call* (retained/switched/dual/lost/ambiguous) is a property of sequence vs motif
and does not use cell-type activity, so it is a general statement about the variant
library. Across all 37,832 variants, **69.8% retain their assigned-TF identity**;
the rest are mostly ambiguous (15.0%) or dual-shared (11.2%), with loss (3.2%) and
true switching (0.8%) rare. Identity confidence degrades smoothly as a variant
diverges from the consensus (lower relative affinity):

| relative affinity (1 = consensus) | retained | dual | switched | ambiguous | lost | retained & high-conf |
|---|---|---|---|---|---|---|
| < 0.1 (most divergent) | 49.7% | 11.8 | **2.3** | **27.9** | **8.3** | 30.8% |
| 0.1–0.3 | 71.6 | 11.6 | 0.4 | 14.5 | 2.0 | 52.9 |
| 0.3–0.6 | 80.3 | 11.7 | 0.2 | 7.1 | 0.8 | 66.1 |
| 0.6–0.9 | 84.7 | 10.2 | 0.0 | 4.8 | 0.2 | 75.8 |
| ≥ 0.9 (near consensus) | 82.9 | 6.6 | 0.0 | 10.1 | 0.4 | 71.8 |

**Take-away:** TF identity is robust to moderate sequence variation — for variants at
≥ 0.3 of consensus affinity, > 80% remain confidently the same TF and switching is
essentially nil. Identity erodes only for the most divergent variants (< 0.1 affinity):
~28% become ambiguous, ~8% lose all motif match, and a small ~2% switch TF. (The slight
rise in ambiguity at ≥ 0.9 is the minimal short E-box / low-information motifs, which
are sequence-ambiguous regardless of affinity.) This quantifies the confidence one can
place in a designed variant as a function of how far it strays from the consensus.

## 9. Results — OVARIAN-CANCER-SPECIFIC

Layering the OV8/IOSE activity and functional corroboration on the same calls:

- **43%** of the 4,550 switch/dual calls are **functionally corroborated** — the
  destination TF has tumour-active sensors and the variant behaves like them.
- Among the load-bearing **tumour-gain** variants (best variant gained tumour activity
  over consensus), identity is **predominantly retained** (~64%): the gain is mostly
  the *same* TF being affinity-tuned, not a different TF moving in. A minority involve
  a different TF, concentrated in the longer variants.
- Worked locus: **PAX8** (a reviewer-named gene) repeatedly acquires E-box
  (→ MLX/MYC/MAX) or AP-1 (→ FOSL2) cores — see
  [`pax8_switch_example.md`](pax8_switch_example.md).

## 10. Cross-context replication — T-cell activation screen

The identical pipeline was run on the primary-human-T-cell activation screen
(`identity_scan_tcell.csv`; 12,113 variants quantified in both stimulated and resting
T cells; on-state = stimulated). The sequence-based identity result **replicates the
ovarian-cancer findings almost exactly**, establishing that the conclusions are a
property of the variant library, not of one cell system:

| metric | ovarian cancer | T-cell activation |
|---|---|---|
| variants scanned | 37,832 | 12,113 |
| retain assigned-TF identity | 69.8% | **71.6%** |
| dual / switched / lost | 11.2 / 0.8 / 3.2% | **10.3 / 0.9 / 2.9%** |
| retained at < 0.1 affinity (most divergent) | 49.7% | **50.4%** |
| switched at < 0.1 affinity | 2.3% | **2.6%** |
| ambiguous at < 0.1 affinity | 27.9% | **27.7%** |

The same affinity-dependent erosion of identity is seen: confident retention rises
from ~50% at the most divergent sites to ~85% near consensus, and TF switching is
negligible except at very low affinity. **Note on functional corroboration:** the
T-cell switch/dual corroboration rate is lower (≈8% vs 43%), because stimulated-cell
RD ratios are compressed (median ≈ 0.49, max ≈ 1.0) relative to the wider OV8 range, so
the fixed activity thresholds (on-state median ≥ 0.5 or max ≥ 2.0) clear less often.
This is a property of the readout scale, not of the identity calls, which replicate
directly. (Because OvCa and T-cell screen the *same* synthetic-enhancer library, every
T-cell binding site is also present in the OvCa scan; the value here is the independent
cross-context replication, not additional sequence coverage.)

## 11. Reproducibility

```bash
pip install numpy pandas scipy                # only these; no MOODS/MEME needed
python identity_scan_full.py ovca             # ~5 min, writes identity_scan_full.csv
python identity_scan_full.py tcell            # ~1.5 min, writes identity_scan_tcell.csv
```
Deterministic; the scorer, family grouping, decision thresholds, and functional-atlas
construction are all in the one script (the project argument selects the input table and
on/off activity columns). Key parameters (editable at the top):
`P_SIG=1e-4`, `SWITCH_MARGIN=2`, `FAM_CORR=0.60`, Bonferroni = 0.05/6012.

## 11b. Library coverage scan (every construct gets a call)

The construct library (`library.sqlite`) holds **54,193** distinct binding sites —
the **93.9%** of the 57,715 designed sensors that survived cloning/screening into
real barcoded constructs (the other 3,522 designed sensors have no recoverable
activity — 100% NA across barcodes — and no construct page, so are out of scope).
The activity-quantified standalone tables cover 37,832 of those 54,193; the remainder
were filtered out before activity analysis and so had no identity call. `identity_scan_coverage.py` runs the *same*
`classify_sequence()` classifier (imported from `identity_scan_full.py`) on those
16,361 remaining sites, taking their assigned TF / PWM directly from the construct
database. Their call distribution matches the quantified set (retained ~66%, dual
~14%, ambiguous ~16%, lost ~4%, switched ~0.7%). Because these sites are in neither
activity screen, **functional corroboration is not available** for them — they carry
the sequence call only, and the app marks corroboration "not measured" for both
screens. `build_variant_identity.py` merges the quantified and coverage rows into the
app lookup so **100% of constructs** show an identity card.

```bash
python identity_scan_coverage.py        # ~2 min, writes identity_scan_coverage.csv
python build_variant_identity.py        # merges -> dashboard .../variant_identity.csv
```

## 12. Limitations

- Sequence-based **prediction** of which motif a variant matches — not a measurement of
  binding (which would need PBM/SELEX/ChIP).
- Short/low-information sites (≤ ~7 bp) are intrinsically unresolvable and are reported
  as `ambiguous`/`lost` rather than force-called.
- Functional corroboration requires the destination TF to have its own sensors in the
  library (~1,036 of 1,370 TFs do); otherwise the call stays sequence-only. Its absolute
  rate also depends on the screen's activity range (see §10).
- Uniform-background model; a genome dinucleotide background would shift absolute
  p-values slightly but not the relative calls.
