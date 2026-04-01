"""Tests for research/runner/experiment_pipeline.py.

Covers the validation assertions:
  VAL-PIPELINE-001 through VAL-PIPELINE-012
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_PATH = (
    REPO_ROOT
    / "research"
    / "runner"
    / "experiment_pipeline.py"
)


def _load_pipeline():
    """Import the pipeline module."""
    spec = importlib.util.spec_from_file_location(
        "experiment_pipeline", str(PIPELINE_PATH),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["experiment_pipeline"] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_cli(
    *args: str,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Invoke experiment_pipeline.py as a subprocess."""
    cmd = [sys.executable, str(PIPELINE_PATH), *args]
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        env=merged_env,
        timeout=30,
    )


# -------------------------------------------------------------------
# Module import tests
# -------------------------------------------------------------------


class TestPipelineImport:
    """Pipeline module is importable and exports core types."""

    def test_module_importable(self):
        mod = _load_pipeline()
        assert mod is not None

    def test_app_exists(self):
        mod = _load_pipeline()
        assert hasattr(mod, "app")

    def test_eval_metrics_model(self):
        mod = _load_pipeline()
        m = mod.EvalMetrics(
            pass_rates=[0.8, 0.9],
            total_pass_rate=0.85,
            checkpoint_count=2,
        )
        assert m.total_pass_rate == 0.85
        assert len(m.pass_rates) == 2

    def test_experiment_row_model(self):
        mod = _load_pipeline()
        row = mod.ExperimentRow(
            problem_id="file_backup",
            model="opus-4.5",
            mode="single",
        )
        assert row.problem_id == "file_backup"
        assert row.mode == "single"
        assert row.manipulation_check == "skipped"

    def test_pipeline_result_model(self):
        mod = _load_pipeline()
        r = mod.PipelineResult(
            problem="test",
            model="test",
            budget=5.0,
            budget_split=70,
        )
        assert r.problem == "test"
        assert r.errors == []
        assert r.partial is False


# -------------------------------------------------------------------
# CLI tests
# -------------------------------------------------------------------


class TestCLI:
    """Pipeline CLI accepts required arguments."""

    def test_help_output(self):
        result = _run_cli("--help")
        assert result.returncode == 0
        for flag in [
            "--problem",
            "--model",
            "--budget",
            "--budget-split",
            "--implementer-prompt",
            "--reviewer-prompt",
            "--hypothesis-id",
            "--use-dolt",
        ]:
            assert flag in result.stdout, (
                f"Missing flag {flag} in --help"
            )

    def test_missing_required_args(self):
        result = _run_cli("--no-dolt")
        assert result.returncode != 0

    def test_invalid_budget_split(self):
        result = _run_cli(
            "--problem", "file_backup",
            "--model", "test",
            "--budget", "1.0",
            "--budget-split", "0",
            "--no-dolt",
        )
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "1-99" in combined or "range" in combined.lower()

    def test_invalid_problem(self):
        result = _run_cli(
            "--problem", "nonexistent_problem_xyz",
            "--model", "test",
            "--budget", "1.0",
            "--no-dolt",
        )
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "nonexistent_problem_xyz" in combined


# -------------------------------------------------------------------
# Eval metrics parsing
# -------------------------------------------------------------------


class TestParseEvalResults:
    """VAL-PIPELINE-001 / VAL-PIPELINE-002: Parse eval output."""

    def test_parses_checkpoint_results_jsonl(
        self, tmp_path: Path,
    ):
        """Reads pass rates from checkpoint_results.jsonl."""
        mod = _load_pipeline()
        results = tmp_path / "checkpoint_results.jsonl"
        lines = [
            json.dumps({
                "problem_name": "p",
                "checkpoint_name": f"checkpoint_{i}",
                "pass_counts": pc,
                "total_counts": 10,
            })
            for i, pc in enumerate([8, 9, 10], start=1)
        ]
        results.write_text("\n".join(lines) + "\n")

        metrics = mod.parse_eval_results(tmp_path, "p")
        assert len(metrics.pass_rates) == 3
        assert metrics.pass_rates[0] == pytest.approx(0.8)
        assert metrics.pass_rates[1] == pytest.approx(0.9)
        assert metrics.pass_rates[2] == pytest.approx(1.0)
        assert metrics.total_pass_rate == pytest.approx(0.9)
        assert metrics.checkpoint_count == 3

    def test_parses_flattened_strict_pass_rate(
        self, tmp_path: Path,
    ):
        """Reads pass rates from flattened strict_pass_rate
        keys (the real slop-code eval schema)."""
        mod = _load_pipeline()
        results = tmp_path / "checkpoint_results.jsonl"
        lines = [
            json.dumps({
                "problem": "p",
                "checkpoint": f"checkpoint_{i}",
                "strict_pass_rate": pr,
                "total_tests": 10,
                "passed_tests": int(pr * 10),
            })
            for i, pr in enumerate(
                [0.8, 0.9, 1.0], start=1,
            )
        ]
        results.write_text("\n".join(lines) + "\n")

        metrics = mod.parse_eval_results(tmp_path, "p")
        assert len(metrics.pass_rates) == 3
        assert metrics.pass_rates[0] == pytest.approx(0.8)
        assert metrics.pass_rates[1] == pytest.approx(0.9)
        assert metrics.pass_rates[2] == pytest.approx(1.0)
        assert metrics.total_pass_rate == pytest.approx(
            0.9,
        )

    def test_handles_missing_file(self, tmp_path: Path):
        """Returns empty metrics when file is absent."""
        mod = _load_pipeline()
        metrics = mod.parse_eval_results(tmp_path, "p")
        assert metrics.pass_rates == []
        assert metrics.total_pass_rate == 0.0
        assert metrics.checkpoint_count == 0

    def test_handles_empty_file(self, tmp_path: Path):
        """Returns empty metrics for an empty file."""
        mod = _load_pipeline()
        (tmp_path / "checkpoint_results.jsonl").write_text("")
        metrics = mod.parse_eval_results(tmp_path, "p")
        assert metrics.pass_rates == []

    def test_handles_malformed_json(self, tmp_path: Path):
        """Skips malformed lines gracefully."""
        mod = _load_pipeline()
        results = tmp_path / "checkpoint_results.jsonl"
        good = json.dumps({
            "pass_counts": 8, "total_counts": 10,
        })
        results.write_text(f"{good}\n{{bad\n")
        metrics = mod.parse_eval_results(tmp_path, "p")
        assert len(metrics.pass_rates) == 1

    def test_merges_two_agent_metrics(self, tmp_path: Path):
        """Merges per-checkpoint data from two_agent_metrics."""
        mod = _load_pipeline()

        results = tmp_path / "checkpoint_results.jsonl"
        results.write_text(
            json.dumps({
                "pass_counts": 8, "total_counts": 10,
            }) + "\n",
        )

        ta = {
            "cumulative_cost": 0.15,
            "checkpoints": {
                "checkpoint_1": {
                    "erosion": 0.1,
                    "verbosity": 0.2,
                    "tokens_implementer": 500,
                    "tokens_reviewer": 200,
                    "cost": 0.15,
                },
            },
        }
        (tmp_path / "two_agent_metrics.json").write_text(
            json.dumps(ta),
        )

        metrics = mod.parse_eval_results(tmp_path, "p")
        assert metrics.erosion_scores == [0.1]
        assert metrics.verbosity_scores == [0.2]
        assert metrics.tokens_implementer == [500]
        assert metrics.tokens_reviewer == [200]
        assert metrics.cost_per_checkpoint == [0.15]
        assert metrics.total_cost == pytest.approx(0.15)


