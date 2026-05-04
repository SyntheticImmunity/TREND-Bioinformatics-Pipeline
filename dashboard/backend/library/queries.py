"""Paginated and filtered queries against library.sqlite.

The construct table in the FR-6 viewer paginates 100 rows at a time, optionally
filtered by TF name (case-insensitive prefix), promoter prefix, or PPM name.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from backend import config


@dataclass(frozen=True)
class ConstructRow:
    promoter_name_bc: str
    promoter_name: str
    TFBS_random_bc: str
    TFBS: str
    TF: str
    by_ppm_name: str
    rank: int


@dataclass(frozen=True)
class ConstructPage:
    rows: list[ConstructRow]
    total: int
    offset: int
    limit: int


@contextmanager
def _connect(db_path: Path = config.LIBRARY_DB):
    if not db_path.exists():
        raise FileNotFoundError(
            f"Library database not found at {db_path}. Run `make ingest` first."
        )
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def list_constructs(
    *,
    tf: str | None = None,
    promoter_prefix: str | None = None,
    by_ppm_name: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Path = config.LIBRARY_DB,
) -> ConstructPage:
    """Return a paginated slice of constructs, optionally filtered."""
    limit = max(1, min(limit, 1000))
    offset = max(0, offset)

    where_clauses: list[str] = []
    params: list[object] = []
    if tf:
        where_clauses.append("TF = ?")
        params.append(tf)
    if promoter_prefix:
        where_clauses.append("promoter_name LIKE ?")
        params.append(f"{promoter_prefix}%")
    if by_ppm_name:
        where_clauses.append("by_ppm_name = ?")
        params.append(by_ppm_name)
    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    with _connect(db_path) as con:
        total = con.execute(
            f"SELECT COUNT(*) FROM constructs{where_sql}", params
        ).fetchone()[0]
        rows = con.execute(
            f"""
            SELECT promoter_name_bc, promoter_name, TFBS_random_bc, TFBS, TF, by_ppm_name, rank
              FROM constructs{where_sql}
              ORDER BY TF, promoter_name, promoter_name_bc
              LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()

    return ConstructPage(
        rows=[ConstructRow(**dict(r)) for r in rows],
        total=int(total),
        offset=offset,
        limit=limit,
    )


def _load_summary_classifications() -> dict:
    from backend.library.summary import load_summary
    try:
        return load_summary().get("classifications", {})
    except Exception:
        return {}


def _cacts_tumor_tfs(tumor: str) -> list[str]:
    """Return the upper-case TF names that are CaCTS MTFs for `tumor` AND in TREND."""
    cls = _load_summary_classifications()
    for r in cls.get("cacts_coverage", {}).get("per_tumor", []):
        if r["tumor"] == tumor:
            return [t.upper() for t in r.get("in_tfs", [])]
    return []


def _dalessio_system_tfs(system: str) -> list[str]:
    cls = _load_summary_classifications()
    for r in cls.get("dalessio_coverage", {}).get("per_system", []):
        if r["system"] == system:
            return [t.upper() for t in r.get("in_tfs", [])]
    return []


@dataclass(frozen=True)
class EnhancerRow:
    TF: str
    TF_name_by_PPM: str
    TFBS_sequence: str
    variable_region: str
    by_ppm_name: str
    rank: int
    Lambert_DBD_family: str | None
    Lambert_TF_assessment: str | None
    Lambert_matched: str | None
    n_barcodes: int


@dataclass(frozen=True)
class EnhancerPage:
    rows: list[EnhancerRow]
    total: int
    offset: int
    limit: int


# Whitelist of sortable columns -> SQL expressions. Variable region is sorted
# by length (more useful than the raw 90-120 bp sequence's lexical order).
ENHANCER_SORT_COLUMNS: dict[str, str] = {
    "TF": "TF",
    "TFBS_sequence": "TFBS_sequence",
    "variable_region": "LENGTH(variable_region)",
    "by_ppm_name": "by_ppm_name",
    "rank": "rank",
    "n_barcodes": "n_barcodes",
}


