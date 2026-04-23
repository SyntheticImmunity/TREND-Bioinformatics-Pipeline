# Download the large data files from Dropbox and place them where the dashboard
# and pipeline expect them. Safe to re-run — skips files that are already in
# place. Windows PowerShell version of scripts/download_data.sh.
#
# Usage:
#   pwsh scripts/download_data.ps1            # download + auto-place
#   pwsh scripts/download_data.ps1 -Check     # report what's present, don't download
#
# Total download is ~3 GB. Allow 10-20 minutes on a fast connection.

[CmdletBinding()]
param(
    [switch]$Check
)

$ErrorActionPreference = "Stop"

$DropboxUrl = "https://www.dropbox.com/scl/fo/39jvyy6kjho2nyqo59h6e/AHRDQEU4H6NAR85AP99_UDU?rlkey=rcihdns29sfx69930bz5pbjug&dl=1"
$DownloadDir = "data_download"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$ExpectedFiles = @{
    "codes/2. HPC_cluster_scripts/required_metadata/Lib4.fasta" = "Lib4.fasta"
    "codes/2. HPC_cluster_scripts/required_metadata/Lib4_info_concise_060621.csv" = "Lib4_info_concise_060621.csv"
    "project_data/alignment_results/ovarian_cancer/alignment_result_normalized_in_house_pipeline.csv" = "alignment_result_normalized_in_house_pipeline.csv"
    "project_data/alignment_results/ovarian_cancer/alignment_result_unnormalized_in_house_pipeline.csv" = "alignment_result_unnormalized_in_house_pipeline.csv"
    "project_data/alignment_results/T_cell_activation/alignment_result_normalized_in_house_pipeline..csv" = "alignment_result_normalized_in_house_pipeline..csv"
    "project_data/alignment_results/T_cell_activation/alignment_result_unnormalized_in_house_pipeline.csv" = "alignment_result_unnormalized_in_house_pipeline.csv"
}

function Report-Status {
    Write-Host "=== Data file status ==="
    $missing = 0
    foreach ($target in $ExpectedFiles.Keys) {
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

# Download
New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null
$ZipPath = Join-Path $DownloadDir "trend_data.zip"

if (-not (Test-Path $ZipPath)) {
    Write-Host ""
    Write-Host "=== Downloading from Dropbox (~3 GB) ==="
    Write-Host "  This will take 10-20 minutes on a fast connection."
    Write-Host "  Source: $DropboxUrl"
    Write-Host ""
    Invoke-WebRequest -Uri $DropboxUrl -OutFile $ZipPath
} else {
    Write-Host "Using cached download at $ZipPath"
}

# Extract
Write-Host ""
Write-Host "=== Extracting ==="
$ExtractDir = Join-Path $DownloadDir "extracted"
New-Item -ItemType Directory -Force -Path $ExtractDir | Out-Null
Expand-Archive -Path $ZipPath -DestinationPath $ExtractDir -Force

# Place files
Write-Host ""
Write-Host "=== Placing files into the repo ==="
$placed = 0
foreach ($entry in $ExpectedFiles.GetEnumerator()) {
    $target = $entry.Key
    $filename = $entry.Value
    $src = Get-ChildItem -Path $ExtractDir -Recurse -Filter $filename -File | Select-Object -First 1
    if (-not $src) {
        Write-Host "  [WARN]  $filename not found in the downloaded archive"
        continue
    }
    $targetDir = Split-Path $target -Parent
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    Copy-Item -Path $src.FullName -Destination $target -Force
    $placed++
    Write-Host "  [OK]    $target"
}

Write-Host ""
Write-Host "=== Done — placed $placed files ==="
Report-Status | Out-Null
Write-Host ""
Write-Host "Tip: you can delete the cache to reclaim disk space:"
Write-Host "  Remove-Item -Recurse -Force $DownloadDir"
