"""Tests for research.analysis.query_experiments.

Uses a mock pymysql cursor to verify SQL queries include
validation filters and return correct data structures.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from research.analysis.query_experiments import LOW_N_THRESHOLD
from research.analysis.query_experiments import VALIDATION_FILTER
from research.analysis.query_experiments import ExclusionCounts
from research.analysis.query_experiments import ExperimentRecord
from research.analysis.query_experiments import _parse_json_array
from research.analysis.query_experiments import query_budget_efficiency
from research.analysis.query_experiments import query_erosion_comparison
from research.analysis.query_experiments import query_exclusion_counts
from research.analysis.query_experiments import query_pass_rate_delta
from research.analysis.query_experiments import query_per_problem_breakdown
from research.analysis.query_experiments import query_validated_experiments
from research.analysis.query_experiments import query_verbosity_comparison

# ── Fixtures ─────────────────────────────────────────


@pytest.fixture()
def mock_conn():
    """Create a mock Dolt connection with cursor."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = (
        MagicMock(return_value=cursor)
    )
    conn.cursor.return_value.__exit__ = MagicMock(
        return_value=False,
    )
    return conn, cursor


# ── VALIDATION_FILTER constant ───────────────────────


def test_validation_filter_includes_both_conditions():
    """VALIDATION_FILTER contains both required checks."""
    assert "manipulation_check" in VALIDATION_FILTER
    assert "passed" in VALIDATION_FILTER
    assert "results_valid" in VALIDATION_FILTER
    assert "true" in VALIDATION_FILTER


# ── query_exclusion_counts ───────────────────────────


def test_exclusion_counts_returns_correct_structure(
    mock_conn,
):
    """Exclusion counts parse all five fields."""
    conn, cursor = mock_conn
    cursor.fetchone.return_value = (10, 7, 3, 2, 1)

    result = query_exclusion_counts(conn)

    assert isinstance(result, ExclusionCounts)
    assert result.total == 10
    assert result.valid == 7
    assert result.excluded == 3
    assert result.excluded_manipulation == 2
    assert result.excluded_invalid == 1


def test_exclusion_counts_empty_table(mock_conn):
    """Returns zeros when table is empty."""
    conn, cursor = mock_conn
    cursor.fetchone.return_value = (0, 0, 0, 0, 0)

    result = query_exclusion_counts(conn)

    assert result.total == 0
    assert result.valid == 0


def test_exclusion_counts_no_row(mock_conn):
    """Returns empty counts when no row returned."""
    conn, cursor = mock_conn
    cursor.fetchone.return_value = None

    result = query_exclusion_counts(conn)

    assert result.total == 0


def test_exclusion_counts_is_unfiltered(mock_conn):
    """The exclusion query must NOT have WHERE filter."""
    conn, cursor = mock_conn
    cursor.fetchone.return_value = (0, 0, 0, 0, 0)

    query_exclusion_counts(conn)

    sql = cursor.execute.call_args[0][0]
    # Should NOT have WHERE clause
    assert "WHERE" not in sql.upper().split(
        "FROM experiments"
    )[-1].split("SELECT")[0]


def test_exclusion_counts_references_validation_filter(
    mock_conn,
):
    """Exclusion count uses COUNT(*) - COUNT(filtered)
    pattern referencing the validation filter."""
    conn, cursor = mock_conn
    cursor.fetchone.return_value = (10, 7, 3, 2, 1)

    query_exclusion_counts(conn)

    sql = cursor.execute.call_args[0][0]
    # The SQL should reference the validation filter
    # conditions inside CASE WHEN expressions.
    assert "manipulation_check = 'passed'" in sql, (
        "Exclusion query must reference "
        "manipulation_check filter"
    )
    assert "results_valid = true" in sql, (
        "Exclusion query must reference "
        "results_valid filter"
    )
    # It should use COUNT(*) for total and
    # COUNT(*) - COUNT(CASE WHEN ...) for excluded.
    assert "COUNT(*)" in sql, (
        "Must use COUNT(*) for total"
    )
    flat_sql = " ".join(sql.split())
    assert "COUNT(*) - COUNT(" in flat_sql, (
        "Must use COUNT(*) - COUNT(filtered) pattern"
    )


# ── query_validated_experiments ──────────────────────


