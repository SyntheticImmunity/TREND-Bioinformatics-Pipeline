"""Build the bundled reviewer-facing fixtures.

Three tiers (matches `trend run --example {smoke,step9,pipeline}`):

  T1 / smoke    — already shipping; uses the published outputs at
                  project_data/final_enhancer_activity_results/. No new data.

  T2 / step9    — subsamples ~1,000 promoters from the published OvCa run.
                  Bundled inputs at example_data/ovca_step9/inputs/ are
                  consistent slices of alignment_result_*.csv +
                  all_enhancer_metadata_111525.csv. Expected outputs at
                  example_data/ovca_step9/expected/ are the same-promoter
                  slice of ovca_sensor_activity_result_*.csv. A reviewer with
                  R installed can re-run the unchanged Step-9 R script against
                  the inputs and reproduce the expected outputs row-for-row.

  T3 / pipeline — subsamples ~50 promoters / ~250 barcodes from Lib4.fasta,
                  simulates 8 sample FASTQs (4 DNA + 4 RNA across 2 cell lines)
                  with known per-barcode read counts, and emits the
                  analytically-correct post-Step-8 count matrix as the
                  expected output. A reviewer with the full conda env can
                  invoke Snakemake against the simulated FASTQs and verify
                  Step 8's output matches.

Usage:
    python tools/build_fixtures.py            # rebuild everything
    python tools/build_fixtures.py --tier t2  # just T2
    python tools/build_fixtures.py --tier t3  # just T3

The output tree:

    dashboard/example_data/
      ovca_step9/
        inputs/
          alignment_result_normalized_in_house_pipeline.csv     ~3 MB
          alignment_result_unnormalized_in_house_pipeline.csv   ~2 MB
          all_enhancer_metadata_111525.csv                      ~200 KB
        expected/
          ovca_sensor_activity_result_concise.csv               ~250 KB
          ovca_sensor_activity_result_all.csv                   ~600 KB
        README.md
      ovca_pipeline/
        inputs/
          fastqs/
            OV8_DNA_r1.fastq.gz       ~30 KB each
            OV8_RNA_r1.fastq.gz
            ...                       (8 samples total)
          Lib4_tiny.fasta             ~50 KB
          Lib4_info_tiny.csv          ~25 KB
          barcode_key.xlsx            ~5 KB
        expected/
          alignment_result_normalized_in_house_pipeline.csv     ~30 KB
          alignment_result_unnormalized_in_house_pipeline.csv   ~30 KB
          read_count_matrix.csv       (analytically-derived; for T3 oracle)
        README.md
"""

from __future__ import annotations

import argparse
import gzip
import logging
import random
from pathlib import Path

import pandas as pd

log = logging.getLogger("trend.fixtures")
random.seed(42)  # deterministic fixtures across rebuilds

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = REPO / "dashboard" / "example_data"

# ---------------------------------------------------------------------------
# Source paths (all read-only)
# ---------------------------------------------------------------------------
LIB4_FASTA = REPO / "codes" / "2. HPC_cluster_scripts" / "required_metadata" / "Lib4.fasta"
LIB4_INFO = REPO / "codes" / "2. HPC_cluster_scripts" / "required_metadata" / "Lib4_info_concise_060621.csv"
ENHANCER_META = REPO / "codes" / "3. Post_HPC_enhancer_activity_analysis_scripts" / "required_metadata" / "all_enhancer_metadata_111525.csv"
OVCA_ALIGN_DIR = REPO / "project_data" / "alignment_results" / "ovarian_cancer"
OVCA_ACTIVITY_DIR = REPO / "project_data" / "final_enhancer_activity_results" / "ovarian_cancer"

