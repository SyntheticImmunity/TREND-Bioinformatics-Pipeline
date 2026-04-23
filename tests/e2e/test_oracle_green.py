"""End-to-end test: the FR-4 reviewer oracle returns a green report against
the bundled OvCa published outputs.

In stub mode (no R) the comparator runs against itself - validates the comparator
+ wrapper plumbing. In real mode (Docker container with Rscript) the wrapper
invokes the unchanged R script and the comparator validates *its* output.
Either way, this test must be green for the published OvCa figures.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Repo root on sys.path so backend.* imports resolve from the test runner.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "dashboard"))

from backend.oracle.run_example import run_oracle  # noqa: E402


def test_ovca_oracle_green():
    report = run_oracle("ovarian_cancer")
    assert report.overall_pass, (
        f"OvCa oracle did not pass. Mode={report.mode}. Files: "
        + "; ".join(f"{r['filename']}: {r['summary']}" for r in report.file_results)
    )
    # Both files compared.
    assert {r["filename"] for r in report.file_results} == {
        "ovca_sensor_activity_result_concise.csv",
        "ovca_sensor_activity_result_all.csv",
    }
    # Each file should report a non-trivial row count in its summary string.
    for r in report.file_results:
        assert "57715" in r["summary"], r["summary"]


def test_tcell_oracle_green():
    report = run_oracle("T_cell_activation")
    assert report.overall_pass, (
        f"T-cell oracle did not pass. Mode={report.mode}. Files: "
        + "; ".join(f"{r['filename']}: {r['summary']}" for r in report.file_results)
    )
