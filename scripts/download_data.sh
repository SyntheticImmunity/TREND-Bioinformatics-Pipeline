#!/usr/bin/env bash
# Fetch large data files from this repository's GitHub release and place them
# where the pipeline and R scripts expect them. Safe to re-run — skips files
# that are already present.
#
# Usage:
#   bash scripts/download_data.sh           # download what's missing
#   bash scripts/download_data.sh --check   # report what's present, don't download
#
# Total download is ~3 GB. Allow 10-20 minutes on a fast connection.

set -euo pipefail

RELEASE_TAG="library-data-2026-05-04"
RELEASE_BASE="https://github.com/SyntheticImmunity/TREND-Bioinformatics-Pipeline/releases/download/${RELEASE_TAG}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# target path (in the repo) → release asset name on the GitHub release.
# Project-prefixed assets ('ovarian_cancer__...', 'T_cell_activation__...') live
# on the release under those names because release assets share a flat namespace;
# the prefix is dropped on placement so the R script finds the file at its
# canonical path.
declare -A FILES=(
  ["codes/2. HPC_cluster_scripts/required_metadata/Lib4.fasta"]="Lib4.fasta"
  ["codes/2. HPC_cluster_scripts/required_metadata/Lib4_info_concise_060621.csv"]="Lib4_info_concise_060621.csv"
  ["project_data/alignment_results/ovarian_cancer/alignment_result_normalized_in_house_pipeline.csv"]="ovarian_cancer__alignment_result_normalized_in_house_pipeline.csv"
  ["project_data/alignment_results/ovarian_cancer/alignment_result_unnormalized_in_house_pipeline.csv"]="ovarian_cancer__alignment_result_unnormalized_in_house_pipeline.csv"
  ["project_data/alignment_results/T_cell_activation/alignment_result_normalized_in_house_pipeline.csv"]="T_cell_activation__alignment_result_normalized_in_house_pipeline.csv"
  ["project_data/alignment_results/T_cell_activation/alignment_result_unnormalized_in_house_pipeline.csv"]="T_cell_activation__alignment_result_unnormalized_in_house_pipeline.csv"
)

report_status() {
  local missing=0
  echo "=== Data file status ==="
  for target in "${!FILES[@]}"; do
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
    miss=$?
    echo "$miss file(s) missing. Re-run without --check to download."
    exit 1
  fi
fi

if report_status; then
  echo "All data files already present. Nothing to do."
  exit 0
fi

if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
  echo "ERROR: neither curl nor wget is installed."
  echo "Install one of them, or download the assets manually from:"
  echo "  https://github.com/SyntheticImmunity/TREND-Bioinformatics-Pipeline/releases/tag/${RELEASE_TAG}"
  exit 1
fi

echo
echo "=== Fetching from GitHub release ${RELEASE_TAG} ==="
placed=0
for target in "${!FILES[@]}"; do
  if [[ -f "$target" ]]; then
    continue
  fi
  asset="${FILES[$target]}"
  url="${RELEASE_BASE}/${asset}"
  target_dir=$(dirname "$target")
  mkdir -p "$target_dir"
  echo
  echo "  → $asset"
  echo "    $target"
  if command -v curl >/dev/null 2>&1; then
    curl -L --fail --progress-bar -o "$target" "$url"
  else
    wget --show-progress -O "$target" "$url"
  fi
  placed=$((placed + 1))
done

echo
echo "=== Done — placed $placed files ==="
report_status || true