# -------------------------------------------------------------------
# Slope computation
# -------------------------------------------------------------------


class TestComputeSlope:
    """Slope computation for erosion and verbosity."""

    def test_empty_values(self):
        mod = _load_pipeline()
        assert mod._compute_slope([]) == 0.0

    def test_single_value(self):
        mod = _load_pipeline()
        assert mod._compute_slope([1.0]) == 0.0

    def test_constant_values(self):
        mod = _load_pipeline()
        assert mod._compute_slope([5.0, 5.0, 5.0]) == 0.0

    def test_increasing_values(self):
        mod = _load_pipeline()
        slope = mod._compute_slope([1.0, 2.0, 3.0])
        assert slope == pytest.approx(1.0)

    def test_decreasing_values(self):
        mod = _load_pipeline()
        slope = mod._compute_slope([3.0, 2.0, 1.0])
        assert slope == pytest.approx(-1.0)


# -------------------------------------------------------------------
# Compute deltas
# -------------------------------------------------------------------


class TestComputeDeltas:
    """VAL-PIPELINE-012: Delta computation."""

    def test_positive_delta(self):
        """Two-agent outperforms baseline."""
        mod = _load_pipeline()
        baseline = mod.EvalMetrics(
            total_pass_rate=0.7,
            erosion_slope=0.1,
        )
        two_agent = mod.EvalMetrics(
            total_pass_rate=0.9,
            erosion_slope=0.05,
        )
        dp, de = mod.compute_deltas(baseline, two_agent)
        assert dp == pytest.approx(0.2)
        assert de == pytest.approx(-0.05)

    def test_negative_delta(self):
        """Baseline outperforms two-agent."""
        mod = _load_pipeline()
        baseline = mod.EvalMetrics(
            total_pass_rate=0.9,
            erosion_slope=0.05,
        )
        two_agent = mod.EvalMetrics(
            total_pass_rate=0.7,
            erosion_slope=0.1,
        )
        dp, de = mod.compute_deltas(baseline, two_agent)
        assert dp == pytest.approx(-0.2)
        assert de == pytest.approx(0.05)

    def test_zero_delta(self):
        """Identical performance."""
        mod = _load_pipeline()
        baseline = mod.EvalMetrics(
            total_pass_rate=0.8,
            erosion_slope=0.1,
        )
        two_agent = mod.EvalMetrics(
            total_pass_rate=0.8,
            erosion_slope=0.1,
        )
        dp, de = mod.compute_deltas(baseline, two_agent)
        assert dp == pytest.approx(0.0)
        assert de == pytest.approx(0.0)


# -------------------------------------------------------------------
# Build experiment rows
# -------------------------------------------------------------------


class TestBuildExperimentRow:
    """Row construction from eval metrics."""

    def test_baseline_row(self):
        mod = _load_pipeline()
        metrics = mod.EvalMetrics(
            pass_rates=[0.8, 0.9],
            erosion_scores=[0.1, 0.15],
            total_pass_rate=0.85,
            total_cost=1.50,
            erosion_slope=0.05,
            verbosity_slope=0.02,
            checkpoint_count=2,
        )
        row = mod.build_experiment_row(
            problem="file_backup",
            model="opus-4.5",
            mode="single",
            budget=5.0,
            metrics=metrics,
        )
        assert row.mode == "single"
        assert row.problem_id == "file_backup"
        assert row.pass_rates == [0.8, 0.9]
        assert row.total_pass_rate == 0.85
        assert row.budget_usd == 5.0
        assert row.manipulation_check == "skipped"

    def test_two_agent_row_with_deltas(self):
        mod = _load_pipeline()
        metrics = mod.EvalMetrics(
            pass_rates=[0.9, 0.95],
            total_pass_rate=0.925,
            total_cost=2.0,
            erosion_slope=0.03,
        )
        row = mod.build_experiment_row(
            problem="file_backup",
            model="opus-4.5",
            mode="two-agent",
            budget=5.0,
            metrics=metrics,
            budget_split=70,
            implementer_prompt="impl.jinja",
            reviewer_prompt="rev.jinja",
            baseline_pass_rate=0.85,
            delta_pass_rate=0.075,
            delta_erosion=-0.02,
        )
        assert row.mode == "two-agent"
        assert row.budget_split == 70
        assert row.baseline_pass_rate == 0.85
        assert row.delta_pass_rate == 0.075
        assert row.delta_erosion == -0.02


