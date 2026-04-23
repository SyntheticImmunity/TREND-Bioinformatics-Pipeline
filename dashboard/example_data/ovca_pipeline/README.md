# Tier-3 example: full FASTQ-to-activity reproduction on simulated data

Bundled inputs:
  - 50 promoters x 5 barcodes = 250 constructs from a Lib4 subsample
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
