# TF mRNA does not predict enhancer activity — figure guide

For each figure: first a **plain-language explanation** (what it is, how it's built,
what to look for), then a **formal legend** you can drop into the revision. All
figures use the same join — per-TF tumour-vs-normal mRNA (OV8 / IOSE RNA-seq TPM)
against the TREND ovarian sensor screen — over the **755 TFs** expressed in either
cell type (max TPM > 1) that also have sensors (median 17 sensors per TF).

## Terms used everywhere (read once)

- **Sensor** — one synthetic enhancer (a transcription-factor binding-site variant
  in a reporter). Each TF is represented by *many* sensors (median 17).
- **Sensor selectivity** — a sensor's tumour-vs-normal activity ratio, OV8 / IOSE.
  We usually take log2, so 0 = equal in both, 1 = 2-fold tumour-selective, 2 = 4-fold.
- **Best-sensor selectivity (of a TF)** — the selectivity of that TF's *single most
  tumour-selective sensor*. It answers the practical question: "if I screened this
  TF, what is the best enhancer I could get from it?" One number per TF.
- **Differential TF expression** — log10(OV8 TPM / IOSE TPM): how much more the TF's
  *mRNA* is expressed in tumour vs normal cells. This is the cheap RNA-seq metric one
  might hope to shortcut the screen with. One number per TF.

The whole story: that mRNA number (cheap) tells you almost nothing about the
best-sensor number (which needs the screen).

---

## Figure A — Selecting by mRNA is no better than chance (recovery curve)

**Plain words.** Pretend you must choose which TFs to build enhancers from, and you
can only rank them by one criterion. Define the "right answers" as the **50 TFs whose
best sensor is the most tumour-selective** — the 50 you'd most want to find.
- The **x-axis** is how many TFs you have picked so far (1, 2, 3, …).
- The **y-axis** is what percentage of those 50 right answers you have captured.
- **Red line (mRNA-ranked):** pick TFs in order of mRNA over-expression (most
  over-expressed first); at each step count how many of the 50 you've hit.
- **Grey dashed line (random):** what you'd get picking blindly — recovery rises in
  simple proportion to how many you've picked (a straight diagonal).
- **Green line (screen-guided):** picking by the screen itself, the 50 best *are* your
  first 50 picks, so it shoots straight to 100%.

**What to see:** the red mRNA line sits essentially *on top of* the grey random line.
Picking the top 50 TFs by mRNA recovers **0 of the 50** best (random would give ~7%).
So ranking by mRNA is no better than choosing at random.

**Formal legend.** *Cumulative recovery of the 50 most tumour-selective TFs (ranked by
their best sensor in the TREND screen) as a function of the number of TFs selected.
TFs were selected in descending order of differential mRNA expression (red), by the
screen's own selectivity (green, the ideal), or at random (grey dashed, analytical
expectation). Selection by differential mRNA expression recovers the top sensors no
faster than random selection (0 of the top 50 within the first 50 TFs selected).*

---

## Figure B — The signal lives within each TF, where mRNA cannot see it (variance)

**Plain words.** mRNA gives exactly **one number per TF**. The best it could ever do is
*rank TFs*. But selectivity varies enormously **between sensors of the same TF**, and a
single per-TF number is blind to that.
- **Between-TF variance** = how much TFs differ *from each other* (spread of the per-TF
  averages). This is the only part a per-TF number like mRNA could possibly explain.
- **Within-TF variance** = how much sensors *of the same TF* differ from one another
  (the vertical spread inside a single TF). mRNA cannot address this at all.

We measured **within-TF = 0.34** vs **between-TF = 0.16** → within is **2.1× larger**.
So most of the variation in enhancer selectivity is sensor-to-sensor *inside* a TF —
exactly the part invisible to any per-TF measurement. Even a *perfect* TF-ranker would
miss the larger share of the signal.

**How it's drawn:** each light-blue dot is one sensor, placed by its TF's mRNA
differential (x) and its own selectivity (y); black dots are the per-TF medians. At any
x the blue points scatter widely up and down (large within-TF variance), and the black
medians stay flat (no between-TF trend with mRNA).

**Formal legend.** *Per-sensor tumour selectivity (log2 OV8/IOSE; light points) for all
sensors, positioned by their transcription factor's differential mRNA expression; black
points are per-TF medians. The variance of selectivity within transcription factors
(mean 0.34) exceeds the variance between TF medians (0.16) by 2.1-fold, i.e. the
dominant axis of variation is between sensors of the same TF — a dimension inaccessible
to any single per-TF measurement such as mRNA abundance.*

---

## Figure C — mRNA as a yes/no test for "has a good sensor" (ROC / AUC)

**Plain words.** Turn it into a simple test. Label each TF "good" if it has at least one
≥2-fold-selective sensor (40% of TFs do). Now ask: can the mRNA differential *flag* the
good ones? Slide a cutoff on mRNA from high to low; at each cutoff you catch some good
TFs (true positives) but also wrongly flag some bad ones (false positives). The **ROC
curve** plots that trade-off (true-positive rate vs false-positive rate).

**AUC (area under the curve)** summarizes it in one number = the probability that a
randomly chosen *good* TF has higher mRNA than a randomly chosen *bad* TF.
- AUC = 1.0 → a perfect predictor; AUC = 0.5 → a coin flip (the diagonal dashed line).
- We get **AUC = 0.54** — barely above the 0.50 coin-flip line. mRNA essentially cannot
  tell a TF that has a good sensor from one that doesn't.

