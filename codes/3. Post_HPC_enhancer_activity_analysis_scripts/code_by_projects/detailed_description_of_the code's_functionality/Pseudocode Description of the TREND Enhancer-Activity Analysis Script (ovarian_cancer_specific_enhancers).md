## Pseudocode Description of the TREND Enhancer-Activity Analysis Script

### **Overall purpose**

This R script takes normalized barcode count tables from the TREND library screen and:

1. Computes barcode-level RNA/DNA (RD) ratios per sample.
2. Applies per-sample DNA-abundance and barcode-support filters.
3. Collapses barcode-level data to promoter-level activity metrics.
4. Integrates library design metadata.
5. Computes mean enhancer activity and tumor-vs-control selectivity across replicates.
6. Outputs full and concise activity tables for downstream analysis.

------

### **Inputs**

- `alignment_result_unnormalized_in_house_pipeline.csv`
- `alignment_result_normalized_in_house_pipeline.csv`
- `all_enhancer_metadata_111525.csv`

------

### **Outputs**

- `DNA_threshold_for_samples.pdf`
- `ovca_sensor_activity_result_all.csv`
- `ovca_sensor_activity_result_concise.csv`

------

### **Step-by-step pseudocode**

#### 1. Load libraries and input data

1. Load required R packages:
   - `tidyverse` for data manipulation
   - `gridExtra` for plotting multiple panels into a PDF
2. Set working directory to the folder containing all input files.
3. Read the **unnormalized** alignment result table into `un_normalized_result`.
4. Read the **normalized** alignment result table into `result`.

------

#### 2. Build the core data table (`sensor_info`)

1. Starting from `result` (normalized counts), convert to a tibble.
2. Select:
   - Metadata columns from `promoter_name_bc` through `rank`.
   - Sample-specific count columns using the column structure from `un_normalized_result` (columns 8–23).
3. Reorder columns into a fixed structure:
   - Metadata: `promoter_name_bc:rank`
   - OV8 RNA replicates (r1–r3), OV8 DNA replicates (r1–r3)
   - IOSE RNA replicates (r1–r3), IOSE DNA replicates (r1–r3)
   - ID8 RNA replicates (r1–r2), ID8 DNA replicates (r1–r2)
4. Store the resulting table as `sensor_info`.
    Each row corresponds to a barcode; columns contain counts for each cell line / replicate.

------

#### 3. Quality control: count non-zero entries per sample

1. Identify all sample count columns in `sensor_info` (from column 8 to the last column).
2. For each sample column:
   - Count the number of rows where the count is non-zero.
   - Compute the fraction of non-zero entries relative to the total number of barcodes.
   - Print the sample name, the non-zero count, and the non-zero fraction to the console.
3. This step provides a quick QC summary of coverage per sample.

------

#### 4. Define sample names and DNA thresholds

1. Define an ordered vector of sample names:
   - `OV8_r1`, `OV8_r2`, `OV8_r3`
   - `IOSE_r1`, `IOSE_r2`, `IOSE_r3`
   - `ID8_r1`, `ID8_r2`
2. Define a numeric vector of DNA thresholds (one per sample) based on prior DNA-abundance plot inspection:
   - e.g. `c(2, 3, 5, 6, 3, 2, 30, 35)`
3. Name the threshold vector entries using the sample names so they can be accessed by sample.

------

#### 5. Helper function: create per-sample barcode-level RD ratios

**Function:** `create_sensor_info_for_sample(sample_name)`

**Inputs:**

- `sample_name` (string), e.g. `"OV8_r1"`

**Algorithm:**

1. Split `sample_name` into:
   - `cell_name` (e.g. `"OV8"`)
   - `replicate_num` (e.g. `"r1"`)
2. Construct the column names for this sample:
   - `sample_DNA` = `<cell_name>_Lib4_DNA_<replicate_num>`
   - `sample_RNA` = `<cell_name>_Lib4_RNA_<replicate_num>`
   - `rd_ratio_col` = `<cell_name>_Lib4_RD_ratio_<replicate_num>`
