# T-cell activation TREND project (template)

This directory was scaffolded by `trend init <name> --template T_cell_activation`. Edit `samplesheet.yaml` to match your own donor data.

## What you need to edit

Only `samplesheet.yaml`. The defaults below mirror the manuscript's 2-donor rest/stim run; replace with your own donor IDs and FASTQ paths.

## Run

```bash
trend run --project T_cell_activation --inputs ./fastqs/ --output ./runs/$(date +%F)/
# or on SLURM:
trend run --project T_cell_activation --inputs ./fastqs/ --output ./runs/$(date +%F)/ --profile slurm
```

## What you get

`./runs/<run_id>/outputs/` will contain one CSV per donor with rest/stim/fold-change activity per promoter, plus the run manifest.

Open the dashboard:

```bash
trend dashboard --runs ./runs/
```

## Adapting from the published parameters

The defaults match the manuscript:
- 4 samples (rest_r1, stim_r1, rest_r2, stim_r2)
- DNA threshold vector `[2, 3, 2, 2]`
- Barcode threshold = 8 per promoter (higher than OvCa due to donor variability)
