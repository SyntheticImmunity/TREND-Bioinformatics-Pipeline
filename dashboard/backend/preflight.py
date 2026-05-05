"""FR-2 preflight: detect every external tool and language package the pipeline
needs and produce per-OS install hints when something is missing.

Lives behind /preflight; runs in <5 seconds. Cached for 30 seconds so the Health
page can poll without thrashing subprocesses.
"""

from __future__ import annotations

import importlib.util
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field

from backend import config


@dataclass
class CheckResult:
    name: str
    category: str  # "binary" | "python_package" | "r_package"
    found: bool
    version: str | None = None
    purpose: str = ""
    hint: str = ""
    severity: str = "info"  # "info" | "warning" | "error"


@dataclass
class PreflightReport:
    container_mode: bool
    os_name: str
    os_version: str
    overall: str  # "ok" | "degraded" | "blocked"
    checks: list[CheckResult] = field(default_factory=list)
    summary: str = ""


# Listed in pipeline order (Step 5 → Step 9), with the Python runtime last
# since it underpins everything rather than mapping to a specific step.
_BINARIES = [
    {
        "name": "fastx_collapser",
        "purpose": "Step 5: collapse PCR duplicates by UMI.",
        "version_args": ["-h"],
        "severity_if_missing": "warning",
    },
    {
        "name": "cutadapt",
        "purpose": "Step 6: extract the 20-bp designed barcode by stripping constant flanks.",
        "version_args": ["--version"],
        "severity_if_missing": "warning",
    },
    {
        "name": "bowtie2",
        "purpose": "Step 7: align extracted barcodes to the Lib4 reference.",
        "version_args": ["--version"],
        "severity_if_missing": "warning",
    },
    {
        "name": "samtools",
        "purpose": "Step 8 helper (SAM->BAM conversion via Rsamtools).",
        "version_args": ["--version"],
        "severity_if_missing": "warning",
    },
    {
        "name": "Rscript",
        "purpose": "Step 8 (count tables) and Step 9 (enhancer activity). Required for real runs.",
        "version_args": ["--version"],
        "severity_if_missing": "warning",
    },
    {
        "name": "python",
        "purpose": "Backend runtime; required.",
        "version_args": ["--version"],
        "severity_if_missing": "error",
    },
]


_INSTALL_HINTS = {
    "macos": {
        "Rscript": "brew install r",
        "bowtie2": "brew install bowtie2",
        "samtools": "brew install samtools",
        "cutadapt": "pipx install cutadapt  (or: pip install cutadapt)",
        "fastx_collapser": "brew install fastx_toolkit",
    },
    "linux": {
        "Rscript": "sudo apt-get install r-base",
        "bowtie2": "sudo apt-get install bowtie2",
        "samtools": "sudo apt-get install samtools",
        "cutadapt": "pipx install cutadapt  (or: pip install cutadapt)",
        "fastx_collapser": "sudo apt-get install fastx-toolkit",
    },
    "windows": {
        "Rscript": "Use the Docker container -these bioinformatics tools are not native-Windows-friendly. `cd dashboard && docker compose up`",
        "bowtie2": "Use the Docker container -see canonical path in README.md.",
        "samtools": "Use the Docker container.",
        "cutadapt": "pip install cutadapt  (works on Windows).",
        "fastx_collapser": "Use the Docker container -fastx-toolkit has no Windows build.",
    },
}


# Listed pipeline-step-first (Step 1-3 → analysis-wide), then dashboard
# infrastructure at the bottom. install_name is what `pip install` expects and
# what the user sees in the UI; import_name is what the package actually
# exposes at the Python module level. The two diverge for biopython (installed
# as `biopython`, imported as `Bio`).
_PYTHON_PACKAGES = [
    ("biopython", "Bio", "Demultiplexing and FASTQ parsing in Steps 1-3."),
    ("pandas", "pandas", "Step 1 sample-barcode CSV processing."),
    ("numpy", "numpy", "Comparator and aggregations (used throughout)."),
    ("duckdb", "duckdb", "Library SQLite ingest (one-time)."),
    ("fastapi", "fastapi", "Backend HTTP server."),
]


# All three R packages are used by Steps 8 / 9; tidyverse spans both, the
# others are Step 8 specific.
_R_PACKAGES = [
    ("tidyverse", "Used by both Step 8 and Step 9 R scripts."),
    ("data.table", "Fast CSV ops in Step 8."),
    ("Rsamtools", "SAM->BAM in Step 8 (BiocManager package)."),
]


_cached: tuple[float, PreflightReport] | None = None
_CACHE_SECONDS = 30


def _os_kind() -> str:
    s = platform.system().lower()
    if "darwin" in s:
        return "macos"
    if "linux" in s:
        return "linux"
    if "windows" in s:
        return "windows"
    return "linux"