3. Extract from `sensor_info` the columns:
   - `promoter_name_bc`, `promoter_name`, `sample_RNA`, `sample_DNA`
4. Remove barcodes with **DNA = 0** for this sample.
5. Compute the RNA/DNA ratio for each remaining barcode:
   - `RD_ratio = sample_RNA / sample_DNA`
   - Store in a new column named `rd_ratio_col`.
6. Return the filtered per-sample data frame with barcode-level RD ratios.

------

#### 6. DNA-threshold plots per sample

**Function:** `plot_and_set_DNA_threshold(sample_name)`

**Algorithm:**

1. Parse `sample_name` into `cell_name` and `replicate_num`.
2. Identify the DNA and RNA column names for the sample.
3. Call `create_sensor_info_for_sample(sample_name)` to get barcode-level data with RD ratios.
4. Determine the minimal non-zero DNA count (`base_unit`) for that sample.
5. For a series of DNA-abundance bins indexed by `i = 1..50`:
   - Define the DNA range:
     - `dna_low`  = 0.99 × i × base_unit
     - `dna_high` = 1.01 × i × base_unit
   - Identify barcodes with DNA counts within this bin.
   - If bin is empty: set percent active to `NA`.
   - Otherwise:
     - Calculate the fraction of barcodes in this bin with **RNA ≠ 0** (i.e., transcriptionally active).
     - Store this fraction in `percent_active_vector[i]`.
6. Construct a data frame with:
   - `DNA_abundance` = 1..50
   - `percent_active` = fraction of active barcodes in each bin
7. Generate a scatter plot of `percent_active` vs. `DNA_abundance`:
   - x-axis: bin index (1–50)
   - y-axis: fraction active (0–1)
   - plot title = `<cell_name>_<replicate_num>`
8. Return the ggplot object.

**Batch plotting:**

1. For each `sample_name` in `sample_name_vector`:
   - Call `plot_and_set_DNA_threshold(sample_name)`.
   - Collect all plots in a list.
2. Save all plots into a single PDF file:
   - `DNA_threshold_for_samples.pdf`
      using `grid.arrange` to arrange multiple panels.

------

#### 7. Filtering by DNA threshold and barcode support

**Function:** `filter_sensor_info_list_with_DNA_and_bc_threshold(sample_name, DNA_threshold, bc_threshold = 3, remove_RNA_zero = TRUE)`

**Inputs:**

- `sample_name` (e.g. `"OV8_r1"`)
- `DNA_threshold` (sample-specific scaling factor)
- `bc_threshold` (minimum number of barcodes per promoter; default 3)
- `remove_RNA_zero` (logical; whether to exclude barcodes with RNA = 0)

**Algorithm:**

1. Parse `sample_name` into `cell_name` and `replicate_num`.
2. Build column names:
   - `sample_DNA`, `sample_RNA`, `sample_RD_ratio`.
3. Call `create_sensor_info_for_sample(sample_name)` to:
   - Remove DNA=0 barcodes.
   - Compute RD_ratio per barcode.
4. Compute `base_unit` = minimal DNA count for that sample.
5. Apply DNA-abundance filtering:
   - Keep only barcodes where `DNA > DNA_threshold × base_unit`.
6. If `remove_RNA_zero = TRUE`:
   - Further remove barcodes with `RNA = 0`.
7. Collapse barcode-level data to promoter-level:
   - Group by `promoter_name`.
   - For each promoter:
     - `RNA_sum` = sum of RNA counts across barcodes.
     - `DNA_sum` = sum of DNA counts across barcodes.
     - `median_value` = median RD_ratio across barcodes.
     - `n_bc` = number of barcodes supporting this promoter.
     - `pseudo_Lib2_RD` = RNA_sum / DNA_sum (promoter-level RD ratio).
8. Apply barcode-support filter:
   - Keep only promoters with `n_bc ≥ bc_threshold`.
9. Sort promoters in descending order of:
   - `median_value` (primary)
   - `pseudo_Lib2_RD` (secondary)
   - `n_bc` (tertiary)
