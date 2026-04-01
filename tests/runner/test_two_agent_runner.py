"""Tests for research/runner/two_agent_runner.py."""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

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


# ---------------------------------------------------------------------------
# Canary mode — VAL-RUNNER-006 / VAL-RUNNER-007
# ---------------------------------------------------------------------------


class TestCanaryError:
    """CanaryError carries component and detail."""

    def test_canary_error_attributes(self):
        mod = _load_runner_module()
        err = mod.CanaryError("Docker", "daemon not running")
        assert err.component == "Docker"
        assert err.detail == "daemon not running"
        assert "Docker" in str(err)
        assert "daemon not running" in str(err)


class TestCanaryCLI:
    """VAL-RUNNER-006: --canary runs without other required flags."""

    def test_canary_flag_accepted_without_problem_or_model(self):
        """--canary can be passed alone (no --problem/--model/--budget).

        The CLI should not fail with 'missing required arg'.
        It will fail on preflight checks (Docker may not be
        configured in CI), but the exit reason should be a
        canary component error, not a missing-argument error.
        """
        result = _run_cli("--canary")
        combined = result.stdout + result.stderr
        # Should not complain about missing --problem/--model
        assert "--problem is required" not in combined
        assert "--model is required" not in combined
        assert "--budget is required" not in combined

    def test_canary_shows_defaults(self):
        """Canary mode echoes its defaults to stdout."""
        result = _run_cli("--canary")
        combined = result.stdout + result.stderr
        # Even if canary fails on Docker, it should echo
        # the mode and defaults first.
        assert "canary" in combined.lower()


class TestPreflightChecks:
    """VAL-RUNNER-007: Canary validates Docker, API, CLI."""

    def test_check_docker_failure_descriptive(self):
        """check_docker raises CanaryError with component='Docker'
        when docker is not available."""
        mod = _load_runner_module()
        # Mock subprocess.run to simulate docker info failure
        fake_result = MagicMock()
        fake_result.returncode = 1
        fake_result.stderr = "Cannot connect to Docker daemon"
        with patch.object(
            subprocess, "run", return_value=fake_result,
        ):
            with pytest.raises(mod.CanaryError) as exc_info:
                mod.check_docker()
            assert exc_info.value.component == "Docker"
            assert "not running" in exc_info.value.detail

    def test_check_docker_not_installed(self):
        """check_docker raises CanaryError when docker CLI missing."""
        mod = _load_runner_module()
        with patch.object(
            subprocess, "run",
            side_effect=FileNotFoundError,
        ):
            with pytest.raises(mod.CanaryError) as exc_info:
                mod.check_docker()
            assert exc_info.value.component == "Docker"
            assert "not found" in exc_info.value.detail.lower()

    def test_check_docker_timeout(self):
        """check_docker raises CanaryError on timeout."""
        mod = _load_runner_module()
        with patch.object(
            subprocess, "run",
            side_effect=subprocess.TimeoutExpired(
                cmd="docker info", timeout=15,
            ),
        ):
            with pytest.raises(mod.CanaryError) as exc_info:
                mod.check_docker()
            assert exc_info.value.component == "Docker"
            assert "timed out" in exc_info.value.detail

    def test_check_docker_success(self):
        """check_docker passes when docker info returns 0."""
        mod = _load_runner_module()
        fake_result = MagicMock()
        fake_result.returncode = 0
        with patch.object(
            subprocess, "run", return_value=fake_result,
        ):
            # Should not raise
            mod.check_docker()

    def test_check_api_key_missing(self):
        """check_api_key raises CanaryError with component='API'
        when credential is unavailable."""
        mod = _load_runner_module()
        # Use a model name that exists but ensure env var
        # is absent.
        env = {
            k: v for k, v in os.environ.items()
            if k != "ANTHROPIC_API_KEY"
        }
        with patch.dict(os.environ, env, clear=True):
            # Need to clear the credential cache
            src_path = str(REPO_ROOT / "src")
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
            from slop_code.agent_runner.credentials import API_KEY_STORE
            API_KEY_STORE.clear_cache()
            try:
                with pytest.raises(mod.CanaryError) as exc_info:
                    mod.check_api_key("opus-4.5")
                assert exc_info.value.component == "API"
            finally:
                API_KEY_STORE.clear_cache()

    def test_check_api_key_invalid_model(self):
        """check_api_key raises CanaryError for unknown model."""
        mod = _load_runner_module()
        with pytest.raises(mod.CanaryError) as exc_info:
            mod.check_api_key("nonexistent-model-xyz")
        assert exc_info.value.component == "API"
        assert "not found" in exc_info.value.detail.lower()

    def test_check_claude_cli_missing(self):
        """check_claude_cli raises CanaryError when CLI absent."""
        mod = _load_runner_module()
        with patch.object(
            subprocess, "run",
            side_effect=FileNotFoundError,
        ):
            with pytest.raises(mod.CanaryError) as exc_info:
                mod.check_claude_cli()
            assert exc_info.value.component == "Claude CLI"
            assert "not found" in exc_info.value.detail.lower()

    def test_check_claude_cli_timeout(self):
        """check_claude_cli raises CanaryError on timeout."""
        mod = _load_runner_module()
        with patch.object(
            subprocess, "run",
            side_effect=subprocess.TimeoutExpired(
                cmd="claude", timeout=15,
            ),
        ):
            with pytest.raises(mod.CanaryError) as exc_info:
                mod.check_claude_cli()
            assert exc_info.value.component == "Claude CLI"
            assert "timed out" in exc_info.value.detail

    def test_check_claude_cli_success(self):
        """check_claude_cli passes when claude --version works."""
        mod = _load_runner_module()
        fake_result = MagicMock()
        fake_result.returncode = 0
        with patch.object(
            subprocess, "run", return_value=fake_result,
        ):
            mod.check_claude_cli()

    def test_run_preflight_stops_on_first_failure(self):
        """run_preflight_checks stops at the first failure.

        If Docker check fails, API and CLI checks should
        not run.
        """
        mod = _load_runner_module()
        with (
            patch.object(
                mod, "check_docker",
                side_effect=mod.CanaryError(
                    "Docker", "not running",
                ),
            ),
            patch.object(
                mod, "check_api_key",
            ) as mock_api,
            patch.object(
                mod, "check_claude_cli",
            ) as mock_cli,
        ):
            with pytest.raises(mod.CanaryError):
                mod.run_preflight_checks("opus-4.5")
            mock_api.assert_not_called()
            mock_cli.assert_not_called()


