"""Centralized paths and feature flags. Single source of truth so the rest of the
backend never hard-codes a filesystem path."""

from __future__ import annotations

import os
from pathlib import Path

# Repo layout: dashboard/backend/config.py -> repo root is two levels up.
REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_ROOT = REPO_ROOT / "dashboard"

# Existing pipeline assets (read-only, never modified).
CODES_ROOT = REPO_ROOT / "codes"
PROJECT_DATA_ROOT = REPO_ROOT / "project_data"

LIB4_INFO_CSV = (
    CODES_ROOT
    / "2. HPC_cluster_scripts"
    / "required_metadata"
    / "Lib4_info_concise_060621.csv"
)
LIB4_FASTA = (
    CODES_ROOT / "2. HPC_cluster_scripts" / "required_metadata" / "Lib4.fasta"
)
ENHANCER_METADATA_CSV = (
    CODES_ROOT
    / "3. Post_HPC_enhancer_activity_analysis_scripts"
    / "required_metadata"
    / "all_enhancer_metadata_111525.csv"
)
PWM_FILE = REPO_ROOT / "references" / "all_ENCODE_MotifDb_ppm_no_NA_v1.txt"

# Generated runtime state (gitignored).
STATE_DIR = DASHBOARD_ROOT / "backend" / "state"
LIBRARY_DB = STATE_DIR / "library.sqlite"
LIBRARY_SUMMARY_JSON = STATE_DIR / "library_summary.json"
RUNS_DB = STATE_DIR / "runs.sqlite"

# Run manifests live outside state/ because the published_v1 reference manifest
# ships with the repo.
#
# The runs directory is overridable via the TREND_RUNS_DIR environment variable
# so the dashboard can act as a viewer for runs produced by `trend run --output
# /elsewhere/`. This is the seam that lets the dashboard be deployed on a
# laptop pointing at an SSHFS-mounted cluster runs directory (Persona C in
# the user-workflow story).
RUNS_DIR = Path(os.environ.get("TREND_RUNS_DIR") or (DASHBOARD_ROOT / "runs"))

# Project configs (read-only sample sheets in Phase 1).
PROJECTS_DIR = DASHBOARD_ROOT / "projects"

# Equivalence-test fixtures double as the reviewer-oracle example data via symlink.
EXAMPLE_DATA_DIR = DASHBOARD_ROOT / "example_data"

# Frontend bundle (built by `npm run build`; served by FastAPI in container mode).
FRONTEND_DIST = DASHBOARD_ROOT / "frontend" / "dist"


# Feature flags / runtime mode.
def is_container_mode() -> bool:
    return os.environ.get("TREND_DASHBOARD_MODE") == "container"


# Equivalence tolerances - shared between FR-4 oracle and C2 tests.
DEFAULT_RTOL = 1e-6
DEFAULT_ATOL = 1e-9


# ---------------------------------------------------------------------------
# Internal-only projects (unpublished lab data).
#
# The manuscript deployment (public GitHub repo + Docker image) ships only the
# ovarian_cancer and T_cell_activation screens. Additional lab screens whose
# data is unpublished are registered from this side file, which is gitignored
# AND dockerignored: present in the lab's local build, absent from any public
# artifact. Their result CSVs live under project_data/ and are excluded the same
# way. Committed source never names those projects, so the public repo carries
# no trace of them.
# ---------------------------------------------------------------------------
INTERNAL_PROJECTS_FILE = DASHBOARD_ROOT / "backend" / "internal_projects.json"


def public_only() -> bool:
    """Force public (manuscript-only) mode even when internal data is present on
    disk. Lets the lab preview exactly what the deployed build will serve before
    pushing. Enable with TREND_PUBLIC_ONLY=1."""
    return os.environ.get("TREND_PUBLIC_ONLY", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _read_internal_projects() -> dict:
    """Parse the internal-projects side file, or return {} if it is absent or
    unreadable (the expected state in a public deployment)."""
    import json

    if not INTERNAL_PROJECTS_FILE.exists():
        return {}
    try:
        data = json.loads(INTERNAL_PROJECTS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    # Keep only real project entries: a dict value, non-underscore key (so
    # documentation keys like "_comment" are ignored).
    return {
        name: cfg
        for name, cfg in data.items()
        if isinstance(cfg, dict) and not name.startswith("_")
    }


def internal_project_names() -> frozenset[str]:
    """Names of internal-only projects declared in the side file. Empty in a
    public deploy, where the file does not exist."""
    return frozenset(_read_internal_projects().keys())


def load_internal_selectivity_projects() -> dict:
    """Strip-plot/selection configs for the internal-only projects. Empty when
    the side file is absent (public deploy) or when public_only() is forced."""
    if public_only():
        return {}
    return _read_internal_projects()
