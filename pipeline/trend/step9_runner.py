"""Runtime execution of the rendered Step-9 R script.

The flow:
  1. Caller supplies a parsed samplesheet + a run directory that already
     contains alignment_result_normalized_in_house_pipeline.csv and
     alignment_result_unnormalized_in_house_pipeline.csv (produced by
     Snakemake Steps 1-8).
  2. We render the project-specific R template using the samplesheet.
  3. We materialize the design metadata CSV into the run dir alongside the
     alignment CSVs so the R script (which reads relative paths) finds it.
  4. We invoke `Rscript step9_rendered.R` with cwd = run dir. Outputs land
     in the run dir.
  5. Caller decides what to do with THRESHOLDS_DEFAULT marker etc.

This module is invoked from both:
  * `trend run` after Snakemake completes Steps 1-8
  * `trend run --resume <dir> --rerun-from step9` for fast iteration
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .render_step9 import render_step9, thresholds_supplied

log = logging.getLogger("trend.step9_runner")

# Snakemake's Step-8 puts the alignment CSVs in this subdirectory of the work
# dir. Step-9's R script reads them from the cwd (no prefix), so we copy them
# up before invoking R.
_ALIGNMENT_DIR_NAME = "outputs"
_ALIGNMENT_FILES = (
    "alignment_result_normalized_in_house_pipeline.csv",
    "alignment_result_unnormalized_in_house_pipeline.csv",
)
_METADATA_FILENAME = "all_enhancer_metadata_111525.csv"
_RENDERED_R_FILENAME = "step9_rendered.R"
_THRESHOLDS_DEFAULT_MARKER = "THRESHOLDS_DEFAULT"


@dataclass
class Step9Result:
    rc: int
    rendered_path: Path
    output_files: list[Path]
    used_default_thresholds: bool
    log_tail: str


def render_and_run(
    samplesheet: dict[str, Any],
    run_dir: Path,
    metadata_root: Path,
) -> Step9Result:
    """Render the Step-9 R from samplesheet, invoke it in `run_dir`, return result.

    `metadata_root` is the directory containing all_enhancer_metadata_111525.csv
    (typically codes/3. .../required_metadata/).
    """
    run_dir = run_dir.resolve()
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run dir not found: {run_dir}")

    # Surface the alignment CSVs at the cwd the R script will read from.
    aligned_dir = run_dir / _ALIGNMENT_DIR_NAME
    if aligned_dir.is_dir():
        for fn in _ALIGNMENT_FILES:
            src = aligned_dir / fn
            dst = run_dir / fn
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
    for fn in _ALIGNMENT_FILES:
        if not (run_dir / fn).exists():
            raise FileNotFoundError(
                f"required Step-8 output missing in {run_dir}: {fn}"
            )

    # Materialize the design metadata CSV into cwd.
    metadata_src = metadata_root / _METADATA_FILENAME
    if not metadata_src.exists():
        raise FileNotFoundError(
            f"design metadata CSV not found: {metadata_src}"
        )
    shutil.copy2(metadata_src, run_dir / _METADATA_FILENAME)

    # Render the R template and write it to the run dir.
    rendered = render_step9(samplesheet)
    rendered_path = run_dir / _RENDERED_R_FILENAME
    rendered_path.write_text(rendered)

    # Drop or refresh the THRESHOLDS_DEFAULT marker before invoking R.
    used_defaults = not thresholds_supplied(samplesheet)
    marker_path = run_dir / _THRESHOLDS_DEFAULT_MARKER
    if used_defaults:
        marker_path.write_text(
            "This run used the default DNA threshold (3) for one or more samples.\n"
            "Inspect DNA_threshold_for_samples.pdf, edit samplesheet.yaml in this\n"
            "run directory, and re-run with:\n"
            f"    trend run --resume {run_dir} --rerun-from step9\n"
        )
    else:
        marker_path.unlink(missing_ok=True)

    rscript = shutil.which("Rscript")
    if rscript is None:
        raise FileNotFoundError(
            "Rscript not on PATH. Activate the trend conda env or use the Docker image."
        )

    log.info("Invoking %s in %s", _RENDERED_R_FILENAME, run_dir)
    proc = subprocess.run(
        [rscript, str(rendered_path)],
        cwd=run_dir,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    log_tail = proc.stderr[-1500:] if proc.stderr else proc.stdout[-1500:]
    if proc.returncode != 0:
        log.warning(
            "Rscript exit %s; stderr tail: %s",
            proc.returncode, log_tail,
        )

    # Discover what the R produced (filenames depend on project).
    output_files = sorted(p for p in run_dir.glob("*_sensor_activity_result_*.csv"))

    return Step9Result(
        rc=proc.returncode,
        rendered_path=rendered_path,
        output_files=output_files,
        used_default_thresholds=used_defaults,
        log_tail=log_tail,
    )


def save_samplesheet_copy(samplesheet_path: Path, run_dir: Path) -> Path:
    """Drop a copy of the user's samplesheet into the run dir for later editing.

    Idempotent — if the source already lives in the run dir (as it does on
    a `--rerun-from step9` invocation), the copy is skipped.
    """
    dst = run_dir / "samplesheet.yaml"
    if samplesheet_path.resolve() == dst.resolve():
        return dst
    shutil.copy2(samplesheet_path, dst)
    return dst