# -------------------------------------------------------------------
# Budget check
# -------------------------------------------------------------------


class TestBudgetCheck:
    """VAL-PIPELINE-006: Budget check before starting."""

    def test_sufficient_budget(self):
        mod = _load_pipeline()
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (Decimal("100.00"),)
        conn.cursor.return_value.__enter__ = (
            lambda self: cursor
        )
        conn.cursor.return_value.__exit__ = (
            lambda self, *a: None
        )

        sufficient, remaining = mod.check_budget(
            conn, 10.0,
        )
        assert sufficient is True
        assert remaining == 100.0

    def test_insufficient_budget(self):
        mod = _load_pipeline()
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (Decimal("5.00"),)
        conn.cursor.return_value.__enter__ = (
            lambda self: cursor
        )
        conn.cursor.return_value.__exit__ = (
            lambda self, *a: None
        )

        sufficient, remaining = mod.check_budget(
            conn, 10.0,
        )
        assert sufficient is False
        assert remaining == 5.0

    def test_empty_budget_table(self):
        mod = _load_pipeline()
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn.cursor.return_value.__enter__ = (
            lambda self: cursor
        )
        conn.cursor.return_value.__exit__ = (
            lambda self, *a: None
        )

        sufficient, remaining = mod.check_budget(
            conn, 10.0,
        )
        assert sufficient is False
        assert remaining == 0.0


# -------------------------------------------------------------------
# Budget update
# -------------------------------------------------------------------


class TestBudgetUpdate:
    """VAL-PIPELINE-005: Budget spent updated with actual cost."""

    def test_update_spent(self):
        mod = _load_pipeline()
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = (
            lambda self: cursor
        )
        conn.cursor.return_value.__exit__ = (
            lambda self, *a: None
        )

        mod.update_budget_spent(conn, 3.50)
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args
        assert "spent = spent +" in call_args[0][0]
        assert call_args[0][1] == (3.50,)


# -------------------------------------------------------------------
# Insert experiment row
# -------------------------------------------------------------------


class TestInsertExperimentRow:
    """VAL-PIPELINE-004: Insert rows into Dolt experiments."""

    def test_insert_with_all_columns(self):
        mod = _load_pipeline()
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (42,)
        conn.cursor.return_value.__enter__ = (
            lambda self: cursor
        )
        conn.cursor.return_value.__exit__ = (
            lambda self, *a: None
        )

        row = mod.ExperimentRow(
            problem_id="file_backup",
            model="opus-4.5",
            mode="single",
            budget_usd=5.0,
            pass_rates=[0.8, 0.9],
            erosion_scores=[0.1, 0.15],
            verbosity_scores=[0.2, 0.25],
            tokens_implementer=[500, 600],
            tokens_reviewer=[0, 0],
            cost_per_checkpoint=[0.5, 0.6],
            total_pass_rate=0.85,
            total_cost=1.10,
            erosion_slope=0.05,
            verbosity_slope=0.025,
            manipulation_check="skipped",
            results_valid=True,
        )

        row_id = mod.insert_experiment_row(conn, row)
        assert row_id == 42

        # Check the INSERT was called
        insert_call = cursor.execute.call_args_list[0]
        sql = insert_call[0][0]
        assert "INSERT INTO experiments" in sql
        values = insert_call[0][1]
        # Should have 25 values (matching 25 columns)
        assert len(values) == 25
        # JSON arrays
        assert values[8] == json.dumps([0.8, 0.9])
        assert values[9] == json.dumps([0.1, 0.15])

    def test_insert_preserves_json_arrays(self):
        """JSON columns store per-checkpoint arrays."""
        mod = _load_pipeline()
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        conn.cursor.return_value.__enter__ = (
            lambda self: cursor
        )
        conn.cursor.return_value.__exit__ = (
            lambda self, *a: None
        )

        row = mod.ExperimentRow(
            problem_id="p",
            model="m",
            mode="single",
            pass_rates=[0.5, 0.6, 0.7],
            cost_per_checkpoint=[0.1, 0.2, 0.3],
        )

        mod.insert_experiment_row(conn, row)
        values = cursor.execute.call_args_list[0][0][1]
        # pass_rates is at index 8
        parsed = json.loads(values[8])
        assert parsed == [0.5, 0.6, 0.7]


# -------------------------------------------------------------------
# Checkpoint verification
# -------------------------------------------------------------------


class TestVerifyMatchingCheckpoints:
    """VAL-PIPELINE-003: Both arms have same checkpoints."""

    def test_matching_checkpoints(self, tmp_path: Path):
        mod = _load_pipeline()
        base = tmp_path / "baseline"
        ta = tmp_path / "two_agent"

        for d in [base, ta]:
            prob = d / "file_backup"
            for i in range(1, 4):
                (prob / f"checkpoint_{i}").mkdir(
                    parents=True,
                )

        assert mod.verify_matching_checkpoints(
            base, ta, "file_backup",
        ) is True

    def test_mismatched_checkpoints(self, tmp_path: Path):
        mod = _load_pipeline()
        base = tmp_path / "baseline"
        ta = tmp_path / "two_agent"

        base_prob = base / "file_backup"
        for i in range(1, 4):
            (base_prob / f"checkpoint_{i}").mkdir(
                parents=True,
            )

        ta_prob = ta / "file_backup"
        for i in range(1, 3):
            (ta_prob / f"checkpoint_{i}").mkdir(
                parents=True,
            )

        assert mod.verify_matching_checkpoints(
            base, ta, "file_backup",
        ) is False

    def test_missing_problem_dir(self, tmp_path: Path):
        mod = _load_pipeline()
        base = tmp_path / "baseline"
        base.mkdir()
        ta = tmp_path / "two_agent"
        ta.mkdir()

        assert mod.verify_matching_checkpoints(
            base, ta, "file_backup",
        ) is True  # Both empty == matching


