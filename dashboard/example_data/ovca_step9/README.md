# Tier-2 example: Step-9 reproduction on real subsampled data

Bundled inputs are a stratified random sample of 1,000 promoters
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