**Formal legend.** *Receiver-operating-characteristic curve for differential mRNA
expression used as a classifier of transcription factors that yield at least one
≥2-fold tumour-selective sensor (40% of TFs). The area under the curve (0.54) is close
to the chance value of 0.50, indicating mRNA abundance does not discriminate TFs with
selective enhancers from those without.*

---

## Figure D — Neither prior literature nor mRNA finds the best enhancers (quadrant)

**Plain words.** Every grey dot is one TF, placed by its mRNA differential (x) and its
best-sensor selectivity (y). Dotted lines mark 2-fold mRNA up (vertical) and 2× selective
(horizontal). Three groups of TFs are highlighted in colour:
- **Green — most tumour-selective sensors (the screen's winners).** These are at the
  **top** (high selectivity) but at **flat mRNA** (middle): e.g. the E2F/DP module
  (E2F7, E2F8, E2F6, E2F3, TFDP1) and MYC.
- **Blue — field-acknowledged ovarian-cancer TFs** (PAX8, WT1, SOX17, MECOM, FOXM1).
  These sit **low**: PAX8, the canonical lineage TF, is strongly mRNA-over-expressed yet
  its best sensor is only ~2×; WT1/SOX17/MECOM are neither over-expressed nor selective.
- **Red — most mRNA-over-expressed TFs** (what an RNA-seq screen would pick). These sit
  at the **far right** (high mRNA) but **low** selectivity.

**What to see:** the top of the plot (the best enhancers) is occupied by the green
screen-winners — and *only* by them. The TFs you'd pick from prior biology (blue) or
from mRNA (red) are not there. Each dot's colour is defined in the legend: green = best
sensor from the screen, blue = literature-acknowledged TF, red = most mRNA-differential.

**Formal legend.** *Each point is a transcription factor positioned by its differential
mRNA expression (x) and the selectivity of its most tumour-selective sensor (y); dotted
lines mark 2-fold mRNA over-expression and 2-fold sensor selectivity. Highlighted: the
six TFs with the most selective sensors in the screen (green), field-acknowledged
ovarian-cancer transcription factors (blue: PAX8, WT1, SOX17, MECOM, FOXM1), and the six
most mRNA-over-expressed TFs (red). The most selective enhancers derive from TFs that are
neither the most over-expressed nor the canonical ovarian-cancer factors.*

---

## Figure E — The most over-expressed TFs are unremarkable sensors (distributions)

**Plain words.** Compare two groups of TFs by their best-sensor selectivity:
**all TFs** (grey) vs the **20 most mRNA-over-expressed TFs** (red). The x-axis is
best-sensor selectivity (log2 OV8/IOSE — same "best sensor per TF" number as above).

**"Density" (y-axis)** is just a histogram rescaled so each group's bars sum to the same
total area. We do this because one group has 755 TFs and the other has 20 — plotting raw
counts would make the 755 dwarf the 20. Density answers "what *fraction* of this group
has this selectivity," so the two groups are comparable. Vertical lines mark each group's
median.

**What to see:** the two distributions sit on top of each other (medians 1.76× vs
1.87×). Being among the most over-expressed TFs does not make a TF a better enhancer
source.

**Formal legend.** *Distribution of best-sensor selectivity (log2 OV8/IOSE) for all TFs
(grey) and for the 20 most mRNA-over-expressed TFs (red), shown as area-normalized
densities; vertical lines mark group medians (1.76-fold vs 1.87-fold). The most
over-expressed transcription factors are indistinguishable from the library as a whole
in the selectivity of the enhancers they yield.*

---

## Figure F — mRNA rank vs enhancer rank is a scramble (rank–rank)

**Plain words.** Rank all 755 TFs two ways: by mRNA differential (x-axis, rank 1 = most
over-expressed) and by best-sensor selectivity (y-axis, rank 1 = most selective). If mRNA
predicted enhancer quality, points would fall along a diagonal. Instead they fill the
square at random (**Spearman ρ = 0.10**, i.e. essentially no relationship).

**Why these TFs are labelled (not arbitrary):** the coloured/labelled points are the same
three meaningful groups as Figure D — **green** = the screen's most selective TFs,
**blue** = field-acknowledged ovarian-cancer TFs, **red** = the most mRNA-over-expressed
TFs. You can see green clustered along the bottom (top sensors) but spread all across the
x-axis (their mRNA rank is unremarkable), and red clustered on the left (top mRNA) but
spread all up the y-axis (their sensors are mediocre).

**Formal legend.** *Transcription factors ranked by differential mRNA expression (x;
rank 1 = most over-expressed) versus by best-sensor selectivity (y; rank 1 = most
selective). The two rankings are uncorrelated (Spearman ρ = 0.10). Highlighted groups as
in panel D: most-selective sensors (green), field-acknowledged ovarian-cancer TFs (blue),
and most mRNA-over-expressed TFs (red); none of the three groups aligns the two rankings.*

---

## Figure 0 — reference (your current Fig S3A, reproduced)

**Plain words / legend.** Per-TF differential mRNA expression vs the *median* selectivity
of that TF's sensors; Pearson r = −0.02 (matching the original −0.03). This is the
existing "no correlation" view; figures A–F reframe the same null as a positive,
decision-relevant demonstration.

---

## Note for assembling the revised supplementary figure

These are standalone panels. If they become one multi-panel supplementary figure, a
combined legend would read: *"Differential TF mRNA expression does not predict synthetic-
enhancer selectivity. (A) Recovery curve … (B) variance decomposition … (C) ROC … (D)
TF map with three reference groups … (E) selectivity distributions … (F) rank–rank."*
The same three reference groups (screen-best / literature / mRNA-top) are used in panels
D and F so a reader can track the same TFs across both.
