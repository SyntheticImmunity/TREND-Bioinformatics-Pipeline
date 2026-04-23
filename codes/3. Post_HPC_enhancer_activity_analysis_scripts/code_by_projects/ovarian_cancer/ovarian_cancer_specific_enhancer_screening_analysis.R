library(tidyverse)
library(gridExtra)

## ------------------------------------------------------------------
## Paths & input
## ------------------------------------------------------------------

setwd("E:/TREND_test_run_final_codes/ovca_NCNM_final")  # adjust as needed

# Unnormalized result (used only for column structure)
un_normalized_result <- read.csv(
  "alignment_result_unnormalized_in_house_pipeline.csv",
  header = TRUE,
  stringsAsFactors = FALSE
)

# Normalized result
result <- read.csv(
  "alignment_result_normalized_in_house_pipeline.csv",
  header = TRUE,
  stringsAsFactors = FALSE
)

## ------------------------------------------------------------------
## Construct sensor_info (normalized counts, selected columns)
## ------------------------------------------------------------------

sensor_info <- result %>%
  as_tibble() %>%
  select(
    promoter_name_bc:rank,
    colnames(un_normalized_result)[8:23]
  ) %>%
  select(
    promoter_name_bc:rank,
    OV8_Lib4_RNA_r1:OV8_Lib4_RNA_r3, OV8_Lib4_DNA_r1:OV8_Lib4_DNA_r3,
    IOSE_Lib4_RNA_r1:IOSE_Lib4_RNA_r3, IOSE_Lib4_DNA_r1:IOSE_Lib4_DNA_r3,
    ID8_Lib4_RNA_r1:ID8_Lib4_RNA_r2, ID8_Lib4_DNA_r1:ID8_Lib4_DNA_r2
  )

## ------------------------------------------------------------------
## QC: non-zero entry counts per sample
## ------------------------------------------------------------------

cat("Number of non-zero entries for each sample:\n")
sample_cols <- colnames(sensor_info)[8:ncol(sensor_info)]

for (col in sample_cols) {
  non_zero <- sum(sensor_info[[col]] != 0)
  non_zero_ratio <- non_zero / nrow(sensor_info)
  cat(col, ":", non_zero, "; non-zero-ratio:", non_zero_ratio, "\n")
}

## ------------------------------------------------------------------
## Helpers: sample naming & per-sample data extraction
## ------------------------------------------------------------------

# Sample names (order matters)
sample_name_vector <- c(
  "OV8_r1", "OV8_r2", "OV8_r3",
  "IOSE_r1", "IOSE_r2", "IOSE_r3",
  "ID8_r1", "ID8_r2"
)

# DNA thresholds chosen from DNA-abundance plots
DNA_threshold_vector <- c(2, 3, 5, 6, 3, 2, 30, 35)
names(DNA_threshold_vector) <- sample_name_vector

# Build per-sample dataframe with RD_ratio
create_sensor_info_for_sample <- function(sample_name) {
  parts <- strsplit(sample_name, "_")[[1]]
  cell_name <- parts[1]
  replicate_num <- parts[2]
  
  sample_DNA <- paste(cell_name, "Lib4", "DNA", replicate_num, sep = "_")
  sample_RNA <- paste(cell_name, "Lib4", "RNA", replicate_num, sep = "_")
  rd_ratio_col <- paste(cell_name, "Lib4", "RD_ratio", replicate_num, sep = "_")
  
  sample_df <- sensor_info[, c("promoter_name_bc", "promoter_name", sample_RNA, sample_DNA)]
  sample_df <- sample_df[sample_df[[sample_DNA]] != 0, ]
  sample_df[[rd_ratio_col]] <- sample_df[[sample_RNA]] / sample_df[[sample_DNA]]
  
  sample_df
}

## ------------------------------------------------------------------
## DNA threshold plot per sample
## ------------------------------------------------------------------

