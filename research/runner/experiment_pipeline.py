#!/usr/bin/env python3
"""Experiment pipeline for SCBench research.

Runs both a single-agent baseline and a two-agent experiment
on the same problem, evaluates both with ``slop-code eval``,
writes results to the Dolt ``experiments`` table, and updates
the ``budget`` table with actual spend.

Usage::

    python experiment_pipeline.py \\
        --problem file_backup \\
        --model opus-4.5 \\
        --budget 10.0 \\
        --budget-split 70
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from pydantic import BaseModel
from pydantic import Field

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Repo root (two levels up from research/runner/)
# -------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = REPO_ROOT / "outputs"
PROBLEMS_DIR = REPO_ROOT / "problems"
RUNNER_PATH = (
    REPO_ROOT / "research" / "runner" / "two_agent_runner.py"
)

DEFAULT_IMPLEMENTER_PROMPT = (
    "configs/prompts/default_implementer.jinja"
)
DEFAULT_REVIEWER_PROMPT = (
    "configs/prompts/default_reviewer.jinja"
)
DEFAULT_ENVIRONMENT = (
    "configs/environments/docker-python3.12-uv.yaml"
)

# Dolt connection defaults
DOLT_HOST = "127.0.0.1"
DOLT_PORT = 3307
DOLT_DB = "scbench"


# -------------------------------------------------------------------
# Pydantic models
# -------------------------------------------------------------------


class EvalMetrics(BaseModel):
    """Metrics extracted from slop-code eval output."""

    pass_rates: list[float] = Field(default_factory=list)
    erosion_scores: list[float] = Field(default_factory=list)
    verbosity_scores: list[float] = Field(
        default_factory=list,
    )
    tokens_implementer: list[int] = Field(
        default_factory=list,
    )
    tokens_reviewer: list[int] = Field(
        default_factory=list,
    )
    cost_per_checkpoint: list[float] = Field(
        default_factory=list,
    )
    total_pass_rate: float = 0.0
    total_cost: float = 0.0
    erosion_slope: float = 0.0
    verbosity_slope: float = 0.0
    checkpoint_count: int = 0


class ExperimentRow(BaseModel):
    """Row to insert into the Dolt experiments table."""

    problem_id: str
    model: str
    mode: str  # 'single' or 'two-agent'
    hypothesis_id: str | None = None
    implementer_prompt: str | None = None
    reviewer_prompt: str | None = None
    budget_split: int | None = None
    budget_usd: float = 0.0

    # Per-checkpoint arrays
    pass_rates: list[float] = Field(default_factory=list)
    erosion_scores: list[float] = Field(default_factory=list)
    verbosity_scores: list[float] = Field(
        default_factory=list,
    )
    tokens_implementer: list[int] = Field(
        default_factory=list,
    )
    tokens_reviewer: list[int] = Field(
        default_factory=list,
    )
    cost_per_checkpoint: list[float] = Field(
        default_factory=list,
    )

    # Aggregates
    total_pass_rate: float = 0.0
    total_cost: float = 0.0
    erosion_slope: float = 0.0
    verbosity_slope: float = 0.0

    # Comparison
    baseline_pass_rate: float | None = None
    delta_pass_rate: float | None = None
    delta_erosion: float | None = None

    # Validation
    manipulation_check: str = "skipped"
    manipulation_notes: str | None = None
    results_valid: bool = False
    impl_diff_summary: str | None = None


class PipelineResult(BaseModel):
    """Full result of a pipeline run."""

    problem: str
    model: str
    budget: float
    budget_split: int
    baseline_output_dir: str | None = None
    two_agent_output_dir: str | None = None
    baseline_metrics: EvalMetrics | None = None
    two_agent_metrics: EvalMetrics | None = None
    baseline_row: ExperimentRow | None = None
    two_agent_row: ExperimentRow | None = None
    delta_pass_rate: float | None = None
    delta_erosion: float | None = None
    budget_exceeded: bool = False
    partial: bool = False
    errors: list[str] = Field(default_factory=list)


# -------------------------------------------------------------------
# Dolt helpers
# -------------------------------------------------------------------


def get_dolt_connection(
    host: str = DOLT_HOST,
    port: int = DOLT_PORT,
    db: str = DOLT_DB,
) -> Any:
    """Open a MySQL-compatible connection to Dolt.

    Returns the connection object. Raises if connection fails.
    """
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError(
            "pymysql is required for Dolt access. "
            "Install with: pip install pymysql",
        ) from exc

    return pymysql.connect(
        host=host,
        port=port,
        database=db,
        user="root",
        password="",
        autocommit=True,
    )


def check_budget(
    conn: Any,
    estimated_cost: float,
) -> tuple[bool, float]:
    """Check budget table for sufficient remaining funds.

    Returns (sufficient, remaining) where sufficient is True
    if remaining >= estimated_cost.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT remaining FROM budget WHERE id = 1",
        )
        row = cur.fetchone()
        if row is None:
            return False, 0.0
        remaining = float(row[0])
    return remaining >= estimated_cost, remaining


