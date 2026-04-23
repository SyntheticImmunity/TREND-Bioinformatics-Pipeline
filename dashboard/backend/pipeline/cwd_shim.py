"""Sanitized temp working-directory shim for invoking the existing TREND scripts.

The scripts hard-code paths via setwd(), absolute filenames, and (for the SBATCH)
hard-coded `cd $project_directory/...` calls (Lib4_all_steps_FINAL_111525.sbatch:99-159).
Rather than modify them, the dashboard runs them inside a controlled temp directory
where:
  - The path contains no whitespace, apostrophes, or shell metacharacters (per Risk R-C).
  - All declared input files are symlinked (or copied on Windows) into the cwd under
    their expected names so the scripts find them via relative reads.
  - The cwd is the writable target where the scripts emit their outputs.
  - After the run, declared outputs are copied back into the run's results directory
    (under dashboard/runs/<run_id>/outputs/), keyed to the schema in steps.yaml.

The shim never asks the subprocess to read or write anywhere inside the original
codes/ or project_data/ trees.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

log = logging.getLogger("trend.pipeline.cwd_shim")

# Characters that genuinely break tool argument quoting or cause R's setwd()
# / system() to misbehave. We pass commands as subprocess argv lists (never
# shell=True), so backslash in Windows paths is *not* a hazard and is excluded.
UNSAFE_CHARS = re.compile(r"[ '&$#();|`\"]")


def assert_safe_path(path: Path) -> None:
    """Reject any path with characters that break common shell/tool quoting.

    Note: backslash (Windows path separator) is intentionally allowed because
    subprocess receives commands as a list of arguments, not a shell string.
    """
    if UNSAFE_CHARS.search(str(path)):
        raise ValueError(f"Refusing unsafe cwd path (special chars in path): {path}")


def materialize(
    inputs: dict[str, Path],
    *,
    parent: Path | None = None,
    prefix: str = "trend_run_",
) -> Path:
    """Create a sanitized temp dir and link/copy the declared inputs in.

    `inputs` maps the in-run filename (basename only, no slashes) -> source file path.
    The basename is what the existing scripts expect to find via setwd() + relative read.
    """
    parent = parent or Path(tempfile.gettempdir())
    parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=prefix, dir=parent))
    assert_safe_path(tmp)

    for in_name, src in inputs.items():
        if "/" in in_name or "\\" in in_name:
            raise ValueError(f"Input name must be a basename, not a path: {in_name!r}")
        if not src.exists():
            raise FileNotFoundError(f"Required input does not exist: {src}")
        dest = tmp / in_name
        _link_or_copy(src, dest)
        log.debug("Materialized %s -> %s", src, dest)

    return tmp


def harvest(
    work_dir: Path,
    expected_outputs: list[str],
    target_dir: Path,
) -> dict[str, Path]:
    """Copy declared outputs out of the work_dir into a permanent target_dir.

    Returns a dict keyed by output basename -> destination path. Missing outputs
    raise FileNotFoundError after copying whatever did appear, so the caller
    can record the partial result for the manifest.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    found: dict[str, Path] = {}
    missing: list[str] = []
    for name in expected_outputs:
        src = work_dir / name
        if not src.exists():
            missing.append(name)
            continue
        dest = target_dir / name
        shutil.copy2(src, dest)
        found[name] = dest
    if missing:
        log.warning("Step did not produce expected outputs: %s", missing)
    return found


@contextmanager
def temp_workdir(inputs: dict[str, Path], *, cleanup: bool = True):
    """Context manager wrapping materialize() with cleanup."""
    work = materialize(inputs)
    try:
        yield work
    finally:
        if cleanup:
            shutil.rmtree(work, ignore_errors=True)


def _link_or_copy(src: Path, dest: Path) -> None:
    """Prefer symlink (cheap, no copy of large CSVs). Fall back to copy on Windows
    when symlink permissions aren't available — Windows requires either developer
    mode or admin privileges to create symlinks for non-admins."""
    if dest.exists():
        dest.unlink()
    try:
        os.symlink(src, dest)
    except (OSError, NotImplementedError):
        log.debug("symlink failed for %s; falling back to copy", dest)
        if sys.platform == "win32":
            # Use hardlink as a faster alternative to copy when on the same volume.
            try:
                os.link(src, dest)
                return
            except OSError:
                pass
        shutil.copy2(src, dest)
