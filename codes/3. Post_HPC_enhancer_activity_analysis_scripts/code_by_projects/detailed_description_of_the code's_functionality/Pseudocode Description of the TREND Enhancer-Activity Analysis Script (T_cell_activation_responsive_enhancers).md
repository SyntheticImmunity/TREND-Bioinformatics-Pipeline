## Pseudocode: T-cell Activation–Responsive Enhancer Screen (Two Donors)

### **Overall purpose**

This script processes TREND library MPRA data from a T-cell activation–responsive enhancer screen, performed in **two biological donors** with **resting vs stimulated** conditions.

It:

1. Loads unnormalized and normalized barcode count tables.
2. Computes barcode-level RNA/DNA (RD) ratios per sample.
3. Infers and applies **per-sample DNA abundance thresholds** based on the fraction of transcriptionally active barcodes.
4. Collapses barcodes to enhancer (promoter_name)–level activity metrics, enforcing minimum barcode support.
5. Merges activity summaries with enhancer design metadata.
6. For each donor, computes **stim/rest RD ratios** and outputs donor-specific enhancer activity tables.

------

### **Inputs**

- `alignment_result_unnormalized_in_house_pipeline.csv`
- `alignment_result_normalized_in_house_pipeline.csv`
- `all_enhancer_metadata_111525.csv`

### **Outputs**

- `DNA_threshold_rest_stim_50_percent_reporting.pdf`
- `activation_responsive_enhancer_screening_result_donor1.csv`
- `activation_responsive_enhancer_screening_result_donor2.csv`

------

### **Step-by-step pseudocode**

------

### **B1. Load preprocessed count matrices**

1. **Load libraries:**
   - `tidyverse` for data manipulation
   - `gridExtra` for multi-panel plots
   - `data.table` for efficient data handling
2. **Set working directory** to the folder that contains the count matrices and metadata.
3. **Read unnormalized counts**:
   - Read `alignment_result_unnormalized_in_house_pipeline.csv` into `un_normalized_result_RS`.
   - Convert to tibble `sensor_info_unnormalized_RS`.
4. **Create a copy with zero counts set to NA**:
   - Duplicate `sensor_info_unnormalized_RS` into `sensor_info_unnormalized_RS_remove_zero`.
   - Replace all zeros with `NA`.
   - This version is used for summary statistics where medians and quantiles should reflect *detected* barcodes only.
5. **Read normalized counts**:
   - Read `alignment_result_normalized_in_house_pipeline.csv` into `result_RS`.
   - Convert to tibble `sensor_info`.
   - This normalized table (RNA & DNA) is used for all downstream analyses (thresholding, RD ratios, activity calculations).

------

### **B2. Per-sample normalization and RD ratio calculation**

**Goal:** For each sample (e.g., `rest_r1`, `stim_r1`), compute per-barcode RNA/DNA ratios, optionally after median normalization.

**Function:** `create_sensor_info_for_sample(sample_name, median_normalization = TRUE)`

**Inputs:**

- `sample_name` (string), e.g. `"rest_r1"` or `"stim_r2"`
- `median_normalization` (logical), whether to median-normalize RNA and DNA counts

**Algorithm:**

1. **Parse the sample name**:
   - `cell_name` = part before underscore (e.g., `"rest"`, `"stim"`)
   - `replicate_num` = part after underscore (e.g., `"r1"`, `"r2"`)
2. **Define column names** for this sample:
   - `sample_DNA` = `<cell_name>_Lib4_DNA_<replicate_num>`
   - `sample_RNA` = `<cell_name>_Lib4_RNA_<replicate_num>`
3. **Extract barcode-level data** from `sensor_info`:
   - Keep columns: `promoter_name_bc`, `promoter_name`, `sample_RNA`, `sample_DNA`.
4. **Exclude barcodes with zero DNA counts**:
   - Remove rows where `sample_DNA == 0` (no library representation).
5. **Optional median normalization** (if `median_normalization = TRUE`):
   - For RNA:
     - Divide each RNA count by the median RNA count among barcodes with RNA ≠ 0.
   - For DNA:
     - Divide each DNA count by the median DNA count across all barcodes.
   - Replace original RNA/DNA columns with these normalized values.
   - This corrects for sample-specific sequencing depth and compositional biases.
6. **Compute RD ratio**:
   - For each remaining barcode:
     - `RD_ratio = sample_RNA / sample_DNA`
   - Store in a new column named `<cell_name>_Lib4_RD_ratio_<replicate_num>`.
7. **Return** the per-sample data frame containing:
   - `promoter_name_bc`, `promoter_name`, normalized (or raw) `sample_RNA`, `sample_DNA`, and per-barcode `RD_ratio`.

------

### **B3. Determine DNA abundance thresholds per sample**

**Goal:** For each sample, identify a **DNA abundance threshold** that excludes barcodes with extremely low DNA coverage, based on the fraction of “active” barcodes (non-zero RNA).

