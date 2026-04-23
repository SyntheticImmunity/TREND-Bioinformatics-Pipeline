"""Loader for the precomputed library_summary.json.

The summary is read once on first request and cached in process memory; subsequent
requests serve from cache without touching disk. `make ingest` is the way to refresh.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from backend import config


class SummaryNotBuilt(RuntimeError):
    """Raised when /library/summary is requested but `make ingest` hasn't run."""


@lru_cache(maxsize=1)
def load_summary(path: Path = config.LIBRARY_SUMMARY_JSON) -> dict:
    if not path.exists():
        raise SummaryNotBuilt(
            f"Library summary not found at {path}. Run `make ingest` first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def reset_cache() -> None:
    """Test hook to drop the cached summary (e.g., after rebuild during tests)."""
    load_summary.cache_clear()
