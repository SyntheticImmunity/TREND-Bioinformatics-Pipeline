# Designing a combinatorial enhancer library from single-motif TREND data
### A rational-prioritization proposal — *not* a combinatorial-activity predictor

## 1. Scope: what we claim, and what we do not

We do **not** claim to predict the activity of an arbitrary multi-motif construct.
Combinatorial transcription-factor logic — cooperativity, spacing, orientation,
helical phasing — is not generalizable in current TF biology, and the TREND
library contains no heterotypic (different-motif) constructs, so no interaction
term can be fit from it. **Synergy — an AND-gate — is by definition the deviation
from an independence baseline. It is a quantity an experiment *measures*, not one
that single-site data can predict.** Any tool that claimed otherwise would be the
overclaim a reviewer should reject.

What we *do* claim: single-motif TREND data — uniquely, because it provides
(i) **cell-type-resolved selectivity** for each motif and (ii) a **sequence-variant
dose dial** for each motif — lets us design a combinatorial library that is
**strongly enriched** for the two outcomes of interest (supra-additive activity and
tumor-specific AND-gates). This converts a blind combinatorial screen into a
hypothesis-driven one and yields the first **library-scale measurement of
motif-level cooperativity**.

## 2. Two targets, two baselines — they are not the same problem

| | Target A — *enhanced activity* (OR-like / supra-additive) | Target B — *AND-gate* (coincidence detection) |
|---|---|---|
| Behavior | both motifs individually active; together, more | each motif individually weak; strong **only** when both present |
| Independence baseline | **predicts** the combined activity; rank candidates by it, measure the supra-additive surplus | **predicts LOW for exactly these pairs** → cannot rank them |
| What single-motif data gives | a quantitative ranking | **selection criteria that raise the AND-gate prior**, not a prediction |

This split is the rigorous position: **we predict A; we enrich for B.** Conflating
the two is where combinatorial-prediction claims usually go wrong.

## 3. Why an AND-gate is *enrichable* from single-site data (the biophysics)

An AND-gate requires a steep, nonlinear response that fires only on coincidence.
Three necessary conditions follow, and TREND measures all three at the single-motif
level:

- **Two different TF inputs (D1).** Two copies of the same motif add avidity
  monotonically — no logic. A genuine gate integrates two *distinct* signals, so the
  pair must be two different PWMs / TF families. *(TREND measurable: TF identity.)*
- **Each site individually sub-saturating (D2).** If either motif alone already
  saturates output, there is no "both required" regime — it is already on. An
  AND-gate can only exist when both inputs sit on the **rising, sub-threshold** part
  of their dose-response. **This is precisely what the variant/affinity series lets
  us set:** choose, for each motif, the variant that poises it sub-saturating.
  *(TREND measurable: the per-motif affinity→activity transfer function.)*
- **Both inputs biased toward the target state (D3).** For the gate to be
  *tumor-specific*, both individually weak inputs should still lean tumor (each
  `log2(OV8/IOSE) > 0`). The coincidence of two tumor-leaning signals multiplies the
  bias, sharpening a weak single-input preference into a steep tumor-specific
  threshold. *(TREND measurable: per-motif selectivity.)*

None of this predicts the cooperativity strength ω — that is the experiment's job.
But it concentrates the candidate set on pairs that are *poised to form a
tumor-specific gate if any cooperativity exists*, which is the difference between a
1-in-1000 and a (plausibly) 1-in-10 hit rate.

## 4. Design rules, each tied to a TREND-measurable

| Rule | Rationale | TREND measurable |
|---|---|---|
| **D1** Different TFs / families | two distinct inputs = logic, not avidity | PWM / TF identity |
| **D2** Poise each site sub-saturating (pick the variant) | necessary condition for a cooperative threshold | affinity→activity transfer function (variant series) |
| **D3** Each input individually target-biased | coincidence of two biased inputs = state-specific gate | `log2(OV8/IOSE)` per motif |
| **D4** Keep independence-predicted activity below the observed ceiling | leaves dynamic range for synergy to be detected | activity ceiling across the library |
| **D5** Arm-A: one activity-raiser + one off-state-suppressor; Arm-B: both weak-but-biased | A maximizes additive selectivity; B maximizes the AND-gate prior | fig3/fig4 two-lever decomposition |

## 5. Proposed library (two arms) and falsifiable predictions

- **Arm A — enhancement.** Top complementary pairs by independence-predicted
  selectivity. *Prediction:* combined selectivity ≈ sum of single-motif
  log-selectivities, capped at the activity ceiling; deviations quantify
  cooperativity.
- **Arm B — AND-gate.** Different-TF pairs, both target-biased, both variant-tuned
  sub-saturating. *Prediction:* a measurable subset shows supra-additive,
  state-specific activation (high output only with both sites); the **hit rate and
  the distribution of cooperativity ω are the primary results.**