def test_validated_experiments_uses_filter(mock_conn):
    """All-experiments query includes validation filter."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = []

    query_validated_experiments(conn)

    sql = cursor.execute.call_args[0][0]
    assert "manipulation_check = 'passed'" in sql
    assert "results_valid = true" in sql


def test_validated_experiments_parses_rows(mock_conn):
    """Records are parsed from result rows."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = [
        (
            1, "file_backup", "opus-4.5", "single",
            None, 85.5, 10.0, 0.02, 0.05,
            "[0.8, 0.9]", "[0.01, 0.02]",
            "[0.04, 0.05]",
            None, None, None, 20.0,
            "passed", 1,
        ),
    ]

    records = query_validated_experiments(conn)

    assert len(records) == 1
    assert isinstance(records[0], ExperimentRecord)
    assert records[0].problem_id == "file_backup"
    assert records[0].mode == "single"
    assert records[0].total_pass_rate == 85.5
    assert records[0].pass_rates == [0.8, 0.9]


# ── query_pass_rate_delta ────────────────────────────


def test_pass_rate_delta_uses_filter(mock_conn):
    """Delta query filters both sides of the join."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = []

    query_pass_rate_delta(conn)

    sql = cursor.execute.call_args[0][0]
    # Should have filter on both e1 and e2
    assert sql.count("manipulation_check = 'passed'") >= 2
    assert sql.count("results_valid = true") >= 2


def test_pass_rate_delta_no_ambiguous_columns(
    mock_conn,
):
    """Regression: all column refs in the self-join
    query are qualified with table aliases (e1. or e2.)
    to prevent ambiguous-column SQL errors.

    Previously, the query used ``e2.{VALIDATION_FILTER}``
    which expanded to
    ``e2.manipulation_check = 'passed' AND
    results_valid = true``, leaving ``results_valid``
    unqualified.
    """
    import re as _re

    conn, cursor = mock_conn
    cursor.fetchall.return_value = []

    query_pass_rate_delta(conn)

    sql = cursor.execute.call_args[0][0]
    # After FROM / JOIN, every column reference in
    # WHERE and ON clauses must be alias-qualified.
    # Split out the WHERE clause for inspection.
    where_idx = sql.upper().index("WHERE")
    where_clause = sql[where_idx:]

    # Each "results_valid" must be preceded by alias
    unqualified = _re.findall(
        r"(?<!\w\.)results_valid", where_clause,
    )
    assert len(unqualified) == 0, (
        "results_valid must be alias-qualified (e1. "
        f"or e2.) in self-join: {where_clause}"
    )

    # Each "manipulation_check" must be preceded by alias
    unqualified_mc = _re.findall(
        r"(?<!\w\.)manipulation_check", where_clause,
    )
    assert len(unqualified_mc) == 0, (
        "manipulation_check must be alias-qualified: "
        f"{where_clause}"
    )

    # Verify exact count: 2 each for e1/e2
    assert "e1.manipulation_check" in sql
    assert "e2.manipulation_check" in sql
    assert "e1.results_valid" in sql
    assert "e2.results_valid" in sql


def test_pass_rate_delta_returns_deltas(mock_conn):
    """Delta results are correctly computed."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = [
        ("file_backup", "opus-4.5", "hyp-1",
         80.0, 85.0, 5.0),
        ("todo_app", "opus-4.5", "hyp-1",
         70.0, 65.0, -5.0),
    ]

    results = query_pass_rate_delta(conn)

    assert len(results) == 2
    assert results[0].problem_id == "file_backup"
    assert results[0].delta == 5.0
    assert results[0].sample_size == 2
    assert results[1].delta == -5.0


# ── query_erosion_comparison ─────────────────────────


def test_erosion_comparison_uses_filter(mock_conn):
    """Erosion comparison includes validation filter."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = []

    query_erosion_comparison(conn)

    sql = cursor.execute.call_args[0][0]
    assert "manipulation_check = 'passed'" in sql
    assert "results_valid = true" in sql


def test_erosion_comparison_parses_modes(mock_conn):
    """Returns ModeComparison for each mode."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = [
        ("single", 8, 0.03, 0.01, 0.05),
        ("two-agent", 8, 0.02, 0.005, 0.04),
    ]

    results = query_erosion_comparison(conn)

    assert len(results) == 2
    assert results[0].mode == "single"
    assert results[0].n == 8
    assert results[0].mean == 0.03
    assert results[0].is_preliminary is False


