"""Schema loader. Parses the YAML files in this directory once and exposes a
lookup keyed by filename. Tolerates real-world filename quirks (e.g., the
double-dot CSV in the T-cell folder)."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

SCHEMAS_DIR = Path(__file__).parent

# Real-world quirk: the T-cell normalized CSV ships as ..csv (double dot).
# Loader normalization swaps double dots for single before matching schemas.
_DOUBLE_DOT = re.compile(r"\.\.csv$")


def _normalize_filename(name: str) -> str:
    return _DOUBLE_DOT.sub(".csv", name)


@lru_cache(maxsize=1)
def all_schemas() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for yml in sorted(SCHEMAS_DIR.glob("*.yaml")):
        data = yaml.safe_load(yml.read_text(encoding="utf-8"))
        if not data or "filename" not in data:
            continue
        out[data["filename"]] = data
    return out


def schema_for(filename: str) -> dict[str, Any] | None:
    """Look up a schema by output filename. Glob-style 'donor*' patterns
    in the YAML are matched as Python fnmatch."""
    import fnmatch

    name = _normalize_filename(Path(filename).name)
    schemas = all_schemas()
    if name in schemas:
        return schemas[name]
    for pattern, sch in schemas.items():
        if fnmatch.fnmatch(name, pattern):
            return sch
    return None