plot_and_set_DNA_threshold <- function(sample_name) {
  parts <- strsplit(sample_name, "_")[[1]]
  cell_name <- parts[1]
  replicate_num <- parts[2]
  
  sample_DNA <- paste(cell_name, "Lib4", "DNA", replicate_num, sep = "_")
  sample_RNA <- paste(cell_name, "Lib4", "RNA", replicate_num, sep = "_")
  
  sample_df <- create_sensor_info_for_sample(sample_name)
  base_unit <- min(sample_df[[sample_DNA]])
  
  percent_active_vector <- numeric(50)
  
  for (i in seq_len(50)) {
    dna_low  <- 0.99 * i * base_unit
    dna_high <- 1.01 * i * base_unit
    
    in_bin <- sample_df[[sample_DNA]] >= dna_low &
      sample_df[[sample_DNA]] <= dna_high
    
    num_in_bin <- sum(in_bin)
    if (num_in_bin == 0) {
      percent_active_vector[i] <- NA_real_
    } else {
      percent_active_vector[i] <-
        sum(in_bin & sample_df[[sample_RNA]] != 0) / num_in_bin
    }
  }
  
  percent_active_df <- data.frame(
    DNA_abundance = 1:50,
    percent_active = percent_active_vector
  )
  
  ggplot(percent_active_df, aes(x = DNA_abundance, y = percent_active)) +
    geom_point() +
    xlim(0, 50) +
    ylim(0, 1) +
    ggtitle(paste(cell_name, replicate_num, sep = "_"))
}

# Generate and save DNA threshold plots for all samples
sensor_DNA_threshold_plot_list <- lapply(sample_name_vector, plot_and_set_DNA_threshold)
names(sensor_DNA_threshold_plot_list) <- sample_name_vector

pdf("DNA_threshold_for_samples.pdf")
do.call(grid.arrange, sensor_DNA_threshold_plot_list)
dev.off()

## ------------------------------------------------------------------
## Filtering: DNA threshold + barcode count
## ------------------------------------------------------------------

filter_sensor_info_list_with_DNA_and_bc_threshold <- function(
    sample_name,
    DNA_threshold,
    bc_threshold = 3,
    remove_RNA_zero = TRUE
) {
  parts <- strsplit(sample_name, "_")[[1]]
  cell_name <- parts[1]
  replicate_num <- parts[2]
  
  sample_DNA <- paste(cell_name, "Lib4", "DNA", replicate_num, sep = "_")
  sample_RNA <- paste(cell_name, "Lib4", "RNA", replicate_num, sep = "_")
  sample_RD_ratio <- paste(cell_name, "Lib4", "RD_ratio", replicate_num, sep = "_")
  median_sample_RD_ratio <- paste("median", cell_name, "Lib4", "RD_ratio", replicate_num, sep = "_")
  
  sample_df <- create_sensor_info_for_sample(sample_name)
  base_unit <- min(sample_df[[sample_DNA]])
  
  # 1. DNA threshold filter
  sample_df <- sample_df[sample_df[[sample_DNA]] > DNA_threshold * base_unit, ]
  
  # 2. Optional: remove RNA = 0
  if (remove_RNA_zero) {
    sample_df <- sample_df[sample_df[[sample_RNA]] != 0, ]
  }
  
  # 3. Collapse barcodes to promoter-level summary
  sample_df_collapsed <- sample_df %>%
    group_by(promoter_name) %>%
    summarize(
      RNA_sum       = sum(!!as.symbol(sample_RNA), na.rm = TRUE),
      DNA_sum       = sum(!!as.symbol(sample_DNA), na.rm = TRUE),
      median_value  = median(!!as.symbol(sample_RD_ratio), na.rm = TRUE),
      n_bc          = n(),
      pseudo_Lib2_RD = RNA_sum / DNA_sum,
      .groups       = "drop"
    )
  
  # 4. Filter by minimum number of barcodes
  sample_df_collapsed <- sample_df_collapsed %>%
    filter(n_bc >= bc_threshold) %>%
    arrange(desc(median_value), desc(pseudo_Lib2_RD), desc(n_bc))
  
  colnames(sample_df_collapsed) <- c(
    "promoter_name",
    paste(sample_RNA, "sum", sep = "_"),
    paste(sample_DNA, "sum", sep = "_"),
    median_sample_RD_ratio,
    paste(cell_name, replicate_num, "n_bc", sep = "_"),
    paste(cell_name, "pseudo_Lib2_RD_ratio", replicate_num, sep = "_")
  )
  
  sample_df_collapsed
}

