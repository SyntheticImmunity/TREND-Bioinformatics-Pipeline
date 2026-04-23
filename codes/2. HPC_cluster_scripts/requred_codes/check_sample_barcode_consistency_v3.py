################################################################################
# Script: Lane-wise Barcode Pattern Counting in FASTQ Files (TREND QC Helper)
#
# Purpose:
#   This script scans a set of FASTQ files for internal barcode motifs and counts
#   how many reads in each file contain each pattern. It is primarily intended
#   as a quality control tool to:
#       • check barcode representation across sequencing lanes,
#       • detect under-represented or missing barcodes,
#       • troubleshoot pooling and demultiplexing issues.
#
# Rationale:
#   In the TREND workflow, each sample is tagged with an internal index barcode
#   that appears in the read adjacent to a constant RT-handle-like sequence.
#   This script reconstructs the full search motif:
#
#       base_pattern ("CGACCACCTCTGAC") + <barcode>
#
#   and then scans the sequence lines of each FASTQ record for these motifs.
#   Counts are aggregated per FASTQ file and organized in a CSV report.
#
# What the Script Does:
#   1. Reads a CSV file containing barcode/index sequences (one per row).
#   2. Prepends a fixed base pattern ("CGACCACCTCTGAC") to each barcode.
#   3. Iterates over all FASTQ files in a specified directory.
#   4. Extracts only the sequence line from each 4-line FASTQ record.
#   5. Counts how many reads contain each full motif.
#   6. Parses the lane identifier (e.g., L001, L002) from the filename.
#   7. Builds a Pandas DataFrame summarizing counts per file and per lane.
#   8. Writes the results to a CSV file for downstream inspection.
#
# Inputs:
#   • fastq_directory
#       Path to the folder containing FASTQ files to be analyzed.
#
#   • excel_file_path
#       Path to a CSV file with barcode/index information.
#       The script expects that the barcode is in the first column.
#
#   • output_csv_path
#       Path to the output CSV report containing pattern counts.
#
# FASTQ and Filename Assumptions:
#   • FASTQ files follow the standard 4-line structure:
#         Line 0: Header
#         Line 1: Sequence       <-- searched
#         Line 2: '+'
#         Line 3: Quality
#
#   • Filenames contain a substring of the form:
#         "MW11793-<Lane>_..."
#     where <Lane> encodes lane information (e.g., L001).
#     The function `extract_lane_number()` depends on this pattern.
#
# Environment Requirements:
#   • Python 3.x
#   • pandas installed
#   • FASTQ files accessible on the filesystem (no HPC-specific dependencies)
#
# Notes:
#   • Matching is substring-based: if a motif appears anywhere in the read
#     sequence, it is counted.
#   • The base pattern "CGACCACCTCTGAC" should correspond to the constant region
#     used in your library design; adjust only if using a different construct.
#   • This script is designed as a QC utility and does not replace the full
#     TREND barcode-extraction and activity-quantification pipeline.
################################################################################


import os
import pandas as pd

# Function to read DNA sequences from a FASTQ file
def read_sequences(filepath):
    with open(filepath, 'r') as file:
        return [line.strip() for i, line in enumerate(file) if (i - 1) % 4 == 0]

# Function to count occurrences of patterns in sequences
def count_patterns(sequences, patterns):
    counts = {pattern: 0 for pattern in patterns}
    for seq in sequences:
        for pattern in patterns:
            if pattern in seq:
                counts[pattern] += 1
    return counts

# Read Excel file to get additional patterns
def get_patterns_from_excel(filepath):
    df = pd.read_csv(filepath)
    base_pattern = 'CGACCACCTCTGAC'
    return [base_pattern + str(row[0]).strip() for index, row in df.iterrows()]  # Ensure no leading/trailing spaces

# Extract the L_x information from the filename
def extract_lane_number(filename):
    start = filename.find("MW11793-") + len("MW11793-")
    end = filename.find("_", start)
    return filename[start:end]

# Main processing
def process_fastq_files(directory, excel_path, output_csv):
    patterns = get_patterns_from_excel(excel_path)
    print("Patterns to search:", patterns)  # Debug output to check patterns
    results = []
    
    for filename in os.listdir(directory):
        if filename.endswith('.fastq'):
            lane_number = extract_lane_number(filename)
            file_path = os.path.join(directory, filename)
            sequences = read_sequences(file_path)
            pattern_counts = count_patterns(sequences, patterns)
            pattern_counts = {k.replace('CGACCACCTCTGAC', ''): v for k, v in pattern_counts.items()}  # Remove base pattern from keys
            pattern_counts['Filename'] = filename
            pattern_counts['Lane'] = lane_number
            results.append(pattern_counts)
    
    # Create a DataFrame from the results
    df_results = pd.DataFrame(results)
    df_results.fillna(0, inplace=True)  # Replace any missing values with 0

    # Sort columns based on original index order and by Lane number
    lane_cols = sorted(df_results['Lane'].unique())
    index_order = [p.replace('CGACCACCTCTGAC', '') for p in patterns]
    df_results = df_results[['Filename', 'Lane'] + index_order]
    df_results.columns = ['Filename', 'Lane'] + [col.replace('CGACCACCTCTGAC', '') for col in index_order]  # Clean column names

    # Export to CSV
    df_results.to_csv(output_csv, index=False)

# Set the directory containing FASTQ files and the path to the Excel and output CSV files
fastq_directory = 'E:\\SP038\\first_2500_fastq'
excel_file_path = 'E:\\SP038\\first_2500_fastq\\index_info_for_chat_GPT.csv'
output_csv_path = 'E:\\SP038\\first_2500_fastq\\index_results_v3.csv'

# Run the processing
process_fastq_files(fastq_directory, excel_file_path, output_csv_path)

print(f"Report generated at {output_csv_path}")
