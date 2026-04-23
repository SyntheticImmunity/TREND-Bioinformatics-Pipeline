# trend-pipeline

Standalone, installable end-to-end pipeline for the TREND (Transcription-Factor-Responsive Enhancer Discovery) library.

```bash
# install (Linux or HPC cluster)
conda install -c bioconda trend-pipeline

# reproduce a published figure on the bundled example
trend run --example ovarian_cancer

# run on your own data
trend init my-experiment --template T_cell_activation
$EDITOR my-experiment/samplesheet.yaml
trend run --inputs ./fastqs/ --output ./runs/2026-04/

# launch the dashboard pointed at any runs directory
trend dashboard --runs ./runs/
```

See the top-level `README.md` of this repository for the full documentation.
