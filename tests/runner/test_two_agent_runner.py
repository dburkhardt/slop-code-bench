"""Tests for research/runner/two_agent_runner.py."""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO_ROOT / "research" / "runner" / "two_agent_runner.py"


def _load_runner_module():
    """Import the runner module."""
    spec = importlib.util.spec_from_file_location(
        "two_agent_runner", str(RUNNER_PATH)
    )
    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules so Pydantic can resolve types
    sys.modules["two_agent_runner"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_cli(
    *args: str,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Invoke two_agent_runner.py as a subprocess."""
    cmd = [sys.executable, str(RUNNER_PATH), *args]
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        env=merged_env,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# CLI argument tests
# ---------------------------------------------------------------------------


class TestCLIFlags:
    """VAL-RUNNER-001: CLI accepts all required arguments."""

    def test_help_lists_all_flags(self):
        """--help lists all 7 flags with descriptions."""
        result = _run_cli("--help")
        assert result.returncode == 0
        help_text = result.stdout
        for flag in [
            "--problem",
            "--model",
            "--implementer-prompt",
            "--reviewer-prompt",
            "--budget-split",
            "--budget",
            "--canary",
        ]:
            assert flag in help_text, (
                f"Missing flag {flag} in help output"
            )

    def test_missing_required_args_exits_nonzero(self):
        """Missing required args produce non-zero exit."""
        result = _run_cli()
        assert result.returncode != 0

    def test_problem_and_model_required_without_canary(self):
        """--problem and --model required if --canary not set."""
        result = _run_cli("--budget", "1.0")
        assert result.returncode != 0

    def test_budget_required(self):
        """--budget is always required."""
        result = _run_cli(
            "--problem", "file_backup",
            "--model", "opus-4.5",
        )
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Budget split validation
# ---------------------------------------------------------------------------


class TestBudgetSplitValidation:
    """VAL-RUNNER-015: Budget-split validates range 1-99."""

    @pytest.mark.parametrize(
        "val", ["0", "-1", "-5", "100", "150"],
    )
    def test_out_of_range_rejected(self, val: str):
        """Values outside 1-99 rejected with clear error."""
        result = _run_cli(
            "--budget-split", val,
            "--problem", "test",
            "--model", "test",
            "--budget", "1.0",
        )
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        # Error message mentions the valid range
        assert (
            "1" in combined
            or "99" in combined
            or "range" in combined.lower()
        )

    @pytest.mark.parametrize("val", ["1", "50", "70", "99"])
    def test_valid_range_accepted(self, val: str):
        """Values within 1-99 do not trigger a range error."""
        result = _run_cli(
            "--budget-split", val,
            "--problem", "file_backup",
            "--model", "nonexistent-model-xyz",
            "--budget", "1.0",
        )
        combined = result.stdout + result.stderr
        # Should fail for model validation, not budget-split
        assert "range" not in combined.lower() or (
            "budget" not in combined.lower()
        )

    def test_non_integer_rejected(self):
        """Non-integer value rejected."""
        result = _run_cli(
            "--budget-split", "abc",
            "--problem", "test",
            "--model", "test",
            "--budget", "1.0",
        )
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------


class TestModelValidation:
    """VAL-RUNNER-013: Invalid model name produces clear error."""

    def test_invalid_model_rejected(self):
        """Non-existent model exits non-zero with error naming
        the model before any API calls."""
        result = _run_cli(
            "--problem", "file_backup",
            "--model", "nonexistent-model-xyz",
            "--budget", "1.0",
        )
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "nonexistent-model-xyz" in combined


# ---------------------------------------------------------------------------
# Import-level tests
# ---------------------------------------------------------------------------


class TestRunnerImport:
    """Module can be imported and core objects exist."""

    def test_module_importable(self):
        mod = _load_runner_module()
        assert mod is not None

    def test_app_exists(self):
        mod = _load_runner_module()
        assert hasattr(mod, "app")

    def test_checkpoint_metrics_dataclass(self):
        mod = _load_runner_module()
        assert hasattr(mod, "CheckpointMetrics")
        fields = mod.CheckpointMetrics.model_fields
        for field in [
            "pass_rate",
            "erosion",
            "verbosity",
            "tokens_implementer",
            "tokens_reviewer",
            "cost",
        ]:
            assert field in fields, (
                f"Missing field {field} in CheckpointMetrics"
            )


# ---------------------------------------------------------------------------
# Budget enforcement / cost cap
# ---------------------------------------------------------------------------


class TestBudgetEnforcement:
    """VAL-RUNNER-005: cost cap aborts and saves partial results."""

    def test_validate_budget_split_func(self):
        """Internal budget split validation works."""
        mod = _load_runner_module()
        validate = mod.validate_budget_split
        assert validate(1) == 1
        assert validate(70) == 70
        assert validate(99) == 99
        with pytest.raises(SystemExit):
            validate(0)
        with pytest.raises(SystemExit):
            validate(100)

    def test_cost_cap_check_func(self):
        """is_budget_exceeded returns True when exceeded."""
        mod = _load_runner_module()
        assert mod.is_budget_exceeded(5.0, 4.99) is True
        assert mod.is_budget_exceeded(5.0, 5.01) is False
        assert mod.is_budget_exceeded(5.0, 5.00) is False


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------


class TestOutputStructure:
    """VAL-RUNNER-008: Output directory compatible with
    slop-code eval."""

    def test_build_output_dir(self):
        mod = _load_runner_module()
        out = mod.build_output_dir(
            "file_backup", "opus-4.5", Path("outputs"),
        )
        out_str = str(out)
        assert "file_backup" in out_str
        assert "opus-4.5" in out_str
        assert "two_agent" in out_str
        assert isinstance(out, Path)


# ---------------------------------------------------------------------------
# Metrics tracking
# ---------------------------------------------------------------------------


class TestMetricsTracking:
    """VAL-RUNNER-004: Per-checkpoint metrics tracked."""

    def test_run_metrics_serialisation(self):
        """CheckpointMetrics serializes to JSON with all 6 fields."""
        mod = _load_runner_module()
        metrics = mod.CheckpointMetrics(
            pass_rate=0.85,
            erosion=0.12,
            verbosity=0.15,
            tokens_implementer=1000,
            tokens_reviewer=500,
            cost=0.05,
        )
        data = metrics.model_dump()
        assert len(data) == 6
        assert data["pass_rate"] == 0.85

    def test_run_state_accumulates_metrics(self):
        """RunState accumulates checkpoint metrics and cost."""
        mod = _load_runner_module()
        state = mod.RunState(
            problem="test",
            model="test",
            budget=10.0,
            budget_split=70,
            output_dir=Path("/tmp/test"),  # noqa: S108
        )
        m = mod.CheckpointMetrics(
            pass_rate=1.0,
            erosion=0.0,
            verbosity=0.0,
            tokens_implementer=100,
            tokens_reviewer=50,
            cost=0.01,
        )
        state.checkpoint_metrics["checkpoint_1"] = m
        assert state.cumulative_cost == 0.01
        assert len(state.checkpoint_metrics) == 1


# ---------------------------------------------------------------------------
# Budget split boundary
# ---------------------------------------------------------------------------


class TestBudgetSplitBoundary:
    """VAL-RUNNER-009 / VAL-RUNNER-010: Boundary splits."""

    def test_budget_split_100_rejected(self):
        result = _run_cli(
            "--budget-split", "100",
            "--problem", "test",
            "--model", "test",
            "--budget", "1.0",
        )
        assert result.returncode != 0

    def test_budget_split_0_rejected(self):
        result = _run_cli(
            "--budget-split", "0",
            "--problem", "test",
            "--model", "test",
            "--budget", "1.0",
        )
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Reviewer output context
# ---------------------------------------------------------------------------


class TestReviewerContext:
    """VAL-RUNNER-014: Reviewer output fed to next iteration."""

    def test_build_implementer_prompt_with_review(self):
        """Implementer prompt includes prior reviewer suggestions."""
        mod = _load_runner_module()
        prompt = mod.build_implementer_prompt(
            spec_text="Do X",
            is_continuation=True,
            reviewer_suggestions="Reduce complexity in foo()",
        )
        assert "Reduce complexity in foo()" in prompt

    def test_build_implementer_prompt_without_review(self):
        """Implementer prompt renders without reviewer suggestions."""
        mod = _load_runner_module()
        prompt = mod.build_implementer_prompt(
            spec_text="Do X",
            is_continuation=False,
            reviewer_suggestions=None,
        )
        assert "Do X" in prompt
        assert "reviewer_suggestions" not in prompt


# ---------------------------------------------------------------------------
# Partial result saving
# ---------------------------------------------------------------------------


class TestPartialResults:
    """Partial results saved on budget overrun."""

    def test_save_partial_results(self, tmp_path: Path):
        """RunState.save_results writes metrics JSON
        even with partial data."""
        mod = _load_runner_module()
        state = mod.RunState(
            problem="file_backup",
            model="opus-4.5",
            budget=0.50,
            budget_split=70,
            output_dir=tmp_path,
        )
        m = mod.CheckpointMetrics(
            pass_rate=0.5,
            erosion=0.1,
            verbosity=0.2,
            tokens_implementer=500,
            tokens_reviewer=200,
            cost=0.03,
        )
        state.checkpoint_metrics["checkpoint_1"] = m
        state.save_results()

        metrics_file = tmp_path / "two_agent_metrics.json"
        assert metrics_file.exists()
        data = json.loads(metrics_file.read_text())
        assert "checkpoint_1" in data["checkpoints"]
        assert data["checkpoints"]["checkpoint_1"]["pass_rate"] == 0.5
        assert data["cumulative_cost"] == pytest.approx(0.03)
        assert data["budget_exceeded"] is False

    def test_save_partial_results_budget_exceeded(
        self, tmp_path: Path,
    ):
        """Budget exceeded flag is set in saved metrics."""
        mod = _load_runner_module()
        state = mod.RunState(
            problem="file_backup",
            model="opus-4.5",
            budget=0.01,
            budget_split=70,
            output_dir=tmp_path,
        )
        m = mod.CheckpointMetrics(
            pass_rate=0.5,
            erosion=0.1,
            verbosity=0.2,
            tokens_implementer=500,
            tokens_reviewer=200,
            cost=0.50,
        )
        state.checkpoint_metrics["checkpoint_1"] = m
        state.budget_exceeded = True
        state.save_results()

        data = json.loads(
            (tmp_path / "two_agent_metrics.json").read_text()
        )
        assert data["budget_exceeded"] is True
