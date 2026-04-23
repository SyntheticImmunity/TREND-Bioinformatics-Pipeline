"""Classification aggregates for Figure 1 panels B, C, D, and E.

Reads three reference tables from `references/`:
  - Reddy Table S6.xlsx          → CaCTS MTFs per TCGA tumor type (Panel D)
  - D'Alessio Table S1.xlsx       → Top-10 specificity-ranked TFs per tissue (Panel E)
  - Table_S2_DAlessio_tissue_system_mapping.csv → Tissue→system mapping (15 systems)
  - Table_S1_Lambert_alias_mapping.csv (optional) → 34 alias-resolved TFs

Plus the existing enhancer_meta CSV for DBD-family TF + sensor counts (Panels B, C).

Emits four serializable dicts that the dashboard caches and serves:
  - dbd_families          → list[{family, n_tfs, n_sensors, color}]
  - cacts_coverage        → list[{tumor, n_total, n_in, n_missing, in_tfs, missing_tfs, pct}]
  - dalessio_coverage     → list[{system, n_total, n_in, n_missing, in_tfs, missing_tfs, pct}]
  - classification_totals → headline {n_classified_tfs, n_cacts_covered, n_cacts_total, ...}
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from backend import config

log = logging.getLogger("trend.library.classifications")

REFERENCES_DIR = config.REPO_ROOT / "references"
REDDY_XLSX = REFERENCES_DIR / "Reddy Table S6.xlsx"
DALESSIO_XLSX = REFERENCES_DIR / "D'Alessio Table S1.xlsx"
TISSUE_SYSTEM_CSV = REFERENCES_DIR / "Table_S2_DAlessio_tissue_system_mapping.csv"
LAMBERT_ALIAS_CSV = REFERENCES_DIR / "Table_S1_Lambert_alias_mapping.csv"

# 27-color categorical palette for DBD families. Distinct hues, design-system warm.
DBD_PALETTE = [
    "#E63946", "#1D7AC9", "#7B5EA7", "#9D5B94", "#F6A623",
    "#B07A3D", "#E45A8A", "#23A88A", "#E8C547", "#7B7B7B",
    "#5E81AC", "#A3A3A3", "#9DBBE0", "#A6C879", "#5E81AC",
    "#1B7F4E", "#3D8A6F", "#79A3D6", "#5C8FB6", "#D7B47A",
    "#C2A878", "#1F5E3A", "#A8845E", "#9CB67E", "#7E8FA8",
    "#5A7B4B", "#3F4E5E",
]


def _load_enhancer_meta() -> pd.DataFrame:
    return pd.read_csv(config.ENHANCER_METADATA_CSV, low_memory=False)


def _trend_tfs(em: pd.DataFrame) -> set[str]:
    """Set of TFs present in the TREND library, upper-cased for case-insensitive match."""
    return {str(s).upper() for s in em["TF_name_human_curated"].dropna().unique()}


def _load_alias_map() -> dict[str, str]:
    """Library-name -> Lambert-canonical mapping (e.g., EVI1 -> MECOM, BMAL1 -> ARNTL).

    Only includes confirmed-set aliases (the 34 sequence-specific TF synonyms);
    excludes the 4 non-TF entries in the table.
    """
    if not LAMBERT_ALIAS_CSV.exists():
        return {}
    df = pd.read_csv(LAMBERT_ALIAS_CSV)
    df = df[df["In_confirmed_set"] == "Yes"]
    return {
        str(row["Alias_in_source_motif_database"]).upper(): str(row["Lambert_canonical_symbol"]).upper()
        for _, row in df.iterrows()
    }


def _trend_tfs_alias_resolved(em: pd.DataFrame) -> set[str]:
    """Library TFs PLUS their Lambert-canonical aliases (per Table_S1_Lambert_alias_mapping).

    This is the more biologically accurate set for cross-referencing against Reddy
    (cancer MTFs) and D'Alessio (identity TFs), since downstream studies use
    canonical Lambert names while the library uses the source motif-database names.
    """
    base = _trend_tfs(em)
    alias = _load_alias_map()
    expanded = set(base)
    for lib_name, canonical in alias.items():
        if lib_name in base:
            expanded.add(canonical)
    return expanded


def _split_aliased(value: str) -> list[str]:
    """Cells like 'LOC729991-MEF2B /// MEF2B' -> ['MEF2B']. Drops LOC*."""
    out: list[str] = []
    for part in str(value).replace("-", " ").split("///"):
        token = part.strip().split()[0] if part.strip().split() else ""
        if token and not token.upper().startswith("LOC"):
            out.append(token.upper())
    return out


def build_dbd_families(em: pd.DataFrame) -> list[dict[str, Any]]:
    """Panels B and C source data: one row per DBD family with TF count + sensor count.

    Implements the manuscript's category structure: top-N named families surfaced
    individually, with smaller families folded into 'Other (22 families + 15 unclassified)'.
    The 15 unclassified are confirmed sequence-specific TFs whose Lambert DBD family
    was not assigned (Lambert_DBD_family = 'Unknown').
    """
    # Subset 1: confirmed sequence-specific TFs with an assigned DBD family (≠ 'Unknown')
    has_real_family = (
        em["Lambert_DBD_family"].notna()
        & (em["Lambert_DBD_family"] != "Unknown")
        & ~em["Lambert_TF_assessment"].isin(
            ["Unlikely to be sequence specific TF", "ssDNA/RNA binding"]
        )
    )
    classified = em[has_real_family].copy()

    # Subset 2: confirmed TFs whose DBD family is 'Unknown' (the 15 unclassified)
    unclassified_mask = (
        em["Lambert_matched"].eq("Yes")
        & ~em["Lambert_TF_assessment"].isin(
            ["Unlikely to be sequence specific TF", "ssDNA/RNA binding"]
        )
        & (em["Lambert_DBD_family"].isna() | (em["Lambert_DBD_family"] == "Unknown"))
    )
    n_unclassified_tfs = em.loc[unclassified_mask, "TF_name_human_curated"].nunique()
    n_unclassified_sensors = int(unclassified_mask.sum())

    # Per-family TF + sensor counts (distinct TFs)
    tf_counts = (
        classified.groupby("Lambert_DBD_family")["TF_name_human_curated"]
        .nunique()
        .sort_values(ascending=False)
    )
    sensor_counts = classified.groupby("Lambert_DBD_family").size()

    SMALL_FAMILY_THRESHOLD = 4
    big_families = tf_counts[tf_counts >= SMALL_FAMILY_THRESHOLD].index.tolist()
    small_families = tf_counts[tf_counts < SMALL_FAMILY_THRESHOLD].index.tolist()

    rows: list[dict[str, Any]] = []
    for fam in big_families:
        rows.append({
            "family": str(fam),
            "n_tfs": int(tf_counts[fam]),
            "n_sensors": int(sensor_counts.get(fam, 0)),
        })

    # Always emit the "Other" bar — even when there are no <4-member families,
    # the 15 unclassified TFs go here.
    if small_families or n_unclassified_tfs > 0:
        other_tf = int(sum(tf_counts[f] for f in small_families))
        other_sensors = int(sum(sensor_counts.get(f, 0) for f in small_families))
        rows.append({
            "family": f"Other ({len(small_families)} families + {int(n_unclassified_tfs)} unclassified)",
            "n_tfs": other_tf + int(n_unclassified_tfs),
            "n_sensors": other_sensors + n_unclassified_sensors,
        })
        rows.sort(key=lambda r: -r["n_tfs"])

    for i, r in enumerate(rows):
        r["color"] = DBD_PALETTE[i % len(DBD_PALETTE)]

    return rows


def build_cacts_coverage(em: pd.DataFrame) -> dict[str, Any]:
    """Panel D source data: per-tumor-type CaCTS MTF coverage."""
    if not REDDY_XLSX.exists():
        log.warning("Reddy Table S6 not found at %s; skipping CaCTS coverage.", REDDY_XLSX)
        return {"per_tumor": [], "totals": {"n_in": 0, "n_total": 0}}

    raw = pd.read_excel(REDDY_XLSX, header=2)
    raw = raw.rename(columns=lambda c: str(c).strip())
    reddy = raw.dropna(subset=["Tumor Type", "Candidate MTF"]).copy()
    reddy["MTF_upper"] = reddy["Candidate MTF"].astype(str).str.upper()

    # Use alias-resolved set (Lambert canonical names) per Table_S1_Lambert_alias_mapping.
    # This catches MTFs like MECOM that the library calls EVI1 — a known issue
    # documented in references/TREND_library_TF_breakdown.md.
    trend = _trend_tfs_alias_resolved(em)

    rows: list[dict[str, Any]] = []
    for tumor, grp in reddy.groupby("Tumor Type"):
        mtfs = sorted(grp["MTF_upper"].dropna().unique())
        in_trend = sorted([m for m in mtfs if m in trend])
        missing = sorted([m for m in mtfs if m not in trend])
        n_total = len(mtfs)
        n_in = len(in_trend)
        rows.append({
            "tumor": str(tumor),
            "n_total": n_total,
            "n_in": n_in,
            "n_missing": n_total - n_in,
            "pct": round(100.0 * n_in / n_total, 1) if n_total else 0.0,
            "in_tfs": in_trend,
            "missing_tfs": missing,
        })
    rows.sort(key=lambda r: (-r["pct"], -r["n_total"]))

    union_mtfs = sorted(reddy["MTF_upper"].dropna().unique())
    in_union = sum(1 for m in union_mtfs if m in trend)
    return {
        "per_tumor": rows,
        "totals": {
            "n_in": in_union,
            "n_total": len(union_mtfs),
            "pct": round(100.0 * in_union / len(union_mtfs), 1) if union_mtfs else 0.0,
        },
    }


def build_dalessio_coverage(em: pd.DataFrame) -> dict[str, Any]:
    """Panel E source data: per-system identity-TF coverage (top 10 per tissue)."""
    if not DALESSIO_XLSX.exists() or not TISSUE_SYSTEM_CSV.exists():
        log.warning(
            "D'Alessio Table S1 or tissue→system mapping missing; skipping coverage."
        )
        return {"per_system": [], "totals": {"n_in": 0, "n_total": 0}}

    dale = pd.read_excel(DALESSIO_XLSX, skiprows=2)
    spec_col = dale.columns[0]
    tissue_cols = list(dale.columns[1:])
    top10 = dale[dale[spec_col].between(1, 10)]

    syss = pd.read_csv(TISSUE_SYSTEM_CSV)
    tissue_to_system = dict(zip(syss["tissue"], syss["system"]))

    per_tissue: dict[str, set[str]] = {}
    for col in tissue_cols:
        per_tissue[col] = set()
        for v in top10[col].dropna():
            for tf in _split_aliased(v):
                per_tissue[col].add(tf)

    per_system: dict[str, set[str]] = {}
    for tissue, tf_set in per_tissue.items():
        sys = tissue_to_system.get(tissue)
        if sys:
            per_system.setdefault(sys, set()).update(tf_set)

    trend = _trend_tfs_alias_resolved(em)
    rows: list[dict[str, Any]] = []
    for sys, tfs in per_system.items():
        in_t = sorted([t for t in tfs if t in trend])
        missing = sorted([t for t in tfs if t not in trend])
        n_total = len(tfs)
        n_in = len(in_t)
        rows.append({
            "system": sys,
            "n_total": n_total,
            "n_in": n_in,
            "n_missing": n_total - n_in,
            "pct": round(100.0 * n_in / n_total, 1) if n_total else 0.0,
            "in_tfs": in_t,
            "missing_tfs": missing,
        })
    rows.sort(key=lambda r: (-r["pct"], -r["n_total"]))

    union = set().union(*per_system.values()) if per_system else set()
    in_union = sum(1 for t in union if t in trend)
    return {
        "per_system": rows,
        "totals": {
            "n_in": in_union,
            "n_total": len(union),
            "pct": round(100.0 * in_union / len(union), 1) if union else 0.0,
        },
    }


# Hard total of Lambert DBD families per the 2018 census (manuscript references this number).
# We collapse small families into "Other" for the chart but the headline subtitle should
# match the published figure.
N_LAMBERT_DBD_FAMILIES_TOTAL = 49


def build_composition_breakdown(em: pd.DataFrame) -> dict[str, Any]:
    """Hierarchical decomposition of the 1,068 library TFs into:
        729 confirmed sequence-specific TFs (Lambert)
            695 direct symbol matches
            34 alias / synonym matches (per Table_S1_Lambert_alias_mapping)
        91 Lambert entries flagged as non-TFs
            75 'Unlikely to be sequence specific TF'
            16 'ssDNA/RNA binding'
        248 proteins not in the Lambert census (PPI-derived)
    """
    em_unique = em.drop_duplicates(subset=["TF_name_human_curated"]).copy()

    n_total = em_unique["TF_name_human_curated"].nunique()

    n_lambert_yes = (em_unique["Lambert_matched"] == "Yes").sum()
    n_lambert_no = (em_unique["Lambert_matched"] != "Yes").sum()

    n_unlikely = (em_unique["Lambert_TF_assessment"] == "Unlikely to be sequence specific TF").sum()
    n_ssdna = (em_unique["Lambert_TF_assessment"] == "ssDNA/RNA binding").sum()
    n_non_tf = int(n_unlikely + n_ssdna)
    n_confirmed = int(n_lambert_yes - n_non_tf)

    # Direct vs alias: cross-reference against the alias mapping.
    alias = _load_alias_map()
    library_tf_set = set(em_unique["TF_name_human_curated"].dropna().str.upper())
    n_via_alias = sum(1 for lib_name in alias if lib_name in library_tf_set)
    n_direct = int(n_confirmed - n_via_alias)

    return {
        "total": int(n_total),
        "branches": [
            {
                "label": "Confirmed sequence-specific TFs",
                "count": n_confirmed,
                "color": "#1F5E3A",
                "children": [
                    {"label": "Direct Lambert match", "count": n_direct, "color": "#1F5E3A"},
                    {"label": "Lambert match via gene synonym", "count": n_via_alias, "color": "#3D8A6F"},
                ],
            },
            {
                "label": "Lambert entries flagged as non-TFs",
                "count": n_non_tf,
                "color": "#A8845E",
                "children": [
                    {"label": "Unlikely to be sequence-specific", "count": int(n_unlikely), "color": "#A8845E"},
                    {"label": "ssDNA/RNA binding", "count": int(n_ssdna), "color": "#C2A878"},
                ],
            },
            {
                "label": "Not in Lambert census",
                "count": int(n_lambert_no),
                "color": "#7E8FA8",
                "children": [
                    {
                        "label": "Protein-DNA interaction screens (e.g., Hu et al. 2009)",
                        "count": int(n_lambert_no),
                        "color": "#7E8FA8",
                    },
                ],
            },
        ],
    }


def build_classifications() -> dict[str, Any]:
    """Aggregate everything into the structure the API surfaces. Run during ingest."""
    em = _load_enhancer_meta()
    log.info("Building classification aggregates from %s rows of enhancer_meta", len(em))

    dbd = build_dbd_families(em)
    cacts = build_cacts_coverage(em)
    dale = build_dalessio_coverage(em)
    breakdown = build_composition_breakdown(em)

    n_classified = sum(r["n_tfs"] for r in dbd)

    return {
        "schema_version": 2,
        "dbd_families": dbd,
        "cacts_coverage": cacts,
        "dalessio_coverage": dale,
        "composition_breakdown": breakdown,
        "totals": {
            "n_classified_tfs": n_classified,
            "n_dbd_families_chart": len(dbd),  # bars rendered in Panels B/C
            "n_dbd_families_total": N_LAMBERT_DBD_FAMILIES_TOTAL,  # subtitle uses this
            "cacts": cacts["totals"],
            "dalessio": dale["totals"],
        },
    }
