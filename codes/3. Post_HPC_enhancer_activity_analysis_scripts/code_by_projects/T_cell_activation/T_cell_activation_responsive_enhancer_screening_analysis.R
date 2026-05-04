#### ===============================================================
#### Analysis pipeline for T-cell activation responsive enhancer screen (two different donors)
#### ===============================================================

library(tidyverse)
library(gridExtra)
library(data.table)

# Inputs and outputs are read from / written to the current working directory.

## ---- B1. Read preprocessed count matrices (unnormalized & normalized) ----
## Unnormalized and library-size–normalized read count tables were generated
## by the alignment/counting pipeline and are used here for QC and downstream
## activity calculations.

un_normalized_result_RS <- read.csv(
  "alignment_result_unnormalized_in_house_pipeline.csv",
  header = TRUE,
  stringsAsFactors = FALSE
)
sensor_info_unnormalized_RS <- as_tibble(un_normalized_result_RS)

## For summary statistics, zero counts are treated as missing values (NA) so that
## medians and quantiles reflect the distribution of detected barcodes only.
sensor_info_unnormalized_RS_remove_zero <- copy(sensor_info_unnormalized_RS)
sensor_info_unnormalized_RS_remove_zero[
  sensor_info_unnormalized_RS_remove_zero == 0
] <- NA

## Normalized read counts (RNA and DNA) are used for all downstream analyses.
result_RS <- read.csv(
  "alignment_result_normalized_in_house_pipeline.csv",
  header = TRUE,
  stringsAsFactors = FALSE
)

## This tibble is the main data structure used for subsequent filtering
## and activity calculations.
sensor_info <- as_tibble(result_RS)

## ---- B2. Per-sample normalization and RD ratio calculation --------------
## For each sample, we:
##   (1) discard barcodes with zero DNA counts (no library representation);
##   (2) optionally median-normalize RNA and DNA counts; and
##   (3) compute the RNA:DNA (RD) ratio as a proxy for enhancer activity
##       for each barcode.

create_sensor_info_for_sample <- function(sample_name, median_normalization = TRUE) {
  cell_name     <- strsplit(sample_name, "_")[[1]][1]   # condition label
  replicate_num <- strsplit(sample_name, "_")[[1]][2]   # replicate label (r1, r2)
  sample_DNA    <- paste(cell_name, "Lib4", "DNA", replicate_num, sep = "_")
  sample_RNA    <- paste(cell_name, "Lib4", "RNA", replicate_num, sep = "_")
  
  sample_df <- sensor_info[, c("promoter_name_bc", "promoter_name",
                               sample_RNA, sample_DNA)]
  ## Exclude barcodes with zero DNA counts (not represented in the library)
  sample_df <- sample_df[sample_df[[sample_DNA]] != 0, ]
  
  ## Median-normalize RNA and DNA counts to correct for sample-specific depth
  ## and compositional effects, if requested.
  if (median_normalization) {
    sample_RNA_normalized <- sample_df[[sample_RNA]] /
      median(sample_df[[sample_RNA]][sample_df[[sample_RNA]] != 0])
    sample_DNA_normalized <- sample_df[[sample_DNA]] /
      median(sample_df[[sample_DNA]])
    sample_df[[sample_RNA]] <- sample_RNA_normalized
    sample_df[[sample_DNA]] <- sample_DNA_normalized
  }
  
  ## RD_ratio: per-barcode enhancer activity (RNA expression normalized
  ## by its own DNA count).
  sample_df[[paste(cell_name, "Lib4", "RD_ratio", replicate_num, sep = "_")]] <-
    sample_df[[sample_RNA]] / sample_df[[sample_DNA]]
  
  sample_df
}


## ---- B3. Determine DNA abundance thresholds for each sample -------------
## We define a DNA abundance threshold for each sample to exclude barcodes
## with extremely low DNA representation, as these are more prone to
## sampling noise. For a series of increasing DNA copy-number bins
## (multiples of the minimal DNA count), we calculate the fraction of
## “active” barcodes (non-zero RNA) and identify the smallest DNA bin at
## which ≥50% of barcodes are active.

## Sample labels used throughout the analysis
sample_name_vector_RS <- c("rest_r1", "rest_r2", "stim_r1", "stim_r2")

sensor_info_list_RS <- lapply(
  sample_name_vector_RS,
  create_sensor_info_for_sample,
  median_normalization = FALSE
)
names(sensor_info_list_RS) <- sample_name_vector_RS


