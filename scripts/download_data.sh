#!/usr/bin/env bash
# Download the large data files from Dropbox and place them where the dashboard
# and pipeline expect them. Safe to re-run — skips files that are already in
# place and verified.
#
# Usage:
#   bash scripts/download_data.sh           # download + auto-place
#   bash scripts/download_data.sh --check   # report what's present, don't download
#
# Total download is ~3 GB. Allow 10-20 minutes on a fast connection.

set -euo pipefail

DROPBOX_URL="https://www.dropbox.com/scl/fo/39jvyy6kjho2nyqo59h6e/AHRDQEU4H6NAR85AP99_UDU?rlkey=rcihdns29sfx69930bz5pbjug&dl=1"
DOWNLOAD_DIR="data_download"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Files this script must end up placing into the repo.
declare -A EXPECTED_FILES=(
  ["codes/2. HPC_cluster_scripts/required_metadata/Lib4.fasta"]="Lib4.fasta"
  ["codes/2. HPC_cluster_scripts/required_metadata/Lib4_info_concise_060621.csv"]="Lib4_info_concise_060621.csv"
  ["project_data/alignment_results/ovarian_cancer/alignment_result_normalized_in_house_pipeline.csv"]="alignment_result_normalized_in_house_pipeline.csv"
  ["project_data/alignment_results/ovarian_cancer/alignment_result_unnormalized_in_house_pipeline.csv"]="alignment_result_unnormalized_in_house_pipeline.csv"
  ["project_data/alignment_results/T_cell_activation/alignment_result_normalized_in_house_pipeline..csv"]="alignment_result_normalized_in_house_pipeline..csv"
  ["project_data/alignment_results/T_cell_activation/alignment_result_unnormalized_in_house_pipeline.csv"]="alignment_result_unnormalized_in_house_pipeline.csv"
)

# --- Step 1: report what's already present ------------------------------------
report_status() {
  local missing=0
  echo "=== Data file status ==="
  for target in "${!EXPECTED_FILES[@]}"; do
    if [[ -f "$target" ]]; then
      size=$(du -h "$target" | cut -f1)
      printf "  [OK]      %-100s  %s\n" "$target" "$size"
    else
      printf "  [MISSING] %s\n" "$target"
      missing=$((missing + 1))
    fi
  done
  return $missing
}

if [[ "${1:-}" == "--check" ]]; then
  if report_status; then
    echo "All data files present. Nothing to download."
    exit 0
  else
    echo "$? files missing. Re-run without --check to download."
    exit 1
  fi
fi

if report_status; then
  echo "All data files already present. Nothing to do."
  exit 0
fi

# --- Step 2: download the Dropbox folder as a zip -----------------------------
mkdir -p "$DOWNLOAD_DIR"
ZIP_PATH="$DOWNLOAD_DIR/trend_data.zip"

if [[ ! -f "$ZIP_PATH" ]]; then
  echo
  echo "=== Downloading from Dropbox (~3 GB) ==="
  echo "  This will take 10-20 minutes on a fast connection."
  echo "  Source: $DROPBOX_URL"
  echo
  if command -v curl >/dev/null 2>&1; then
    curl -L --progress-bar -o "$ZIP_PATH" "$DROPBOX_URL"
  elif command -v wget >/dev/null 2>&1; then
    wget --show-progress -O "$ZIP_PATH" "$DROPBOX_URL"
  else
    echo "ERROR: neither curl nor wget is installed."
    echo "Manual fallback: open this URL in your browser, save the zip to $ZIP_PATH, and re-run:"
    echo "  $DROPBOX_URL"
    exit 1
  fi
else
  echo "Using cached download at $ZIP_PATH"
fi

# --- Step 3: extract --------------------------------------------------------
echo
echo "=== Extracting ==="
EXTRACT_DIR="$DOWNLOAD_DIR/extracted"
mkdir -p "$EXTRACT_DIR"
if command -v unzip >/dev/null 2>&1; then
  unzip -q -o "$ZIP_PATH" -d "$EXTRACT_DIR"
else
  echo "ERROR: unzip is not installed."
  echo "On Linux/macOS: install with your package manager (apt install unzip / brew install unzip)."
  echo "On Windows: use 7-Zip or right-click → Extract All on $ZIP_PATH, then re-run with --check."
  exit 1
fi

# --- Step 4: place files into the repo ----------------------------------------
echo
echo "=== Placing files into the repo ==="
placed=0
for target in "${!EXPECTED_FILES[@]}"; do
  filename="${EXPECTED_FILES[$target]}"
  # Look for the file anywhere under the extract directory.
  src=$(find "$EXTRACT_DIR" -type f -name "$filename" 2>/dev/null | head -1)
  if [[ -z "$src" ]]; then
    echo "  [WARN]  $filename not found in the downloaded archive"
    continue
  fi
  target_dir=$(dirname "$target")
  mkdir -p "$target_dir"
  cp "$src" "$target"
  placed=$((placed + 1))
  echo "  [OK]    $target"
done

echo
echo "=== Done — placed $placed files ==="
report_status || true
echo
echo "Tip: you can delete the cache to reclaim disk space:"
echo "  rm -rf $DOWNLOAD_DIR"