1. **Define sample labels**:

   - `sample_name_vector_RS = c("rest_r1", "rest_r2", "stim_r1", "stim_r2")`.

2. **Optionally precompute per-sample data (without median normalization)**:

   - For each `sample_name` in `sample_name_vector_RS`, call:
     - `create_sensor_info_for_sample(sample_name, median_normalization = FALSE)`
   - Store in `sensor_info_list_RS`, with names equal to sample names.

3. **Function:** `plot_and_set_DNA_threshold(sample_name)`

   **Algorithm:**

   1. Call `create_sensor_info_for_sample(sample_name)` (with default median normalization = TRUE).
   2. Parse `sample_name` to get:
      - `cell_name` (e.g., `"rest"` or `"stim"`)
      - `replicate_num` (`"r1"` or `"r2"`)
   3. Set:
      - `sample_DNA` = DNA column name for this sample.
      - `sample_RNA` = RNA column name for this sample.
   4. Compute `base_unit` = minimum DNA count in this sample (smallest non-zero DNA count).
   5. Initialize:
      - Empty numeric vector `percent_active_vector`
      - Logical flag `record_theshold = TRUE`
      - `cut_off_threshold = NA`
   6. For `i` from 1 to 100 (representing DNA copy-number bins):
      - Define a narrow DNA bin around `i × base_unit`:
        - `subset_idx = (DNA >= 0.99 * i * base_unit) & (DNA <= 1.01 * i * base_unit)`
      - `num_all` = number of barcodes in the bin.
      - `num_active` = number of barcodes with RNA ≠ 0 in the same bin.
      - If `num_all > 0`:
        - `percent_active = num_active / num_all`
      - Else:
        - `percent_active = NA`
      - Append `percent_active` to `percent_active_vector`.
      - If `percent_active` is not NA, `percent_active ≥ 0.5`, and `record_theshold` is TRUE:
        - Set `cut_off_threshold = i`
        - Set `record_theshold = FALSE` (store the *first* such bin).
   7. Build a data frame:
      - `DNA_abundance = 1..100`
      - `percent_active = percent_active_vector`
   8. Create a scatter plot:
      - x-axis: `DNA_abundance` (bin index 1–100, shown every 10)
      - y-axis: `percent_active` (0–1)
      - Title: `<cell_name>_<replicate_num>_threshold_<cut_off_threshold>`
   9. Return the ggplot object.

4. **Generate threshold plots for all samples:**

   - For each `sample_name` in `sample_name_vector_RS`, call `plot_and_set_DNA_threshold(sample_name)`.
   - Store all plots in `sensor_DNA_threshold_plot_list_RS`.
   - Save all panels into a PDF:
     - `DNA_threshold_rest_stim_50_percent_reporting.pdf`
        using `grid.arrange` for multi-panel layout.

------

### **B4. Apply DNA & barcode-count thresholds, and collapse barcodes**

**Goal:** For each sample:

- Filter out low-DNA and (optionally) RNA-zero barcodes.
- Collapse barcode-level measures to **enhancer-level** summaries.
- Enforce a minimum number of barcodes per enhancer.

**Function:** `filter_sensor_info_list_with_DNA_and_bc_threshold(sample_name, DNA_threshold, bc_threshold, remove_RNA_zero = TRUE)`

**Inputs:**

- `sample_name` (e.g. `"rest_r1"`, `"stim_r2"`)
- `DNA_threshold` (bin index determined externally; multiplies `base_unit`)
- `bc_threshold` (minimum number of barcodes; here set to 8)
- `remove_RNA_zero` (whether to exclude barcodes with zero RNA)

**Algorithm:**

1. Call `create_sensor_info_for_sample(sample_name)` to obtain RD ratios and remove DNA=0 barcodes.
2. Parse `sample_name` into `cell_name` and `replicate_num`.
3. Define column names:
   - `sample_DNA`, `sample_RNA`, and `sample_RD_ratio` for this sample.
4. Compute `base_unit` = minimum DNA count for this sample (same definition as in thresholding).
5. **DNA abundance filter**:
   - Keep only barcodes where `DNA > DNA_threshold × base_unit`.
6. **Optional RNA filter**:
   - If `remove_RNA_zero = TRUE`, drop barcodes with `RNA = 0`.
7. **Collapse to enhancer (promoter_name) level**:
   - Group by `promoter_name`.
   - For each enhancer:
     - `RNA_sum` = sum of RNA counts across barcodes.
     - `DNA_sum` = sum of DNA counts across barcodes.
     - `median_value` = median RD_ratio across barcodes.
     - `n_bc` = number of barcodes (supporting barcodes).
     - `pseudo_Lib2_RD` = RNA_sum / DNA_sum (promoter-level RD ratio).
8. **Enforce barcode-count threshold**:
   - Filter to enhancers with `n_bc ≥ bc_threshold`.
9. **Rank enhancers**:
   - Sort descending by:
     1. `median_value`
     2. `pseudo_Lib2_RD`
     3. `n_bc`
