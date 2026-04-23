"""Tests for the trend CLI: parser shape, init scaffolding, status, --example."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# The CLI lives in pipeline/trend/cli.py. Add pipeline/ to sys.path so
# `import trend.cli` works without requiring `pip install -e pipeline/`.
PIPELINE_DIR = Path(__file__).resolve().parents[2] / "pipeline"
sys.path.insert(0, str(PIPELINE_DIR))

from trend import cli  # noqa: E402


def test_parser_has_all_subcommands():
    parser = cli.build_parser()
    actions = [a for a in parser._actions if hasattr(a, "choices") and a.choices]
    subparsers_action = next(a for a in actions if isinstance(a.choices, dict))
    expected = {"init", "run", "dashboard", "status", "preflight"}
    assert expected.issubset(subparsers_action.choices.keys())


def test_init_scaffolds_ovca_template(tmp_path: Path):
    target = tmp_path / "scaffolded"
    rc = cli.main(["init", str(target), "--template", "ovarian_cancer"])
    assert rc == 0
    assert (target / "samplesheet.yaml").exists()
    assert (target / "project.yaml").exists()
    assert (target / "README.md").exists()
    # Sample sheet should reference the published OvCa cell lines.
    content = (target / "samplesheet.yaml").read_text(encoding="utf-8")
    assert "OV8" in content and "IOSE" in content and "ID8" in content


def test_init_scaffolds_tcell_template(tmp_path: Path):
    target = tmp_path / "tcell"
    rc = cli.main(["init", str(target), "--template", "T_cell_activation"])
    assert rc == 0
    content = (target / "samplesheet.yaml").read_text(encoding="utf-8")
    assert "rest_r1" in content and "stim_r1" in content


def test_init_unknown_template_fails(tmp_path: Path, capsys):
    target = tmp_path / "broken"
    rc = cli.main(["init", str(target), "--template", "does_not_exist"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "unknown template" in err


def test_init_refuses_nonempty_directory(tmp_path: Path, capsys):
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "preexisting.txt").write_text("hi")
    rc = cli.main(["init", str(target), "--template", "ovarian_cancer"])
    assert rc == 2
    assert "exists and is not empty" in capsys.readouterr().err


def test_run_example_ovca_green(capsys):
    """End-to-end: trend run --example ovarian_cancer should pass via the
    bundled comparator (stub mode when R isn't installed)."""
    rc = cli.main(["run", "--example", "ovarian_cancer"])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "overall_pass: True" in captured
    assert "MATCH" in captured


def test_run_example_tcell_green(capsys):
    rc = cli.main(["run", "--example", "T_cell_activation"])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "overall_pass: True" in captured


def test_status_reads_an_existing_manifest(tmp_path: Path, capsys):
    runs_dir = tmp_path / "runs"
    run_id = "test-run-abc"
    (runs_dir / run_id).mkdir(parents=True)
    (runs_dir / run_id / "manifest.json").write_text(json.dumps({
        "run_id": run_id,
        "project": "ovarian_cancer",
        "status": "completed",
        "created_at": "2026-04-23T10:00:00+00:00",
        "finished_at": "2026-04-23T10:30:00+00:00",
        "work_dir": "/tmp/work",
        "software": {"R": "3.5.1", "bowtie2": "2.3.4.3"},
        "steps": [
            {"id": "step_2_flip_orientation", "status": "completed", "exit_code": 0, "runtime_seconds": 12.3},
            {"id": "step_7_align_barcodes", "status": "completed", "exit_code": 0, "runtime_seconds": 45.6},
        ],
    }))
    rc = cli.main(["status", run_id, "--runs-dir", str(runs_dir)])
    out = capsys.readouterr().out
    assert rc == 0
    assert run_id in out
    assert "ovarian_cancer" in out
    assert "step_7_align_barcodes" in out
    assert "R" in out


def test_status_missing_manifest_errors(tmp_path: Path, capsys):
    rc = cli.main(["status", "nonexistent-run", "--runs-dir", str(tmp_path)])
    assert rc == 2
    assert "manifest not found" in capsys.readouterr().err