def _build_enhancer_filters(
    *,
    q: str | None,
    tf: str | None,
    tfbs_prefix: str | None,
    by_ppm_name: str | None,
    dbd_family: str | None,
    cacts_tumor: str | None,
    dalessio_system: str | None,
    tf_contains: str | None,
    tfbs_contains: str | None,
    ppm_contains: str | None,
    vr_contains: str | None,
    dbd_contains: str | None,
) -> tuple[str, list[object]]:
    where: list[str] = []
    params: list[object] = []
    if q:
        like = f"%{q}%"
        where.append(
            "(TF LIKE ? OR TFBS_sequence LIKE ? OR by_ppm_name LIKE ? OR variable_region LIKE ?)"
        )
        params.extend([like, like, like, like])
    if tf:
        where.append("TF = ?")
        params.append(tf)
    if tfbs_prefix:
        where.append("TFBS_sequence LIKE ?")
        params.append(f"{tfbs_prefix}%")
    if by_ppm_name:
        where.append("by_ppm_name = ?")
        params.append(by_ppm_name)
    # The classification filters require subselects — we do not denormalize the
    # CaCTS / D'Alessio mappings into the enhancers table, since those mappings
    # change as upstream studies evolve. Subselects against the summary JSON
    # would be expensive; instead we resolve them via a small in-memory list of
    # eligible TFs derived from the summary at request time.
    if dbd_family:
        where.append(
            "by_ppm_name IN (SELECT by_ppm_name FROM enhancer_meta WHERE Lambert_DBD_family = ?)"
        )
        params.append(dbd_family)
    if tf_contains:
        where.append("TF LIKE ?")
        params.append(f"%{tf_contains}%")
    if tfbs_contains:
        where.append("TFBS_sequence LIKE ?")
        params.append(f"%{tfbs_contains}%")
    if ppm_contains:
        where.append("by_ppm_name LIKE ?")
        params.append(f"%{ppm_contains}%")
    if vr_contains:
        where.append("variable_region LIKE ?")
        params.append(f"%{vr_contains}%")
    if dbd_contains:
        where.append("Lambert_DBD_family LIKE ?")
        params.append(f"%{dbd_contains}%")
    if cacts_tumor:
        eligible = _cacts_tumor_tfs(cacts_tumor)
        if eligible:
            placeholders = ",".join("?" * len(eligible))
            where.append(f"UPPER(TF) IN ({placeholders})")
            params.extend(eligible)
        else:
            where.append("0=1")
    if dalessio_system:
        eligible = _dalessio_system_tfs(dalessio_system)
        if eligible:
            placeholders = ",".join("?" * len(eligible))
            where.append(f"UPPER(TF) IN ({placeholders})")
            params.extend(eligible)
        else:
            where.append("0=1")
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    return where_sql, params


def _enhancer_order_sql(sort_by: str, sort_dir: str) -> str:
    sort_expr = ENHANCER_SORT_COLUMNS.get(sort_by, "TF")
    sort_dir_sql = "DESC" if (sort_dir or "").lower() == "desc" else "ASC"
    # Always include a deterministic secondary sort for stable pagination.
    # rank is the immediate secondary so a "sort by TF" naturally groups
    # rank 1, 2, 3 within each TF before falling back to TFBS / PPM tiebreakers.
    return f"ORDER BY {sort_expr} {sort_dir_sql}, TF ASC, rank ASC, TFBS_sequence ASC, by_ppm_name ASC"


