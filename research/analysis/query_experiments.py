"""Query the Dolt experiments table with validation filters.

Every analytical query includes the mandatory filters:
    manipulation_check = 'passed' AND results_valid = true

The ONE exception is ``query_exclusion_counts``, which
intentionally scans all rows to compute how many experiments
were excluded by validation.

Usage::

    from research.analysis.query_experiments import (
        get_connection,
        query_validated_experiments,
        query_exclusion_counts,
        query_pass_rate_delta,
        query_erosion_comparison,
        query_verbosity_comparison,
        query_budget_efficiency,
        query_per_problem_breakdown,
    )
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from dataclasses import field
from typing import Any

logger = logging.getLogger(__name__)

# Dolt connection defaults
DOLT_HOST = "127.0.0.1"
DOLT_PORT = 3307
DOLT_DB = "scbench"

# ── Mandatory validation filter ──────────────────────
# Applied to ALL analytical queries except the
# exclusion-count query.
VALIDATION_FILTER = (
    "manipulation_check = 'passed' "
    "AND results_valid = true"
)

# Threshold below which results are flagged preliminary.
LOW_N_THRESHOLD = 5


# ── Data classes ─────────────────────────────────────


@dataclass
class ExclusionCounts:
    """Counts of total, valid, and excluded experiments."""

    total: int = 0
    valid: int = 0
    excluded: int = 0
    excluded_manipulation: int = 0
    excluded_invalid: int = 0


@dataclass
class PassRateDelta:
    """Pass rate delta for a single problem/model pair."""

    problem_id: str = ""
    model: str = ""
    hypothesis_id: str | None = None
    baseline_pass_rate: float = 0.0
    two_agent_pass_rate: float = 0.0
    delta: float = 0.0
    sample_size: int = 2


@dataclass
class ModeComparison:
    """Aggregate statistics for one mode."""

    mode: str = ""
    n: int = 0
    mean: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    is_preliminary: bool = False


@dataclass
class BudgetEfficiency:
    """Budget efficiency for one mode."""

    mode: str = ""
    n: int = 0
    mean_cost: float = 0.0
    mean_pass_rate: float = 0.0
    cost_per_pct_point: float | None = None
    is_preliminary: bool = False


@dataclass
class PerProblemRow:
    """Per-problem breakdown for one mode."""

    problem_id: str = ""
    mode: str = ""
    n: int = 0
    mean_pass_rate: float = 0.0
    mean_erosion_slope: float = 0.0
    mean_verbosity_slope: float = 0.0
    mean_cost: float = 0.0
    is_preliminary: bool = False


@dataclass
class ExperimentRecord:
    """Full experiment record from Dolt."""

    id: int = 0
    problem_id: str = ""
    model: str = ""
    mode: str = ""
    hypothesis_id: str | None = None
    total_pass_rate: float = 0.0
    total_cost: float = 0.0
    erosion_slope: float = 0.0
    verbosity_slope: float = 0.0
    pass_rates: list[float] = field(
        default_factory=list,
    )
    erosion_scores: list[float] = field(
        default_factory=list,
    )
    verbosity_scores: list[float] = field(
        default_factory=list,
    )
    baseline_pass_rate: float | None = None
    delta_pass_rate: float | None = None
    delta_erosion: float | None = None
    budget_usd: float = 0.0
    manipulation_check: str = "skipped"
    results_valid: bool = False


# ── Connection helper ────────────────────────────────


def get_connection(
    host: str = DOLT_HOST,
    port: int = DOLT_PORT,
    db: str = DOLT_DB,
) -> Any:
    """Open a pymysql connection to Dolt.

    Returns the connection object.
    """
    import pymysql

    return pymysql.connect(
        host=host,
        port=port,
        database=db,
        user="root",
        password="",
        autocommit=True,
    )


# ── Query functions ──────────────────────────────────


def query_exclusion_counts(
    conn: Any,
) -> ExclusionCounts:
    """Count total, valid, and excluded experiments.

    This is the ONE permitted unfiltered query. It scans
    all rows to compute how many were excluded.
    """
    sql = """
    SELECT
      COUNT(*) AS total_experiments,
      SUM(CASE WHEN manipulation_check = 'passed'
                AND results_valid = true
           THEN 1 ELSE 0 END) AS valid_experiments,
      COUNT(*) - SUM(
        CASE WHEN manipulation_check = 'passed'
                  AND results_valid = true
        THEN 1 ELSE 0 END
      ) AS excluded_experiments,
      SUM(CASE WHEN manipulation_check != 'passed'
           THEN 1 ELSE 0 END)
        AS excluded_manipulation_check,
      SUM(CASE WHEN results_valid != true
           THEN 1 ELSE 0 END)
        AS excluded_invalid_results
    FROM experiments
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
    if row is None:
        return ExclusionCounts()
    return ExclusionCounts(
        total=int(row[0] or 0),
        valid=int(row[1] or 0),
        excluded=int(row[2] or 0),
        excluded_manipulation=int(row[3] or 0),
        excluded_invalid=int(row[4] or 0),
    )