plot_and_set_DNA_threshold <- function(sample_name) {
  sample_df <- create_sensor_info_for_sample(sample_name)
  cell_name     <- strsplit(sample_name, "_")[[1]][1]
  replicate_num <- strsplit(sample_name, "_")[[1]][2]
  sample_DNA    <- paste(cell_name, "Lib4", "DNA", replicate_num, sep = "_")
  sample_RNA    <- paste(cell_name, "Lib4", "RNA", replicate_num, sep = "_")
  base_unit     <- min(sample_df[[sample_DNA]])
  
  percent_active_vector <- numeric()
  record_theshold       <- TRUE
  cut_off_threshold     <- NA_real_
  
  for (i in 1:100) {
    subset_idx <- sample_df[[sample_DNA]] >= (0.99 * i * base_unit) &
      sample_df[[sample_DNA]] <= (1.01 * i * base_unit)
    num_all    <- sum(subset_idx)
    num_active <- sum(subset_idx & (sample_df[[sample_RNA]] != 0))
    percent_active <- ifelse(num_all > 0, num_active / num_all, NA_real_)
    percent_active_vector <- c(percent_active_vector, percent_active)
    
    if (!is.na(percent_active) && percent_active >= 0.5 && record_theshold) {
      cut_off_threshold <- i
      record_theshold   <- FALSE
    }
  }
  
  percent_active_df <- data.frame(
    DNA_abundance = 1:100,
    percent_active = percent_active_vector
  )
  
  ggplot(percent_active_df) +
    geom_point(aes(x = DNA_abundance, y = percent_active)) +
    scale_x_continuous(limits = c(1, 100),
                       breaks = seq(0, 100, 10)) +
    ylim(0, 1) +
    ggtitle(paste(cell_name, replicate_num,
                  "threshold", cut_off_threshold, sep = "_"))
}


## Generate and save DNA threshold plots for all samples.
sensor_DNA_threshold_plot_list_RS <- lapply(
  sample_name_vector_RS,
  plot_and_set_DNA_threshold
)
names(sensor_DNA_threshold_plot_list_RS) <- sample_name_vector_RS

pdf("DNA_threshold_rest_stim_50_percent_reporting.pdf",
    width = 16, height = 12)
do.call(grid.arrange, sensor_DNA_threshold_plot_list_RS)
dev.off()


## ---- B4. Apply DNA and barcode-count thresholds and collapse barcodes ---
## For each sample, we:
##   (1) exclude barcodes below a sample-specific DNA abundance threshold;
##   (2) optionally exclude barcodes with zero RNA counts;
##   (3) collapse barcodes belonging to the same enhancer (promoter_name)
##       by summarizing RNA and DNA counts and the distribution of RD ratios;
##   (4) enforce a minimum number of barcodes (bc_threshold) per enhancer,
##       and rank enhancers by activity metrics.

