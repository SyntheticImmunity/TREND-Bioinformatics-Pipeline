"""Local subprocess pipeline runner with status events.

Reads `steps.yaml` for step contracts; invokes each step's command in the
materialized temp cwd via `cwd_shim.materialize`; captures exit code, runtime,
and stderr tail; writes/updates the run manifest after every step.

Execution modes:
  - 'real': run the actual commands. Requires bowtie2, samtools, cutadapt, etc.
  - 'dry_run': replace each command with a Python stub that touches expected
    output files and exits zero. Used to demo the orchestration UI when the
    bioinformatics toolchain isn't installed (i.e., outside the canonical
    Docker container — the FR-2 preflight flips this automatically).

The runner is yield-based so the SSE endpoint in main.py can stream step
status events to the browser without polling.
"""

from __future__ import annotations

import dataclasses
import logging
import shlex
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from backend import config
from backend.pipeline import cwd_shim
from backend.provenance import manifest as manifest_module
from backend.provenance.manifest import RunManifest, StepRecord, hash_files, write_manifest

log = logging.getLogger("trend.pipeline.runner")

STEPS_YAML = Path(__file__).parent / "steps.yaml"


def load_steps() -> list[dict[str, Any]]:
    """Parse steps.yaml. Returns list of step dicts in declaration order."""
    raw = yaml.safe_load(STEPS_YAML.read_text(encoding="utf-8"))
    return raw["steps"]


def _resolve_command(template: list[str], context: dict[str, str]) -> list[str]:
    """Substitute {placeholders} in command_template tokens."""
    return [tok.format(**context) for tok in template]


def _run_one(cmd: list[str], cwd: Path, *, timeout: float = 600) -> tuple[int, list[str]]:
    """Execute a command, capturing stderr tail (last 50 lines) and exit code."""
    log.info("Running: %s (cwd=%s)", shlex.join(cmd), cwd)
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
    )
    tail = (proc.stderr or "").splitlines()[-50:]
    return proc.returncode, tail


