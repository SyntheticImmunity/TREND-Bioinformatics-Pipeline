"""One-shot ingest of TREND library metadata into SQLite + a precomputed summary JSON.

Two source CSVs feed the library viewer:

  Lib4_info_concise_060621.csv          ~2.73M rows (one per designed barcode-construct)
  all_enhancer_metadata_111525.csv      ~58K   rows (one per (TFBS, TF, rank), richly annotated)

DuckDB ingests both efficiently into a single SQLite file; aggregates needed by the
FR-6 summary cards / histograms / stacked bar are precomputed once and serialized so
the API can serve them without hitting SQLite at all.

Idempotent: skips work if outputs are newer than inputs (mtime check).

CLI:
    python -m backend.library.ingest \
        --lib4-info /path/Lib4_info_concise_060621.csv \
        --enhancer-meta /path/all_enhancer_metadata_111525.csv \
        --library-db backend/state/library.sqlite \
        --library-summary backend/state/library_summary.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import duckdb

from backend import config
from backend.library import classifications as _classifications

log = logging.getLogger("trend.library.ingest")


# Histogram bins for barcodes-per-promoter; 40 bins covers the typical TREND library.
BARCODES_PER_PROMOTER_BINS = 40


def needs_rebuild(inputs: list[Path], outputs: list[Path]) -> bool:
    """Return True if any output is missing or older than any input."""
    if not all(p.exists() for p in outputs):
        return True
    oldest_output = min(p.stat().st_mtime for p in outputs)
    newest_input = max(p.stat().st_mtime for p in inputs)
    return newest_input > oldest_output


def ingest(
    lib4_info_csv: Path,
    enhancer_meta_csv: Path,
    library_db: Path,
    library_summary: Path,
    *,
    force: bool = False,
) -> dict:
    """Build library.sqlite + library_summary.json. Return the summary dict."""
    inputs = [lib4_info_csv, enhancer_meta_csv]
    outputs = [library_db, library_summary]

    for src in inputs:
        if not src.exists():
            raise FileNotFoundError(
                f"Required source CSV missing: {src}. "
                "Has the TREND repo been cloned with metadata intact?"
            )

    if not force and not needs_rebuild(inputs, outputs):
        log.info("Library is up to date; skipping ingest. Use --force to rebuild.")
        return json.loads(library_summary.read_text(encoding="utf-8"))

    library_db.parent.mkdir(parents=True, exist_ok=True)

    # If the SQLite file already exists, drop it before ATTACH so we get a clean rebuild
    # (DuckDB's sqlite extension appends, doesn't replace).
    if library_db.exists():
        library_db.unlink()

    log.info("Starting ingest via DuckDB.")
    t0 = time.perf_counter()

    con = duckdb.connect(":memory:")
    con.execute("INSTALL sqlite; LOAD sqlite;")

    # Load both CSVs into DuckDB tables. read_csv_auto handles the quoted Lib4 file
    # and the unquoted enhancer-metadata file uniformly.
    con.execute(
        f"CREATE TABLE constructs AS SELECT * FROM read_csv_auto('{lib4_info_csv.as_posix()}', "
        "header=true, sample_size=-1)"
    )
    con.execute(
        f"CREATE TABLE enhancer_meta AS SELECT * FROM read_csv_auto('{enhancer_meta_csv.as_posix()}', "
        "header=true, sample_size=-1)"
    )

    n_constructs = con.execute("SELECT COUNT(*) FROM constructs").fetchone()[0]
    n_meta = con.execute("SELECT COUNT(*) FROM enhancer_meta").fetchone()[0]
    log.info("Loaded %s constructs and %s enhancer-metadata rows.", n_constructs, n_meta)

    # Build summary aggregates while we're still in DuckDB (much faster than SQLite).
    summary = build_summary(con)

    # Materialize a third table at the *enhancer* level: one row per designed
    # enhancer (collapsing the barcode dimension), with n_barcodes attached so
    # the enhancer table can paginate at sub-50ms latency without joining
    # 57K x 2.7M rows on every page request. Includes the Lambert taxonomy
    # columns so the enhancer table can show DBD family + TF assessment.
    con.execute(
        """
        CREATE TABLE enhancers AS
        SELECT
            em.TF_name_human_curated      AS TF,
            em.TF_name_by_PPM             AS TF_name_by_PPM,
            em.TFBS_sequence              AS TFBS_sequence,
            em.variable_region            AS variable_region,
            em.by_ppm_name                AS by_ppm_name,
            em.rank                       AS rank,
            em.Lambert_DBD_family         AS Lambert_DBD_family,
            em.Lambert_TF_assessment      AS Lambert_TF_assessment,
            em.Lambert_matched            AS Lambert_matched,
            COALESCE(c.n_barcodes, 0)     AS n_barcodes
        FROM enhancer_meta em
        LEFT JOIN (
            SELECT by_ppm_name, rank, COUNT(*) AS n_barcodes
              FROM constructs
             GROUP BY by_ppm_name, rank
        ) c
          ON em.by_ppm_name = c.by_ppm_name
         AND em.rank        = c.rank
        """
    )
    n_enhancers = con.execute("SELECT COUNT(*) FROM enhancers").fetchone()[0]
    log.info("Built enhancer-level table: %s rows.", n_enhancers)

    # Export all three tables to SQLite and add covering indices for the queries
    # the FR-6 enhancer table will issue (TF filter, TFBS prefix, by_ppm_name).
    sqlite_path = library_db.as_posix()
    con.execute(f"ATTACH '{sqlite_path}' AS sqlite_db (TYPE SQLITE)")
    con.execute("CREATE TABLE sqlite_db.constructs AS SELECT * FROM constructs")
    con.execute("CREATE TABLE sqlite_db.enhancer_meta AS SELECT * FROM enhancer_meta")
    con.execute("CREATE TABLE sqlite_db.enhancers AS SELECT * FROM enhancers")
    con.execute("DETACH sqlite_db")
    con.close()

    # Add SQLite indices via sqlite_utils for the user-facing query patterns.
    import sqlite3

    sql_con = sqlite3.connect(library_db)
    try:
        sql_con.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_constructs_tf ON constructs(TF);
            CREATE INDEX IF NOT EXISTS idx_constructs_promoter ON constructs(promoter_name);
            CREATE INDEX IF NOT EXISTS idx_constructs_ppm ON constructs(by_ppm_name);
            CREATE INDEX IF NOT EXISTS idx_constructs_pkbc ON constructs(promoter_name_bc);
            CREATE INDEX IF NOT EXISTS idx_meta_tf_human ON enhancer_meta(TF_name_human_curated);
            CREATE INDEX IF NOT EXISTS idx_meta_tf_ppm ON enhancer_meta(TF_name_by_PPM);
            CREATE INDEX IF NOT EXISTS idx_meta_ppm_rank ON enhancer_meta(by_ppm_name, rank);
            CREATE INDEX IF NOT EXISTS idx_enh_tf ON enhancers(TF);
            CREATE INDEX IF NOT EXISTS idx_enh_tfbs ON enhancers(TFBS_sequence);
            CREATE INDEX IF NOT EXISTS idx_enh_ppm ON enhancers(by_ppm_name);
            """
        )
        sql_con.commit()
    finally:
        sql_con.close()

    # Build classification aggregates (Figure 1 Panels B/C/D/E) from the
    # reference tables in references/. Cheap (~5s); included in every ingest.
    log.info("Building classification aggregates (DBD families, CaCTS, D'Alessio)…")
    summary["classifications"] = _classifications.build_classifications()
    log.info(
        "Classifications: %s/%s DBD bars, %s/%s CaCTS, %s/%s D'Alessio",
        summary["classifications"]["totals"]["n_dbd_families_chart"],
        summary["classifications"]["totals"]["n_dbd_families_total"],
        summary["classifications"]["totals"]["cacts"]["n_in"],
        summary["classifications"]["totals"]["cacts"]["n_total"],
        summary["classifications"]["totals"]["dalessio"]["n_in"],
        summary["classifications"]["totals"]["dalessio"]["n_total"],
    )

    # Persist the summary JSON.
    library_summary.parent.mkdir(parents=True, exist_ok=True)
    library_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    elapsed = time.perf_counter() - t0
    log.info("Ingest complete in %.1fs. SQLite: %s, summary: %s", elapsed, library_db, library_summary)
    return summary


