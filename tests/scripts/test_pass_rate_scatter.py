from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "graphing"
    / "pass_rate_scatter.py"
)
SPEC = importlib.util.spec_from_file_location(
    "pass_rate_scatter_module", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_compute_erosion_uses_complexity_mass_gini():
    df = pd.DataFrame(
        [
            {
                "mass.complexity_concentration": 0.6,
                "functions": 10,
                "methods": 0,
                "cc_high_count": 0,
                "cc_extreme_count": 0,
                "lint_errors": 10,
                "loc": 100,
            }
        ]
    )

    out = MODULE.compute_erosion(df)

    assert out.iloc[0] == pytest.approx(0.6)


def test_compute_erosion_returns_nan_when_required_columns_missing():
    df = pd.DataFrame([{"functions": 10, "methods": 0, "loc": 100}])

    out = MODULE.compute_erosion(df)

    assert pd.isna(out.iloc[0])
