# TREND Library Bioinformatics Pipeline --- README

This README accompanies the TREND (Transcription-Factor-Responsive Enhancer Discovery) bioinformatics pipeline.
It provides system requirements, installation instructions, and the full instructions for reproducing key enhancer
analyses described in the manuscript.

------------------------------------------------------------------------

## 1. System Requirements

### **Operating System**

-   Linux-based HPC cluster (recommended)
-   Compatible with macOS or Linux workstation

### **Languages**

-   **Python ≥ 3.7**
-   **R ≥ 4.0**

### **Required Software & Tools**

-   **Bowtie2**
-   **SAMtools**
-   **FASTX-Toolkit**
-   **Cutadapt**
-   **SLURM** (or any job scheduler; e.g., LSF, PBS)

### **Memory/CPU**

-   Alignment and UMI-collapsing steps require multi-core CPUs
-   Recommended: 8--32 cores, 32--128 GB RAM depending on library size

------------------------------------------------------------------------

## 2. Installation Guide

### **Clone or download the TREND pipeline**

Place the following scripts in a working directory:

-   `Lib4_all_steps_FINAL_111525.sbatch`
-   `check_sample_barcode_consistency_v3.py`
-   `correct_read_orientation_for_Lib4_mbcf.py`
-   `demultiplex_fastq_for_Lib4_FINAL.py`
-   `extract_counts_from_samfiles_Lib4.R`
-   `ovarian_cancer_specific_enhancer_screening_analysis.R`

### **Install dependencies**

#### **Python**

``` bash
pip install biopython pandas numpy
```

#### **R**

Install required R packages:

``` r
install.packages(c("tidyverse", "data.table", "Rsamtools"))
```

#### **Command‑line tools**

``` bash
# Example for Ubuntu
sudo apt-get install bowtie2 samtools fastx-toolkit cutadapt
```

### **Configure cluster environment**

If using SLURM, edit the `.sbatch` file: - Update directory paths - Set cluster partition / walltime - Adjust CPU/Memory requests

### 3. **Run End‑to‑End Using SLURM for Steps 1-8**

``` bash
sbatch Lib4_all_steps_FINAL_111525.sbatch
```

### **Or run steps manually using the detailed instructions provided in the section below**

1.  Verify barcodes
2.  Flip orientations
3.  Demultiplex
4.  Trim adaptors
5.  Collapse UMIs
6.  Extract barcodes
7.  Bowtie2 alignment
8.  Create barcode count tables
9.  Run the enhancer‑activity quantification script

Expected outputs:
`alignment_result_unnormalized_in_house_pipeline.csv` 
`alignment_result_normalized_in_house_pipeline.csv`

------------------------------------------------------------------------

## 4. Detailed Instructions for Each Step

### **Step 1: (Optional) Verify sample–barcode consistency**

Before beginning the analysis, extract a small subset of reads from each demultiplexed FASTQ file to ensure that sample barcodes match the correct sample identities.
 The script **`check_sample_barcode_consistency_v3.py`** can be run either on a command line or locally.
 It cross-references the barcode key file with sequencing read headers and confirms that each demultiplexed file corresponds to its intended sample.

------

### **Step 2: Correct read orientation (“flipping”)**

TREND library FASTQ files often contain reads in mixed orientations.
 Run **`correct_read_orientation_for_Lib4_mbcf.py`** to identify reverse-complement reads using constant regions and flip them into the correct orientation.
 Corrected files are saved with the prefix **`flipped_`**.

------

### **Step 3: (Optional) Demultiplexing**

If sequencing data were not demultiplexed by the core, run:
 **`demultiplex_fastq_for_Lib4_FINAL.py`**
 together with a barcode–sample key file (e.g., `.xlsx` mapping sample names and barcode sequences).

This separates reads into individual FASTQ files for each sample.

------

### **Step 4: Trim sequencing adaptors**

Trim residual Illumina adaptor sequence from the 3′ ends of reads using **FASTX-Toolkit**.
 Adjust trimming length to remove low-quality bases and adaptor remnants, retaining only the insert of interest.

------

### **Step 5: Collapse reads by unique molecular identifier (UMI)**

To reduce PCR bias, collapse identical reads sharing the same UMI using **`fastx_collapser`**.
 This converts FASTQ to FASTA and ensures only one representative read per UMI proceeds to downstream counting.

------

### **Step 6: Extract barcode region**

Trim each collapsed read to retain the **20-bp designed barcode** between the BamHI site and RT-handle2.
 Use **Cutadapt** to remove flanking constant sequences.
 Reads lacking the expected motif are discarded.