def update_budget_spent(
    conn: Any,
    actual_cost: float,
) -> None:
    """Add *actual_cost* to the budget table's spent column."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE budget "
            "SET spent = spent + %s "
            "WHERE id = 1",
            (actual_cost,),
        )


def insert_experiment_row(
    conn: Any,
    row: ExperimentRow,
) -> int:
    """Insert a row into the experiments table.

    Returns the auto-generated id.
    """
    sql = (
        "INSERT INTO experiments ("
        "  problem_id, model, mode, hypothesis_id,"
        "  implementer_prompt, reviewer_prompt,"
        "  budget_split, budget_usd,"
        "  pass_rates, erosion_scores, verbosity_scores,"
        "  tokens_implementer, tokens_reviewer,"
        "  cost_per_checkpoint,"
        "  total_pass_rate, total_cost,"
        "  erosion_slope, verbosity_slope,"
        "  baseline_pass_rate, delta_pass_rate,"
        "  delta_erosion,"
        "  manipulation_check, manipulation_notes,"
        "  results_valid, impl_diff_summary"
        ") VALUES ("
        "  %s, %s, %s, %s,"
        "  %s, %s,"
        "  %s, %s,"
        "  %s, %s, %s,"
        "  %s, %s,"
        "  %s,"
        "  %s, %s,"
        "  %s, %s,"
        "  %s, %s,"
        "  %s,"
        "  %s, %s,"
        "  %s, %s"
        ")"
    )
    values = (
        row.problem_id,
        row.model,
        row.mode,
        row.hypothesis_id,
        row.implementer_prompt,
        row.reviewer_prompt,
        row.budget_split,
        row.budget_usd,
        json.dumps(row.pass_rates),
        json.dumps(row.erosion_scores),
        json.dumps(row.verbosity_scores),
        json.dumps(row.tokens_implementer),
        json.dumps(row.tokens_reviewer),
        json.dumps(row.cost_per_checkpoint),
        row.total_pass_rate,
        row.total_cost,
        row.erosion_slope,
        row.verbosity_slope,
        row.baseline_pass_rate,
        row.delta_pass_rate,
        row.delta_erosion,
        row.manipulation_check,
        row.manipulation_notes,
        row.results_valid,
        row.impl_diff_summary,
    )
    with conn.cursor() as cur:
        cur.execute(sql, values)
        cur.execute("SELECT LAST_INSERT_ID()")
        result = cur.fetchone()
    return int(result[0]) if result else 0


# -------------------------------------------------------------------
# Eval metrics parsing
# -------------------------------------------------------------------


def parse_eval_results(
    output_dir: Path,
    problem: str,
) -> EvalMetrics:
    """Parse ``checkpoint_results.jsonl`` from an eval run.

    Extracts per-checkpoint pass rates, erosion, verbosity,
    and cost metrics.  Works for both single-agent baseline
    runs and two-agent runs by reading all flattened metric
    keys from the JSONL.
    """
    results_file = output_dir / "checkpoint_results.jsonl"
    metrics = EvalMetrics()

    if not results_file.exists():
        return metrics

    lines = results_file.read_text().splitlines()
    for line in lines:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Prefer flattened metric keys (strict_pass_rate)
        # produced by the real slop-code eval pipeline.
        # Fall back to total_tests/passed_tests, then
        # legacy pass_counts/total_counts.
        if "strict_pass_rate" in data:
            pr = float(data["strict_pass_rate"])
        elif "total_tests" in data:
            total = data.get("total_tests", 0)
            passed = data.get("passed_tests", 0)
            pr = (
                round(passed / total, 4)
                if total > 0
                else 0.0
            )
        else:
            total = data.get("total_counts", 0)
            passed = data.get("pass_counts", 0)
            pr = (
                round(passed / total, 4)
                if total > 0
                else 0.0
            )
        metrics.pass_rates.append(pr)

        # Extract erosion, verbosity, and cost from
        # flattened JSONL keys (available in both
        # baseline and two-agent eval output).
        if "erosion" in data:
            metrics.erosion_scores.append(
                float(data["erosion"]),
            )
        if "verbosity" in data:
            metrics.verbosity_scores.append(
                float(data["verbosity"]),
            )
        if "cost" in data:
            metrics.cost_per_checkpoint.append(
                float(data["cost"]),
            )

    metrics.checkpoint_count = len(metrics.pass_rates)
    if metrics.pass_rates:
        metrics.total_pass_rate = round(
            sum(metrics.pass_rates)
            / len(metrics.pass_rates),
            4,
        )

    # Parse two-agent metrics if available
    ta_metrics_file = output_dir / "two_agent_metrics.json"
    if ta_metrics_file.exists():
        _merge_two_agent_metrics(metrics, ta_metrics_file)

    # Compute slopes
    metrics.erosion_slope = _compute_slope(
        metrics.erosion_scores,
    )
    metrics.verbosity_slope = _compute_slope(
        metrics.verbosity_scores,
    )

    # Compute total cost
    if metrics.cost_per_checkpoint:
        metrics.total_cost = round(
            sum(metrics.cost_per_checkpoint), 6,
        )

    return metrics


def _merge_two_agent_metrics(
    metrics: EvalMetrics,
    ta_metrics_file: Path,
) -> None:
    """Merge per-checkpoint data from two_agent_metrics.json.

    Only fills in fields not already populated from the
    JSONL eval output.  Erosion, verbosity, and cost are
    extracted from the JSONL when available, so we skip
    them here if already present.  Token counts are only
    available in two_agent_metrics.json.
    """
    try:
        data = json.loads(ta_metrics_file.read_text())
    except (json.JSONDecodeError, OSError):
        return

    checkpoints = data.get("checkpoints", {})

    # Determine which fields were already populated
    # from the JSONL eval output.
    has_erosion = bool(metrics.erosion_scores)
    has_verbosity = bool(metrics.verbosity_scores)
    has_cost = bool(metrics.cost_per_checkpoint)

    for _name, cp in sorted(checkpoints.items()):
        if isinstance(cp, dict):
            # Only fill erosion/verbosity/cost from
            # the runner if JSONL didn't provide them.
            if not has_erosion:
                metrics.erosion_scores.append(
                    cp.get("erosion", 0.0),
                )
            if not has_verbosity:
                metrics.verbosity_scores.append(
                    cp.get("verbosity", 0.0),
                )
            # Token counts are always from the runner.
            metrics.tokens_implementer.append(
                cp.get("tokens_implementer", 0),
            )
            metrics.tokens_reviewer.append(
                cp.get("tokens_reviewer", 0),
            )
            if not has_cost:
                metrics.cost_per_checkpoint.append(
                    cp.get("cost", 0.0),
                )

    metrics.total_cost = round(
        data.get("cumulative_cost", 0.0), 6,
    )


def _compute_slope(values: list[float]) -> float:
    """Compute least-squares slope of *values* over indices.

    Returns 0.0 if fewer than 2 values.
    """
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum(
        (i - x_mean) * (v - y_mean)
        for i, v in enumerate(values)
    )
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return round(num / den, 4)


# -------------------------------------------------------------------
# Checkpoint discovery
# -------------------------------------------------------------------


def get_checkpoints(problem: str) -> list[str]:
    """Return sorted checkpoint names for *problem*."""
    problem_dir = PROBLEMS_DIR / problem
    if not problem_dir.is_dir():
        return []
    return sorted(
        d.name
        for d in problem_dir.iterdir()
        if d.is_dir() and d.name.startswith("checkpoint_")
    )


def verify_matching_checkpoints(
    baseline_dir: Path,
    two_agent_dir: Path,
    problem: str,
) -> bool:
    """Verify both arms produced the same checkpoint dirs."""
    def _cp_names(d: Path) -> set[str]:
        prob_dir = d / problem
        if not prob_dir.is_dir():
            return set()
        return {
            c.name
            for c in prob_dir.iterdir()
            if c.is_dir()
            and c.name.startswith("checkpoint_")
        }

    return _cp_names(baseline_dir) == _cp_names(
        two_agent_dir,
    )


# -------------------------------------------------------------------
# Run helpers
# -------------------------------------------------------------------


def run_baseline(
    problem: str,
    model: str,
    budget: float,
    prompt: str,
    environment: str = DEFAULT_ENVIRONMENT,
) -> tuple[Path | None, int]:
    """Run ``slop-code run`` for the single-agent baseline.

    Passes ``save_dir`` and ``save_template`` overrides so
    that the output lands in a known location instead of
    relying on prefix-based directory detection.

    Returns (output_dir, exit_code).
    """
    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    run_name = f"baseline_{model}_{problem}_{ts}"
    output_dir = OUTPUTS_DIR / run_name

    cmd = [
        sys.executable, "-m", "slop_code",
        "run",
        "--problem", problem,
        "--model", model,
        "--prompt", prompt,
        "--environment", environment,
        "--evaluate",
        f"agent.cost_limits.cost_limit={budget}",
        f"save_dir={output_dir}",
        "save_template=.",
    ]

    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }

    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=3600,
            env=env,
        )
    except subprocess.TimeoutExpired:
        logger.error("Baseline run timed out after 3600s")
        return None, 1

    # The output directory was passed explicitly so it
    # should exist.  Fall back to general lookup only
    # when the explicit dir is absent.
    if output_dir.is_dir():
        return output_dir, result.returncode

    actual_dir = _find_latest_run_dir(
        problem, prefix=None,
    )
    if actual_dir is not None:
        return actual_dir, result.returncode
    return output_dir, result.returncode


def run_two_agent(
    problem: str,
    model: str,
    budget: float,
    budget_split: int,
    implementer_prompt: str,
    reviewer_prompt: str,
) -> tuple[Path | None, int]:
    """Run the two-agent runner.

    Returns (output_dir, exit_code).
    """
    cmd = [
        sys.executable,
        str(RUNNER_PATH),
        "--problem", problem,
        "--model", model,
        "--budget", str(budget),
        "--budget-split", str(budget_split),
        "--implementer-prompt", implementer_prompt,
        "--reviewer-prompt", reviewer_prompt,
    ]

    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }

    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=3600,
            env=env,
        )
    except subprocess.TimeoutExpired:
        logger.error("Two-agent run timed out after 3600s")
        return None, 1

    # Find the actual output directory.  The runner
    # names its dirs ``two_agent_...`` by default, but
    # fall back to any directory containing the problem.
    actual_dir = _find_latest_run_dir(
        problem, prefix="two_agent",
    )
    if actual_dir is None:
        actual_dir = _find_latest_run_dir(
            problem, prefix=None,
        )
    if actual_dir is not None:
        return actual_dir, result.returncode
    return None, result.returncode


def run_eval(output_dir: Path) -> int:
    """Run ``slop-code eval`` on *output_dir*.

    Returns the exit code.
    """
    cmd = [
        sys.executable, "-m", "slop_code",
        "eval",
        str(output_dir),
    ]

    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }

    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=600,
            env=env,
        )
    except subprocess.TimeoutExpired:
        logger.error("Eval timed out after 600s")
        return 1

    return result.returncode


def _find_latest_run_dir(
    problem: str,
    prefix: str | None = None,
) -> Path | None:
    """Find the most recent output dir containing *problem*.

    When *prefix* is given, only directories whose name
    starts with *prefix* are considered.  When *prefix*
    is ``None``, all directories are scanned.
    """
    if not OUTPUTS_DIR.exists():
        return None
    candidates: list[tuple[float, Path]] = []
    for d in OUTPUTS_DIR.iterdir():
        if not d.is_dir():
            continue
        if prefix is not None and not d.name.startswith(
            prefix,
        ):
            continue
        prob_dir = d / problem
        if prob_dir.is_dir():
            candidates.append((d.stat().st_mtime, d))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


# -------------------------------------------------------------------
# Build experiment rows
# -------------------------------------------------------------------


def build_experiment_row(
    problem: str,
    model: str,
    mode: str,
    budget: float,
    metrics: EvalMetrics,
    budget_split: int | None = None,
    implementer_prompt: str | None = None,
    reviewer_prompt: str | None = None,
    hypothesis_id: str | None = None,
    manipulation_check: str = "skipped",
    manipulation_notes: str | None = None,
    results_valid: bool = False,  # noqa: FBT001, FBT002
    baseline_pass_rate: float | None = None,
    delta_pass_rate: float | None = None,
    delta_erosion: float | None = None,
) -> ExperimentRow:
    """Build an ``ExperimentRow`` from eval metrics."""
    return ExperimentRow(
        problem_id=problem,
        model=model,
        mode=mode,
        hypothesis_id=hypothesis_id,
        implementer_prompt=implementer_prompt,
        reviewer_prompt=reviewer_prompt,
        budget_split=budget_split,
        budget_usd=budget,
        pass_rates=metrics.pass_rates,
        erosion_scores=metrics.erosion_scores,
        verbosity_scores=metrics.verbosity_scores,
        tokens_implementer=metrics.tokens_implementer,
        tokens_reviewer=metrics.tokens_reviewer,
        cost_per_checkpoint=metrics.cost_per_checkpoint,
        total_pass_rate=metrics.total_pass_rate,
        total_cost=metrics.total_cost,
        erosion_slope=metrics.erosion_slope,
        verbosity_slope=metrics.verbosity_slope,
        baseline_pass_rate=baseline_pass_rate,
        delta_pass_rate=delta_pass_rate,
        delta_erosion=delta_erosion,
        manipulation_check=manipulation_check,
        manipulation_notes=manipulation_notes,
        results_valid=results_valid,
    )


def compute_deltas(
    baseline: EvalMetrics,
    two_agent: EvalMetrics,
) -> tuple[float, float]:
    """Compute delta_pass_rate and delta_erosion.

    delta_pass_rate = two_agent - baseline total pass rate
    delta_erosion = two_agent - baseline erosion slope
    """
    dp = round(
        two_agent.total_pass_rate
        - baseline.total_pass_rate,
        4,
    )
    de = round(
        two_agent.erosion_slope
        - baseline.erosion_slope,
        4,
    )
    return dp, de


# -------------------------------------------------------------------
# Pipeline
# -------------------------------------------------------------------


def run_pipeline(
    problem: str,
    model: str,
    budget: float,
    budget_split: int = 70,
    implementer_prompt: str = DEFAULT_IMPLEMENTER_PROMPT,
    reviewer_prompt: str = DEFAULT_REVIEWER_PROMPT,
    hypothesis_id: str | None = None,
    dolt_conn: Any | None = None,
    environment: str = DEFAULT_ENVIRONMENT,
) -> PipelineResult:
    """Execute the full experiment pipeline.

    Steps:
      1. Check Dolt budget table (refuses if insufficient).
      2. Run single-agent baseline via ``slop-code run``.
      3. Run two-agent experiment via ``two_agent_runner``.
      4. Evaluate both outputs via ``slop-code eval``.
      5. Compute delta_pass_rate and delta_erosion.
      6. Insert rows into Dolt experiments table.
      7. Update Dolt budget table with actual spend.

    Both arms use the same model and budget for fair
    comparison.
    """
    # Ensure the NVIDIA model-name proxy is running
    # (required for Claude Code + NVIDIA NIM endpoint).
    from two_agent_runner import ensure_nvidia_proxy

    try:
        ensure_nvidia_proxy()
        typer.echo("NVIDIA proxy: running on port 8200")
    except Exception as exc:  # noqa: BLE001
        typer.echo(
            f"Warning: NVIDIA proxy not started: {exc}",
            err=True,
        )

    result = PipelineResult(
        problem=problem,
        model=model,
        budget=budget,
        budget_split=budget_split,
    )

    # ── Step 1: Budget check ──────────────────────────
    if dolt_conn is not None:
        try:
            sufficient, remaining = check_budget(
                dolt_conn, budget * 2,
            )
            if not sufficient:
                result.errors.append(
                    f"Insufficient budget: ${remaining:.2f} "
                    f"remaining, need ${budget * 2:.2f} "
                    f"(${budget:.2f} per arm)",
                )
                return result
        except Exception as exc:  # noqa: BLE001
            result.errors.append(
                f"Budget check failed: {exc}",
            )
            return result

    # ── Step 2: Baseline run ──────────────────────────
    typer.echo(
        f"Running baseline (single-agent) on "
        f"{problem} with {model} ...",
    )
    baseline_dir, baseline_rc = run_baseline(
        problem=problem,
        model=model,
        budget=budget,
        prompt=implementer_prompt,
        environment=environment,
    )

    if baseline_dir is not None:
        result.baseline_output_dir = str(baseline_dir)

    if baseline_rc != 0 and baseline_dir is None:
        result.errors.append(
            f"Baseline run failed (exit code {baseline_rc})",
        )
        result.partial = True

    # ── Step 3: Two-agent run ─────────────────────────
    typer.echo(
        f"Running two-agent on {problem} with {model} "
        f"(split {budget_split}/{100 - budget_split}) ...",
    )
    ta_dir, ta_rc = run_two_agent(
        problem=problem,
        model=model,
        budget=budget,
        budget_split=budget_split,
        implementer_prompt=implementer_prompt,
        reviewer_prompt=reviewer_prompt,
    )

    if ta_dir is not None:
        result.two_agent_output_dir = str(ta_dir)

    if ta_rc != 0 and ta_dir is None:
        result.errors.append(
            f"Two-agent run failed (exit code {ta_rc})",
        )
        result.partial = True

    if ta_rc != 0 and ta_dir is not None:
        # Budget exceeded mid-run: still has partial results
        result.budget_exceeded = True
        result.partial = True

    # ── Step 4: Evaluate both ─────────────────────────
    baseline_metrics = EvalMetrics()
    ta_metrics = EvalMetrics()

    if baseline_dir is not None and baseline_dir.exists():
        typer.echo("Evaluating baseline output ...")
        eval_rc = run_eval(baseline_dir)
        if eval_rc != 0:
            result.errors.append(
                "Baseline eval failed "
                f"(exit code {eval_rc})",
            )
        baseline_metrics = parse_eval_results(
            baseline_dir, problem,
        )
        result.baseline_metrics = baseline_metrics

    if ta_dir is not None and ta_dir.exists():
        typer.echo("Evaluating two-agent output ...")
        eval_rc = run_eval(ta_dir)
        if eval_rc != 0:
            result.errors.append(
                "Two-agent eval failed "
                f"(exit code {eval_rc})",
            )
        ta_metrics = parse_eval_results(ta_dir, problem)
        result.two_agent_metrics = ta_metrics

    # ── Step 4.5: Checkpoint parity check ────────────
    if (
        baseline_dir is not None
        and ta_dir is not None
        and baseline_dir.exists()
        and ta_dir.exists()
        and not verify_matching_checkpoints(
            baseline_dir, ta_dir, problem,
        )
    ):
        result.errors.append(
            "Checkpoint mismatch: baseline and "
            "two-agent arms produced different "
            "checkpoint directories.",
        )

    # ── Step 5: Compute deltas ────────────────────────
    delta_pr, delta_er = compute_deltas(
        baseline_metrics, ta_metrics,
    )
    result.delta_pass_rate = delta_pr
    result.delta_erosion = delta_er

    # ── Step 6: Build and insert rows ─────────────────
    baseline_row = build_experiment_row(
        problem=problem,
        model=model,
        mode="single",
        budget=budget,
        metrics=baseline_metrics,
        implementer_prompt=implementer_prompt,
        hypothesis_id=hypothesis_id,
        manipulation_check="skipped",
        results_valid=bool(baseline_metrics.pass_rates),
    )
    result.baseline_row = baseline_row

    ta_row = build_experiment_row(
        problem=problem,
        model=model,
        mode="two-agent",
        budget=budget,
        metrics=ta_metrics,
        budget_split=budget_split,
        implementer_prompt=implementer_prompt,
        reviewer_prompt=reviewer_prompt,
        hypothesis_id=hypothesis_id,
        manipulation_check="skipped",
        results_valid=bool(ta_metrics.pass_rates),
        baseline_pass_rate=baseline_metrics.total_pass_rate,
        delta_pass_rate=delta_pr,
        delta_erosion=delta_er,
    )
    result.two_agent_row = ta_row

    if dolt_conn is not None:
        try:
            insert_experiment_row(dolt_conn, baseline_row)
            insert_experiment_row(dolt_conn, ta_row)
            typer.echo(
                "Inserted experiment rows into Dolt.",
            )
        except Exception as exc:  # noqa: BLE001
            result.errors.append(
                f"Dolt INSERT failed: {exc}",
            )

        # ── Step 7: Update budget ─────────────────────
        total_cost = (
            baseline_metrics.total_cost
            + ta_metrics.total_cost
        )
        try:
            update_budget_spent(dolt_conn, total_cost)
            typer.echo(
                f"Budget updated: +${total_cost:.2f}",
            )
        except Exception as exc:  # noqa: BLE001
            result.errors.append(
                f"Budget UPDATE failed: {exc}",
            )

    # ── Summary ───────────────────────────────────────
    typer.echo(
        f"\nPipeline complete for {problem}.\n"
        f"  Baseline pass rate: "
        f"{baseline_metrics.total_pass_rate:.4f}\n"
        f"  Two-agent pass rate: "
        f"{ta_metrics.total_pass_rate:.4f}\n"
        f"  Delta pass rate: {delta_pr:+.4f}\n"
        f"  Delta erosion:   {delta_er:+.4f}"
    )

    return result


# -------------------------------------------------------------------
# Typer CLI
# -------------------------------------------------------------------

app = typer.Typer(
    name="experiment-pipeline",
    help=(
        "Run a baseline vs. two-agent experiment on "
        "a SlopCodeBench problem, evaluate both, and "
        "write results to Dolt."
    ),
    add_completion=False,
)


@app.command()
def main(
    problem: str = typer.Option(
        ...,
        "--problem",
        help="Problem name to run.",
    ),
    model: str = typer.Option(
        ...,
        "--model",
        help="Model name or alias.",
    ),
    budget: float = typer.Option(
        ...,
        "--budget",
        help=(
            "Maximum spend per arm in USD. Both arms "
            "use this same budget."
        ),
    ),
    budget_split: int = typer.Option(
        70,
        "--budget-split",
        help=(
            "Percentage of per-checkpoint budget for "
            "the implementer (1-99). Used for the "
            "two-agent arm only."
        ),
    ),
    implementer_prompt: str = typer.Option(
        DEFAULT_IMPLEMENTER_PROMPT,
        "--implementer-prompt",
        help="Path to implementer Jinja prompt template.",
    ),
    reviewer_prompt: str = typer.Option(
        DEFAULT_REVIEWER_PROMPT,
        "--reviewer-prompt",
        help="Path to reviewer Jinja prompt template.",
    ),
    hypothesis_id: str | None = typer.Option(
        None,
        "--hypothesis-id",
        help="Bead ID of the hypothesis being tested.",
    ),
    environment: str = typer.Option(
        DEFAULT_ENVIRONMENT,
        "--environment",
        help="Path to environment config.",
    ),
    use_dolt: bool = typer.Option(  # noqa: FBT001
        True,  # noqa: FBT003
        "--use-dolt/--no-dolt",
        help="Write results to Dolt (default: yes).",
    ),
    dolt_host: str = typer.Option(
        DOLT_HOST,
        "--dolt-host",
        help="Dolt server host.",
    ),
    dolt_port: int = typer.Option(
        DOLT_PORT,
        "--dolt-port",
        help="Dolt server port.",
    ),
) -> None:
    """Run baseline vs. two-agent experiment pipeline."""

    # Validate budget_split
    if budget_split < 1 or budget_split > 99:
        typer.echo(
            f"Error: --budget-split must be in range "
            f"1-99, got {budget_split}",
            err=True,
        )
        raise SystemExit(1)

    # Validate problem
    prob_dir = PROBLEMS_DIR / problem
    if not prob_dir.is_dir():
        typer.echo(
            f"Error: unknown problem '{problem}'.",
            err=True,
        )
        raise SystemExit(1)

    # Connect to Dolt if requested
    dolt_conn = None
    if use_dolt:
        try:
            dolt_conn = get_dolt_connection(
                host=dolt_host, port=dolt_port,
            )
            typer.echo("Connected to Dolt.")
        except Exception as exc:  # noqa: BLE001
            typer.echo(
                f"Warning: Could not connect to Dolt: "
                f"{exc}. Running without Dolt.",
                err=True,
            )

    try:
        result = run_pipeline(
            problem=problem,
            model=model,
            budget=budget,
            budget_split=budget_split,
            implementer_prompt=implementer_prompt,
            reviewer_prompt=reviewer_prompt,
            hypothesis_id=hypothesis_id,
            dolt_conn=dolt_conn,
            environment=environment,
        )
    finally:
        if dolt_conn is not None:
            dolt_conn.close()

    if result.errors:
        typer.echo("\nErrors:", err=True)
        for err in result.errors:
            typer.echo(f"  - {err}", err=True)

    if result.partial:
        typer.echo(
            "\nPartial results saved.", err=True,
        )
        raise SystemExit(1)

    # Propagate non-zero exit on critical errors
    # (eval failures, Dolt write failures, checkpoint
    # mismatches) even when the run is not partial.
    if result.errors:
        raise SystemExit(1)


if __name__ == "__main__":
    app()
