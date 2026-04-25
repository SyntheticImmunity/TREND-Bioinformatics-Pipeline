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
