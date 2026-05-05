# Fetch large data files from this repository's GitHub release and place them
# where the pipeline and R scripts expect them. Safe to re-run — skips files
# that are already present. Windows PowerShell version of scripts/download_data.sh.
#
# Usage:
#   pwsh scripts/download_data.ps1            # download what's missing
#   pwsh scripts/download_data.ps1 -Check     # report what's present, don't download
#
# Total download is ~3 GB. Allow 10-20 minutes on a fast connection.

[CmdletBinding()]
param(
    [switch]$Check
)

$ErrorActionPreference = "Stop"

$ReleaseTag = "library-data-2026-05-04"
$ReleaseBase = "https://github.com/SyntheticImmunity/TREND-Bioinformatics-Pipeline/releases/download/$ReleaseTag"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

# target path (in the repo) → release asset name on the GitHub release.
# Project-prefixed assets ('ovarian_cancer__...', 'T_cell_activation__...') live
# on the release under those names because release assets share a flat namespace;
# the prefix is dropped on placement so the R script finds the file at its
# canonical path.
$Files = [ordered]@{
    "codes/2. HPC_cluster_scripts/required_metadata/Lib4.fasta" = "Lib4.fasta"
    "codes/2. HPC_cluster_scripts/required_metadata/Lib4_info_concise_060621.csv" = "Lib4_info_concise_060621.csv"
    "project_data/alignment_results/ovarian_cancer/alignment_result_normalized_in_house_pipeline.csv" = "ovarian_cancer__alignment_result_normalized_in_house_pipeline.csv"
    "project_data/alignment_results/ovarian_cancer/alignment_result_unnormalized_in_house_pipeline.csv" = "ovarian_cancer__alignment_result_unnormalized_in_house_pipeline.csv"
    "project_data/alignment_results/T_cell_activation/alignment_result_normalized_in_house_pipeline.csv" = "T_cell_activation__alignment_result_normalized_in_house_pipeline.csv"
    "project_data/alignment_results/T_cell_activation/alignment_result_unnormalized_in_house_pipeline.csv" = "T_cell_activation__alignment_result_unnormalized_in_house_pipeline.csv"
}

function Report-Status {
    Write-Host "=== Data file status ==="
    $missing = 0
    foreach ($target in $Files.Keys) {
        if (Test-Path $target) {
            $size = "{0:N1} MB" -f ((Get-Item $target).Length / 1MB)
            Write-Host ("  [OK]      {0,-100}  {1}" -f $target, $size)
        } else {
            Write-Host "  [MISSING] $target"
            $missing++
        }
    }
    return $missing
}

$missing = Report-Status

if ($Check) {
    if ($missing -eq 0) { exit 0 } else { exit 1 }
}

if ($missing -eq 0) {
    Write-Host "All data files already present. Nothing to do."
    exit 0
}

Write-Host ""
Write-Host "=== Fetching from GitHub release $ReleaseTag ==="
$placed = 0
foreach ($entry in $Files.GetEnumerator()) {
    $target = $entry.Key
    if (Test-Path $target) {
        continue
    }
    $asset = $entry.Value
    $url = "$ReleaseBase/$asset"
    $targetDir = Split-Path $target -Parent
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    Write-Host ""
    Write-Host "  -> $asset"
    Write-Host "     $target"
    Invoke-WebRequest -Uri $url -OutFile $target
    $placed++
}

Write-Host ""
Write-Host "=== Done — placed $placed files ==="
Report-Status | Out-Null
