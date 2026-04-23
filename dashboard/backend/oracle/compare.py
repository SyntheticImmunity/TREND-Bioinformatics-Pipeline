"""Re-export of the shared csv_compare predicate so the backend can import
it without depending on the test tree's package layout.

Single source of truth lives in tests/equivalence/helpers/csv_compare.py.
This module loads that file by absolute path so the backend doesn't have to
add tests/ to PYTHONPATH at import time.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from backend import config

_CSV_COMPARE_PATH = config.REPO_ROOT / "tests" / "equivalence" / "helpers" / "csv_compare.py"
_MODULE_NAME = "trend.csv_compare"

_spec = importlib.util.spec_from_file_location(_MODULE_NAME, _CSV_COMPARE_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Could not load csv_compare from {_CSV_COMPARE_PATH}")
_module = importlib.util.module_from_spec(_spec)
# Register before exec so dataclass can find the module via cls.__module__ lookup
# (Python 3.14 dataclasses tightened this requirement).
sys.modules[_MODULE_NAME] = _module
_spec.loader.exec_module(_module)

compare_csv = _module.compare_csv
CompareResult = _module.CompareResult
