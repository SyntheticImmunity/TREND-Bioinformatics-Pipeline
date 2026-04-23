#!/bin/bash

#SBATCH -p medium
#SBATCH -t 3-00:00
#SBATCH -c 4
#SBATCH --mem=200G
#SBATCH -o slurm.%j.out
#SBATCH -e slurm.%j.err

################################################################################
# Script: TREND Lib4 amplicon pipeline (HMS O2 / SLURM batch job)
#
# Purpose:
#   This SLURM batch script runs the full TREND Lib4 barcode-processing pipeline
#   on the HMS O2 (or similar) HPC cluster. It takes raw amplicon-based NGS
#   reads and produces:
#       • UMI-collapsed barcode FASTA files,
#       • Bowtie2-aligned SAM files against the Lib4 reference,
#       • construct-level barcode count tables via an in-house R script.
#
# Overview of the pipeline:
#   1. Correct read orientation:
#        - Use a Python script to detect reverse-oriented reads and flip them,
#          producing "flipped_*_R1_001.fastq" files.
#   2. (Optional) Demultiplexing:
#        - If the core has not performed demultiplexing, use a custom Python
#          script plus a barcode–sample key file to split pooled reads into
#          per-sample FASTQ files.
#   3. Adaptor trimming:
#        - Use FASTX-Toolkit (fastx_trimmer) to trim 3' ends and remove residual
#          Illumina adaptor/low-quality bases.
#   4. UMI collapsing:
#        - Use fastx_collapser to collapse identical reads by UMI, reducing PCR
#          bias and converting FASTQ to FASTA.
#   5. Barcode extraction:
#        - Use cutadapt to trim reads and retain only the 20-bp designed barcode
#          sequence between BamHI and RT-handle2.
#   6. Barcode alignment:
#        - Use Bowtie2 to align barcode sequences to the Lib4 reference (Lib4.fasta),
#          generating SAM files for each sample.
#   7. Count extraction:
#        - Run an in-house R script (extract_counts_from_samfiles_Lib4.R) to
#          generate raw and normalized barcode count tables.
#
# Inputs & directory layout:
#   • project_directory
#       - The working directory for this run (e.g., /n/scratch3/users/<user>/SP0XX).
#       - Must contain raw FASTQ files named "*_R1_001.fastq".
#
#   • Key support files (copied automatically from /home/mw277/... when needed):
#       - correct_read_orientation_for_Lib4_precursor_mbcf.py
#       - Lib4.fasta
#       - Lib4_info_concise_060621.csv
#       - allTF_synpro_top10_final_Lib2_for_Agilent_061220.csv
#       - extract_counts_from_samfiles_Lib4.R
#
# Cluster / module assumptions:
#   • Environment supports the following modules:
#       - fastx/0.0.13
#       - python/3.7.4 (or compatible Python3)
#       - gcc/6.2.0
#       - bowtie2/2.3.4.3
#       - R/3.5.1
#   • SLURM options at the top request:
#       - medium partition
#       - 3 days wall-time
#       - 4 CPU cores
#       - 200 GB RAM
#
# Notes:
#   • Update `project_directory` before running to match the current experiment
#     (e.g., SP035 → SP036).
#   • The optional demultiplexing block is commented out; enable it only if
#     the sequencing core did not demultiplex or sample–barcode assignments
#     need to be re-derived.
#   • The cutadapt parameters (e.g., -g adapter sequence, -t trim length) and
#     fastx_trimmer trimming parameter (-t) may require adjustment for different
#     library designs or read lengths.
#   • Ensure all required key files are accessible. The /home/mw277/... paths shown here
#     are only example locations—update them to match the file locations in your own
#     project directory or copy/symlink the files accordingly.
#   • This script is designed as a full end-to-end pipeline; intermediate
#     directories (demultiplexed_fastq, trimmed_fastq, sam_files, etc.) are
#     created automatically in `project_directory`.
################################################################################

# Commands below
project_directory="/n/scratch3/users/m/mw277/SP035" # need to change accordingly

# Key analysis steps:
# 1. flip and correct the orientation of all the reads
# 2. (optional) demultiplexing
# 3. trim the tail of the reads to remove NGS adaptor
# 4. collapse read by UMI to remove PCR bias (this step will also convert fastq files into fasta files)
# 5. trim the read to only keep the 20-bp design barcodes (only keep sequence between BamHI and RT-handle2)
# 6. count the barcodes by using the Bowtie2 aligner
# 7. extract counts with a in-house R script (extract_counts_from_samfiles_Lib4.R)

