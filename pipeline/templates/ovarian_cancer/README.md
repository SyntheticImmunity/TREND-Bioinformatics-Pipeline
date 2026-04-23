# Ovarian cancer TREND project (template)

This directory was scaffolded by `trend init <name> --template ovarian_cancer`. Edit `samplesheet.yaml` to match your own data, then run the pipeline.

## What you need to edit

Only `samplesheet.yaml`. Replace the example sample IDs, FASTQ paths, and per-sample DNA thresholds with values matching your sequencing run. Everything else (the analysis logic, the metadata files, the column algebra) is handled by the pipeline.

## Run

```bash
# On a workstation
trend run --project ovarian_cancer --inputs ./fastqs/ --output ./runs/$(date +%F)/

# On a SLURM cluster (one extra flag — Snakemake handles scheduling)
trend run --project ovarian_cancer --inputs ./fastqs/ --output ./runs/$(date +%F)/ --profile slurm
```

## What you get

After a successful run, `./runs/<run_id>/outputs/` will contain:

- `ovca_sensor_activity_result_concise.csv` — promoter-level activity sorted by tumor selectivity
- `ovca_sensor_activity_result_all.csv` — full annotated table
- `manifest.json` — provenance: code commit, software versions, input/output SHA-256s, parameters

Open the dashboard to explore them interactively:

```bash
trend dashboard --runs ./runs/
```

## Adapting from the published parameters

The defaults in `samplesheet.yaml` mirror the manuscript's published OvCa run exactly:
- 8 samples (3× OV8 + 3× IOSE + 2× ID8)
- DNA threshold vector `[2, 3, 5, 6, 3, 2, 30, 35]`
- Barcode threshold = 3 per promoter

If your library coverage differs, regenerate the diagnostic threshold plots first (`DNA_threshold_for_samples.pdf` lands in your run directory after a complete run) and pick per-sample cutoffs at the ~75% activity-retention point.
