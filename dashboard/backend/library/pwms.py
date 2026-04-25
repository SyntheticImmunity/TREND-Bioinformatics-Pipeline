"""Parse the ENCODE/MotifDb PPM file into an in-memory dict for the frontend.

File format (one motif per record):
    >NAME description...
    a_p0 a_p1 a_p2 ... a_pW
    c_p0 c_p1 c_p2 ... c_pW
    g_p0 g_p1 g_p2 ... g_pW
    t_p0 t_p1 t_p2 ... t_pW

Rows are A, C, G, T in order (verified against MYC_disc1 → CACGTG E-box).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from backend import config


def _parse(path: Path) -> dict[str, list[list[float]]]:
    pwms: dict[str, list[list[float]]] = {}
    name: str | None = None
    rows: list[list[float]] = []
    with path.open() as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name and len(rows) == 4:
                    pwms[name] = rows
                name = line[1:].split()[0]
                rows = []
            else:
                rows.append([float(x) for x in line.split()])
    if name and len(rows) == 4:
        pwms[name] = rows
    return pwms


@lru_cache(maxsize=1)
def load_pwms() -> dict[str, list[list[float]]]:
    """Return all PPMs as {name: [[A...], [C...], [G...], [T...]]}.

    Cached for the lifetime of the process; the source file is ~3.6 MB and
    parses in well under a second.
    """
    if not config.PWM_FILE.exists():
        return {}
    return _parse(config.PWM_FILE)