# -------------------------------------------------------------------
# Get checkpoints
# -------------------------------------------------------------------


class TestGetCheckpoints:
    """Checkpoint discovery from problem directory."""

    def test_finds_checkpoints(self, tmp_path: Path):
        mod = _load_pipeline()
        prob = tmp_path / "problems" / "test_prob"
        for i in range(1, 4):
            (prob / f"checkpoint_{i}").mkdir(parents=True)
        # Also a non-checkpoint dir
        (prob / "tests").mkdir(parents=True)

        with patch.object(
            mod, "PROBLEMS_DIR", tmp_path / "problems",
        ):
            cps = mod.get_checkpoints("test_prob")

        assert cps == [
            "checkpoint_1",
            "checkpoint_2",
            "checkpoint_3",
        ]

    def test_empty_for_missing_problem(self):
        mod = _load_pipeline()
        with patch.object(
            mod, "PROBLEMS_DIR",
            Path("/nonexistent"),
        ):
            assert mod.get_checkpoints("nope") == []


# -------------------------------------------------------------------
# Pipeline integration (mocked subprocess calls)
# -------------------------------------------------------------------


class TestRunPipeline:
    """VAL-PIPELINE-001 through VAL-PIPELINE-012."""

    @pytest.fixture()
    def mock_env(self, tmp_path):
        """Create a mock environment for pipeline."""
        mod = _load_pipeline()

        # Create problem dir
        prob = tmp_path / "problems" / "test_prob"
        for i in range(1, 3):
            (prob / f"checkpoint_{i}").mkdir(parents=True)

        # Create baseline output
        base_out = tmp_path / "outputs" / "baseline_run"
        base_prob = base_out / "test_prob"
        for i in range(1, 3):
            cp = base_prob / f"checkpoint_{i}"
            cp.mkdir(parents=True)
        (base_out / "checkpoint_results.jsonl").write_text(
            json.dumps({
                "pass_counts": 8, "total_counts": 10,
            }) + "\n"
            + json.dumps({
                "pass_counts": 9, "total_counts": 10,
            }) + "\n",
        )
        (base_out / "environment.yaml").write_text(
            "runtime: docker\n",
        )

        # Create two-agent output
        ta_out = tmp_path / "outputs" / "two_agent_run"
        ta_prob = ta_out / "test_prob"
        for i in range(1, 3):
            cp = ta_prob / f"checkpoint_{i}"
            cp.mkdir(parents=True)
        (ta_out / "checkpoint_results.jsonl").write_text(
            json.dumps({
                "pass_counts": 9, "total_counts": 10,
            }) + "\n"
            + json.dumps({
                "pass_counts": 10, "total_counts": 10,
            }) + "\n",
        )
        (ta_out / "two_agent_metrics.json").write_text(
            json.dumps({
                "cumulative_cost": 0.30,
                "checkpoints": {
                    "checkpoint_1": {
                        "erosion": 0.1,
                        "verbosity": 0.2,
                        "tokens_implementer": 500,
                        "tokens_reviewer": 200,
                        "cost": 0.15,
                    },
                    "checkpoint_2": {
                        "erosion": 0.15,
                        "verbosity": 0.25,
                        "tokens_implementer": 600,
                        "tokens_reviewer": 300,
                        "cost": 0.15,
                    },
                },
            }),
        )
        (ta_out / "environment.yaml").write_text(
            "runtime: docker\n",
        )

        return {
            "mod": mod,
            "tmp_path": tmp_path,
            "base_out": base_out,
            "ta_out": ta_out,
        }

    def test_pipeline_happy_path_no_dolt(
        self, mock_env,
    ):
        """Pipeline runs both arms, evaluates, computes deltas
        without Dolt."""
        mod = mock_env["mod"]
        base_out = mock_env["base_out"]
        ta_out = mock_env["ta_out"]

        with (
            patch.object(
                mod, "run_baseline",
                return_value=(base_out, 0),
            ),
            patch.object(
                mod, "run_two_agent",
                return_value=(ta_out, 0),
            ),
            patch.object(
                mod, "run_eval",
                return_value=0,
            ),
        ):
            result = mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                budget_split=70,
                dolt_conn=None,
            )

        assert result.baseline_metrics is not None
        assert result.two_agent_metrics is not None
        assert result.baseline_metrics.total_pass_rate == (
            pytest.approx(0.85)
        )
        assert result.two_agent_metrics.total_pass_rate == (
            pytest.approx(0.95)
        )
        assert result.delta_pass_rate == pytest.approx(0.1)
        assert result.errors == []
        assert result.partial is False

    def test_pipeline_with_dolt(self, mock_env):
        """Pipeline writes to Dolt experiments and budget."""
        mod = mock_env["mod"]
        base_out = mock_env["base_out"]
        ta_out = mock_env["ta_out"]

        conn = MagicMock()
        cursor = MagicMock()
        # Budget check: sufficient
        cursor.fetchone.side_effect = [
            (Decimal("100.00"),),  # budget check
            (1,),   # baseline insert id
            (2,),   # two-agent insert id
        ]
        conn.cursor.return_value.__enter__ = (
            lambda self: cursor
        )
        conn.cursor.return_value.__exit__ = (
            lambda self, *a: None
        )

        with (
            patch.object(
                mod, "run_baseline",
                return_value=(base_out, 0),
            ),
            patch.object(
                mod, "run_two_agent",
                return_value=(ta_out, 0),
            ),
            patch.object(
                mod, "run_eval",
                return_value=0,
            ),
        ):
            result = mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                budget_split=70,
                dolt_conn=conn,
            )

        assert result.errors == []
        # Verify Dolt interactions happened
        calls = cursor.execute.call_args_list
        sqls = [c[0][0] for c in calls]
        # Budget check
        assert any(
            "SELECT remaining" in s for s in sqls
        )
        # Two INSERT INTO experiments
        inserts = [
            s for s in sqls
            if "INSERT INTO experiments" in s
        ]
        assert len(inserts) == 2
        # Budget update
        assert any(
            "UPDATE budget" in s for s in sqls
        )

    def test_pipeline_refuses_insufficient_budget(
        self, mock_env,
    ):
        """VAL-PIPELINE-006: Refuses if budget insufficient."""
        mod = mock_env["mod"]
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (Decimal("1.00"),)
        conn.cursor.return_value.__enter__ = (
            lambda self: cursor
        )
        conn.cursor.return_value.__exit__ = (
            lambda self, *a: None
        )

        result = mod.run_pipeline(
            problem="test_prob",
            model="opus-4.5",
            budget=5.0,
            dolt_conn=conn,
        )

        assert len(result.errors) > 0
        assert "insufficient" in result.errors[0].lower()
        # Should NOT have run anything
        assert result.baseline_output_dir is None
        assert result.two_agent_output_dir is None

    def test_pipeline_partial_on_baseline_failure(
        self, mock_env,
    ):
        """Partial results when baseline fails."""
        mod = mock_env["mod"]
        ta_out = mock_env["ta_out"]

        with (
            patch.object(
                mod, "run_baseline",
                return_value=(None, 1),
            ),
            patch.object(
                mod, "run_two_agent",
                return_value=(ta_out, 0),
            ),
            patch.object(
                mod, "run_eval",
                return_value=0,
            ),
        ):
            result = mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                dolt_conn=None,
            )

        assert result.partial is True
        assert any(
            "baseline" in e.lower()
            for e in result.errors
        )

    def test_pipeline_partial_on_budget_exceeded(
        self, mock_env,
    ):
        """VAL-PIPELINE-008: Partial results on budget
        exceeded."""
        mod = mock_env["mod"]
        base_out = mock_env["base_out"]
        ta_out = mock_env["ta_out"]

        with (
            patch.object(
                mod, "run_baseline",
                return_value=(base_out, 0),
            ),
            patch.object(
                mod, "run_two_agent",
                return_value=(ta_out, 1),
            ),
            patch.object(
                mod, "run_eval",
                return_value=0,
            ),
        ):
            result = mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                dolt_conn=None,
            )

        assert result.budget_exceeded is True
        assert result.partial is True
        # Still has two-agent metrics (partial)
        assert result.two_agent_metrics is not None

    def test_pipeline_both_arms_same_model_budget(
        self, mock_env,
    ):
        """VAL-PIPELINE-013: Both arms use identical model
        and budget."""
        mod = mock_env["mod"]
        base_out = mock_env["base_out"]
        ta_out = mock_env["ta_out"]

        baseline_args = {}
        ta_args = {}

        def capture_baseline(**kwargs):
            baseline_args.update(kwargs)
            return base_out, 0

        def capture_ta(**kwargs):
            ta_args.update(kwargs)
            return ta_out, 0

        with (
            patch.object(
                mod, "run_baseline",
                side_effect=capture_baseline,
            ),
            patch.object(
                mod, "run_two_agent",
                side_effect=capture_ta,
            ),
            patch.object(
                mod, "run_eval",
                return_value=0,
            ),
        ):
            mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                budget_split=70,
                dolt_conn=None,
            )

        assert baseline_args["model"] == ta_args["model"]
        assert baseline_args["budget"] == ta_args["budget"]

    def test_pipeline_rows_have_matching_model_budget(
        self, mock_env,
    ):
        """Both Dolt rows use same model and budget_usd."""
        mod = mock_env["mod"]
        base_out = mock_env["base_out"]
        ta_out = mock_env["ta_out"]

        with (
            patch.object(
                mod, "run_baseline",
                return_value=(base_out, 0),
            ),
            patch.object(
                mod, "run_two_agent",
                return_value=(ta_out, 0),
            ),
            patch.object(
                mod, "run_eval",
                return_value=0,
            ),
        ):
            result = mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                dolt_conn=None,
            )

        assert result.baseline_row is not None
        assert result.two_agent_row is not None
        assert (
            result.baseline_row.model
            == result.two_agent_row.model
        )
        assert (
            result.baseline_row.budget_usd
            == result.two_agent_row.budget_usd
        )

    def test_delta_pass_rate_formula(self, mock_env):
        """delta_pass_rate = two_agent - baseline."""
        mod = mock_env["mod"]
        base_out = mock_env["base_out"]
        ta_out = mock_env["ta_out"]

        with (
            patch.object(
                mod, "run_baseline",
                return_value=(base_out, 0),
            ),
            patch.object(
                mod, "run_two_agent",
                return_value=(ta_out, 0),
            ),
            patch.object(
                mod, "run_eval",
                return_value=0,
            ),
        ):
            result = mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                dolt_conn=None,
            )

        # baseline: (0.8+0.9)/2 = 0.85
        # two-agent: (0.9+1.0)/2 = 0.95
        # delta = 0.95 - 0.85 = 0.10
        assert result.delta_pass_rate == pytest.approx(
            0.1, abs=0.001,
        )

    def test_delta_erosion_formula(self, mock_env):
        """delta_erosion = two_agent - baseline erosion slope."""
        mod = mock_env["mod"]
        base_out = mock_env["base_out"]
        ta_out = mock_env["ta_out"]

        with (
            patch.object(
                mod, "run_baseline",
                return_value=(base_out, 0),
            ),
            patch.object(
                mod, "run_two_agent",
                return_value=(ta_out, 0),
            ),
            patch.object(
                mod, "run_eval",
                return_value=0,
            ),
        ):
            result = mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                dolt_conn=None,
            )

        # Baseline has no erosion data -> slope 0
        # Two-agent has erosion [0.1, 0.15] -> slope 0.05
        # delta_erosion = 0.05 - 0.0 = 0.05
        assert result.delta_erosion == pytest.approx(
            0.05, abs=0.001,
        )

    def test_two_agent_row_has_deltas(self, mock_env):
        """Two-agent row includes delta_pass_rate and
        delta_erosion."""
        mod = mock_env["mod"]
        base_out = mock_env["base_out"]
        ta_out = mock_env["ta_out"]

        with (
            patch.object(
                mod, "run_baseline",
                return_value=(base_out, 0),
            ),
            patch.object(
                mod, "run_two_agent",
                return_value=(ta_out, 0),
            ),
            patch.object(
                mod, "run_eval",
                return_value=0,
            ),
        ):
            result = mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                dolt_conn=None,
            )

        ta_row = result.two_agent_row
        assert ta_row is not None
        assert ta_row.delta_pass_rate is not None
        assert ta_row.delta_erosion is not None
        assert ta_row.baseline_pass_rate is not None

    def test_baseline_row_has_no_deltas(self, mock_env):
        """Baseline row does not have deltas."""
        mod = mock_env["mod"]
        base_out = mock_env["base_out"]
        ta_out = mock_env["ta_out"]

        with (
            patch.object(
                mod, "run_baseline",
                return_value=(base_out, 0),
            ),
            patch.object(
                mod, "run_two_agent",
                return_value=(ta_out, 0),
            ),
            patch.object(
                mod, "run_eval",
                return_value=0,
            ),
        ):
            result = mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                dolt_conn=None,
            )

        base_row = result.baseline_row
        assert base_row is not None
        assert base_row.delta_pass_rate is None
        assert base_row.delta_erosion is None