# 1. flip and correct the orientation of all the reads
cd $project_directory/
cp /home/mw277/key_files_for_Lib2_Lib4_analysis/correct_read_orientation_for_Lib4_precursor_mbcf.py $project_directory
for i in $(ls *_R1_001.fastq); do python3 correct_read_orientation_for_Lib4_precursor_mbcf.py ${i};done
mkdir demultiplexed_fastq
mv flipped_*_R1_001.fastq $project_directory/demultiplexed_fastq

# 2. (optional) demultiplexing
# Currently, MBCF help us to do the demultiplexing. So, we can skip the following step as long as our sample barcodes are indeed linked with our samples.Sometimes it is not like this, or MBCF does not help us with demultiplexing. Then we will need to perform the demultiplexing ourselves. If so, need to change the settings in the "demultiplex_fastq_for_Lib4_FINAL.py" and need to upload the barcode sample files to the folder (e.g., "DFCI_core_Novaseq_042821_Lib4.xlsx"), and run the following commands: 
#module load gcc/6.2.0
#module load python/3.6.0
#raw_fastq_file_name="flipped_DNA_R1.fastq" # need to change accordingly
#barcode_info_file="info_for_demultiplex_DNA.xlsx" # need to change accordingly
#python demultiplex_fastq_for_Lib4_FINAL.py $raw_fastq_file_name $barcode_info_file # for running fastq-grep on Lib4
#mkdir undemultiplexed_fastq
#mv $raw_fastq_file_name ./undemultiplexed_fastq # need to change the file name accordingly
#mkdir demultiplexed_fastq
#mv flipped_*_R1_001.fastq $project_directory/demultiplexed_fastq

# 3. trim the tail of the reads to remove NGS adaptor

cd $project_directory/demultiplexed_fastq
module load fastx/0.0.13
for i in $(ls *.fastq); do fastx_trimmer -Q33 -t 17 -i ${i} -o ${i}_trimmed.fastq ${i};done # may need to adjust -t parameter
mkdir trimmed_fastq
mv *_trimmed.fastq ./trimmed_fastq

# 4. collapse read by UMI to remove PCR bias (this step will also convert fastq files into fasta files)
cd $project_directory/demultiplexed_fastq/trimmed_fastq
for i in $(ls *.fastq); do fastx_collapser -Q33 -v -i ${i} -o ${i}_UMI_collapsed.fa ${i};done

# 5. trim the read to only keep the 20-bp design barcodes (only keep sequence between BamHI and RT-handle2)
module load python/3.7.4
cd $project_directory/demultiplexed_fastq/trimmed_fastq/
mkdir UMI_collapsed_fasta
mv *.fa ./UMI_collapsed_fasta
cd $project_directory/demultiplexed_fastq/trimmed_fastq/UMI_collapsed_fasta
for i in $(ls *.fa); do cutadapt -g TAAAGCGGCCGCGAGGATCC...CGCAGACTCGACCACCTCTGAC --discard-untrimmed -o ${i}_trimmed.fa ${i};done #https://cutadapt.readthedocs.io/en/v1.16/guide.html
mv *_trimmed.fa $project_directory

# 6. count the barcodes by using the Bowtie2 aligner
# need to copy "Lib4.fasta", "Lib4_info_concise_060621.csv", "allTF_synpro_top10_final_Lib2_for_Agilent_061220.csv", and "extract_counts_from_samfiles_Lib4.R" files to the "/n/scratch3/users/m/mw277/SPXXX" folder
cp /home/mw277/key_files_for_Lib2_Lib4_analysis/Lib4.fasta $project_directory
cp /home/mw277/key_files_for_Lib2_Lib4_analysis/Lib4_info_concise_060621.csv $project_directory
cp /home/mw277/key_files_for_Lib2_Lib4_analysis/allTF_synpro_top10_final_Lib2_for_Agilent_061220.csv $project_directory
# double check that this current script and the above files are in the same folder if you are running this part manually

module load gcc/6.2.0
module load bowtie2/2.3.4.3
cd $project_directory
mkdir sam_files
bowtie2-build Lib4.fasta Lib4
for i in $(ls *.fa); do bowtie2 -f --threads 4 -x Lib4 -U ${i} -S ./sam_files/${i}.sam; done
# move fa files to a folder to cleanup the working directory
mkdir UMI_collapsed_fasta_files
mv *trimmed.fa UMI_collapsed_fasta_files

# 7. extract counts with a in-house R script (extract_counts_from_samfiles_Lib4.R)
cp /home/mw277/key_files_for_Lib2_Lib4_analysis/extract_counts_from_samfiles_Lib4.R $project_directory
module load gcc/6.2.0 R/3.5.1
Rscript extract_counts_from_samfiles_Lib4.R