- **Built-in controls.** Every pair's single-site constructs (already the native
  TREND format) give the exact per-construct independence baseline; scrambled-spacer
  and reversed-orientation versions isolate architecture effects.

## 6. Why only TREND enables this

At library scale you need **both axes simultaneously**: cell-type resolution (to make
the gate state-specific) *and* a per-motif sequence-variant dose dial (to poise each
site in the cooperativity-sensitive regime). TREND is, to our knowledge, the only
resource that supplies both for thousands of motifs — which is what turns "test
random pairs" into "test pairs poised to form tumor-specific gates."

## 7. Sourcing the cooperativity prior from native genomic grammar

Single-motif data cannot tell us *which* pairs cooperate — but the genome already
ran that screen over evolutionary time. We therefore import the cooperativity prior
from native co-occurrence rather than inventing it. Two sources, of different
strength:

- **TF adjacency + spacing matrix (primary, stronger).** Scan a reference genome
  (and/or a cancer-enhancer set) with the same ENCODE/MotifDb PWM collection TREND
  uses; for every motif pair, test whether the two sites co-occur at *short,
  constrained distances and orientations* more than a shuffled/dinucleotide-matched
  background. Preferred spacing is the genomic fingerprint of cooperative/composite
  binding, and — crucially — **it also specifies the spacing and orientation to build
  with**, removing one of the architecture unknowns from §7. Output: a ranked,
  spacing-annotated list of candidate cooperative pairs.
- **Cancer super-enhancer co-occurrence (context filter, weaker).** Which TFs
  co-occur in cancer super-enhancers (public H3K27ac / BRD4). Good for restricting to
  *cancer-relevant* pairs, but weak evidence of *direct* cooperativity (super-enhancers
  span tens of kb, so co-occurrence may be independent co-binding). Use as a context
  filter on top of the adjacency matrix, not as the primary signal.

**Integration with TREND (each evidence source used for what it is good at):**
native grammar selects *which pair* and *what spacing* (the cooperativity prior);
TREND selects *which sequence variant* of each motif (target-biased, headroom-aware
per §3–4) and supplies the cell-state selectivity of each input. A candidate
construct is thus a genomically-preferred, spacing-defined motif pair, each site
instantiated with the TREND variant that maximises target selectivity while staying
sub-saturating.

**Feasibility / scoping.** A context-agnostic adjacency+spacing matrix is computable
now from a reference genome plus the PWM file already in the repo; the all-pairs scan
is made tractable by **restricting to the TREND-relevant TF set** (the few hundred
motifs that are target-biased in the screen) rather than all ~6,000 PWMs. The
cancer-specific super-enhancer filter requires external ENCODE/GEO peak data (a
bounded download + ROSE-style super-enhancer calling). This analysis is double-duty
with the reviewers' native-genome requests (endogenous-enhancer mapping; super-enhancer
context; named cancer loci).

**Caveat.** Native co-occurrence is correlational and chromatin-context-dependent;
co-binding in the genome need not reproduce as synergy in a synthetic reporter. It is
the *best available prior*, not a guarantee — the combinatorial library still measures
the actual cooperativity ω for each prioritised pair.

## 8. Limitations (state up front)

Spacing, orientation, helical phasing, and the cooperativity parameter ω itself are
**not** modeled; they are held constant by design or scanned within the new library.
The output is an **experiment design plus a null baseline**, not an activity oracle.
Validation requires building the combinatorial library.

## 9. One-paragraph reviewer-response version

> We agree that combinatorial enhancer logic is not yet predictable from first
> principles, and we do not claim a combinatorial-activity model. We instead show how
> the single-motif TREND resource rationally *designs* a combinatorial screen. Because
> TREND resolves each motif's activity by cell state and, through its sequence-variant
> series, maps each motif's affinity→activity dose-response, it uniquely identifies
> motif pairs that are (i) driven by two different transcription factors, (ii)
> individually biased toward the target state, and (iii) individually poised in the
> sub-saturating regime where cooperativity can produce a threshold — the three
> necessary conditions for a state-specific AND-gate. The proposed library tests these
> prioritized pairs against their exact single-site independence baselines, providing
> the first library-scale measurement of motif-level cooperativity and a direct route
> to coincidence-detector enhancers. To prioritise pairs likely to cooperate, we draw
> the prior from native genomic grammar — motif adjacency, preferred spacing, and
> cancer super-enhancer co-occurrence — and instantiate each genomically-favoured pair
> with the TREND variants that maximise target selectivity. This reframes combinatorial
> design from unconstrained prediction to data-driven hypothesis generation, which we
> believe is the appropriate and rigorous use of the resource.
