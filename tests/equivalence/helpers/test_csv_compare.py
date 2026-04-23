"""Test the equivalence comparator itself — the load-bearing predicate that
both the C2 gate and the FR-4 reviewer oracle depend on."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tests.equivalence.helpers.csv_compare import compare_csv


@pytest.fixture
def tmp_csvs(tmp_path: Path):
    def _make(name: str, df: pd.DataFrame) -> Path:
        p = tmp_path / name
        df.to_csv(p, index=False)
        return p

    return _make


def test_identical_csvs_match(tmp_csvs):
    df = pd.DataFrame({"id": ["a", "b", "c"], "x": [1.0, 2.0, 3.0]})
    a = tmp_csvs("a.csv", df)
    b = tmp_csvs("b.csv", df)
    res = compare_csv(a, b, primary_key="id")
    assert res.equivalent
    assert "3 rows" in res.summary or "3" in res.summary


def test_extra_column_caught(tmp_csvs):
    a = tmp_csvs("a.csv", pd.DataFrame({"id": ["a"], "x": [1.0], "extra": [9]}))
    b = tmp_csvs("b.csv", pd.DataFrame({"id": ["a"], "x": [1.0]}))
    res = compare_csv(a, b, primary_key="id")
    assert not res.equivalent
    assert "extra" in res.column_diff["only_in_actual"]


def test_numeric_within_tolerance_passes(tmp_csvs):
    a = tmp_csvs("a.csv", pd.DataFrame({"id": ["a"], "x": [1.0000001]}))
    b = tmp_csvs("b.csv", pd.DataFrame({"id": ["a"], "x": [1.0]}))
    res = compare_csv(a, b, primary_key="id", rtol=1e-6, atol=1e-9)
    # Within rtol=1e-6: relative diff ~1e-7
    assert res.equivalent


def test_numeric_outside_tolerance_caught(tmp_csvs):
    a = tmp_csvs("a.csv", pd.DataFrame({"id": ["a"], "x": [1.5]}))
    b = tmp_csvs("b.csv", pd.DataFrame({"id": ["a"], "x": [1.0]}))
    res = compare_csv(a, b, primary_key="id")
    assert not res.equivalent
    assert len(res.numeric_mismatches) == 1
    assert res.numeric_mismatches[0]["column"] == "x"


def test_nan_equal_nan(tmp_csvs):
    a = tmp_csvs("a.csv", pd.DataFrame({"id": ["a", "b"], "x": [float("nan"), 1.0]}))
    b = tmp_csvs("b.csv", pd.DataFrame({"id": ["a", "b"], "x": [float("nan"), 1.0]}))
    res = compare_csv(a, b, primary_key="id")
    assert res.equivalent


def test_row_count_mismatch_caught(tmp_csvs):
    a = tmp_csvs("a.csv", pd.DataFrame({"id": ["a", "b"], "x": [1.0, 2.0]}))
    b = tmp_csvs("b.csv", pd.DataFrame({"id": ["a"], "x": [1.0]}))
    res = compare_csv(a, b, primary_key="id")
    assert not res.equivalent
    assert res.row_count_diff == (2, 1)


def test_string_mismatch_caught(tmp_csvs):
    a = tmp_csvs("a.csv", pd.DataFrame({"id": ["a"], "tag": ["alpha"]}))
    b = tmp_csvs("b.csv", pd.DataFrame({"id": ["a"], "tag": ["beta"]}))
    res = compare_csv(a, b, primary_key="id")
    assert not res.equivalent
    assert any(m["column"] == "tag" for m in res.string_mismatches)