# -------------------------------------------------------------------
# Experiments table schema (VAL-PIPELINE-010)
# -------------------------------------------------------------------


class TestExperimentsSchema:
    """VAL-PIPELINE-010: 27 columns match spec."""

    def test_experiment_row_has_all_fields(self):
        """ExperimentRow has all columns from Section 8."""
        mod = _load_pipeline()
        fields = mod.ExperimentRow.model_fields
        expected = [
            "problem_id", "model", "mode",
            "hypothesis_id",
            "implementer_prompt", "reviewer_prompt",
            "budget_split", "budget_usd",
            "pass_rates", "erosion_scores",
            "verbosity_scores",
            "tokens_implementer", "tokens_reviewer",
            "cost_per_checkpoint",
            "total_pass_rate", "total_cost",
            "erosion_slope", "verbosity_slope",
            "baseline_pass_rate", "delta_pass_rate",
            "delta_erosion",
            "manipulation_check", "manipulation_notes",
            "results_valid", "impl_diff_summary",
        ]
        for col in expected:
            assert col in fields, (
                f"Missing column {col} in ExperimentRow"
            )

    def test_insert_sql_has_25_columns(self):
        """INSERT statement covers all 25 data columns
        (id and created_at are auto-generated)."""
        mod = _load_pipeline()
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        conn.cursor.return_value.__enter__ = (
            lambda self: cursor
        )
        conn.cursor.return_value.__exit__ = (
            lambda self, *a: None
        )

        row = mod.ExperimentRow(
            problem_id="p",
            model="m",
            mode="single",
        )
        mod.insert_experiment_row(conn, row)

        insert_call = cursor.execute.call_args_list[0]
        values = insert_call[0][1]
        assert len(values) == 25