def build_summary(con: duckdb.DuckDBPyConnection) -> dict:
    """Compute the FR-6 summary aggregates from an in-memory DuckDB connection
    that already has `constructs` and `enhancer_meta` tables loaded."""

    total_constructs = con.execute("SELECT COUNT(*) FROM constructs").fetchone()[0]
    total_promoters = con.execute("SELECT COUNT(DISTINCT promoter_name) FROM constructs").fetchone()[0]
    total_tfs_lib = con.execute("SELECT COUNT(DISTINCT TF) FROM constructs").fetchone()[0]
    total_tfs_curated = con.execute(
        "SELECT COUNT(DISTINCT TF_name_human_curated) FROM enhancer_meta "
        "WHERE TF_name_human_curated IS NOT NULL AND TF_name_human_curated != ''"
    ).fetchone()[0]
    total_variable_regions = con.execute(
        "SELECT COUNT(DISTINCT variable_region) FROM enhancer_meta"
    ).fetchone()[0]

    # Histogram: barcodes per promoter, 40 bins, linear scale on [1, max].
    bcs_per_promoter = con.execute(
        "SELECT COUNT(*) AS n FROM constructs GROUP BY promoter_name"
    ).fetchall()
    counts = [row[0] for row in bcs_per_promoter]
    histogram = _histogram(counts, BARCODES_PER_PROMOTER_BINS)

    # Median is more robust than mean here because the barcode-count distribution
    # has a long right tail (a few promoters are heavily covered, most aren't).
    counts_sorted = sorted(counts)
    n = len(counts_sorted)
    if n == 0:
        median_barcodes_per_promoter = 0.0
    elif n % 2:
        median_barcodes_per_promoter = float(counts_sorted[n // 2])
    else:
        median_barcodes_per_promoter = (
            counts_sorted[n // 2 - 1] + counts_sorted[n // 2]
        ) / 2.0
    mean_barcodes_per_promoter = (
        total_constructs / total_promoters if total_promoters else 0.0
    )

    # Top-20 chart: enhancers per TF (collapsing the multibarcode dimension).
    # An enhancer is one row of enhancer_meta — one (TFBS, TF, by_ppm_name, rank)
    # combination — so this counts unique designs per TF, not barcodes.
    enhancers_per_tf_full = con.execute(
        """
        SELECT TF_name_human_curated AS tf, COUNT(*) AS n
          FROM enhancer_meta
         WHERE TF_name_human_curated IS NOT NULL
           AND TF_name_human_curated != ''
         GROUP BY TF_name_human_curated
         ORDER BY n DESC
        """
    ).fetchall()
    top_n = 50
    head = [{"tf": tf, "count": int(n)} for tf, n in enhancers_per_tf_full[:top_n]]
    tail_count = sum(int(n) for _, n in enhancers_per_tf_full[top_n:])
    enhancers_per_tf = head + (
        [{"tf": "Other", "count": tail_count}] if tail_count else []
    )

    # Variable-region length distribution from enhancer_meta.
    vr_lengths = con.execute(
        "SELECT LENGTH(variable_region) AS len FROM enhancer_meta WHERE variable_region IS NOT NULL"
    ).fetchall()
    vr_length_values = [row[0] for row in vr_lengths]
    vr_length_histogram = _histogram(vr_length_values, 30)

    return {
        "schema_version": 2,
        "total_constructs": int(total_constructs),
        "total_promoters": int(total_promoters),
        "total_tfs_in_library": int(total_tfs_lib),
        "total_tfs_curated": int(total_tfs_curated),
        "total_variable_regions": int(total_variable_regions),
        "mean_barcodes_per_promoter": round(mean_barcodes_per_promoter, 3),
        "median_barcodes_per_promoter": round(median_barcodes_per_promoter, 1),
        "barcodes_per_promoter_histogram": histogram,
        # Schema v2: enhancers_per_tf replaces constructs_per_tf for the top-20
        # chart. constructs_per_tf retained under its old key for back-compat;
        # consumers should prefer enhancers_per_tf.
        "enhancers_per_tf": enhancers_per_tf,
        "constructs_per_tf": enhancers_per_tf,  # alias: same shape, different semantics
        "variable_region_length_histogram": vr_length_histogram,
    }


def _histogram(values: list[int], n_bins: int) -> dict:
    """Linear-bin histogram. Returns {bin_edges: [...], counts: [...]}."""
    if not values:
        return {"bin_edges": [], "counts": []}
    lo, hi = min(values), max(values)
    if lo == hi:
        return {"bin_edges": [lo, hi + 1], "counts": [len(values)]}
    width = (hi - lo) / n_bins
    edges = [lo + i * width for i in range(n_bins + 1)]
    edges[-1] = hi  # absorb floating-point drift on the right edge
    counts = [0] * n_bins
    for v in values:
        # Map v onto a bin index in [0, n_bins-1].
        idx = int((v - lo) / width) if width else 0
        if idx >= n_bins:
            idx = n_bins - 1
        counts[idx] += 1
    return {"bin_edges": edges, "counts": counts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--lib4-info", type=Path, default=config.LIB4_INFO_CSV)
    parser.add_argument("--enhancer-meta", type=Path, default=config.ENHANCER_METADATA_CSV)
    parser.add_argument("--library-db", type=Path, default=config.LIBRARY_DB)
    parser.add_argument("--library-summary", type=Path, default=config.LIBRARY_SUMMARY_JSON)
    parser.add_argument("--force", action="store_true", help="Rebuild even if outputs are fresh.")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    summary = ingest(
        lib4_info_csv=args.lib4_info,
        enhancer_meta_csv=args.enhancer_meta,
        library_db=args.library_db,
        library_summary=args.library_summary,
        force=args.force,
    )
    print(json.dumps({k: v for k, v in summary.items() if not isinstance(v, dict | list)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