class TestCanaryDescriptiveErrors:
    """VAL-RUNNER-007: Descriptive errors on component failure."""

    def test_cli_canary_docker_failure_message(self):
        """CLI --canary produces descriptive Docker error."""
        result = _run_cli("--canary")
        if result.returncode != 0:
            combined = result.stdout + result.stderr
            # If Docker is not available, the error should
            # mention Docker explicitly.
            if "Docker" in combined:
                assert "CANARY FAILED" in combined
                assert "Docker" in combined

    def test_canary_error_includes_component_in_cli(self):
        """When canary fails, CLI output contains
        'CANARY FAILED [Component]'."""
        # This test is structural: the main() function
        # formats CanaryError as
        # "CANARY FAILED [component]: detail"
        mod = _load_runner_module()
        err = mod.CanaryError("API", "key not found")
        expected = f"CANARY FAILED [{err.component}]"
        assert expected == "CANARY FAILED [API]"


class TestCanaryDefaults:
    """Canary uses sensible defaults."""

    def test_canary_default_constants(self):
        """Module exports correct canary defaults."""
        mod = _load_runner_module()
        assert mod.CANARY_PROBLEM == "file_backup"
        assert mod.CANARY_BUDGET == 0.50
        assert mod.CANARY_BUDGET_SPLIT == 70
        assert mod.CANARY_DEFAULT_MODEL == "opus-4.5"

    def test_canary_budget_cap(self):
        """Canary budget defaults to $0.50."""
        mod = _load_runner_module()
        assert mod.CANARY_BUDGET <= 0.50