# -------------------------------------------------------------------
# Manipulation check (VAL-PIPELINE-011)
# -------------------------------------------------------------------


class TestManipulationCheck:
    """VAL-PIPELINE-011: manipulation_check propagated."""

    def test_default_manipulation_check(self):
        mod = _load_pipeline()
        row = mod.ExperimentRow(
            problem_id="p",
            model="m",
            mode="single",
        )
        assert row.manipulation_check == "skipped"

    def test_manipulation_check_propagated(self):
        mod = _load_pipeline()
        metrics = mod.EvalMetrics()
        row = mod.build_experiment_row(
            problem="p",
            model="m",
            mode="single",
            budget=1.0,
            metrics=metrics,
            manipulation_check="passed",
            manipulation_notes="All checks OK",
        )
        assert row.manipulation_check == "passed"
        assert row.manipulation_notes == "All checks OK"

    def test_failed_manipulation_check(self):
        mod = _load_pipeline()
        metrics = mod.EvalMetrics()
        row = mod.build_experiment_row(
            problem="p",
            model="m",
            mode="single",
            budget=1.0,
            metrics=metrics,
            manipulation_check="failed",
            manipulation_notes="Confound detected",
            results_valid=False,
        )
        assert row.manipulation_check == "failed"
        assert row.results_valid is False


# -------------------------------------------------------------------
# Eval metrics tolerance (VAL-PIPELINE-007)
# -------------------------------------------------------------------


