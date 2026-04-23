################################################################################
# Script: FASTQ Demultiplexing by Barcode (Lib4-Specific Version)
#
# Purpose:
#   This script demultiplexes a pooled FASTQ file into per-sample FASTQ files
#   using sample-specific barcode sequences. It is designed for TREND Lib4
#   libraries, which require appending the full RT-handle sequence to ensure
#   that each barcode is matched at the correct position within the read.
#
# Rationale:
#   TREND libraries store sample identity using a short index barcode embedded
#   in the read adjacent to a constant RT-handle sequence. Standard FASTQ
#   demultiplexing tools cannot directly use these internal barcodes, so this
#   script searches for the concatenated RT-handle + barcode sequence within
#   each read. Reads containing the matched sequence are written to the
#   corresponding sample FASTQ file.
#
# Required Inputs:
#   1. fastq_file_name  — Path to the pooled FASTQ file.
#   2. barcode_sample_info — Excel file (.xlsx) containing sample names and
#      barcodes. The script expects:
#           'Index seq' column → barcode sequences
#           'Sample'    column → output FASTQ file names
#      (starting from row 2, since skiprows=1 is used)
#
# Output:
#   A directory "../SP011_Lib4/demultiplexed_fastq" is created.
#   Each sample receives a separate FASTQ file named:
#           <Sample>.fastq
#
# Dependencies & Environment:
#   • Python 3.x
#   • pandas
#   • fastq-grep (from fastq-tools)
#       The script calls it as:
#           /home/mw277/fastq-tools-master/src/fastq-grep
#     Ensure this path exists or update it for your system.
#
# Notes:
#   • The constant sequence "CGCAGACTCGACCACCTCTGAC" is prepended to each barcode
#     to reconstruct the full search motif used in Lib4.
#   • The script uses os.system() calls for file creation and grepping; for large
#     FASTQ files, consider parallelization or GNU grep optimized approaches.
#   • Destination paths may need to be updated depending on directory structure.
################################################################################

import os
import pandas as pd
from sys import argv
fastq_file_name = argv[1]
barcode_sample_info = argv[2]
bc_sample_match = pd.read_excel(barcode_sample_info, skiprows=1)
print(bc_sample_match)
barcodes = bc_sample_match['Index seq']
sample_name = bc_sample_match['Sample']
os.system('mkdir ../SP011_Lib4/demultiplexed_fastq')
for bc, s_name in zip(barcodes, sample_name):
    bc = 'CGCAGACTCGACCACCTCTGAC'+ bc #append the full RT-handle sequence to ensure grepped barcode is at the right place for Lib4
    os.system('/home/mw277/fastq-tools-master/src/fastq-grep '+bc+' '+fastq_file_name+' > '+'../SP011_Lib4/demultiplexed_fastq/'+s_name+'.fastq') #need to change destination accordingly
