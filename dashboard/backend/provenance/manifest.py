"""Per-run provenance manifests (FR-5).

Each pipeline run writes a `dashboard/runs/<run_id>/manifest.json` that captures
*everything* a third party would need to reproduce or audit the run:
  - run id, ISO timestamp, total runtime
  - software versions (Python, R, key tools)
  - per-step exit code and runtime
  - SHA-256 of every declared input file and every produced output
  - the parameter set / project config snapshot

The manifest is the durable artifact; the FastAPI run-history list reads from
the manifest files (and a SQLite index for fast queries).
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend import config
from backend.provenance.hashes import sha256_file


@dataclass
class StepRecord:
    id: str
    name: str
    status: str  # pending | running | completed | failed | skipped
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    runtime_seconds: float | None = None
    stderr_tail: list[str] = field(default_factory=list)
    inputs: dict[str, str] = field(default_factory=dict)   # path -> sha256
    outputs: dict[str, str] = field(default_factory=dict)  # path -> sha256


@dataclass
class RunManifest:
    run_id: str
    project: str
    created_at: str
    finished_at: str | None
    status: str  # running | completed | failed
    dashboard_version: str
    software: dict[str, str]
    parameters: dict[str, Any]
    work_dir: str
    steps: list[StepRecord] = field(default_factory=list)


def _detect_software_versions() -> dict[str, str]:
    """Best-effort version capture for the tools in the pipeline path."""
    versions: dict[str, str] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    for tool in ("R", "Rscript", "bowtie2", "samtools", "cutadapt", "fastx_collapser"):
        binary = shutil.which(tool)
        if not binary:
            versions[tool] = "missing"
            continue
        try:
            # Each tool reports version differently; capture the first non-empty line.
            for arg in (("--version",), ("-v",)):
                proc = subprocess.run(
                    [binary, *arg], capture_output=True, text=True, timeout=5
                )
                output = (proc.stdout or proc.stderr).strip()
                if output:
                    versions[tool] = output.splitlines()[0].strip()
                    break
            else:
                versions[tool] = "present (version unparsed)"
        except (subprocess.TimeoutExpired, OSError) as exc:
            versions[tool] = f"present (probe failed: {exc})"
    return versions


def new_manifest(run_id: str, project: str, work_dir: Path, parameters: dict[str, Any]) -> RunManifest:
    from backend import __version__

    return RunManifest(
        run_id=run_id,
        project=project,
        created_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None,
        status="running",
        dashboard_version=__version__,
        software=_detect_software_versions(),
        parameters=parameters,
        work_dir=str(work_dir),
    )


def hash_files(paths: list[Path]) -> dict[str, str]:
    """Hash a list of files; missing files are skipped (callers tolerate empty inputs)."""
    return {str(p): sha256_file(p) for p in paths if p.exists()}


def write_manifest(manifest: RunManifest, dest: Path | None = None) -> Path:
    target = dest or (config.RUNS_DIR / manifest.run_id / "manifest.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(manifest), indent=2), encoding="utf-8")
    return target


def load_manifest(run_id: str) -> RunManifest:
    path = config.RUNS_DIR / run_id / "manifest.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["steps"] = [StepRecord(**s) for s in raw.get("steps", [])]
    return RunManifest(**raw)