# Helper: create a filtered list for a given barcode threshold
make_filtered_list <- function(bc_threshold = 3, remove_RNA_zero = TRUE) {
  out <- mapply(
    filter_sensor_info_list_with_DNA_and_bc_threshold,
    sample_name   = sample_name_vector,
    DNA_threshold = DNA_threshold_vector[sample_name_vector],
    MoreArgs      = list(
      bc_threshold    = bc_threshold,
      remove_RNA_zero = remove_RNA_zero
    ),
    SIMPLIFY = FALSE
  )
  names(out) <- sample_name_vector
  out
}

# Main filtered list used downstream (bc_threshold = 3)
sensor_info_list_filtered <- make_filtered_list(bc_threshold = 3)

## ------------------------------------------------------------------
## Library design metadata
## ------------------------------------------------------------------

all_sensors <- read.csv(
  "all_enhancer_metadata_111525.csv",
  header = TRUE,
  stringsAsFactors = FALSE
)

all_sensors <- all_sensors %>%
  as_tibble() %>%
  select(
    TFBS_sequence,
    TF_name_by_PPM,
    variable_region,
    by_ppm_name,
    rank,
    TF_name_human_curated
  ) %>%
  mutate(
    promoter_name = paste(TFBS_sequence, TF_name_by_PPM, sep = "_")
  ) %>%
  arrange(TF_name_human_curated, rank) %>%
  select(
    promoter_name,
    TFBS_sequence,
    TF_name_by_PPM,
    TF_name_human_curated,
    variable_region,
    by_ppm_name,
    rank
  )

## ------------------------------------------------------------------
## Combine activity results across samples and write output
## ------------------------------------------------------------------

create_final_sensor_activity_result_dataframe <- function(sensor_info_list) {
  # Merge per-sample collapsed tables
  sensor_activity_result_filtered <- sensor_info_list %>%
    purrr::reduce(left_join, by = "promoter_name")
  
  # Add design metadata
  sensor_activity_result_filtered <- left_join(
    all_sensors,
    sensor_activity_result_filtered,
    by = "promoter_name"
  )
  
  # NA count (kept as in original script)
  sensor_activity_result_filtered$NA_count <- apply(
    sensor_activity_result_filtered,
    1,
    function(x) sum(is.na(x)) / 5
  )
  
  sensor_activity_result_filtered <- sensor_activity_result_filtered %>%
    mutate(
      mean_OV8_RD_ratio = rowMeans(
        select(., median_OV8_Lib4_RD_ratio_r1,
               median_OV8_Lib4_RD_ratio_r2,
               median_OV8_Lib4_RD_ratio_r3),
        na.rm = TRUE
      ),
      mean_IOSE_RD_ratio = rowMeans(
        select(., median_IOSE_Lib4_RD_ratio_r1,
               median_IOSE_Lib4_RD_ratio_r2,
               median_IOSE_Lib4_RD_ratio_r3),
        na.rm = TRUE
      ),
      mean_ID8_RD_ratio = rowMeans(
        select(., median_ID8_Lib4_RD_ratio_r1,
               median_ID8_Lib4_RD_ratio_r2),
        na.rm = TRUE
      )
    ) %>%
    mutate(
      mean_OV8_to_IOSE_RD_ratio = mean_OV8_RD_ratio / mean_IOSE_RD_ratio,
      mean_ID8_to_IOSE_RD_ratio = mean_ID8_RD_ratio / mean_IOSE_RD_ratio
    ) %>%
    arrange(desc(mean_OV8_to_IOSE_RD_ratio))
  
  sensor_activity_result_concise <- sensor_activity_result_filtered %>%
    select(
      promoter_name:rank,
      NA_count:mean_ID8_to_IOSE_RD_ratio
    ) %>%
    arrange(desc(mean_OV8_to_IOSE_RD_ratio))
  
  write.csv(sensor_activity_result_filtered, "ovca_sensor_activity_result_all.csv", row.names = FALSE)
  write.csv(sensor_activity_result_concise,  "ovca_sensor_activity_result_concise.csv", row.names = FALSE)
}

create_final_sensor_activity_result_dataframe(sensor_info_list_filtered)