10. **Rename columns** to encode sample/condition information:
    - `promoter_name`
    - `<sample_RNA>_sum`, `<sample_DNA>_sum`
    - `median_<cell_name>_Lib4_RD_ratio_<replicate_num>`
    - `<cell_name>_<replicate_num>_n_bc`
    - `<cell_name>_pseudo_Lib2_RD_ratio_<replicate_num>`
11. Return the collapsed enhancer-level table.

**Apply thresholds for all samples:**

1. Define:
   - `DNA_threshold_vector_RS = c(2, 2, 3, 2)`, one entry per sample (`rest_r1`, `rest_r2`, `stim_r1`, `stim_r2`).
   - `bc_threshold_vector_RS = rep(8, length(sample_name_vector_RS))`.
2. Initialize `sensor_info_list_filtered_RS` as an empty list.
3. For each index `i` in `sample_name_vector_RS`:
   - Call `filter_sensor_info_list_with_DNA_and_bc_threshold` with:
     - `sample_name = sample_name_vector_RS[i]`
     - `DNA_threshold = DNA_threshold_vector_RS[i]`
     - `bc_threshold = bc_threshold_vector_RS[i]`
   - Store the resulting enhancer-level table in `sensor_info_list_filtered_RS[[i]]`.
4. Name elements of `sensor_info_list_filtered_RS` with the sample names.

------

### **B5. Merge with enhancer metadata and compute donor-level activities**

**Goal:** For each **biological donor** (replicate label `r1` and `r2`), merge enhancer activity from rest and stim conditions, attach design metadata, and compute a stim/rest activity ratio.

1. **Read enhancer metadata**:

   - Read `all_enhancer_metadata_111525.csv` into `all_sensors`.
   - Select columns:
     - `TFBS_sequence`, `TF_name_by_PPM`, `TF_name_human_curated`, `variable_region`, `by_ppm_name`, `rank`.
   - Create `promoter_name = TFBS_sequence + "_" + TF_name_by_PPM`.
   - Sort rows by `TF_name_by_PPM` and `rank`.
   - Keep ordered columns:
     - `promoter_name`, and `TFBS_sequence` through `rank`.

2. **Function:** `create_final_sensor_activity_result_dataframe_RS(sensor_info_list, output_basename = "output")`

   This function generates **one CSV per donor**, combining rest and stim.

   **Internal helper:** `build_for_rep(rep_label, donor_label)`

   **Inputs:**

   - `rep_label` = `"r1"` (donor 1) or `"r2"` (donor 2)
   - `donor_label` = `"donor1"` or `"donor2"`
   - `sensor_info_list` = list of enhancer-level tables for `rest_r1`, `rest_r2`, `stim_r1`, `stim_r2`.

   **Algorithm:**

   1. Select the **two samples** corresponding to this donor / replicate label:
      - For `rep_label = "r1"`: select `rest_r1` and `stim_r1`.
      - For `rep_label = "r2"`: select `rest_r2` and `stim_r2`.
      - Use `grepl("_r1$")` or `grepl("_r2$")` on the names of `sensor_info_list` to filter.
   2. Merge the rest and stim enhancer tables by `promoter_name`:
      - Apply `purrr::reduce(..., full_join, by = "promoter_name")`.
   3. Attach enhancer design metadata:
      - Left join `all_sensors` to the merged activity table by `promoter_name`.
   4. Compute donor-specific stim/rest RD ratios:
      - If `rep_label == "r1"`:
        - Add column:
          - `stim_to_rest_RD_ratio_r1 = median_stim_Lib4_RD_ratio_r1 / median_rest_Lib4_RD_ratio_r1`.
        - Build a concise output table:
          - Select:
            - Metadata columns `promoter_name:rank`
            - All `median_...` columns (rest and stim medians)
            - All `*_n_bc` columns (barcode counts)
            - `stim_to_rest_RD_ratio_r1`.
      - If `rep_label == "r2"`:
        - Add:
          - `stim_to_rest_RD_ratio_r2 = median_stim_Lib4_RD_ratio_r2 / median_rest_Lib4_RD_ratio_r2`.
        - Build concise table with:
          - `promoter_name:rank`
          - `median_...` columns
          - `*_n_bc` columns
          - `stim_to_rest_RD_ratio_r2`.
   5. Write donor-specific CSV:
      - File name = `paste0(output_basename, "_", donor_label, ".csv")`.
      - e.g. `activation_responsive_enhancer_screening_result_donor1.csv`.

   **Outer function call:**

   - Call `build_for_rep("r1", "donor1")`.
   - Call `build_for_rep("r2", "donor2")`.

3. **Generate final outputs:**

   - Call:

     ```
     create_final_sensor_activity_result_dataframe_RS(
       sensor_info_list_filtered_RS,
       output_basename = "activation_responsive_enhancer_screening_result"
     )
     ```

   - This writes out **two donor-specific enhancer activity tables**, each summarizing rest and stim conditions and reporting a stim/rest RD ratio for each enhancer.