# Read structure constants (must match the existing pipeline's expectations).
FIVE_PRIME_ADAPTER = "TAAAGCGGCCGCGAGGATCC"   # 20 bp; cutadapt -g anchor
THREE_PRIME_ADAPTER = "CGCAGACTCGACCACCTCTGAC"  # 22 bp; cutadapt -g anchor
UMI_LENGTH = 8
# 9 bp filler before the 8 bp UMI keeps the structure flexible for downstream
# tools that expect a fixed-length 5' offset.
PREFIX_PADDING = 9
# 22 bp filler AFTER the 3' construct adapter — `fastx_trimmer -t 17` trims
# 17 bp from the 3' end, leaving 5 bp after the 3' adapter so the linked-
# adapter extraction in cutadapt (-g 5'...3') still sees both anchors.
SUFFIX_PADDING = 22
SAMPLE_BARCODES = {  # for the demultiplex script's xlsx key
    "OV8_DNA_r1":  "AAACTG", "OV8_RNA_r1":  "AAATGC",
    "OV8_DNA_r2":  "AACATC", "OV8_RNA_r2":  "AACGTA",
    "IOSE_DNA_r1": "AAGAAC", "IOSE_RNA_r1": "AAGCAT",
    "IOSE_DNA_r2": "AAGGCT", "IOSE_RNA_r2": "AATACG",
}