class TestMetricsTolerance:
    """VAL-PIPELINE-007: Eval metrics match stored values
    within 0.001 tolerance."""

    def test_metrics_round_trip(self, tmp_path: Path):
        """Parsed metrics match what would be stored in Dolt."""
        mod = _load_pipeline()

        results = tmp_path / "checkpoint_results.jsonl"
        results.write_text(
            json.dumps({
                "pass_counts": 8, "total_counts": 10,
            }) + "\n"
            + json.dumps({
                "pass_counts": 9, "total_counts": 10,
            }) + "\n",
        )

        metrics = mod.parse_eval_results(tmp_path, "p")
        row = mod.build_experiment_row(
            problem="p",
            model="m",
            mode="single",
            budget=1.0,
            metrics=metrics,
        )

        # Verify metrics match within tolerance
        for i, pr in enumerate(metrics.pass_rates):
            assert abs(row.pass_rates[i] - pr) < 0.001
        assert abs(
            row.total_pass_rate - metrics.total_pass_rate,
        ) < 0.001
        assert abs(
            row.erosion_slope - metrics.erosion_slope,
        ) < 0.001
        assert abs(
            row.verbosity_slope - metrics.verbosity_slope,
        ) < 0.001

    def test_delta_tolerance(self):
        """Delta computations are within 0.001 of expected."""
        mod = _load_pipeline()
        baseline = mod.EvalMetrics(
            total_pass_rate=0.85,
            erosion_slope=0.1,
        )
        two_agent = mod.EvalMetrics(
            total_pass_rate=0.92,
            erosion_slope=0.07,
        )
        dp, de = mod.compute_deltas(baseline, two_agent)
        assert abs(dp - 0.07) < 0.001
        assert abs(de - (-0.03)) < 0.001


# -------------------------------------------------------------------
# Partial results on budget-aborted run (VAL-PIPELINE-008)
# -------------------------------------------------------------------


class TestPartialResults:
    """Partial results stored on budget abort."""

    def test_partial_with_dolt(self):
        """Partial results are inserted into Dolt on abort."""
        mod = _load_pipeline()
        # Create minimal output dirs
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            base_out = td_path / "baseline"
            base_out.mkdir()
            (base_out / "checkpoint_results.jsonl").write_text(
                json.dumps({
                    "pass_counts": 5,
                    "total_counts": 10,
                }) + "\n",
            )
            (base_out / "environment.yaml").write_text(
                "runtime: docker\n",
            )

            ta_out = td_path / "two_agent"
            ta_out.mkdir()
            (ta_out / "checkpoint_results.jsonl").write_text(
                json.dumps({
                    "pass_counts": 3,
                    "total_counts": 10,
                }) + "\n",
            )
            (ta_out / "environment.yaml").write_text(
                "runtime: docker\n",
            )

            conn = MagicMock()
            cursor = MagicMock()
            cursor.fetchone.side_effect = [
                (Decimal("100.00"),),  # budget check
                (1,),  # baseline insert id
                (2,),  # ta insert id
            ]
            conn.cursor.return_value.__enter__ = (
                lambda self: cursor
            )
            conn.cursor.return_value.__exit__ = (
                lambda self, *a: None
            )

            with (
                patch.object(
                    mod, "run_baseline",
                    return_value=(base_out, 0),
                ),
                patch.object(
                    mod, "run_two_agent",
                    return_value=(ta_out, 1),
                ),
                patch.object(
                    mod, "run_eval",
                    return_value=0,
                ),
            ):
                result = mod.run_pipeline(
                    problem="test_prob",
                    model="opus-4.5",
                    budget=5.0,
                    dolt_conn=conn,
                )

            assert result.partial is True
            # Still inserted rows
            inserts = [
                c for c in cursor.execute.call_args_list
                if "INSERT INTO experiments" in c[0][0]
            ]
            assert len(inserts) == 2


# -------------------------------------------------------------------
# Checkpoint parity check invoked (fix-canary-pipeline)
# -------------------------------------------------------------------


class TestCheckpointParityInvoked:
    """verify_matching_checkpoints is called in pipeline."""

    def test_parity_check_runs(self, tmp_path: Path):
        """Pipeline calls verify_matching_checkpoints
        before Dolt insert."""
        mod = _load_pipeline()

        base_out = tmp_path / "baseline"
        ta_out = tmp_path / "two_agent"
        for d in [base_out, ta_out]:
            prob = d / "test_prob"
            for i in range(1, 3):
                (prob / f"checkpoint_{i}").mkdir(
                    parents=True,
                )
            (d / "checkpoint_results.jsonl").write_text(
                json.dumps({
                    "strict_pass_rate": 0.8,
                    "total_tests": 10,
                    "passed_tests": 8,
                }) + "\n",
            )

        with (
            patch.object(
                mod, "run_baseline",
                return_value=(base_out, 0),
            ),
            patch.object(
                mod, "run_two_agent",
                return_value=(ta_out, 0),
            ),
            patch.object(
                mod, "run_eval",
                return_value=0,
            ),
            patch.object(
                mod,
                "verify_matching_checkpoints",
                return_value=True,
            ) as mock_verify,
        ):
            mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                dolt_conn=None,
            )

        mock_verify.assert_called_once_with(
            base_out, ta_out, "test_prob",
        )

    def test_mismatch_appends_error(self, tmp_path: Path):
        """Checkpoint mismatch adds error to result."""
        mod = _load_pipeline()

        base_out = tmp_path / "baseline"
        ta_out = tmp_path / "two_agent"
        for d in [base_out, ta_out]:
            d.mkdir(parents=True)
            (d / "checkpoint_results.jsonl").write_text(
                json.dumps({
                    "strict_pass_rate": 0.8,
                }) + "\n",
            )

        with (
            patch.object(
                mod, "run_baseline",
                return_value=(base_out, 0),
            ),
            patch.object(
                mod, "run_two_agent",
                return_value=(ta_out, 0),
            ),
            patch.object(
                mod, "run_eval",
                return_value=0,
            ),
            patch.object(
                mod,
                "verify_matching_checkpoints",
                return_value=False,
            ),
        ):
            result = mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                dolt_conn=None,
            )

        assert any(
            "mismatch" in e.lower()
            for e in result.errors
        )