10. Rename columns to reflect:
    - RNA_sum and DNA_sum for that sample
    - `median_<cell_name>_Lib4_RD_ratio_<replicate_num>`
    - `<cell_name>_<replicate_num>_n_bc`
    - `<cell_name>_pseudo_Lib2_RD_ratio_<replicate_num>`
11. Return the promoter-level table for that sample.

**Create a list of filtered tables across samples:**

**Function:** `make_filtered_list(bc_threshold = 3, remove_RNA_zero = TRUE)`

1. For each `sample_name` in `sample_name_vector`:
   - Retrieve `DNA_threshold` from `DNA_threshold_vector`.
   - Call `filter_sensor_info_list_with_DNA_and_bc_threshold(...)` with the chosen DNA threshold and `bc_threshold`.
2. Collect all per-sample promoter-level tables in a named list.
3. This list (`sensor_info_list_filtered`) contains one filtered table per sample and is used for downstream merging.

------

#### 8. Load and prepare library design metadata (`all_sensors`)

1. Read the `all_enhancer_metadata_111525.csv` file into `all_sensors`.
2. Convert to tibble and select:
   - `TFBS_sequence`
   - `TF_name_by_PPM`
   - `variable_region`
   - `by_ppm_name`
   - `rank`
   - `TF_name_human_curated`
3. Construct a `promoter_name` column:
   - `promoter_name = TFBS_sequence + "_" + TF_name_by_PPM`
4. Arrange rows by `TF_name_human_curated` and `rank`.
5. Select and order columns as:
   - `promoter_name`, `TFBS_sequence`, `TF_name_by_PPM`, `TF_name_human_curated`, `variable_region`, `by_ppm_name`, `rank`.
6. This table provides the design metadata to be joined with activity results.

------

#### 9. Merge activity results across samples and compute summary metrics

**Function:** `create_final_sensor_activity_result_dataframe(sensor_info_list)`

**Algorithm:**

1. Merge per-sample promoter-level tables:
   - Use a reduction with `left_join` on `promoter_name`.
   - Start from the first sample table and iteratively join the rest.
   - Result: a wide table with one row per promoter and activity metrics for all samples.
2. Add library design metadata:
   - Left-join `all_sensors` to the merged activity table by `promoter_name`.
3. Quantify missingness:
   - For each row, compute `NA_count` as the (scaled) number of NA values across selected columns (as in original code).
4. Compute mean RD ratios across replicates:
   - `mean_OV8_RD_ratio` = row-wise mean of `median_OV8_Lib4_RD_ratio_r1`, `r2`, `r3`.
   - `mean_IOSE_RD_ratio` = row-wise mean of `median_IOSE_Lib4_RD_ratio_r1`, `r2`, `r3`.
   - `mean_ID8_RD_ratio` = row-wise mean of `median_ID8_Lib4_RD_ratio_r1`, `r2`.
   - All means are computed with `na.rm = TRUE`.
5. Compute tumor-vs-control selectivity:
   - `mean_OV8_to_IOSE_RD_ratio` = `mean_OV8_RD_ratio / mean_IOSE_RD_ratio`.
   - `mean_ID8_to_IOSE_RD_ratio` = `mean_ID8_RD_ratio / mean_IOSE_RD_ratio`.
6. Sort promoters in descending order of `mean_OV8_to_IOSE_RD_ratio`.
7. Create a **full** result table (`sensor_activity_result_filtered`):
   - Contains all metadata and intermediate columns.
8. Create a **concise** result table (`sensor_activity_result_concise`):
   - Includes:
     - Design metadata (`promoter_name` through `rank`)
     - `NA_count`
     - Mean activity metrics
     - Tumor/control fold ratios
   - Sorted again by `mean_OV8_to_IOSE_RD_ratio`.
9. Write both tables to disk:
   - `ovca_sensor_activity_result_all.csv`
   - `ovca_sensor_activity_result_concise.csv`
10. Call `create_final_sensor_activity_result_dataframe(sensor_info_list_filtered)` to execute the full workflow.