"""trend — TREND enhancer-screening pipeline.

A standalone, installable end-to-end pipeline for the TREND (Transcription-
Factor-Responsive Enhancer Discovery) library. Wraps — never rewrites — the
manuscript's existing scripts.

Public CLI:
    trend init <name> [--template ovarian_cancer|T_cell_activation]
    trend run --inputs <dir> --output <dir> [--profile local|slurm]
    trend dashboard [--runs <dir>] [--port 8000]
    trend status <run_id>

Public Python API (re-exported from the dashboard backend so a single import
gives you the runner, comparator, and provenance writer wherever the pipeline
package is installed):
    from trend import pipeline, oracle, provenance
"""

from __future__ import annotations

__version__ = "0.1.0"


def _bind_dashboard_backend():
    """Make `from trend import pipeline, oracle, provenance` work whether the
    user installed `trend-pipeline` alone or alongside the dashboard backend.

    The implementation lives in dashboard/backend/ today (cwd_shim, runner,
    manifest, comparator). This function adds dashboard/ to sys.path and
    re-exports the relevant submodules under the `trend` namespace, so the
    CLI doesn't have to know which layout is on disk.
    """
    import importlib
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    dashboard_path = repo_root / "dashboard"
    if dashboard_path.exists() and str(dashboard_path) not in sys.path:
        sys.path.insert(0, str(dashboard_path))

    bound: dict[str, object] = {}
    for shortname, modpath in (
        ("pipeline", "backend.pipeline"),
        ("oracle", "backend.oracle"),
        ("provenance", "backend.provenance"),
        ("library", "backend.library"),
        ("preflight", "backend.preflight"),
        ("config", "backend.config"),
    ):
        try:
            bound[shortname] = importlib.import_module(modpath)
        except ImportError:
            pass
    return bound


_bound = _bind_dashboard_backend()
pipeline = _bound.get("pipeline")
oracle = _bound.get("oracle")
provenance = _bound.get("provenance")
library = _bound.get("library")
preflight = _bound.get("preflight")
config = _bound.get("config")