# -------------------------------------------------------------------
# Non-zero exit on critical errors (fix-canary-pipeline)
# -------------------------------------------------------------------


class TestNonZeroExitOnErrors:
    """CLI exits non-zero on critical eval/Dolt errors."""

    def test_exit_nonzero_on_eval_failure(
        self, tmp_path: Path,
    ):
        """Pipeline records error when eval fails."""
        mod = _load_pipeline()

        base_out = tmp_path / "baseline"
        base_out.mkdir()
        (base_out / "checkpoint_results.jsonl").write_text(
            json.dumps({
                "strict_pass_rate": 0.8,
            }) + "\n",
        )
        ta_out = tmp_path / "two_agent"
        ta_out.mkdir()
        (ta_out / "checkpoint_results.jsonl").write_text(
            json.dumps({
                "strict_pass_rate": 0.9,
            }) + "\n",
        )

        with (
            patch.object(
                mod, "run_baseline",
                return_value=(base_out, 0),
            ),
            patch.object(
                mod, "run_two_agent",
                return_value=(ta_out, 0),
            ),
            patch.object(
                mod, "run_eval",
                return_value=1,
            ),
        ):
            res = mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                dolt_conn=None,
            )

        # Eval failure recorded
        assert any(
            "eval failed" in e.lower()
            for e in res.errors
        )

    def test_pipeline_errors_propagated_by_cli(
        self, tmp_path: Path,
    ):
        """Pipeline result with errors (but not partial)
        still has errors attribute set. The CLI should
        exit non-zero on any errors."""
        mod = _load_pipeline()

        base_out = tmp_path / "baseline"
        base_out.mkdir()
        (base_out / "checkpoint_results.jsonl").write_text(
            json.dumps({
                "strict_pass_rate": 0.8,
            }) + "\n",
        )
        ta_out = tmp_path / "two_agent"
        ta_out.mkdir()
        (ta_out / "checkpoint_results.jsonl").write_text(
            json.dumps({
                "strict_pass_rate": 0.9,
            }) + "\n",
        )

        with (
            patch.object(
                mod, "run_baseline",
                return_value=(base_out, 0),
            ),
            patch.object(
                mod, "run_two_agent",
                return_value=(ta_out, 0),
            ),
            patch.object(
                mod, "run_eval",
                return_value=1,
            ),
        ):
            res = mod.run_pipeline(
                problem="test_prob",
                model="opus-4.5",
                budget=5.0,
                dolt_conn=None,
            )

        # Eval failures recorded
        assert len(res.errors) > 0
        assert any(
            "eval failed" in e.lower()
            for e in res.errors
        )
        # Result is NOT partial (both runs completed)
        assert res.partial is False


# -------------------------------------------------------------------
# Baseline output directory uses explicit save_dir
# -------------------------------------------------------------------


class TestBaselineOutputDir:
    """Baseline run uses explicit save_dir override."""

    def test_baseline_cmd_includes_save_dir(self):
        """run_baseline command includes save_dir override."""
        mod = _load_pipeline()
        captured_cmd: list[str] = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        with (
            patch("subprocess.run", side_effect=fake_run),
            patch.object(
                mod, "_find_latest_run_dir",
                return_value=None,
            ),
        ):
            mod.run_baseline(
                problem="test",
                model="test",
                budget=1.0,
                prompt="just-solve",
            )

        # Should contain save_dir= override
        save_args = [
            a for a in captured_cmd
            if a.startswith("save_dir=")
        ]
        assert len(save_args) == 1
        assert "baseline_" in save_args[0]

        # Should contain save_template=. override
        template_args = [
            a for a in captured_cmd
            if a.startswith("save_template=")
        ]
        assert len(template_args) == 1
        assert template_args[0] == "save_template=."


# -------------------------------------------------------------------
# _find_latest_run_dir prefix=None
# -------------------------------------------------------------------


class TestFindLatestRunDir:
    """_find_latest_run_dir supports optional prefix."""

    def test_finds_without_prefix(self, tmp_path: Path):
        """Finds any dir with the problem when prefix=None."""
        mod = _load_pipeline()

        run_dir = tmp_path / "outputs" / "custom_name"
        (run_dir / "test_prob").mkdir(parents=True)

        with patch.object(
            mod, "OUTPUTS_DIR",
            tmp_path / "outputs",
        ):
            result = mod._find_latest_run_dir(
                "test_prob", prefix=None,
            )

        assert result is not None
        assert result.name == "custom_name"

    def test_filters_by_prefix(self, tmp_path: Path):
        """Filters by prefix when given."""
        mod = _load_pipeline()

        outputs = tmp_path / "outputs"
        # Create dirs with different prefixes
        (outputs / "baseline_run" / "test_prob").mkdir(
            parents=True,
        )
        (outputs / "custom_run" / "test_prob").mkdir(
            parents=True,
        )

        with patch.object(
            mod, "OUTPUTS_DIR", outputs,
        ):
            result = mod._find_latest_run_dir(
                "test_prob", prefix="baseline",
            )

        assert result is not None
        assert result.name == "baseline_run"

    def test_returns_none_when_no_match(
        self, tmp_path: Path,
    ):
        """Returns None when no dirs match."""
        mod = _load_pipeline()

        outputs = tmp_path / "outputs"
        outputs.mkdir()

        with patch.object(
            mod, "OUTPUTS_DIR", outputs,
        ):
            result = mod._find_latest_run_dir(
                "test_prob", prefix=None,
            )

        assert result is None
