"""Plain-language failure classifier (FR-9).

Loads error_hints.yaml once and exposes `classify(stderr_tail)` -> hint dict.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

HINTS_YAML = Path(__file__).parent / "error_hints.yaml"


@lru_cache(maxsize=1)
def _rules() -> list[dict[str, Any]]:
    raw = yaml.safe_load(HINTS_YAML.read_text(encoding="utf-8"))
    rules = raw.get("rules", [])
    for r in rules:
        r["_compiled"] = re.compile(r["pattern"], re.IGNORECASE | re.MULTILINE)
    return rules


def classify(stderr: list[str] | str) -> dict[str, str]:
    """Match the first applicable rule. Always returns a dict — the catch-all
    rule at the end of the YAML guarantees a hint even for unfamiliar errors."""
    text = "\n".join(stderr) if isinstance(stderr, list) else (stderr or "")
    for rule in _rules():
        if rule["_compiled"].search(text):
            return {
                "rule_id": rule["id"],
                "headline": rule["headline"],
                "action": rule["action"].strip(),
            }
    return {
        "rule_id": "unclassified",
        "headline": "Step failed.",
        "action": "Inspect the manifest for the full stderr.",
    }
