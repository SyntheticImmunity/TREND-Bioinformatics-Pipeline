"""Equivalence predicate for CSV outputs.

Used by *both* the C2 equivalence tests (tests/equivalence/) and the FR-4 reviewer
oracle (backend/oracle/compare.py via re-export). Single source of truth — a fix
here simultaneously fixes the CI gate and the user-facing green/red badge.

Equivalence rules per plan §"Equivalence test harness":
  * Schema:  column-name set equality (order-independent), dtype equality.
  * Numeric: numpy.isclose(rtol, atol) with NaN-equal-NaN.
  * String : exact equality after sort by primary key.
  * Rows   : count equality. Order equality only for files whose downstream
             consumer depends on order (callers pass `ordered=True`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class CompareResult:
    equivalent: bool
    actual_path: Path
    expected_path: Path
    column_diff: dict[str, list[str]] = field(default_factory=dict)
    dtype_diff: dict[str, tuple[str, str]] = field(default_factory=dict)
    row_count_diff: tuple[int, int] | None = None
    numeric_mismatches: list[dict] = field(default_factory=list)
    string_mismatches: list[dict] = field(default_factory=list)
    summary: str = ""

    def headline(self) -> str:
        if self.equivalent:
            return f"MATCH: {self.actual_path.name} == {self.expected_path.name}"
        return f"DIFFERS: {self.summary}"


def compare_csv(
    actual: Path,
    expected: Path,
    *,
    primary_key: str | list[str] | None = None,
    ordered: bool = False,
    rtol: float = 1e-6,
    atol: float = 1e-9,
    max_mismatches_to_record: int = 10,
) -> CompareResult:
    """Compare two CSVs for numerical-and-schema equivalence.

    `primary_key`: column(s) to sort on before comparison when ordered=False.
                   If None, falls back to sorting by the lexicographic union
                   of all string columns (best-effort; pass primary_key for
                   deterministic order with NaNs in string columns).
    """
    df_a = pd.read_csv(actual)
    df_e = pd.read_csv(expected)

    res = CompareResult(equivalent=True, actual_path=actual, expected_path=expected)

    cols_a = set(df_a.columns)
    cols_e = set(df_e.columns)
    only_actual = sorted(cols_a - cols_e)
    only_expected = sorted(cols_e - cols_a)
    if only_actual or only_expected:
        res.equivalent = False
        res.column_diff = {"only_in_actual": only_actual, "only_in_expected": only_expected}

    if len(df_a) != len(df_e):
        res.equivalent = False
        res.row_count_diff = (len(df_a), len(df_e))

    common_cols = sorted(cols_a & cols_e)
    if not res.row_count_diff and common_cols:
        # Sort both frames identically before per-cell comparison.
        if not ordered:
            sort_cols = (
                [primary_key] if isinstance(primary_key, str) else primary_key
            ) or [c for c in common_cols if df_a[c].dtype == object][:3]
            if sort_cols:
                try:
                    df_a = df_a.sort_values(sort_cols).reset_index(drop=True)
                    df_e = df_e.sort_values(sort_cols).reset_index(drop=True)
                except KeyError:
                    pass

        for col in common_cols:
            a_dtype = str(df_a[col].dtype)
            e_dtype = str(df_e[col].dtype)
            if a_dtype != e_dtype:
                # Numeric vs. numeric of different precision is OK (compared with isclose).
                # Numeric vs. string is a real diff.
                a_numeric = pd.api.types.is_numeric_dtype(df_a[col])
                e_numeric = pd.api.types.is_numeric_dtype(df_e[col])
                if a_numeric != e_numeric:
                    res.equivalent = False
                    res.dtype_diff[col] = (a_dtype, e_dtype)
                    continue

            if pd.api.types.is_numeric_dtype(df_a[col]):
                a = df_a[col].to_numpy(dtype=float, copy=False)
                e = df_e[col].to_numpy(dtype=float, copy=False)
                # NaN-equal-NaN
                both_nan = np.isnan(a) & np.isnan(e)
                close = np.isclose(a, e, rtol=rtol, atol=atol) | both_nan
                bad = np.where(~close)[0]
                if bad.size:
                    res.equivalent = False
                    for i in bad[:max_mismatches_to_record]:
                        res.numeric_mismatches.append(
                            {
                                "column": col,
                                "row": int(i),
                                "actual": _safe_float(a[i]),
                                "expected": _safe_float(e[i]),
                            }
                        )
            else:
                a = df_a[col].astype("string").fillna("")
                e = df_e[col].astype("string").fillna("")
                bad = (a != e).to_numpy().nonzero()[0]
                if bad.size:
                    res.equivalent = False
                    for i in bad[:max_mismatches_to_record]:
                        res.string_mismatches.append(
                            {
                                "column": col,
                                "row": int(i),
                                "actual": str(a.iloc[int(i)]),
                                "expected": str(e.iloc[int(i)]),
                            }
                        )

    if res.equivalent:
        res.summary = f"all {len(common_cols)} columns equivalent across {len(df_a)} rows"
    else:
        bits = []
        if res.column_diff:
            bits.append(f"column-set differs (extra={res.column_diff.get('only_in_actual',[])}, "
                        f"missing={res.column_diff.get('only_in_expected',[])})")
        if res.row_count_diff:
            bits.append(f"row count {res.row_count_diff[0]} vs {res.row_count_diff[1]}")
        if res.dtype_diff:
            bits.append(f"dtype differs in {list(res.dtype_diff)[:3]}")
        if res.numeric_mismatches:
            n = len(res.numeric_mismatches)
            bits.append(f"{n} numeric cell mismatch{'es' if n != 1 else ''} (showing up to {max_mismatches_to_record})")
        if res.string_mismatches:
            n = len(res.string_mismatches)
            bits.append(f"{n} string cell mismatch{'es' if n != 1 else ''}")
        res.summary = "; ".join(bits) or "differs (no specific reason recorded)"

    return res


def _safe_float(v) -> float | str:
    if v is None:
        return "null"
    if isinstance(v, float) and math.isnan(v):
        return "NaN"
    return float(v)