def _probe_binary(name: str, version_args: list[str]) -> tuple[bool, str | None]:
    binary = shutil.which(name)
    if not binary:
        return False, None

    # fastx_collapser has no --version flag; -h returns the usage line.
    # Conda installs fastx-toolkit 0.0.14, but the binary itself can't report it,
    # so we just confirm presence rather than show the usage banner.
    if name == "fastx_collapser":
        return True, "present"

    try:
        proc = subprocess.run(
            [binary, *version_args],
            capture_output=True, text=True, timeout=5, check=False,
        )
        out = (proc.stdout or proc.stderr).strip()
        if not out:
            return True, "present"
        first = out.splitlines()[0].strip()

        # bowtie2 prints the absolute interpreter path before "version X.Y.Z" —
        # e.g. "/opt/conda/envs/trend/bin/bowtie2-align-s version 2.5.5". Strip
        # the path; show "bowtie2 2.5.5".
        if name == "bowtie2" and " version " in first:
            return True, f"bowtie2 {first.split(' version ', 1)[1].strip()}"

        # cutadapt --version emits the bare version string ("5.2"). Prefix with
        # the tool name so the value reads naturally on its own.
        if name == "cutadapt":
            return True, f"cutadapt {first}"

        return True, first
    except Exception as exc:  # noqa: BLE001 - capture timeout/OS errors uniformly
        return True, f"present (probe failed: {exc})"


def _probe_python_pkg(name: str) -> tuple[bool, str | None]:
    spec = importlib.util.find_spec(name)
    if spec is None:
        return False, None
    try:
        mod = __import__(name)
        version = getattr(mod, "__version__", None)
        return True, version
    except ImportError:
        return True, "present (import failed)"


def _probe_r_pkg(name: str, rscript: str | None) -> tuple[bool, str | None]:
    if not rscript:
        return False, "Rscript missing"
    try:
        proc = subprocess.run(
            [rscript, "-e", f'cat(as.character(packageVersion("{name}")))'],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return True, proc.stdout.strip()
        return False, None
    except Exception:
        return False, None


def run_preflight(force: bool = False) -> PreflightReport:
    global _cached
    now = time.time()
    if _cached and not force and (now - _cached[0]) < _CACHE_SECONDS:
        return _cached[1]

    os_kind = _os_kind()
    hints = _INSTALL_HINTS.get(os_kind, {})
    report = PreflightReport(
        container_mode=config.is_container_mode(),
        os_name=os_kind,
        os_version=platform.platform(),
        overall="ok",
    )
    n_warnings = 0
    n_errors = 0

    for spec in _BINARIES:
        found, version = _probe_binary(spec["name"], spec["version_args"])
        severity = "info" if found else spec["severity_if_missing"]
        if not found:
            if severity == "error":
                n_errors += 1
            elif severity == "warning":
                n_warnings += 1
        report.checks.append(
            CheckResult(
                name=spec["name"],
                category="binary",
                found=found,
                version=version,
                purpose=spec["purpose"],
                hint=hints.get(spec["name"], "") if not found else "",
                severity=severity,
            )
        )

    for install_name, import_name, purpose in _PYTHON_PACKAGES:
        found, version = _probe_python_pkg(import_name)
        severity = "info" if found else "warning"
        if not found:
            n_warnings += 1
        report.checks.append(
            CheckResult(
                name=install_name, category="python_package", found=found, version=version,
                purpose=purpose,
                hint="" if found else f"pip install {install_name}",
                severity=severity,
            )
        )

    rscript = shutil.which("Rscript")
    for pkg, purpose in _R_PACKAGES:
        found, version = _probe_r_pkg(pkg, rscript)
        severity = "info" if found else ("warning" if rscript else "info")
        if not found and rscript:
            n_warnings += 1
        report.checks.append(
            CheckResult(
                name=pkg, category="r_package", found=found, version=version,
                purpose=purpose,
                hint="" if found else (
                    f'R: install.packages("{pkg}")' if pkg != "Rsamtools"
                    else 'R: BiocManager::install("Rsamtools")'
                ),
                severity=severity,
            )
        )

    if n_errors:
        report.overall = "blocked"
    elif n_warnings:
        report.overall = "degraded"
    else:
        report.overall = "ok"

    bits: list[str] = []
    if n_errors:
        bits.append(f"{n_errors} blocker{'s' if n_errors != 1 else ''}")
    if n_warnings:
        bits.append(f"{n_warnings} missing piece{'s' if n_warnings != 1 else ''}")
    report.summary = (
        "All required pieces present. Real pipeline runs are go."
        if report.overall == "ok"
        else "; ".join(bits) + ". " + (
            "Use the Docker container for guaranteed reproducibility."
            if not report.container_mode else "Container is missing tools -rebuild the image."
        )
    )

    _cached = (now, report)
    return report


def report_dict(force: bool = False) -> dict:
    return asdict(run_preflight(force=force))