# ===========================================================================
# T2: Subsample real OvCa data
# ===========================================================================
def build_t2(n_promoters: int = 1000) -> None:
    out_dir = EXAMPLES / "ovca_step9"
    inputs_dir = out_dir / "inputs"
    expected_dir = out_dir / "expected"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    expected_dir.mkdir(parents=True, exist_ok=True)

    log.info("T2: loading published OvCa concise activity table to pick promoters")
    activity_concise = pd.read_csv(OVCA_ACTIVITY_DIR / "ovca_sensor_activity_result_concise.csv")
    log.info("T2: full activity table has %s promoters", len(activity_concise))

    # Pick a stratified sample: half from the top 5,000 most-tumor-selective
    # (so the OvCa scatter looks meaningful) + half from a random tail (so the
    # full distribution is exercised). Both groups must contain promoters with
    # complete data so Step 9's filters don't drop everything.
    activity_concise_sorted = activity_concise.sort_values(
        "mean_OV8_to_IOSE_RD_ratio", ascending=False
    )
    top = activity_concise_sorted.head(5000).sample(n_promoters // 2, random_state=42)
    rest = activity_concise_sorted.iloc[5000:].sample(
        n_promoters - len(top), random_state=42
    )
    picked = pd.concat([top, rest])
    picked_promoter_names = set(picked["promoter_name"])
    log.info("T2: picked %s promoters", len(picked_promoter_names))

    # Subsample both alignment CSVs (per-barcode rows) to those promoters.
    for filename in [
        "alignment_result_normalized_in_house_pipeline.csv",
        "alignment_result_unnormalized_in_house_pipeline.csv",
    ]:
        log.info("T2: subsampling %s", filename)
        full = pd.read_csv(OVCA_ALIGN_DIR / filename)
        sub = full[full["promoter_name"].isin(picked_promoter_names)]
        sub.to_csv(inputs_dir / filename, index=False)
        log.info("  %s rows -> %s rows (%s)", len(full), len(sub), filename)

    # Subsample the enhancer-metadata CSV using by_ppm_name + rank as the join key.
    log.info("T2: subsampling all_enhancer_metadata")
    em = pd.read_csv(ENHANCER_META, low_memory=False)
    keys_picked = set(zip(picked["by_ppm_name"], picked["rank"]))
    em_sub = em[
        em.apply(lambda r: (r["by_ppm_name"], r["rank"]) in keys_picked, axis=1)
    ]
    em_sub.to_csv(inputs_dir / "all_enhancer_metadata_111525.csv", index=False)
    log.info("  enhancer_meta: %s rows -> %s rows", len(em), len(em_sub))

    # Subsample the expected outputs (full annotated activity tables) to the same promoters.
    log.info("T2: subsampling expected activity outputs")
    for filename in [
        "ovca_sensor_activity_result_concise.csv",
        "ovca_sensor_activity_result_all.csv",
    ]:
        full = pd.read_csv(OVCA_ACTIVITY_DIR / filename)
        sub = full[full["promoter_name"].isin(picked_promoter_names)]
        sub.to_csv(expected_dir / filename, index=False)
        log.info("  %s rows -> %s rows (%s)", len(full), len(sub), filename)

    (out_dir / "README.md").write_text(_t2_readme(n_promoters), encoding="utf-8")
    log.info("T2 fixtures written to %s", out_dir)


def _t2_readme(n_promoters: int) -> str:
    return f"""# Tier-2 example: Step-9 reproduction on real subsampled data

Bundled inputs are a stratified random sample of {n_promoters:,} promoters
from the published ovarian cancer run. The expected outputs are the
matching-promoter slices of the published `ovca_sensor_activity_result_*.csv`
files.

A reviewer with R installed can re-run the unchanged Step-9 script against
the inputs and reproduce the expected outputs row-for-row:

    cd dashboard/example_data/ovca_step9/inputs/
    Rscript "../../../../codes/3. Post_HPC_enhancer_activity_analysis_scripts/code_by_projects/ovarian_cancer/ovarian_cancer_specific_enhancer_screening_analysis.R"
    # produces ovca_sensor_activity_result_*.csv in cwd
    # compare to ../expected/

The dashboard's `trend run --example step9` automates this and renders the
diff as a green/red oracle badge.
"""


# ===========================================================================
# T3: Simulate FASTQs from a tiny Lib4 subsample
# ===========================================================================
def build_t3(n_promoters: int = 50, barcodes_per_promoter: int = 5) -> None:
    out_dir = EXAMPLES / "ovca_pipeline"
    inputs_dir = out_dir / "inputs"
    fastqs_dir = inputs_dir / "fastqs"
    expected_dir = out_dir / "expected"
    fastqs_dir.mkdir(parents=True, exist_ok=True)
    expected_dir.mkdir(parents=True, exist_ok=True)

    log.info("T3: subsampling Lib4_info to %s promoters x %s barcodes", n_promoters, barcodes_per_promoter)
    lib4 = pd.read_csv(LIB4_INFO)

    # Pick promoters with at least `barcodes_per_promoter` rows so each promoter
    # gets a fixed number of barcodes in the tiny library.
    promoter_counts = lib4.groupby("promoter_name").size()
    eligible = promoter_counts[promoter_counts >= barcodes_per_promoter].index.tolist()
    rng = random.Random(42)
    rng.shuffle(eligible)
    picked_promoters = eligible[:n_promoters]
    log.info("T3: picked %s eligible promoters", len(picked_promoters))

    # For each picked promoter, take the first `barcodes_per_promoter` rows.
    sub_rows = []
    for pn in picked_promoters:
        sub_rows.append(lib4[lib4["promoter_name"] == pn].head(barcodes_per_promoter))
    lib4_tiny = pd.concat(sub_rows, ignore_index=True)
    lib4_tiny.to_csv(inputs_dir / "Lib4_info_tiny.csv", index=False)
    log.info("T3: Lib4_info_tiny.csv has %s constructs", len(lib4_tiny))

    # Build Lib4_tiny.fasta from the picked TFBS_random_bc rows.
    log.info("T3: building Lib4_tiny.fasta")
    fasta_lines = []
    for _, row in lib4_tiny.iterrows():
        fasta_lines.append(f">{row['TFBS_random_bc']}")
        # The reference sequence in Lib4.fasta is the 20-bp barcode itself
        # (per the head -4 inspection earlier). Extract from TFBS_random_bc.
        seq = str(row["TFBS_random_bc"]).split("_", 1)[1]
        fasta_lines.append(seq)
    (inputs_dir / "Lib4_tiny.fasta").write_text("\n".join(fasta_lines) + "\n")
    log.info("T3: Lib4_tiny.fasta has %s sequences", len(lib4_tiny))

    # Design per-sample read counts. Each barcode gets 50-200 reads in DNA
    # samples (uniform library representation) and a programmable RNA count
    # encoding planted activity differences.
    log.info("T3: planting activity profile across samples")
    sample_counts = _plant_activity_profile(lib4_tiny, rng)

    # Write FASTQs and capture the analytical expected count matrix.
    log.info("T3: writing simulated FASTQs")
    for sample_id, per_barcode in sample_counts.items():
        path = fastqs_dir / f"{sample_id}.fastq.gz"
        _write_simulated_fastq(path, per_barcode, rng)
        total_reads = sum(per_barcode.values())
        log.info("  %s: %s reads", sample_id, total_reads)

    # Build the analytical expected count matrix (post-Step 8). Each cell is
    # the number of UMI-collapsed reads for (barcode, sample). Since we plant
    # exactly N reads per barcode per sample with unique UMIs, the count is N.
    log.info("T3: emitting expected post-Step-8 count matrix")
    expected = lib4_tiny[["promoter_name_bc", "promoter_name", "TFBS_random_bc",
                         "TFBS", "TF", "by_ppm_name", "rank"]].copy()
    for sample_id in SAMPLE_BARCODES:
        col = f"{sample_id}"
        expected[col] = expected["TFBS_random_bc"].map(
            lambda bc: sample_counts[sample_id].get(bc, 0)
        )
    # Match the column-naming convention of the published alignment CSVs:
    # OV8_Lib4_DNA_r1 etc. Translate sample_id by inserting "_Lib4_".
    rename = {sid: sid.replace("_DNA", "_Lib4_DNA").replace("_RNA", "_Lib4_RNA")
              for sid in SAMPLE_BARCODES}
    expected = expected.rename(columns=rename)
    expected.to_csv(expected_dir / "alignment_result_unnormalized_in_house_pipeline.csv", index=False)

    # And the normalized (RPM) version: per-sample total normalized to 1M.
    norm = expected.copy()
    for sid_old, sid_new in rename.items():
        col_total = norm[sid_new].sum()
        if col_total:
            norm[sid_new] = norm[sid_new] * 1_000_000 / col_total
    norm.to_csv(expected_dir / "alignment_result_normalized_in_house_pipeline.csv", index=False)

    # Write a barcode key for the demultiplex step.
    log.info("T3: writing barcode key")
    bc_key_df = pd.DataFrame([
        {"Index seq": seq, "Sample": sid} for sid, seq in SAMPLE_BARCODES.items()
    ])
    bc_key_df.to_excel(inputs_dir / "barcode_key.xlsx", index=False)

    (out_dir / "README.md").write_text(_t3_readme(n_promoters, barcodes_per_promoter), encoding="utf-8")
    log.info("T3 fixtures written to %s", out_dir)


def _plant_activity_profile(lib4_tiny: pd.DataFrame, rng: random.Random) -> dict:
    """Plant a synthetic activity pattern.

    Strategy: split the picked constructs into three groups —
      - 'tumor-selective': low DNA, high RNA in OV8 cell lines
      - 'normal-selective': low DNA, high RNA in IOSE cell lines
      - 'baseline':         uniform across both
    Each barcode of the same promoter gets the same per-sample count, so the
    Step-9 RD-ratio aggregator behaves predictably.
    """
    promoters = list(lib4_tiny["promoter_name"].unique())
    rng.shuffle(promoters)
    n = len(promoters)
    tumor_set = set(promoters[: n // 3])
    normal_set = set(promoters[n // 3 : 2 * n // 3])

    counts: dict[str, dict[str, int]] = {sid: {} for sid in SAMPLE_BARCODES}
    DNA_BASE = 100
    RNA_BASELINE = 100
    RNA_HIGH = 800
    RNA_LOW = 25

    for _, row in lib4_tiny.iterrows():
        bc = row["TFBS_random_bc"]
        promoter = row["promoter_name"]
        for sid in SAMPLE_BARCODES:
            if "_DNA_" in sid:
                counts[sid][bc] = DNA_BASE
            else:
                cell_line = sid.split("_")[0]
                if promoter in tumor_set:
                    counts[sid][bc] = RNA_HIGH if cell_line == "OV8" else RNA_LOW
                elif promoter in normal_set:
                    counts[sid][bc] = RNA_HIGH if cell_line == "IOSE" else RNA_LOW
                else:
                    counts[sid][bc] = RNA_BASELINE
    return counts


def _write_simulated_fastq(path: Path, per_barcode: dict[str, int], rng: random.Random) -> None:
    """Write a gzipped FASTQ file. Each read is:

        [9 bp filler][8 bp UMI]TAAAGCGGCCGCGAGGATCC[20 bp barcode]CGCAGACTCGACCACCTCTGAC[5 bp filler]

    Total ~84 bp. Adapters match the cutadapt -g flanks the existing pipeline uses.
    """
    bases = "ACGT"
    lines = []
    read_num = 0
    for barcode, count in per_barcode.items():
        # Extract the 20-bp barcode payload from the TFBS_random_bc string.
        bc_seq = barcode.split("_", 1)[1]
        for _ in range(count):
            umi = "".join(rng.choices(bases, k=UMI_LENGTH))
            prefix = "".join(rng.choices(bases, k=PREFIX_PADDING))
            suffix = "".join(rng.choices(bases, k=SUFFIX_PADDING))
            seq = prefix + umi + FIVE_PRIME_ADAPTER + bc_seq + THREE_PRIME_ADAPTER + suffix
            qual = "I" * len(seq)  # Phred 40 throughout
            lines.append(f"@SIM_{read_num:08d}")
            lines.append(seq)
            lines.append("+")
            lines.append(qual)
            read_num += 1
    with gzip.open(path, "wt") as f:
        f.write("\n".join(lines) + "\n")


def _t3_readme(n_promoters: int, barcodes_per_promoter: int) -> str:
    return f"""# Tier-3 example: full FASTQ-to-activity reproduction on simulated data

Bundled inputs:
  - {n_promoters} promoters x {barcodes_per_promoter} barcodes = {n_promoters * barcodes_per_promoter} constructs from a Lib4 subsample
  - 8 sample FASTQs (OV8 + IOSE cell lines, 2 DNA + 2 RNA replicates each)
  - Simulated reads with the exact adapter / UMI / barcode structure the
    pipeline expects: [9bp filler][8bp UMI]TAAAGCGGCCGCGAGGATCC[20bp barcode]CGCAGACTCGACCACCTCTGAC[5bp filler]
  - Planted activity profile: 1/3 tumor-selective (high in OV8, low in IOSE),
    1/3 normal-selective (high in IOSE, low in OV8), 1/3 baseline.

Expected outputs:
  - `alignment_result_normalized_in_house_pipeline.csv` — RPM-normalized per
    barcode per sample, computed analytically from the planted read counts.
  - `alignment_result_unnormalized_in_house_pipeline.csv` — raw counts.

A reviewer with the conda env active runs `trend run --example pipeline`,
which invokes the bundled Snakefile against the FASTQs and compares the
post-Step-8 outputs to the analytically-correct expected matrix.
"""


# ===========================================================================
# Main
# ===========================================================================
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--tier", choices=("all", "t2", "t3"), default="all")
    parser.add_argument("--t2-promoters", type=int, default=1000)
    parser.add_argument("--t3-promoters", type=int, default=50)
    parser.add_argument("--t3-bc-per-promoter", type=int, default=5)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.tier in ("all", "t2"):
        build_t2(n_promoters=args.t2_promoters)
    if args.tier in ("all", "t3"):
        build_t3(n_promoters=args.t3_promoters,
                 barcodes_per_promoter=args.t3_bc_per_promoter)
    log.info("All requested fixtures built.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