def query_validated_experiments(
    conn: Any,
) -> list[ExperimentRecord]:
    """Fetch all validated experiments.

    Applies mandatory validation filter:
    ``manipulation_check = 'passed' AND results_valid = true``
    """
    sql = f"""
    SELECT
      id, problem_id, model, mode, hypothesis_id,
      total_pass_rate, total_cost,
      erosion_slope, verbosity_slope,
      pass_rates, erosion_scores, verbosity_scores,
      baseline_pass_rate, delta_pass_rate, delta_erosion,
      budget_usd, manipulation_check, results_valid
    FROM experiments
    WHERE {VALIDATION_FILTER}
    ORDER BY id
    """  # noqa: S608
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    records: list[ExperimentRecord] = []
    for r in rows:
        records.append(
            ExperimentRecord(
                id=int(r[0]),
                problem_id=str(r[1]),
                model=str(r[2]),
                mode=str(r[3]),
                hypothesis_id=(
                    str(r[4]) if r[4] else None
                ),
                total_pass_rate=float(r[5] or 0),
                total_cost=float(r[6] or 0),
                erosion_slope=float(r[7] or 0),
                verbosity_slope=float(r[8] or 0),
                pass_rates=_parse_json_array(r[9]),
                erosion_scores=_parse_json_array(r[10]),
                verbosity_scores=_parse_json_array(
                    r[11],
                ),
                baseline_pass_rate=(
                    float(r[12]) if r[12] is not None
                    else None
                ),
                delta_pass_rate=(
                    float(r[13]) if r[13] is not None
                    else None
                ),
                delta_erosion=(
                    float(r[14]) if r[14] is not None
                    else None
                ),
                budget_usd=float(r[15] or 0),
                manipulation_check=str(r[16] or ""),
                results_valid=bool(r[17]),
            ),
        )
    return records


def query_pass_rate_delta(
    conn: Any,
) -> list[PassRateDelta]:
    """Compute pass rate delta (two-agent - baseline).

    Joins two-agent and baseline rows matched on
    problem_id, model, and hypothesis_id. Both sides
    must pass validation filters.
    """
    sql = f"""
    SELECT
      e2.problem_id,
      e2.model,
      e2.hypothesis_id,
      e1.total_pass_rate AS baseline_pass_rate,
      e2.total_pass_rate AS two_agent_pass_rate,
      e2.total_pass_rate - e1.total_pass_rate
        AS pass_rate_delta
    FROM experiments e2
    JOIN experiments e1
      ON e1.problem_id = e2.problem_id
      AND e1.model = e2.model
      AND (e1.hypothesis_id = e2.hypothesis_id
           OR (e1.hypothesis_id IS NULL
               AND e2.hypothesis_id IS NULL))
    WHERE e2.mode = 'two-agent'
      AND e1.mode = 'single'
      AND e2.{VALIDATION_FILTER}
      AND e1.{VALIDATION_FILTER}
    ORDER BY pass_rate_delta DESC
    """  # noqa: S608
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    results: list[PassRateDelta] = []
    for r in rows:
        results.append(
            PassRateDelta(
                problem_id=str(r[0]),
                model=str(r[1]),
                hypothesis_id=(
                    str(r[2]) if r[2] else None
                ),
                baseline_pass_rate=float(r[3] or 0),
                two_agent_pass_rate=float(r[4] or 0),
                delta=float(r[5] or 0),
                sample_size=2,
            ),
        )
    return results