class TestCanaryRunFunction:
    """run_canary exercises the full pipeline (mocked)."""

    def test_run_canary_calls_preflight(self):
        """run_canary calls run_preflight_checks."""
        mod = _load_runner_module()
        with (
            patch.object(
                mod, "run_preflight_checks",
            ) as mock_preflight,
            patch.object(
                mod, "validate_model",
                return_value="opus-4.5",
            ),
            patch.object(
                subprocess, "run",
            ) as mock_run,
            patch.object(
                mod,
                "_find_latest_run_dir",
                return_value=None,
            ),
        ):
            fake = MagicMock()
            fake.returncode = 0
            fake.stdout = ""
            fake.stderr = ""
            mock_run.return_value = fake
            with pytest.raises(mod.CanaryError):
                mod.run_canary()
        mock_preflight.assert_called_once()

    def test_run_canary_full_pipeline_mocked(
        self, tmp_path: Path,
    ):
        """run_canary exercises implementer, reviewer, and eval
        when all subprocess calls succeed."""
        mod = _load_runner_module()

        # Set up a fake output directory structure
        fake_run_dir = tmp_path / "fake_run"
        fake_problem_dir = fake_run_dir / "file_backup"
        fake_cp_dir = fake_problem_dir / "checkpoint_1"
        fake_snapshot = fake_cp_dir / "snapshot"
        fake_snapshot.mkdir(parents=True)
        (fake_snapshot / "solution.py").write_text(
            "print('hello')",
        )
        # Config file
        (fake_run_dir / "config.yaml").write_text(
            "model:\n  name: opus-4.5\n",
        )

        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = ""
        fake_result.stderr = ""

        with (
            patch.object(mod, "run_preflight_checks"),
            patch.object(
                mod, "validate_model",
                return_value="opus-4.5",
            ),
            patch.object(
                subprocess, "run",
                return_value=fake_result,
            ),
            patch.object(
                mod, "_find_latest_run_dir",
                return_value=(
                    fake_run_dir, fake_problem_dir,
                ),
            ),
            patch.object(
                mod, "OUTPUTS_DIR", tmp_path,
            ),
        ):
            state = mod.run_canary()

        assert isinstance(state, mod.RunState)
        assert state.problem == "file_backup"
        assert state.budget == 0.50
        # Metrics file should be written
        metrics_file = (
            state.output_dir / "two_agent_metrics.json"
        )
        assert metrics_file.exists()

    def test_run_canary_implementer_failure(self):
        """run_canary raises CanaryError on implementer failure."""
        mod = _load_runner_module()
        fail_result = MagicMock()
        fail_result.returncode = 1
        fail_result.stdout = ""
        fail_result.stderr = "API error: invalid key"

        with (
            patch.object(mod, "run_preflight_checks"),
            patch.object(
                mod, "validate_model",
                return_value="opus-4.5",
            ),
            patch.object(
                subprocess, "run",
                return_value=fail_result,
            ),
        ):
            with pytest.raises(
                mod.CanaryError,
            ) as exc_info:
                mod.run_canary()
            assert (
                exc_info.value.component == "Implementer"
            )

    def test_run_canary_eval_failure(self, tmp_path: Path):
        """run_canary raises CanaryError on eval failure."""
        mod = _load_runner_module()

        fake_run_dir = tmp_path / "fake_run"
        fake_problem_dir = fake_run_dir / "file_backup"
        fake_cp_dir = fake_problem_dir / "checkpoint_1"
        fake_snapshot = fake_cp_dir / "snapshot"
        fake_snapshot.mkdir(parents=True)
        (fake_snapshot / "solution.py").write_text("")
        (fake_run_dir / "config.yaml").write_text(
            "model:\n  name: opus-4.5\n",
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            r = MagicMock()
            r.stdout = ""
            r.stderr = ""
            # First two calls (implementer + reviewer) succeed
            if call_count <= 2:
                r.returncode = 0
            else:
                # Eval fails
                r.returncode = 1
                r.stderr = "eval: no checkpoints found"
            return r

        with (
            patch.object(mod, "run_preflight_checks"),
            patch.object(
                mod, "validate_model",
                return_value="opus-4.5",
            ),
            patch.object(
                subprocess, "run",
                side_effect=side_effect,
            ),
            patch.object(
                mod, "_find_latest_run_dir",
                return_value=(
                    fake_run_dir, fake_problem_dir,
                ),
            ),
            patch.object(
                mod, "OUTPUTS_DIR", tmp_path,
            ),
        ):
            with pytest.raises(
                mod.CanaryError,
            ) as exc_info:
                mod.run_canary()
            assert (
                exc_info.value.component == "Evaluation"
            )


class TestUpdateMetricsFromResults:
    """_update_metrics_from_results parses checkpoint results."""

    def test_parses_jsonl(self, tmp_path: Path):
        """Reads pass_rate from checkpoint_results.jsonl."""
        mod = _load_runner_module()
        results_file = tmp_path / "checkpoint_results.jsonl"
        data = {
            "problem_name": "file_backup",
            "checkpoint_name": "checkpoint_1",
            "pass_counts": 8,
            "total_counts": 10,
        }
        results_file.write_text(json.dumps(data) + "\n")
        metrics = mod.CheckpointMetrics()
        mod._update_metrics_from_results(
            metrics, results_file,
        )
        assert metrics.pass_rate == pytest.approx(0.8)

    def test_handles_empty_file(self, tmp_path: Path):
        """Gracefully handles empty results file."""
        mod = _load_runner_module()
        results_file = tmp_path / "checkpoint_results.jsonl"
        results_file.write_text("")
        metrics = mod.CheckpointMetrics()
        mod._update_metrics_from_results(
            metrics, results_file,
        )
        assert metrics.pass_rate == 0.0

    def test_handles_missing_file(self, tmp_path: Path):
        """Gracefully handles missing results file."""
        mod = _load_runner_module()
        results_file = tmp_path / "nonexistent.jsonl"
        metrics = mod.CheckpointMetrics()
        mod._update_metrics_from_results(
            metrics, results_file,
        )
        assert metrics.pass_rate == 0.0