------

### **Step 7: Align barcodes to the reference library**

Align barcode FASTA files to the TREND library reference using **Bowtie2**.

- Build a reference index from **`Lib4.fasta`**
- Align with parameters optimized for short, high-similarity sequences
- Output SAM files are generated for counting

------

### **Step 8: Generate barcode count tables**

Run the R script **`extract_counts_from_samfiles_Lib4.R`** to quantify barcode abundance.

This script:

- Converts SAM to BAM using **Rsamtools**
- Uses **`idxstatsBam()`** to extract mapped read counts per barcode
- Compiles:
  - **Raw read-count matrix**
  - **Normalized RPM matrix**
- Merges results with the library reference file (**`Lib4_info_concise_060621.csv`**)
- Outputs two annotated tables:

**Output files:**

- `alignment_result_unnormalized_in_house_pipeline.csv`
- `alignment_result_normalized_in_house_pipeline.csv`

These files provide barcode-level abundance for downstream enhancer-activity analysis.

------

### **Step 9: Downstream quantitative enhancer-activity analysis**

Run:
 **`ovarian_cancer_specific_enhancer_screening_analysis.R`**

Ensure the following files are in the same directory:

1. `ovarian_cancer_specific_enhancer_screening_analysis.R`
2. `alignment_result_normalized_in_house_pipeline.csv`
3. `alignment_result_unnormalized_in_house_pipeline.csv`
4. `all_enhancer_metadata_111525.csv`

#### **What the script does**

- Loads normalized + unnormalized count tables
- Selects RNA/DNA columns for OV8, IOSE, and ID8
- Applies sample-specific DNA-abundance thresholds
- Collapses barcode-level RD ratios into promoter-level scores

------

## 5. **Key Analytical Steps In the Step 9 Script**

### **1. Data loading and structuring**

- Import unnormalized and normalized alignment results
- Create analysis-ready data frames containing library metadata and RNA/DNA counts per replicate

### **2. Initial filtering**

- Remove barcodes with **DNA = 0**
- Remove entries with **RNA = 0**
- Require **≥ 3 barcodes per promoter** (`bc_threshold = 3`)

### **3. DNA-abundance thresholding per sample**

- Script generates **DNA_threshold_for_samples.pdf** diagnostic plots
- Applies sample-specific DNA cutoffs (e.g., `c(2,3,5,6,3,2,30,35)`) corresponding to the abundance level where ~75% of constructs remain active
- Removes underrepresented, noisy barcodes

### **4. Activity computation and replicate summarization**

- Computes barcode-level RNA/DNA (RD) ratios
- Collapses RD ratios within each replicate using **median**
- Computes **mean RD ratios** across replicates for each cell line (e.g., `mean_OV8_RD_ratio`)
- Calculates tumor-vs-control selectivity:
  - `mean_OV8_to_IOSE_RD_ratio`
  - `mean_ID8_to_IOSE_RD_ratio`

### **5. Aggregation with design and export**

- Merge filtered activity table with library annotation (e.g., TF, TFBS sequence, variable region, rank)
- Export:
  - Full table
  - Concise table sorted by tumor-selective activity

------

### **Output files**

- `ovca_sensor_activity_result_all.csv`
   *Full annotated activity table with per-replicate medians and fold ratios*
- `ovca_sensor_activity_result_concise.csv`
   *Condensed table with promoter ID, core annotations, and tumor/control ratios*
- `DNA_threshold_for_samples.pdf`
   *Diagnostic DNA-abundance plots used for cutoff selection*

------

### **Expected results**

This analysis yields:

- Barcode- and promoter-level **RNA/DNA activity ratios**
- Per–cell line **mean activity scores** (e.g., OV8 vs IOSE)
- Ranked lists of **high-confidence synthetic enhancers** that pass coverage, detection, and barcode-support filters

## 6. License

This pipeline is distributed under the **MIT License**.

------------------------------------------------------------------------

## 7. Location of Code & Documentation

A public repository link may be added upon acceptance.
For review, all scripts are included in the Dropbox URL (https://www.dropbox.com/scl/fo/39jvyy6kjho2nyqo59h6e/AHRDQEU4H6NAR85AP99_UDU?rlkey=rcihdns29sfx69930bz5pbjug&dl=0).

------------------------------------------------------------------------

## 8. Contact

For questions, please contact the corresponding author or submit a GitHub issue (after repository launch).

------------------------------------------------------------------------