filter_sensor_info_list_with_DNA_and_bc_threshold <- function(
    sample_name,
    DNA_threshold,
    bc_threshold,
    remove_RNA_zero = TRUE
) {
  sample_df <- create_sensor_info_for_sample(sample_name)
  cell_name     <- strsplit(sample_name, "_")[[1]][1]
  replicate_num <- strsplit(sample_name, "_")[[1]][2]
  sample_DNA    <- paste(cell_name, "Lib4", "DNA", replicate_num, sep = "_")
  sample_RNA    <- paste(cell_name, "Lib4", "RNA", replicate_num, sep = "_")
  sample_RD_ratio <- paste(cell_name, "Lib4", "RD_ratio", replicate_num, sep = "_")
  median_sample_RD_ratio <- paste(
    "median", cell_name, "Lib4", "RD_ratio", replicate_num, sep = "_"
  )
  
  base_unit <- min(sample_df[[sample_DNA]])
  sample_df <- sample_df[sample_df[[sample_DNA]] > DNA_threshold * base_unit, ]
  if (remove_RNA_zero) {
    sample_df <- sample_df[sample_df[[sample_RNA]] != 0, ]
  }
  
  sample_df_collapsed <- sample_df %>%
    dplyr::group_by(promoter_name) %>%
    dplyr::summarize(
      RNA_sum      = sum(!!rlang::sym(sample_RNA), na.rm = TRUE),
      DNA_sum      = sum(!!rlang::sym(sample_DNA), na.rm = TRUE),
      median_value = median(!!rlang::sym(sample_RD_ratio)),
      n_bc         = dplyr::n(),
      pseudo_Lib2_RD = RNA_sum / DNA_sum,
      .groups      = "drop"
    ) %>%
    dplyr::filter(n_bc >= bc_threshold) %>%
    dplyr::arrange(dplyr::desc(median_value),
                   dplyr::desc(pseudo_Lib2_RD),
                   dplyr::desc(n_bc))
  
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

## DNA abundance thresholds and minimum barcode counts were selected to
## match the parameters used in the original analysis, after relabeling
## replicates. Each entry in DNA_threshold_vector_RS corresponds to one
## sample in sample_name_vector_RS.
DNA_threshold_vector_RS <- c(2, 2, 3, 2)
bc_threshold_vector_RS  <- rep(8, length(sample_name_vector_RS))

sensor_info_list_filtered_RS <- list()
for (i in seq_along(sample_name_vector_RS)) {
  df_to_append <- filter_sensor_info_list_with_DNA_and_bc_threshold(
    sample_name_vector_RS[i],
    DNA_threshold_vector_RS[i],
    bc_threshold_vector_RS[i]
  )
  sensor_info_list_filtered_RS[[i]] <- df_to_append
}
names(sensor_info_list_filtered_RS) <- sample_name_vector_RS


## ---- B5. Join with enhancer metadata and compute donor-level activities --
## Enhancer (promoter_name)–level activity tables are merged with the design
## metadata (TF, motif, and sequence information). For each donor, we compile
## a final table including summary statistics and the stim/rest RD ratio.

all_sensors <- read.csv(
  "all_enhancer_metadata_111525.csv",
  header = TRUE,
  stringsAsFactors = FALSE
)

all_sensors <- all_sensors %>%
  dplyr::select(TFBS_sequence, TF_name_by_PPM, TF_name_human_curated,
                variable_region, by_ppm_name, rank) %>%
  dplyr::mutate(promoter_name = paste(TFBS_sequence, TF_name_by_PPM, sep = "_")) %>%
  dplyr::arrange(TF_name_by_PPM, rank) %>%
  dplyr::select(promoter_name, TFBS_sequence:rank)


create_final_sensor_activity_result_dataframe_RS <- function(sensor_info_list, 
                                                             output_basename = "output") {
  
  ## Internal helper: build and write output for a single biological donor
  ## (corresponding to one replicate label).
  build_for_rep <- function(rep_label, donor_label) {
    ## Select the two samples (conditions) corresponding to this replicate,
    ## e.g. "rest_r1" and "stim_r1".
    subset_list <- sensor_info_list[grepl(paste0("_", rep_label, "$"),
                                          names(sensor_info_list))]
    
    ## Merge activity summaries across conditions by enhancer (promoter_name).
    sensor_activity_result_filtered <- subset_list %>%
      purrr::reduce(full_join, by = "promoter_name")
    
    ## Attach enhancer design metadata.
    sensor_activity_result_filtered <- dplyr::left_join(
      all_sensors,
      sensor_activity_result_filtered,
      by = "promoter_name"
    )
    
    ## Compute condition-specific stim/rest RD ratios for this donor.
    if (rep_label == "r1") {
      sensor_activity_result_filtered <- sensor_activity_result_filtered %>%
        dplyr::mutate(
          stim_to_rest_RD_ratio_r1 =
            median_stim_Lib4_RD_ratio_r1 / median_rest_Lib4_RD_ratio_r1
        )
      
      sensor_activity_result_concise <- sensor_activity_result_filtered %>%
        dplyr::select(
          promoter_name:rank,
          dplyr::contains("median_"),
          dplyr::contains("_n_bc"),
          stim_to_rest_RD_ratio_r1
        )
      
    } else if (rep_label == "r2") {
      sensor_activity_result_filtered <- sensor_activity_result_filtered %>%
        dplyr::mutate(
          stim_to_rest_RD_ratio_r2 =
            median_stim_Lib4_RD_ratio_r2 / median_rest_Lib4_RD_ratio_r2
        )
      
      sensor_activity_result_concise <- sensor_activity_result_filtered %>%
        dplyr::select(
          promoter_name:rank,
          dplyr::contains("median_"),
          dplyr::contains("_n_bc"),
          stim_to_rest_RD_ratio_r2
        )
    }
    
    ## Each donor-specific table is written as a separate CSV file.
    file_name <- paste0(
      output_basename, "_", donor_label, ".csv"
    )
    
    write.csv(sensor_activity_result_concise, file_name, row.names = FALSE)
  }
  
  ## Here r1 and r2 correspond to the two biological donors.
  build_for_rep("r1", "donor1")
  build_for_rep("r2", "donor2")
}

## Generate final donor-specific enhancer activity tables.
create_final_sensor_activity_result_dataframe_RS(
  sensor_info_list_filtered_RS,
  output_basename = "activation_responsive_enhancer_screening_result"
)