def test_erosion_comparison_flags_low_n(mock_conn):
    """Low-N groups are flagged as preliminary."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = [
        ("single", 3, 0.03, 0.01, 0.05),
    ]

    results = query_erosion_comparison(conn)

    assert results[0].is_preliminary is True


# ── query_verbosity_comparison ───────────────────────


def test_verbosity_comparison_uses_filter(mock_conn):
    """Verbosity comparison includes validation filter."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = []

    query_verbosity_comparison(conn)

    sql = cursor.execute.call_args[0][0]
    assert "manipulation_check = 'passed'" in sql
    assert "results_valid = true" in sql


def test_verbosity_comparison_parses_modes(mock_conn):
    """Returns ModeComparison for verbosity."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = [
        ("single", 10, 0.08, 0.02, 0.15),
        ("two-agent", 10, 0.05, 0.01, 0.10),
    ]

    results = query_verbosity_comparison(conn)

    assert len(results) == 2
    assert results[1].mode == "two-agent"
    assert results[1].mean == 0.05


# ── query_budget_efficiency ──────────────────────────


def test_budget_efficiency_uses_filter(mock_conn):
    """Budget efficiency includes validation filter."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = []

    query_budget_efficiency(conn)

    sql = cursor.execute.call_args[0][0]
    assert "manipulation_check = 'passed'" in sql
    assert "results_valid = true" in sql


def test_budget_efficiency_computes_cpp(mock_conn):
    """Cost per pct point computed when N >= 3."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = [
        ("single", 5, 8.0, 80.0),
        ("two-agent", 5, 12.0, 85.0),
    ]

    results = query_budget_efficiency(conn)

    assert len(results) == 2
    assert results[0].cost_per_pct_point is not None
    assert results[0].cost_per_pct_point == pytest.approx(
        8.0 / 80.0, abs=0.001,
    )


def test_budget_efficiency_no_cpp_low_n(mock_conn):
    """Cost per pct point is None when N < 3."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = [
        ("single", 2, 8.0, 80.0),
    ]

    results = query_budget_efficiency(conn)

    assert results[0].cost_per_pct_point is None


def test_budget_efficiency_no_cpp_zero_pr(mock_conn):
    """Cost per pct point is None when pass rate is 0."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = [
        ("single", 5, 8.0, 0.0),
    ]

    results = query_budget_efficiency(conn)

    assert results[0].cost_per_pct_point is None


# ── query_per_problem_breakdown ──────────────────────


def test_per_problem_uses_filter(mock_conn):
    """Per-problem query includes validation filter."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = []

    query_per_problem_breakdown(conn)

    sql = cursor.execute.call_args[0][0]
    assert "manipulation_check = 'passed'" in sql
    assert "results_valid = true" in sql


def test_per_problem_parses_rows(mock_conn):
    """Per-problem rows are parsed correctly."""
    conn, cursor = mock_conn
    cursor.fetchall.return_value = [
        ("file_backup", "single", 3, 80.0,
         0.02, 0.05, 8.0),
        ("file_backup", "two-agent", 3, 85.0,
         0.01, 0.03, 12.0),
    ]

    results = query_per_problem_breakdown(conn)

    assert len(results) == 2
    assert results[0].problem_id == "file_backup"
    assert results[0].mode == "single"
    assert results[0].n == 3
    assert results[0].is_preliminary is True


# ── _parse_json_array ────────────────────────────────


def test_parse_json_array_string():
    """Parses JSON string to float list."""
    assert _parse_json_array("[1.0, 2.5, 3.0]") == [
        1.0, 2.5, 3.0,
    ]


def test_parse_json_array_none():
    """Returns empty list for None."""
    assert _parse_json_array(None) == []


def test_parse_json_array_list():
    """Returns float list from list input."""
    assert _parse_json_array([1, 2, 3]) == [
        1.0, 2.0, 3.0,
    ]


def test_parse_json_array_invalid_string():
    """Returns empty list for invalid JSON."""
    assert _parse_json_array("not json") == []


def test_parse_json_array_empty_string():
    """Returns empty list for empty JSON array."""
    assert _parse_json_array("[]") == []


# ── Low-N threshold ──────────────────────────────────


def test_low_n_threshold_value():
    """LOW_N_THRESHOLD is 5."""
    assert LOW_N_THRESHOLD == 5
