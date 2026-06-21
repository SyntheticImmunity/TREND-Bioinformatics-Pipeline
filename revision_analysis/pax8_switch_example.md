# Worked example — single-nucleotide motif switching at PAX8-derived variants

**Addresses:** R1-minor-1 (do single-/few-nucleotide changes switch the *recognized*
transcription factor?) and R3 (which names PAX8 as a target of interest).

## Method (one line)
Each variant's binding site is scanned against all 6,012 ENCODE/MotifDb PWMs with
calibrated (FIMO-style) p-values; a match to a *different, motif-dissimilar* TF
family is reported only if it is significant, and is then **functionally
corroborated** against the rest of the screen — i.e. does that target TF have its
own tumour-active sensors, and does this variant's activity fall in their range?

## What the scan shows for PAX8
The paired-domain PAX8 motif sits a single/few substitutions away from two very
common short cores, and PAX8-derived variants repeatedly acquire them:

- a **CACGTG E-box** → read by the bHLH factors **MLX / MYC / MAX**
- a **TGA(C/G)TCA AP-1 site** → read by the bZIP factor **FOSL2 (AP-1)**

Two representative, functionally cross-validated calls:

| assigned | variant site | switches to | OV8 | IOSE | log2(OV8/IOSE) | seq p (other) | functional corroboration | confidence |
|---|---|---|---|---|---|---|---|---|
| PAX8 | `CTTTAA`**`CACGTG`**`AAC` | **MLX** (E-box) | 1.22 | 0.67 | **+0.88 (tumour-leaning)** | 4×10⁻⁵ | MLX has 77 own sensors, tumour-active (median OV8 1.23, best 8.8×); this variant's OV8 (1.22) sits *on* the MLX sensor median | med |
| PAX8 | `TT`**`GACTCA`**`CGCGTA` | **FOSL2** (AP-1) | 0.99 | 2.81 | −1.51 (normal-leaning) | 7×10⁻⁶ | FOSL2/AP-1 has 222 own sensors, tumour-active and activity-concordant | **high** |

The same PAX8 background also produces a series of lower-confidence E-box duals
(MYC, MAX, ZBTB33, SOX8, NKX2, EN1…), consistent with the CACGTG core being read
promiscuously across the bHLH family.

## Why this is more than a motif match
Each call rests on **three independent lines** that the motif scan alone could not
supply:
1. **Sequence** — the variant gained a canonical E-box / AP-1 core (and lost the PAX8
   match).
2. **Functional presence** — the destination TF (MLX, FOSL2) is independently shown
   to be a tumour-active driver in *this* screen by its own sensors.
3. **Concordance** — the variant's measured activity matches that destination TF's
   sensor range.

This is the internal-consistency argument the resource uniquely enables: TREND is at
once a sequence library and a same-experiment functional TF-activity atlas, so a
sequence-based identity call can be validated against functional replication within
the same dataset.

## Honest scope
- **PAX8→MLX** is *functionally* corroborated but its sequence match (p≈4×10⁻⁵) does
  not clear genome-wide (Bonferroni) significance, so it is graded **med**, not high —
  the functional evidence lifts it one tier but does not manufacture certainty.
- **PAX8→FOSL2** clears both bars and is graded **high**, but it is *normal*-selective
  — a reminder that motif switching occurs in both directions, not only toward
  tumour gain.
- These remain sequence-plus-function *predictions*; direct binding (PBM/SELEX/ChIP)
  is out of computational scope.

## Bottom line
Single-/few-nucleotide changes at PAX8-derived sensors demonstrably switch the
recognised TF family (most often to E-box bHLH or AP-1 bZIP factors), and the switch
can be corroborated by the destination TF's own functional behaviour in the same
screen — a concrete, quantified answer to R1-minor-1 at a reviewer-named locus.