def query_erosion_comparison(
    conn: Any,
) -> list[ModeComparison]:
    """Compare erosion slope averages between modes.

    Groups by mode and computes mean, min, max with
    sample sizes.
    """
    sql = f"""
    SELECT
      mode,
      COUNT(*) AS n,
      AVG(erosion_slope) AS mean_erosion_slope,
      MIN(erosion_slope) AS min_erosion_slope,
      MAX(erosion_slope) AS max_erosion_slope
    FROM experiments
    WHERE {VALIDATION_FILTER}
    GROUP BY mode
    """  # noqa: S608
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    results: list[ModeComparison] = []
    for r in rows:
        n = int(r[1] or 0)
        results.append(
            ModeComparison(
                mode=str(r[0]),
                n=n,
                mean=float(r[2] or 0),
                min_val=float(r[3] or 0),
                max_val=float(r[4] or 0),
                is_preliminary=n < LOW_N_THRESHOLD,
            ),
        )
    return results


def query_verbosity_comparison(
    conn: Any,
) -> list[ModeComparison]:
    """Compare verbosity slope averages between modes.

    Groups by mode and computes mean, min, max with
    sample sizes.
    """
    sql = f"""
    SELECT
      mode,
      COUNT(*) AS n,
      AVG(verbosity_slope) AS mean_verbosity_slope,
      MIN(verbosity_slope) AS min_verbosity_slope,
      MAX(verbosity_slope) AS max_verbosity_slope
    FROM experiments
    WHERE {VALIDATION_FILTER}
    GROUP BY mode
    """  # noqa: S608
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    results: list[ModeComparison] = []
    for r in rows:
        n = int(r[1] or 0)
        results.append(
            ModeComparison(
                mode=str(r[0]),
                n=n,
                mean=float(r[2] or 0),
                min_val=float(r[3] or 0),
                max_val=float(r[4] or 0),
                is_preliminary=n < LOW_N_THRESHOLD,
            ),
        )
    return results


def query_budget_efficiency(
    conn: Any,
) -> list[BudgetEfficiency]:
    """Compute budget efficiency (cost per pct point).

    Groups by mode. Does not compute cost_per_pct_point
    for groups with N < 3.
    """
    sql = f"""
    SELECT
      mode,
      COUNT(*) AS n,
      AVG(total_cost) AS mean_cost,
      AVG(total_pass_rate) AS mean_pass_rate
    FROM experiments
    WHERE {VALIDATION_FILTER}
    GROUP BY mode
    """  # noqa: S608
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    results: list[BudgetEfficiency] = []
    for r in rows:
        n = int(r[1] or 0)
        mean_cost = float(r[2] or 0)
        mean_pr = float(r[3] or 0)
        # Only compute derived stat if N >= 3 and
        # pass rate > 0.
        cpp: float | None = None
        if n >= 3 and mean_pr > 0:
            cpp = round(mean_cost / mean_pr, 4)
        results.append(
            BudgetEfficiency(
                mode=str(r[0]),
                n=n,
                mean_cost=round(mean_cost, 4),
                mean_pass_rate=round(mean_pr, 4),
                cost_per_pct_point=cpp,
                is_preliminary=n < LOW_N_THRESHOLD,
            ),
        )
    return results


def query_per_problem_breakdown(
    conn: Any,
) -> list[PerProblemRow]:
    """Per-problem breakdown grouped by mode.

    Returns rows sorted by problem_id, then mode.
    """
    sql = f"""
    SELECT
      problem_id,
      mode,
      COUNT(*) AS n,
      AVG(total_pass_rate) AS mean_pass_rate,
      AVG(erosion_slope) AS mean_erosion_slope,
      AVG(verbosity_slope) AS mean_verbosity_slope,
      AVG(total_cost) AS mean_cost
    FROM experiments
    WHERE {VALIDATION_FILTER}
    GROUP BY problem_id, mode
    ORDER BY problem_id, mode
    """  # noqa: S608
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    results: list[PerProblemRow] = []
    for r in rows:
        n = int(r[2] or 0)
        results.append(
            PerProblemRow(
                problem_id=str(r[0]),
                mode=str(r[1]),
                n=n,
                mean_pass_rate=float(r[3] or 0),
                mean_erosion_slope=float(r[4] or 0),
                mean_verbosity_slope=float(r[5] or 0),
                mean_cost=float(r[6] or 0),
                is_preliminary=n < LOW_N_THRESHOLD,
            ),
        )
    return results


# ── Helpers ──────────────────────────────────────────


def _parse_json_array(
    value: Any,
) -> list[float]:
    """Parse a JSON array column from Dolt."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [float(v) for v in parsed]
        except (json.JSONDecodeError, ValueError):
            return []
    if isinstance(value, (list, tuple)):
        return [float(v) for v in value]
    return []