def _ensure_runs_db() -> sqlite3.Connection:
    config.RUNS_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.RUNS_DB)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
          run_id TEXT PRIMARY KEY,
          project TEXT,
          status TEXT,
          mode TEXT,
          created_at TEXT,
          finished_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);
        """
    )
    con.commit()
    return con


def _record_run(run_id: str, project: str, status: str, mode: str, created_at: str, finished_at: str | None) -> None:
    con = _ensure_runs_db()
    try:
        con.execute(
            """
            INSERT INTO runs (run_id, project, status, mode, created_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
              status = excluded.status,
              finished_at = excluded.finished_at
            """,
            (run_id, project, status, mode, created_at, finished_at),
        )
        con.commit()
    finally:
        con.close()


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    """Return recent runs.

    Combines two sources:
      1. The local runs.sqlite (runs the dashboard itself orchestrated).
      2. Any manifest.json files under config.RUNS_DIR (runs produced elsewhere
         by `trend run --output config.RUNS_DIR`, possibly on a remote cluster
         with the directory mounted via SSHFS).

    Source #2 lets the dashboard act as a pure viewer with no execution
    component — Persona C in the user-workflow story.
    """
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []

    if config.RUNS_DB.exists():
        con = sqlite3.connect(config.RUNS_DB)
        con.row_factory = sqlite3.Row
        try:
            for r in con.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall():
                rows.append(dict(r))
                seen.add(r["run_id"])
        finally:
            con.close()

    if config.RUNS_DIR.exists():
        for manifest_path in sorted(
            config.RUNS_DIR.glob("*/manifest.json"), reverse=True
        ):
            run_id = manifest_path.parent.name
            if run_id in seen:
                continue
            try:
                import json
                m = json.loads(manifest_path.read_text(encoding="utf-8"))
                rows.append(
                    {
                        "run_id": run_id,
                        "project": m.get("project", "?"),
                        "status": m.get("status", "?"),
                        "mode": "external",
                        "created_at": m.get("created_at"),
                        "finished_at": m.get("finished_at"),
                    }
                )
                seen.add(run_id)
            except (OSError, ValueError):
                continue
            if len(rows) >= limit:
                break

    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return rows[:limit]


def _dry_run_step(step: dict[str, Any], work_dir: Path) -> tuple[int, list[str]]:
    """Stub a step: touch declared outputs, return zero exit code.

    Used so the /run UI can demo end-to-end orchestration without bowtie2 et al.
    """
    log.info("Dry-running step %s; touching outputs.", step["id"])
    for name in step.get("outputs", []):
        # Only "touch" outputs whose names look like real filenames.
        if "{" in name or "_csvs" in name or "_fastqs" in name or "_files" in name:
            continue
        target = work_dir / Path(name).name
        target.touch()
    time.sleep(0.4)  # let the SSE consumer paint each step distinctly
    return 0, ["[dry-run stub - command not actually executed]"]


def run_pipeline(
    project: str,
    *,
    inputs: dict[str, Path],
    parameters: dict[str, Any] | None = None,
    mode: str = "real",
    step_filter: list[str] | None = None,
) -> Iterator[dict[str, Any]]:
    """Execute the pipeline, yielding status events after every step transition.

    Each yielded event is a serializable dict. The SSE endpoint forwards them as-is.
    """
    if mode not in ("real", "dry_run"):
        raise ValueError(f"unknown mode: {mode}")

    steps = load_steps()
    if step_filter:
        wanted = set(step_filter)
        steps = [s for s in steps if s["id"] in wanted]
        if not steps:
            raise ValueError(f"step_filter {step_filter} matched no steps in steps.yaml")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:6]
    work_dir = cwd_shim.materialize(inputs)
    cwd_shim.assert_safe_path(work_dir)

    manifest = manifest_module.new_manifest(
        run_id=run_id, project=project, work_dir=work_dir, parameters=parameters or {}
    )
    manifest.steps = [
        StepRecord(id=s["id"], name=s["name"], status="pending") for s in steps
    ]
    write_manifest(manifest)
    _record_run(run_id, project, "running", mode, manifest.created_at, None)

    yield {"event": "run_started", "run_id": run_id, "mode": mode, "n_steps": len(steps)}

    failed = False
    for idx, step in enumerate(steps):
        rec = manifest.steps[idx]
        rec.status = "running"
        rec.started_at = datetime.now(timezone.utc).isoformat()
        rec.inputs = hash_files(list(inputs.values()))
        write_manifest(manifest)
        yield {
            "event": "step_started",
            "run_id": run_id,
            "step_id": rec.id,
            "step_name": rec.name,
        }

        t0 = time.perf_counter()
        try:
            if mode == "dry_run":
                exit_code, stderr_tail = _dry_run_step(step, work_dir)
            else:
                command_template = step.get("command_template") or []
                if not command_template:
                    raise RuntimeError(f"Step {rec.id} has no command_template")
                context = {
                    "codes_root": str(config.CODES_ROOT),
                    "work_dir": str(work_dir),
                    **(parameters or {}),
                }
                cmd = _resolve_command(command_template, context)
                exit_code, stderr_tail = _run_one(cmd, work_dir)
        except FileNotFoundError as exc:
            exit_code, stderr_tail = 127, [f"Tool not found: {exc}"]
        except Exception as exc:
            exit_code, stderr_tail = 1, [f"Runner error: {exc}"]

        rec.finished_at = datetime.now(timezone.utc).isoformat()
        rec.runtime_seconds = round(time.perf_counter() - t0, 3)
        rec.exit_code = exit_code
        rec.stderr_tail = stderr_tail

        # Hash whatever outputs appeared (real files only — declarative names like
        # 'per_sample_fastqs' are not real basenames).
        produced_paths = [
            work_dir / Path(name).name
            for name in step.get("outputs", [])
            if (work_dir / Path(name).name).exists()
        ]
        rec.outputs = hash_files(produced_paths)
        rec.status = "completed" if exit_code == 0 else "failed"
        write_manifest(manifest)

        yield {
            "event": "step_finished",
            "run_id": run_id,
            "step_id": rec.id,
            "status": rec.status,
            "exit_code": exit_code,
            "runtime_seconds": rec.runtime_seconds,
        }

        if exit_code != 0:
            failed = True
            for later in manifest.steps[idx + 1 :]:
                later.status = "skipped"
            break

    manifest.status = "failed" if failed else "completed"
    manifest.finished_at = datetime.now(timezone.utc).isoformat()
    write_manifest(manifest)

    # Harvest declared real-file outputs into the run's results dir.
    run_outputs_dir = config.RUNS_DIR / run_id / "outputs"
    run_outputs_dir.mkdir(parents=True, exist_ok=True)
    real_outputs: list[str] = []
    for s in steps:
        for name in s.get("outputs", []):
            if "{" not in name and not name.endswith(("_csvs", "_fastqs", "_files")):
                real_outputs.append(Path(name).name)
    cwd_shim.harvest(work_dir, real_outputs, run_outputs_dir)

    # Cleanup tmp work_dir; the manifest + harvested outputs are durable.
    shutil.rmtree(work_dir, ignore_errors=True)

    _record_run(
        run_id, project, manifest.status, mode, manifest.created_at, manifest.finished_at
    )
    yield {"event": "run_finished", "run_id": run_id, "status": manifest.status}


def get_manifest_dict(run_id: str) -> dict[str, Any]:
    """Load the on-disk manifest as a dict (for the API)."""
    m = manifest_module.load_manifest(run_id)
    out = dataclasses.asdict(m)
    return out