def list_enhancers(
    *,
    q: str | None = None,
    tf: str | None = None,
    tfbs_prefix: str | None = None,
    by_ppm_name: str | None = None,
    dbd_family: str | None = None,
    cacts_tumor: str | None = None,
    dalessio_system: str | None = None,
    tf_contains: str | None = None,
    tfbs_contains: str | None = None,
    ppm_contains: str | None = None,
    vr_contains: str | None = None,
    dbd_contains: str | None = None,
    sort_by: str = "TF",
    sort_dir: str = "asc",
    limit: int = 100,
    offset: int = 0,
    db_path: Path = config.LIBRARY_DB,
) -> EnhancerPage:
    """Return a paginated, filterable, sortable slice of enhancers.

    Filters (compose with AND when multiple are supplied):
      q              free-text substring matched across TF, TFBS_sequence,
                     by_ppm_name, and variable_region (case-insensitive).
      tf             exact TF match.
      tfbs_prefix    TFBS_sequence prefix match.
      by_ppm_name    exact PPM identifier.

    Sort:
      sort_by        one of TF, TFBS_sequence, variable_region, by_ppm_name,
                     rank, n_barcodes. Variable region sorts by length.
      sort_dir       'asc' or 'desc'.
    """
    limit = max(1, min(limit, 1000))
    offset = max(0, offset)

    where_sql, params = _build_enhancer_filters(
        q=q, tf=tf, tfbs_prefix=tfbs_prefix, by_ppm_name=by_ppm_name,
        dbd_family=dbd_family, cacts_tumor=cacts_tumor, dalessio_system=dalessio_system,
        tf_contains=tf_contains, tfbs_contains=tfbs_contains, ppm_contains=ppm_contains,
        vr_contains=vr_contains, dbd_contains=dbd_contains,
    )
    order_sql = _enhancer_order_sql(sort_by, sort_dir)

    with _connect(db_path) as con:
        total = con.execute(
            f"SELECT COUNT(*) FROM enhancers{where_sql}", params
        ).fetchone()[0]
        rows = con.execute(
            f"""
            SELECT TF, TF_name_by_PPM, TFBS_sequence, variable_region,
                   by_ppm_name, rank,
                   Lambert_DBD_family, Lambert_TF_assessment, Lambert_matched,
                   n_barcodes
              FROM enhancers{where_sql}
              {order_sql}
              LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()

    return EnhancerPage(
        rows=[EnhancerRow(**dict(r)) for r in rows],
        total=int(total),
        offset=offset,
        limit=limit,
    )


def iter_enhancers_for_export(
    *,
    q: str | None = None,
    tf: str | None = None,
    tfbs_prefix: str | None = None,
    by_ppm_name: str | None = None,
    dbd_family: str | None = None,
    cacts_tumor: str | None = None,
    dalessio_system: str | None = None,
    tf_contains: str | None = None,
    tfbs_contains: str | None = None,
    ppm_contains: str | None = None,
    vr_contains: str | None = None,
    dbd_contains: str | None = None,
    sort_by: str = "TF",
    sort_dir: str = "asc",
    db_path: Path = config.LIBRARY_DB,
):
    """Yield every enhancer row matching the same filters as list_enhancers,
    in the same sort order, with no pagination cap. Used by the CSV export
    endpoint so a download captures the full filtered set, not just a page."""
    where_sql, params = _build_enhancer_filters(
        q=q, tf=tf, tfbs_prefix=tfbs_prefix, by_ppm_name=by_ppm_name,
        dbd_family=dbd_family, cacts_tumor=cacts_tumor, dalessio_system=dalessio_system,
        tf_contains=tf_contains, tfbs_contains=tfbs_contains, ppm_contains=ppm_contains,
        vr_contains=vr_contains, dbd_contains=dbd_contains,
    )
    order_sql = _enhancer_order_sql(sort_by, sort_dir)

    with _connect(db_path) as con:
        cur = con.execute(
            f"""
            SELECT TF, TF_name_by_PPM, TFBS_sequence, variable_region,
                   by_ppm_name, rank,
                   Lambert_DBD_family, Lambert_TF_assessment, Lambert_matched,
                   n_barcodes
              FROM enhancers{where_sql}
              {order_sql}
            """,
            params,
        )
        for row in cur:
            yield EnhancerRow(**dict(row))


def get_construct(identifier: str, db_path: Path = config.LIBRARY_DB) -> dict | None:
    """Return one construct + its enhancer-metadata join row (or None).

    Accepts either a `promoter_name_bc` (the fully-barcoded construct ID used
    throughout Lib4) or a `promoter_name` (the non-barcoded promoter ID that
    appears in the per-promoter result CSVs and the cancer-selective table).
    When given the latter, returns one of the barcoded variants — enough to
    populate the metadata view; per-condition activity is fetched separately
    via the performance endpoint.
    """
    with _connect(db_path) as con:
        row = con.execute(
            "SELECT * FROM constructs WHERE promoter_name_bc = ?",
            (identifier,),
        ).fetchone()
        if row is None:
            row = con.execute(
                "SELECT * FROM constructs WHERE promoter_name = ? LIMIT 1",
                (identifier,),
            ).fetchone()
        if row is None:
            return None
        construct = dict(row)
        meta = con.execute(
            """
            SELECT *
              FROM enhancer_meta
             WHERE by_ppm_name = ? AND rank = ?
             LIMIT 1
            """,
            (construct["by_ppm_name"], construct["rank"]),
        ).fetchone()
    return {"construct": construct, "metadata": dict(meta) if meta else None}
