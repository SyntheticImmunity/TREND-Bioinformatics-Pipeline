"""SHA-256 helpers for provenance manifests."""

from __future__ import annotations

import hashlib
from pathlib import Path

CHUNK = 1 << 20  # 1 MiB


def sha256_file(path: Path) -> str:
    """Stream a file through SHA-256 in 1 MiB chunks. Memory-stable for large CSVs."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
