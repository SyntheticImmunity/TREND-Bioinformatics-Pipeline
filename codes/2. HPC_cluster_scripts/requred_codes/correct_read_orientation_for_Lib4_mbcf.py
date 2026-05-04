################################################################################
# Script: Read Orientation Correction for MBCF Amplicon Sequencing (TREND Lib4)
#
# Purpose:
#   This script corrects read orientation ("flips" reads) for amplicon-based NGS
#   data generated through the MBCF workflow used for TREND libraries. Because
#   amplicon sequencing can produce reads in both forward and reverse
#   orientations, this script detects reverse-orientation reads and converts them
#   to the forward orientation so downstream barcode extraction and alignment are
#   accurate.
#
# Rationale:
#   In TREND Lib4 sequencing, specific constant regions (vector features) appear
#   within the read. If the read is in reverse orientation, these features appear
#   as reverse-complement sequences. By scanning the read for the presence of
#   these reverse-orientation signatures, this script identifies such reads,
#   reverse-complements the sequence, and also reverses the associated Phred
#   quality string to maintain positional correctness.
#
# How Orientation is Detected:
#   • Two constant sequence motifs are defined:
#         vector_feature_rc1 = 'TCCATGCCGA'
#         vector_feature_rc2 = 'AGGTGGTCGAGT'
#   • If either motif is present, the script assumes the read is in reverse
#     orientation and flips the read using BioPython's Seq.reverse_complement().
#
# FASTQ Handling:
#   FASTQ format follows a 4-line cycle:
#       Line 0: Header
#       Line 1: Sequence
#       Line 2: '+'
#       Line 3: Quality scores
#
#   The script:
#       • Writes the header unmodified.
#       • Flips the sequence if needed.
#       • Writes the + line unchanged.
#       • Reverses the Phred quality string if the sequence was flipped.
#
# Inputs:
#   • input_file  — the FASTQ file to be corrected (provided via argv[1]).
#       Example:
#           python correct_read_orientation_for_Lib4_mbcf.py myfile.fastq
#
# Outputs:
#   • A new FASTQ file named:
#           flipped_<input_file>
#     located in the directory specified by `working_dir`.
#
# Environment Requirements:
#   • Python 3.x
#   • BioPython installed (for Seq and reverse_complement)
#   • Sufficient scratch/storage space for output FASTQ files
#
# Assumptions:
#   • Reads must contain either vector_feature_rc1 or vector_feature_rc2
#     to be considered reverse-oriented.
#   • `working_dir` must be updated to a valid directory for your system.
#   • The script streams through the FASTQ file sequentially, enabling support
#     for large NGS files without loading them into memory.
#
# Notes:
#   • This script is optimized for TREND Lib4 sequencing design. If vector
#     features differ in other libraries, update the constant feature sequences.
#   • Runtime is printed at the end for performance monitoring.
#   • This orientation correction step is typically performed before UMI
#     collapsing, barcode trimming, and Bowtie2 alignment.
################################################################################

import os
from Bio.Seq import Seq
import time
from sys import argv
working_dir = ''  # operate in the current working directory
input_file = argv[1]
output_fastq = open('flipped_' + input_file, 'a+')

vector_feature_rc1 = 'TCCATGCCGA'
vector_feature_rc2 = 'AGGTGGTCGAGT'

start = time.perf_counter()

#Read fastq file and store it as a pd dataframe
with open(working_dir + input_file, 'r') as f:
    for index, line in enumerate(f):
        flip_phred_score = False
        #print(index)
        #print(line)
        if index % 4 == 0:
            output_fastq.write(line.strip('\n'))
            output_fastq.write('\n')
        if index % 4 == 1:
            sequence = Seq(line.strip('\n'))
            if vector_feature_rc1 in sequence or vector_feature_rc2 in sequence:
                sequence = sequence.reverse_complement()
                output_fastq.write(str(sequence))
                output_fastq.write('\n')
                flip_phred_score = True
            else:
                output_fastq.write(str(sequence))
                output_fastq.write('\n')
        if index % 4 == 2:
            output_fastq.write(line.strip('\n'))
            output_fastq.write('\n')
        if index % 4 == 3:
            if flip_phred_score:
                output_fastq.write(line.strip('\n')[::-1])
                output_fastq.write('\n')
            else:
                output_fastq.write(line.strip('\n'))
                output_fastq.write('\n')

output_fastq.close()

done_correction_and_writing = time.perf_counter()

print(f'total time used {done_correction_and_writing-start:.2f} second(s)')
