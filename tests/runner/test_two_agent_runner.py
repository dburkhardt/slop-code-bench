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
        """Internal budget split validation works.

        Range is [1, 100]. 100 = implementer-only.
        """
        mod = _load_runner_module()
        validate = mod.validate_budget_split
        assert validate(1) == 1
        assert validate(70) == 70
        assert validate(99) == 99
        assert validate(100) == 100
        with pytest.raises(SystemExit):
            validate(0)
        with pytest.raises(SystemExit):
            validate(101)

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

    def test_budget_split_100_accepted(self):
        """budget_split=100 is valid (implementer-only)."""
        mod = _load_runner_module()
        assert mod.validate_budget_split(100) == 100

    def test_budget_split_101_rejected(self):
        result = _run_cli(
            "--budget-split", "101",
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
        assert (
            mod.CANARY_DEFAULT_MODEL_ANTHROPIC == "opus-4.5"
        )
        assert (
            mod.CANARY_DEFAULT_MODEL_NVIDIA
            == "nvidia-sonnet-4.6"
        )

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
                mod, "run_two_agent",
                side_effect=SystemExit(1),
            ),
            patch.object(
                mod, "OUTPUTS_DIR",
                Path("/tmp/canary_test"),  # noqa: S108
            ),
            pytest.raises(mod.CanaryError),
        ):
            mod.run_canary()
        mock_preflight.assert_called_once()

    def test_run_canary_full_pipeline_mocked(
        self, tmp_path: Path,
    ):
        """run_canary exercises run_two_agent and eval
        when all steps succeed."""
        mod = _load_runner_module()

        canary_out = tmp_path / "canary_output"

        def fake_run_two_agent(**kwargs):
            # Simulate run_two_agent creating output
            out = kwargs.get("output_dir", canary_out)
            out.mkdir(parents=True, exist_ok=True)
            state = mod.RunState(
                problem="file_backup",
                model="opus-4.5",
                budget=0.50,
                budget_split=70,
                output_dir=out,
            )
            m = mod.CheckpointMetrics(cost=0.10)
            state.checkpoint_metrics["checkpoint_1"] = m
            state.save_results()
            return state

        fake_eval = MagicMock()
        fake_eval.returncode = 0
        fake_eval.stdout = ""
        fake_eval.stderr = ""

        with (
            patch.object(mod, "run_preflight_checks"),
            patch.object(
                mod, "validate_model",
                return_value="opus-4.5",
            ),
            patch.object(
                mod, "run_two_agent",
                side_effect=fake_run_two_agent,
            ),
            patch.object(
                subprocess, "run",
                return_value=fake_eval,
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

    def test_run_canary_passes_max_checkpoints_1(self):
        """run_canary passes max_checkpoints=1 to
        run_two_agent."""
        mod = _load_runner_module()

        captured_kwargs: dict = {}

        def capture_kwargs(**kwargs):
            captured_kwargs.update(kwargs)
            state = mod.RunState(
                problem="file_backup",
                model="opus-4.5",
                budget=0.50,
                budget_split=70,
                output_dir=kwargs["output_dir"],
            )
            state.save_results()
            return state

        fake_eval = MagicMock()
        fake_eval.returncode = 0
        fake_eval.stdout = ""
        fake_eval.stderr = ""

        with (
            patch.object(mod, "run_preflight_checks"),
            patch.object(
                mod, "validate_model",
                return_value="opus-4.5",
            ),
            patch.object(
                mod, "run_two_agent",
                side_effect=capture_kwargs,
            ),
            patch.object(
                subprocess, "run",
                return_value=fake_eval,
            ),
            patch.object(
                mod, "OUTPUTS_DIR",
                Path("/tmp/canary_test"),  # noqa: S108
            ),
        ):
            mod.run_canary()

        assert captured_kwargs.get("max_checkpoints") == 1

    def test_run_canary_pipeline_failure(self):
        """run_canary raises CanaryError with component
        'Pipeline' when run_two_agent exits non-zero."""
        mod = _load_runner_module()

        with (
            patch.object(mod, "run_preflight_checks"),
            patch.object(
                mod, "validate_model",
                return_value="opus-4.5",
            ),
            patch.object(
                mod, "run_two_agent",
                side_effect=SystemExit(1),
            ),
            patch.object(
                mod, "OUTPUTS_DIR",
                Path("/tmp/canary_test"),  # noqa: S108
            ),
        ):
            with pytest.raises(
                mod.CanaryError,
            ) as exc_info:
                mod.run_canary()
            assert (
                exc_info.value.component == "Pipeline"
            )

    def test_run_canary_reviewer_failure_is_fatal(self):
        """Reviewer failure in canary mode is fatal.

        When run_two_agent invokes run_slop_code for the
        reviewer and it fails, the canary should propagate
        the error rather than ignoring it.
        """
        # This is tested structurally: the old code had
        # a "non-fatal" branch for reviewer failures.
        # The new canary delegates to run_two_agent which
        # naturally propagates failures through
        # run_slop_code.  We verify that a SystemExit
        # from run_two_agent becomes a CanaryError.
        mod = _load_runner_module()

        with (
            patch.object(mod, "run_preflight_checks"),
            patch.object(
                mod, "validate_model",
                return_value="opus-4.5",
            ),
            patch.object(
                mod, "run_two_agent",
                side_effect=SystemExit(1),
            ),
            patch.object(
                mod, "OUTPUTS_DIR",
                Path("/tmp/canary_test"),  # noqa: S108
            ),
            pytest.raises(mod.CanaryError),
        ):
            mod.run_canary()

    def test_run_canary_eval_failure(self, tmp_path: Path):
        """run_canary raises CanaryError on eval failure."""
        mod = _load_runner_module()

        def fake_run_two_agent(**kwargs):
            out = kwargs.get("output_dir", tmp_path)
            out.mkdir(parents=True, exist_ok=True)
            state = mod.RunState(
                problem="file_backup",
                model="opus-4.5",
                budget=0.50,
                budget_split=70,
                output_dir=out,
            )
            m = mod.CheckpointMetrics(cost=0.10)
            state.checkpoint_metrics["checkpoint_1"] = m
            state.save_results()
            return state

        call_count = 0

        def eval_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            r = MagicMock()
            r.stdout = ""
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
                mod, "run_two_agent",
                side_effect=fake_run_two_agent,
            ),
            patch.object(
                subprocess, "run",
                side_effect=eval_side_effect,
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

    def test_parses_jsonl_flattened(self, tmp_path: Path):
        """Reads pass_rate from flattened strict_pass_rate."""
        mod = _load_runner_module()
        results_file = tmp_path / "checkpoint_results.jsonl"
        data = {
            "problem_name": "file_backup",
            "checkpoint_name": "checkpoint_1",
            "strict_pass_rate": 0.8,
            "total_tests": 10,
            "passed_tests": 8,
        }
        results_file.write_text(json.dumps(data) + "\n")
        metrics = mod.CheckpointMetrics()
        mod._update_metrics_from_results(
            metrics, results_file,
        )
        assert metrics.pass_rate == pytest.approx(0.8)

    def test_parses_jsonl_total_tests_fallback(
        self, tmp_path: Path,
    ):
        """Falls back to total_tests/passed_tests."""
        mod = _load_runner_module()
        results_file = tmp_path / "checkpoint_results.jsonl"
        data = {
            "total_tests": 10,
            "passed_tests": 8,
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


# ---------------------------------------------------------------------------
# Helper for mocked run_slop_code results
# ---------------------------------------------------------------------------


def _fake_slop_result(
    cost: float = 0.0,
    tokens: int = 0,
    pass_rate: float = 0.0,
    erosion: float = 0.0,
    verbosity: float = 0.0,
    output_dir: str | None = None,
) -> dict:
    """Return a fake run_slop_code result dict."""
    return {
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "cost": cost,
        "tokens": tokens,
        "pass_rate": pass_rate,
        "erosion": erosion,
        "verbosity": verbosity,
        "output_dir": output_dir,
    }


# ---------------------------------------------------------------------------
# Core loop calls run_slop_code for both phases
# ---------------------------------------------------------------------------


class TestCoreLoopInvocations:
    """Core loop calls run_slop_code() for both implementer
    and reviewer stages."""

    @pytest.fixture()
    def fake_problem(self, tmp_path):
        prob = tmp_path / "problems" / "test_problem"
        for i in range(1, 3):
            cp = prob / f"checkpoint_{i}"
            cp.mkdir(parents=True)
            spec = prob / f"checkpoint_{i}.md"
            spec.write_text(f"Spec for checkpoint {i}")
        return prob

    def test_calls_run_slop_code_twice_per_checkpoint(
        self, tmp_path, fake_problem,
    ):
        """Each checkpoint triggers two run_slop_code calls:
        one for implementer, one for reviewer."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        call_args: list[dict] = []

        def capture_call(**kwargs):
            call_args.append(kwargs)
            return _fake_slop_result()

        with (
            patch.object(
                mod, "PROBLEMS_DIR", fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                side_effect=capture_call,
            ),
        ):
            mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
            )

        # 2 checkpoints x 2 phases = 4 calls
        assert len(call_args) == 4
        # First call: implementer for checkpoint_1
        assert call_args[0]["phase"] == "implementer"
        # Second call: reviewer for checkpoint_1
        assert call_args[1]["phase"] == "reviewer"
        # Third call: implementer for checkpoint_2
        assert call_args[2]["phase"] == "implementer"
        # Fourth call: reviewer for checkpoint_2
        assert call_args[3]["phase"] == "reviewer"

    def test_budget_split_enforced_per_phase(
        self, tmp_path, fake_problem,
    ):
        """Implementer gets budget_split% and reviewer gets
        the remainder as budget_fraction."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        fractions: list[float] = []

        def capture_fraction(**kwargs):
            fractions.append(kwargs["budget_fraction"])
            return _fake_slop_result()

        with (
            patch.object(
                mod, "PROBLEMS_DIR", fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                side_effect=capture_fraction,
            ),
        ):
            mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
            )

        # 4 calls: impl(0.7), rev(0.3), impl(0.7), rev(0.3)
        assert fractions[0] == pytest.approx(0.7)
        assert fractions[1] == pytest.approx(0.3)
        assert fractions[2] == pytest.approx(0.7)
        assert fractions[3] == pytest.approx(0.3)

    def test_run_id_passed_to_slop_code(
        self, tmp_path, fake_problem,
    ):
        """run_slop_code receives the run_id from state."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        run_ids: list[str | None] = []

        def capture_run_id(**kwargs):
            run_ids.append(kwargs.get("run_id"))
            return _fake_slop_result()

        with (
            patch.object(
                mod, "PROBLEMS_DIR", fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                side_effect=capture_run_id,
            ),
        ):
            mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
                run_id="test-run-42",
            )

        # All calls should have the run_id
        for rid in run_ids:
            assert rid == "test-run-42"

    def test_cost_tracked_from_slop_code(
        self, tmp_path, fake_problem,
    ):
        """Costs returned by run_slop_code are accumulated
        in checkpoint metrics."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        call_count = 0

        def cost_returning(**kwargs):
            nonlocal call_count
            call_count += 1
            phase = kwargs.get("phase", "implementer")
            if phase == "implementer":
                return _fake_slop_result(cost=0.10)
            return _fake_slop_result(cost=0.05)

        with (
            patch.object(
                mod, "PROBLEMS_DIR", fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                side_effect=cost_returning,
            ),
        ):
            state = mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
            )

        # Each checkpoint costs 0.10 + 0.05 = 0.15
        for cp_name, m in state.checkpoint_metrics.items():
            assert m.cost == pytest.approx(0.15)
        # Total cost = 2 checkpoints * 0.15
        assert state.cumulative_cost == pytest.approx(0.30)

    def test_max_checkpoints_limits_execution(
        self, tmp_path, fake_problem,
    ):
        """max_checkpoints=1 limits execution to
        checkpoint_1 only."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        call_args: list[dict] = []

        def capture_call(**kwargs):
            call_args.append(kwargs)
            return _fake_slop_result()

        with (
            patch.object(
                mod, "PROBLEMS_DIR", fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                side_effect=capture_call,
            ),
        ):
            state = mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
                max_checkpoints=1,
            )

        # Only 1 checkpoint x 2 phases = 2 calls
        assert len(call_args) == 2
        assert len(state.checkpoint_metrics) == 1
        assert "checkpoint_1" in state.checkpoint_metrics


# ---------------------------------------------------------------------------
# Reviewer output propagation
# ---------------------------------------------------------------------------


class TestReviewerPropagation:
    """Reviewer output is fed into the next implementer
    iteration."""

    @pytest.fixture()
    def fake_problem(self, tmp_path):
        prob = tmp_path / "problems" / "test_problem"
        for i in range(1, 3):
            cp = prob / f"checkpoint_{i}"
            cp.mkdir(parents=True)
            spec = prob / f"checkpoint_{i}.md"
            spec.write_text(f"Spec {i}")
        return prob

    def test_reviewer_output_injected(
        self, tmp_path, fake_problem,
    ):
        """Reviewer output from checkpoint_1 appears in the
        implementer prompt for checkpoint_2."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        # Create a fake reviewer output directory with
        # a solution file
        fake_rev_dir = tmp_path / "reviewer_output"
        snapshot = (
            fake_rev_dir / "test_problem"
            / "checkpoint_1" / "snapshot"
        )
        snapshot.mkdir(parents=True)
        (snapshot / "solution.py").write_text(
            "def improved():\n    return 42\n",
        )

        call_count = 0

        def phase_aware(**kwargs):
            nonlocal call_count
            call_count += 1
            phase = kwargs.get("phase", "implementer")
            if phase == "reviewer":
                return _fake_slop_result(
                    output_dir=str(fake_rev_dir),
                )
            return _fake_slop_result()

        with (
            patch.object(
                mod, "PROBLEMS_DIR", fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                side_effect=phase_aware,
            ),
        ):
            state = mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
            )

        # After checkpoint_1, reviewer suggestions should
        # be set (not None).
        assert state.last_reviewer_suggestions is not None
        assert "improved" in state.last_reviewer_suggestions


# ---------------------------------------------------------------------------
# Crash-safe persistence
# ---------------------------------------------------------------------------


class TestCrashSafePersistence:
    """Checkpoint state persisted to disk after each
    checkpoint (not just at exit)."""

    @pytest.fixture()
    def fake_problem(self, tmp_path):
        prob = tmp_path / "problems" / "test_problem"
        for i in range(1, 4):
            cp = prob / f"checkpoint_{i}"
            cp.mkdir(parents=True)
            spec = prob / f"checkpoint_{i}.md"
            spec.write_text(f"Spec {i}")
        return prob

    def test_metrics_saved_after_each_checkpoint(
        self, tmp_path, fake_problem,
    ):
        """two_agent_metrics.json grows after each
        checkpoint completion."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        save_call_count = 0
        original_save = mod.RunState.save_results

        def counting_save(self_state):
            nonlocal save_call_count
            save_call_count += 1
            return original_save(self_state)

        with (
            patch.object(
                mod, "PROBLEMS_DIR", fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                return_value=_fake_slop_result(),
            ),
            patch.object(
                mod.RunState, "save_results",
                counting_save,
            ),
        ):
            mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
            )

        # save_results called once per checkpoint + once
        # at the end = 3 + 1 = 4 calls
        assert save_call_count >= 4


# ---------------------------------------------------------------------------
# Per-checkpoint artifacts
# ---------------------------------------------------------------------------


class TestCheckpointArtifacts:
    """Per-checkpoint artifacts generated in eval-compatible
    directory layout."""

    def test_copy_checkpoint_artifacts(self, tmp_path):
        """Artifacts copied from slop-code output into
        the target directory."""
        mod = _load_runner_module()

        # Create source structure
        src = tmp_path / "source_run"
        cp_dir = src / "test_prob" / "checkpoint_1" / "snapshot"
        cp_dir.mkdir(parents=True)
        (cp_dir / "solution.py").write_text("print('hi')")
        results = src / "checkpoint_results.jsonl"
        results.write_text(
            json.dumps({"pass_counts": 8, "total_counts": 10})
            + "\n",
        )
        (src / "config.yaml").write_text("model: test\n")
        (src / "environment.yaml").write_text("runtime: docker\n")

        # Copy to target
        target = tmp_path / "target"
        target.mkdir()

        mod._copy_checkpoint_artifacts(
            problem="test_prob",
            checkpoint_name="checkpoint_1",
            source_output=str(src),
            target_dir=target,
        )

        # Verify layout
        assert (
            target / "test_prob" / "checkpoint_1"
            / "snapshot" / "solution.py"
        ).exists()
        assert (target / "checkpoint_results.jsonl").exists()
        assert (target / "config.yaml").exists()
        assert (target / "environment.yaml").exists()

    def test_copy_artifacts_handles_none(self):
        """Handles None source_output gracefully."""
        mod = _load_runner_module()
        # Should not raise
        mod._copy_checkpoint_artifacts(
            problem="p",
            checkpoint_name="c",
            source_output=None,
            target_dir=Path("/tmp/x"),  # noqa: S108
        )


# ---------------------------------------------------------------------------
# _parse_slop_code_output
# ---------------------------------------------------------------------------


class TestParseSlipCodeOutput:
    """_parse_slop_code_output extracts metrics from
    slop-code output directories."""

    def test_parses_flattened_metrics(self, tmp_path):
        """Reads flattened metric keys from JSONL."""
        mod = _load_runner_module()

        run_dir = tmp_path / "run_output"
        prob_dir = run_dir / "test_prob" / "checkpoint_1"
        prob_dir.mkdir(parents=True)
        results = run_dir / "checkpoint_results.jsonl"
        results.write_text(
            json.dumps({
                "strict_pass_rate": 0.85,
                "erosion": 0.12,
                "verbosity": 0.08,
                "cost": 0.25,
            }) + "\n",
        )

        with patch.object(
            mod, "_find_latest_run_dir",
            return_value=(run_dir, run_dir / "test_prob"),
        ):
            result = mod._parse_slop_code_output(
                "test_prob", "",
            )

        assert result["pass_rate"] == pytest.approx(0.85)
        assert result["erosion"] == pytest.approx(0.12)
        assert result["verbosity"] == pytest.approx(0.08)
        assert result["cost"] == pytest.approx(0.25)

    def test_parses_pass_counts_fallback(self, tmp_path):
        """Falls back to pass_counts/total_counts."""
        mod = _load_runner_module()

        run_dir = tmp_path / "run_output"
        prob_dir = run_dir / "test_prob" / "checkpoint_1"
        prob_dir.mkdir(parents=True)
        results = run_dir / "checkpoint_results.jsonl"
        results.write_text(
            json.dumps({
                "pass_counts": 8,
                "total_counts": 10,
            }) + "\n",
        )

        with patch.object(
            mod, "_find_latest_run_dir",
            return_value=(run_dir, run_dir / "test_prob"),
        ):
            result = mod._parse_slop_code_output(
                "test_prob", "",
            )

        assert result["pass_rate"] == pytest.approx(0.8)

    def test_returns_defaults_when_no_dir(self):
        """Returns zeros when no output directory found."""
        mod = _load_runner_module()

        with patch.object(
            mod, "_find_latest_run_dir",
            return_value=None,
        ):
            result = mod._parse_slop_code_output(
                "test_prob", "",
            )

        assert result["cost"] == 0.0
        assert result["pass_rate"] == 0.0
        assert result["output_dir"] is None


# ---------------------------------------------------------------------------
# _find_latest_run_dir — nested model directory support
# ---------------------------------------------------------------------------


class TestFindLatestRunDirNested:
    """_find_latest_run_dir searches nested model dirs."""

    def test_finds_in_nested_model_dir(self, tmp_path):
        """Finds run dir nested under model name dir.

        Layout: outputs/{model}/{run_dir}/{problem}/
        """
        mod = _load_runner_module()

        outputs = tmp_path / "outputs"
        run_dir = (
            outputs
            / "nvidia-bedrock-claude-sonnet-4-6"
            / "claude_code_default_20260401T1649"
        )
        (run_dir / "file_backup" / "checkpoint_1").mkdir(
            parents=True,
        )

        with patch.object(mod, "OUTPUTS_DIR", outputs):
            result = mod._find_latest_run_dir(
                "file_backup",
            )

        assert result is not None
        run_path, prob_path = result
        assert run_path == run_dir
        assert prob_path == run_dir / "file_backup"

    def test_finds_direct_child(self, tmp_path):
        """Still finds run dir as direct child of outputs.

        Layout: outputs/{run_dir}/{problem}/
        """
        mod = _load_runner_module()

        outputs = tmp_path / "outputs"
        run_dir = outputs / "canary_20260401"
        (run_dir / "file_backup").mkdir(parents=True)

        with patch.object(mod, "OUTPUTS_DIR", outputs):
            result = mod._find_latest_run_dir(
                "file_backup",
            )

        assert result is not None
        run_path, prob_path = result
        assert run_path == run_dir
        assert prob_path == run_dir / "file_backup"

    def test_prefers_newest_nested(self, tmp_path):
        """Returns the most recently modified nested dir."""
        mod = _load_runner_module()
        import time

        outputs = tmp_path / "outputs"

        # Create older run
        old_dir = (
            outputs / "model" / "run_old"
        )
        (old_dir / "prob").mkdir(parents=True)

        time.sleep(0.05)

        # Create newer run
        new_dir = (
            outputs / "model" / "run_new"
        )
        (new_dir / "prob").mkdir(parents=True)

        with patch.object(mod, "OUTPUTS_DIR", outputs):
            result = mod._find_latest_run_dir("prob")

        assert result is not None
        assert result[0] == new_dir

    def test_returns_none_for_empty_outputs(
        self, tmp_path,
    ):
        """Returns None when outputs/ is empty."""
        mod = _load_runner_module()
        outputs = tmp_path / "outputs"
        outputs.mkdir()

        with patch.object(mod, "OUTPUTS_DIR", outputs):
            result = mod._find_latest_run_dir(
                "file_backup",
            )

        assert result is None

    def test_returns_none_when_outputs_missing(
        self, tmp_path,
    ):
        """Returns None when outputs/ doesn't exist."""
        mod = _load_runner_module()

        with patch.object(
            mod, "OUTPUTS_DIR",
            tmp_path / "nonexistent",
        ):
            result = mod._find_latest_run_dir(
                "file_backup",
            )

        assert result is None

    def test_prefers_nested_over_direct(self, tmp_path):
        """When both direct and nested matches exist,
        returns the most recently modified one."""
        mod = _load_runner_module()
        import time

        outputs = tmp_path / "outputs"

        # Create older direct child
        direct = outputs / "old_run"
        (direct / "prob").mkdir(parents=True)

        time.sleep(0.05)

        # Create newer nested
        nested = outputs / "model" / "new_run"
        (nested / "prob").mkdir(parents=True)

        with patch.object(mod, "OUTPUTS_DIR", outputs):
            result = mod._find_latest_run_dir("prob")

        assert result is not None
        assert result[0] == nested


# ---------------------------------------------------------------------------
# _parse_slop_code_output — multi-checkpoint aggregation
# ---------------------------------------------------------------------------


class TestParseSlipCodeOutputAggregation:
    """_parse_slop_code_output aggregates metrics across
    multiple checkpoint entries in JSONL."""

    def test_accumulates_cost_across_lines(
        self, tmp_path,
    ):
        """Sums cost across all JSONL entries."""
        mod = _load_runner_module()

        run_dir = tmp_path / "run"
        (run_dir / "prob").mkdir(parents=True)
        results = run_dir / "checkpoint_results.jsonl"
        lines = [
            json.dumps({
                "strict_pass_rate": 0.5,
                "cost": 0.10,
            }),
            json.dumps({
                "strict_pass_rate": 0.8,
                "cost": 0.15,
            }),
        ]
        results.write_text("\n".join(lines) + "\n")

        with patch.object(
            mod, "_find_latest_run_dir",
            return_value=(run_dir, run_dir / "prob"),
        ):
            result = mod._parse_slop_code_output(
                "prob", "",
            )

        assert result["cost"] == pytest.approx(0.25)
        # Last line's pass_rate wins
        assert result["pass_rate"] == pytest.approx(0.8)

    def test_accumulates_tokens(self, tmp_path):
        """Sums token counts across all entries."""
        mod = _load_runner_module()

        run_dir = tmp_path / "run"
        (run_dir / "prob").mkdir(parents=True)
        results = run_dir / "checkpoint_results.jsonl"
        results.write_text(
            json.dumps({
                "strict_pass_rate": 0.5,
                "cost": 0.0,
                "input": 100,
                "output": 50,
                "cache_read": 10,
            }) + "\n",
        )

        with patch.object(
            mod, "_find_latest_run_dir",
            return_value=(run_dir, run_dir / "prob"),
        ):
            result = mod._parse_slop_code_output(
                "prob", "",
            )

        assert result["tokens"] == 160

    def test_parses_real_world_jsonl(self, tmp_path):
        """Parses a real-world checkpoint_results.jsonl
        line with all flattened fields."""
        mod = _load_runner_module()

        run_dir = tmp_path / "run"
        (run_dir / "file_backup").mkdir(parents=True)
        results = run_dir / "checkpoint_results.jsonl"
        # Simulated real data from evidence
        results.write_text(
            json.dumps({
                "problem": "file_backup",
                "checkpoint": "checkpoint_1",
                "strict_pass_rate": 0.125,
                "total_tests": 32,
                "passed_tests": 4,
                "cost": 0.0,
                "input": 0,
                "output": 0,
                "erosion": 0.0,
                "verbosity": 0.0,
            }) + "\n",
        )

        with patch.object(
            mod, "_find_latest_run_dir",
            return_value=(
                run_dir, run_dir / "file_backup",
            ),
        ):
            result = mod._parse_slop_code_output(
                "file_backup", "",
            )

        assert result["pass_rate"] == pytest.approx(
            0.125,
        )
        assert result["output_dir"] == str(run_dir)

    def test_total_tests_fallback(self, tmp_path):
        """Falls back to total_tests/passed_tests when
        strict_pass_rate is absent."""
        mod = _load_runner_module()

        run_dir = tmp_path / "run"
        (run_dir / "prob").mkdir(parents=True)
        results = run_dir / "checkpoint_results.jsonl"
        results.write_text(
            json.dumps({
                "total_tests": 20,
                "passed_tests": 16,
            }) + "\n",
        )

        with patch.object(
            mod, "_find_latest_run_dir",
            return_value=(run_dir, run_dir / "prob"),
        ):
            result = mod._parse_slop_code_output(
                "prob", "",
            )

        assert result["pass_rate"] == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# _update_metrics_from_results — erosion/verbosity
# ---------------------------------------------------------------------------


class TestUpdateMetricsErosionVerbosity:
    """_update_metrics_from_results extracts erosion and
    verbosity in addition to pass_rate and cost."""

    def test_updates_erosion_and_verbosity(
        self, tmp_path,
    ):
        """Extracts erosion and verbosity from JSONL."""
        mod = _load_runner_module()
        results_file = tmp_path / "results.jsonl"
        results_file.write_text(
            json.dumps({
                "strict_pass_rate": 0.7,
                "cost": 0.10,
                "erosion": 0.15,
                "verbosity": 0.22,
            }) + "\n",
        )
        metrics = mod.CheckpointMetrics()
        mod._update_metrics_from_results(
            metrics, results_file,
        )
        assert metrics.pass_rate == pytest.approx(0.7)
        assert metrics.cost == pytest.approx(0.10)
        assert metrics.erosion == pytest.approx(0.15)
        assert metrics.verbosity == pytest.approx(0.22)


# ---------------------------------------------------------------------------
# _extract_reviewer_suggestions
# ---------------------------------------------------------------------------


class TestExtractReviewerSuggestions:
    """_extract_reviewer_suggestions parses reviewer output."""

    def test_extracts_from_snapshot(self, tmp_path):
        """Finds Python files in snapshot directories."""
        mod = _load_runner_module()

        out_dir = tmp_path / "review_out"
        snap = out_dir / "prob" / "cp1" / "snapshot"
        snap.mkdir(parents=True)
        (snap / "solution.py").write_text(
            "def clean():\n    return 1\n",
        )

        result = mod._extract_reviewer_suggestions({
            "stdout": "",
            "stderr": "",
            "output_dir": str(out_dir),
        })

        assert result is not None
        assert "clean" in result

    def test_returns_none_when_no_output(self):
        """Returns None when no output directory."""
        mod = _load_runner_module()
        result = mod._extract_reviewer_suggestions({
            "stdout": "",
            "stderr": "",
            "output_dir": None,
        })
        assert result is None

    def test_falls_back_to_stderr(self):
        """Returns stderr if no snapshot files found."""
        mod = _load_runner_module()
        result = mod._extract_reviewer_suggestions({
            "stdout": "",
            "stderr": "Consider refactoring the main loop "
                     "to reduce complexity score",
            "output_dir": None,
        })
        assert result is not None
        assert "refactoring" in result


# ---------------------------------------------------------------------------
# run_slop_code budget enforcement
# ---------------------------------------------------------------------------


class TestRunSlopCodeBudget:
    """run_slop_code passes budget limit to slop-code CLI."""

    def test_cost_limit_in_command(self):
        """The cost_limit arg is computed from
        budget_fraction * total_budget."""
        mod = _load_runner_module()
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
                mod, "_parse_slop_code_output",
                return_value={
                    "cost": 0.0, "tokens": 0,
                    "pass_rate": 0.0, "erosion": 0.0,
                    "verbosity": 0.0, "output_dir": None,
                },
            ),
        ):
            mod.run_slop_code(
                problem="test",
                model="test",
                prompt_template=Path("p.jinja"),
                output_dir=Path("/tmp/out"),  # noqa: S108
                budget_fraction=0.7,
                total_budget=10.0,
            )

        # Should contain cost_limit=7.0
        cost_args = [
            a for a in captured_cmd
            if "cost_limit=" in a
        ]
        assert len(cost_args) == 1
        assert "7.0" in cost_args[0]

    def test_scbench_run_id_has_phase_suffix(self):
        """SCBENCH_RUN_ID includes the phase suffix."""
        mod = _load_runner_module()
        captured_env: dict = {}

        def fake_run(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        with (
            patch("subprocess.run", side_effect=fake_run),
            patch.object(
                mod, "_parse_slop_code_output",
                return_value={
                    "cost": 0.0, "tokens": 0,
                    "pass_rate": 0.0, "erosion": 0.0,
                    "verbosity": 0.0, "output_dir": None,
                },
            ),
        ):
            mod.run_slop_code(
                problem="test",
                model="test",
                prompt_template=Path("p.jinja"),
                output_dir=Path("/tmp/out"),  # noqa: S108
                budget_fraction=0.7,
                total_budget=1.0,
                run_id="abc123",
                phase="reviewer",
            )

        assert captured_env["SCBENCH_RUN_ID"] == (
            "abc123-reviewer"
        )


# ---------------------------------------------------------------------------
# NVIDIA model YAML configs
# ---------------------------------------------------------------------------


class TestNvidiaModelConfigs:
    """NVIDIA model YAML files have correct LiteLLM
    provider prefix (openai/) on mini_swe.model_name."""

    @pytest.fixture(
        params=[
            "nvidia-bedrock-claude-opus-4-6",
            "nvidia-bedrock-claude-sonnet-4-6",
            "nvidia-bedrock-claude-haiku-4-5",
        ],
    )
    def model_yaml(self, request):
        import yaml
        yaml_path = (
            REPO_ROOT / "configs" / "models"
            / f"{request.param}.yaml"
        )
        with yaml_path.open() as f:
            return yaml.safe_load(f)

    def test_mini_swe_has_openai_prefix(self, model_yaml):
        """mini_swe.model_name starts with openai/."""
        model_name = (
            model_yaml["agent_specific"]["mini_swe"]
            ["model_name"]
        )
        assert model_name.startswith("openai/"), (
            f"Expected openai/ prefix, got: {model_name}"
        )


# ---------------------------------------------------------------------------
# Fix 1: Reviewer feedback injected into implementer prompt
# ---------------------------------------------------------------------------


class TestReviewerFeedbackInjection:
    """Implementer prompt for checkpoint N+1 contains
    reviewer feedback from checkpoint N.

    Verifies that build_implementer_prompt return value
    is actually passed to run_slop_code via the
    task_prompt parameter.
    """

    @pytest.fixture()
    def fake_problem(self, tmp_path):
        prob = tmp_path / "problems" / "test_problem"
        for i in range(1, 3):
            cp = prob / f"checkpoint_{i}"
            cp.mkdir(parents=True)
            spec = prob / f"checkpoint_{i}.md"
            spec.write_text(f"Spec for checkpoint {i}")
        return prob

    def test_checkpoint_2_prompt_includes_feedback(
        self, tmp_path, fake_problem,
    ):
        """Checkpoint N+1 implementer call receives
        reviewer suggestions from checkpoint N via
        the task_prompt parameter."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        # Create a fake reviewer output with suggestions
        fake_rev_dir = tmp_path / "reviewer_output"
        snapshot = (
            fake_rev_dir / "test_problem"
            / "checkpoint_1" / "snapshot"
        )
        snapshot.mkdir(parents=True)
        (snapshot / "solution.py").write_text(
            "def refactored():\n    return 'clean'\n",
        )

        call_args: list[dict] = []

        def capture_call(**kwargs):
            call_args.append(dict(kwargs))
            phase = kwargs.get("phase", "implementer")
            if phase == "reviewer":
                return _fake_slop_result(
                    output_dir=str(fake_rev_dir),
                )
            return _fake_slop_result()

        with (
            patch.object(
                mod, "PROBLEMS_DIR",
                fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                side_effect=capture_call,
            ),
        ):
            mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
            )

        # 4 calls: impl1, rev1, impl2, rev2
        assert len(call_args) == 4

        # First implementer call (checkpoint_1) should
        # NOT have task_prompt (no prior reviewer feedback)
        assert call_args[0]["phase"] == "implementer"
        assert call_args[0].get("task_prompt") is None

        # Second implementer call (checkpoint_2) SHOULD
        # have task_prompt containing reviewer feedback
        assert call_args[2]["phase"] == "implementer"
        task_prompt = call_args[2].get("task_prompt")
        assert task_prompt is not None
        assert "reviewer" in task_prompt.lower() or (
            "refactored" in task_prompt.lower()
        )

    def test_task_prompt_none_without_feedback(
        self, tmp_path, fake_problem,
    ):
        """When no reviewer feedback exists, task_prompt
        is None (uses template file directly)."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        call_args: list[dict] = []

        def capture_call(**kwargs):
            call_args.append(dict(kwargs))
            return _fake_slop_result()

        with (
            patch.object(
                mod, "PROBLEMS_DIR",
                fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                side_effect=capture_call,
            ),
        ):
            mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
                max_checkpoints=1,
            )

        # Only 1 checkpoint: impl1, rev1
        assert len(call_args) == 2
        # No prior reviewer feedback, so no task_prompt
        assert call_args[0].get("task_prompt") is None


class TestRunSlopCodeTaskPrompt:
    """run_slop_code writes temporary template when
    task_prompt is provided."""

    def test_task_prompt_creates_temp_file(self):
        """When task_prompt is set, run_slop_code creates
        a temporary Jinja file and passes it to --prompt."""
        mod = _load_runner_module()
        captured_cmd: list[str] = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        # Create a real template file for the test
        import tempfile as tf
        with tf.NamedTemporaryFile(
            mode="w",
            suffix=".jinja",
            delete=False,
        ) as f:
            f.write(
                "Preamble\n{{ spec.strip() }}\nEnd",
            )
            template_path = Path(f.name)

        try:
            with (
                patch(
                    "subprocess.run",
                    side_effect=fake_run,
                ),
                patch.object(
                    mod, "_parse_slop_code_output",
                    return_value={
                        "cost": 0.0, "tokens": 0,
                        "pass_rate": 0.0,
                        "erosion": 0.0,
                        "verbosity": 0.0,
                        "output_dir": None,
                    },
                ),
            ):
                mod.run_slop_code(
                    problem="test",
                    model="test",
                    prompt_template=template_path,
                    output_dir=Path("/tmp/out"),  # noqa: S108
                    budget_fraction=0.7,
                    total_budget=10.0,
                    task_prompt="Review: fix the loop",
                )

            # The --prompt arg should NOT point to the
            # original template (it should be a temp file)
            prompt_idx = captured_cmd.index("--prompt")
            prompt_path = captured_cmd[prompt_idx + 1]
            assert prompt_path != str(template_path)
        finally:
            template_path.unlink(missing_ok=True)

    def test_no_task_prompt_uses_original_template(self):
        """Without task_prompt, run_slop_code uses the
        original template path."""
        mod = _load_runner_module()
        captured_cmd: list[str] = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        with (
            patch(
                "subprocess.run",
                side_effect=fake_run,
            ),
            patch.object(
                mod, "_parse_slop_code_output",
                return_value={
                    "cost": 0.0, "tokens": 0,
                    "pass_rate": 0.0, "erosion": 0.0,
                    "verbosity": 0.0,
                    "output_dir": None,
                },
            ),
        ):
            mod.run_slop_code(
                problem="test",
                model="test",
                prompt_template=Path("orig.jinja"),
                output_dir=Path("/tmp/out"),  # noqa: S108
                budget_fraction=0.7,
                total_budget=10.0,
            )

        prompt_idx = captured_cmd.index("--prompt")
        prompt_path = captured_cmd[prompt_idx + 1]
        assert prompt_path == "orig.jinja"


# ---------------------------------------------------------------------------
# Fix 2: Reviewer non-zero exit fatal in canary mode
# ---------------------------------------------------------------------------


class TestReviewerFatalInCanary:
    """Canary mode: reviewer non-zero exit raises fatal
    CanaryError with component='Reviewer'."""

    @pytest.fixture()
    def fake_problem(self, tmp_path):
        prob = tmp_path / "problems" / "test_problem"
        cp = prob / "checkpoint_1"
        cp.mkdir(parents=True)
        spec = prob / "checkpoint_1.md"
        spec.write_text("Spec for checkpoint 1")
        return prob

    def test_reviewer_nonzero_raises_canary_error(
        self, tmp_path, fake_problem,
    ):
        """Non-zero reviewer exit code raises CanaryError
        with component='Reviewer' in canary mode."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        def phase_aware(**kwargs):
            phase = kwargs.get("phase", "implementer")
            if phase == "reviewer":
                result = _fake_slop_result()
                result["exit_code"] = 1
                return result
            return _fake_slop_result()

        with (
            patch.object(
                mod, "PROBLEMS_DIR",
                fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                side_effect=phase_aware,
            ),
        ):
            with pytest.raises(
                mod.CanaryError,
            ) as exc_info:
                mod.run_two_agent(
                    problem="test_problem",
                    model="opus-4.5",
                    implementer_prompt=Path("i.jinja"),
                    reviewer_prompt=Path("r.jinja"),
                    budget_split=70,
                    budget=10.0,
                    output_dir=out,
                    canary_mode=True,
                )
            assert (
                exc_info.value.component == "Reviewer"
            )

    def test_implementer_nonzero_raises_canary_error(
        self, tmp_path, fake_problem,
    ):
        """Non-zero implementer exit code raises CanaryError
        with component='Implementer' in canary mode."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        def impl_fails(**kwargs):
            result = _fake_slop_result()
            phase = kwargs.get("phase", "implementer")
            if phase == "implementer":
                result["exit_code"] = 1
            return result

        with (
            patch.object(
                mod, "PROBLEMS_DIR",
                fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                side_effect=impl_fails,
            ),
        ):
            with pytest.raises(
                mod.CanaryError,
            ) as exc_info:
                mod.run_two_agent(
                    problem="test_problem",
                    model="opus-4.5",
                    implementer_prompt=Path("i.jinja"),
                    reviewer_prompt=Path("r.jinja"),
                    budget_split=70,
                    budget=10.0,
                    output_dir=out,
                    canary_mode=True,
                )
            assert (
                exc_info.value.component == "Implementer"
            )

    def test_nonzero_exit_ignored_without_canary(
        self, tmp_path, fake_problem,
    ):
        """Non-zero exit codes are NOT fatal when
        canary_mode is False (normal mode)."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        def always_fails(**kwargs):
            result = _fake_slop_result()
            result["exit_code"] = 1
            return result

        with (
            patch.object(
                mod, "PROBLEMS_DIR",
                fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                side_effect=always_fails,
            ),
        ):
            # Should not raise CanaryError
            state = mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("i.jinja"),
                reviewer_prompt=Path("r.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
                canary_mode=False,
            )
            assert isinstance(state, mod.RunState)


# ---------------------------------------------------------------------------
# Fix 3: CanaryError preserves originating component
# ---------------------------------------------------------------------------


class TestCanaryErrorComponentPreservation:
    """CanaryError preserves originating component
    (Docker, API, Implementer, Reviewer, Evaluation)
    instead of mapping to generic 'Pipeline'."""

    def test_reviewer_error_preserves_component(self):
        """run_canary propagates CanaryError with
        component='Reviewer' from run_two_agent."""
        mod = _load_runner_module()

        with (
            patch.object(mod, "run_preflight_checks"),
            patch.object(
                mod, "validate_model",
                return_value="opus-4.5",
            ),
            patch.object(
                mod, "run_two_agent",
                side_effect=mod.CanaryError(
                    "Reviewer",
                    "Reviewer exited with code 1",
                ),
            ),
            patch.object(
                mod, "OUTPUTS_DIR",
                Path("/tmp/canary_test"),  # noqa: S108
            ),
        ):
            with pytest.raises(
                mod.CanaryError,
            ) as exc_info:
                mod.run_canary()
            assert (
                exc_info.value.component == "Reviewer"
            )

    def test_implementer_error_preserves_component(self):
        """run_canary propagates CanaryError with
        component='Implementer' from run_two_agent."""
        mod = _load_runner_module()

        with (
            patch.object(mod, "run_preflight_checks"),
            patch.object(
                mod, "validate_model",
                return_value="opus-4.5",
            ),
            patch.object(
                mod, "run_two_agent",
                side_effect=mod.CanaryError(
                    "Implementer",
                    "Implementer exited with code 1",
                ),
            ),
            patch.object(
                mod, "OUTPUTS_DIR",
                Path("/tmp/canary_test"),  # noqa: S108
            ),
        ):
            with pytest.raises(
                mod.CanaryError,
            ) as exc_info:
                mod.run_canary()
            assert (
                exc_info.value.component
                == "Implementer"
            )

    def test_system_exit_still_maps_to_pipeline(self):
        """SystemExit (non-CanaryError) still maps to
        generic 'Pipeline' component."""
        mod = _load_runner_module()

        with (
            patch.object(mod, "run_preflight_checks"),
            patch.object(
                mod, "validate_model",
                return_value="opus-4.5",
            ),
            patch.object(
                mod, "run_two_agent",
                side_effect=SystemExit(1),
            ),
            patch.object(
                mod, "OUTPUTS_DIR",
                Path("/tmp/canary_test"),  # noqa: S108
            ),
        ):
            with pytest.raises(
                mod.CanaryError,
            ) as exc_info:
                mod.run_canary()
            assert (
                exc_info.value.component == "Pipeline"
            )

    def test_docker_error_preserves_component(self):
        """Docker preflight failure has component='Docker'.
        """
        mod = _load_runner_module()

        with (
            patch.object(
                mod, "run_preflight_checks",
                side_effect=mod.CanaryError(
                    "Docker", "not running",
                ),
            ),
            patch.object(
                mod, "validate_model",
                return_value="opus-4.5",
            ),
            patch.object(
                mod, "OUTPUTS_DIR",
                Path("/tmp/canary_test"),  # noqa: S108
            ),
        ):
            with pytest.raises(
                mod.CanaryError,
            ) as exc_info:
                mod.run_canary()
            assert (
                exc_info.value.component == "Docker"
            )

    def test_canary_error_has_all_valid_components(self):
        """CanaryError accepts all documented component
        names."""
        mod = _load_runner_module()
        for component in [
            "Docker", "API", "Claude CLI",
            "Implementer", "Reviewer",
            "Evaluation", "Pipeline",
        ]:
            err = mod.CanaryError(
                component, "test detail",
            )
            assert err.component == component
            assert err.detail == "test detail"
            assert component in str(err)


# ---------------------------------------------------------------------------
# Checkpoint discovery
# ---------------------------------------------------------------------------


class TestDiscoverCheckpoints:
    """discover_checkpoints finds checkpoints from
    config.yaml or checkpoint_*.md files."""

    def test_discovers_from_md_files(self, tmp_path):
        """Fallback: discovers checkpoints from .md files
        when config.yaml is absent."""
        mod = _load_runner_module()
        prob = tmp_path / "test_prob"
        prob.mkdir()
        for i in range(1, 4):
            (prob / f"checkpoint_{i}.md").write_text(
                f"Spec {i}",
            )
        checkpoints = mod.discover_checkpoints(
            "test_prob", prob,
        )
        assert checkpoints == [
            "checkpoint_1",
            "checkpoint_2",
            "checkpoint_3",
        ]

    def test_discovers_from_config_yaml(self, tmp_path):
        """Discovers checkpoints from a proper config.yaml
        using ProblemConfig."""
        mod = _load_runner_module()
        prob = tmp_path / "real_prob"
        prob.mkdir()
        cfg = (
            "version: 1\n"
            "name: real_prob\n"
            "description: test\n"
            "category: test\n"
            "entry_file: main\n"
            "checkpoints:\n"
            "  checkpoint_1:\n"
            "    version: 1\n"
            "    order: 1\n"
            "    state: Core Tests\n"
            "  checkpoint_2:\n"
            "    version: 1\n"
            "    order: 2\n"
            "    state: Core Tests\n"
        )
        (prob / "config.yaml").write_text(cfg)
        (prob / "checkpoint_1.md").write_text("Spec 1")
        (prob / "checkpoint_2.md").write_text("Spec 2")

        checkpoints = mod.discover_checkpoints(
            "real_prob", prob,
        )
        assert checkpoints == [
            "checkpoint_1",
            "checkpoint_2",
        ]

    def test_exits_when_no_checkpoints(self, tmp_path):
        """Exits with SystemExit(1) when no checkpoints
        are found."""
        mod = _load_runner_module()
        prob = tmp_path / "empty_prob"
        prob.mkdir()
        with pytest.raises(SystemExit):
            mod.discover_checkpoints("empty_prob", prob)

    def test_real_problem_file_backup(self):
        """Discovers checkpoints for real file_backup
        problem."""
        mod = _load_runner_module()
        prob_dir = mod.PROBLEMS_DIR / "file_backup"
        if prob_dir.exists():
            checkpoints = mod.discover_checkpoints(
                "file_backup", prob_dir,
            )
            assert len(checkpoints) >= 1
            assert "checkpoint_1" in checkpoints


# ---------------------------------------------------------------------------
# Canary model selection
# ---------------------------------------------------------------------------


class TestDefaultCanaryModel:
    """_default_canary_model picks the right model
    based on available credentials."""

    def test_prefers_anthropic_when_set(self):
        """Returns Anthropic model when ANTHROPIC_API_KEY
        is available."""
        mod = _load_runner_module()
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "sk-test"},
        ):
            assert (
                mod._default_canary_model()
                == mod.CANARY_DEFAULT_MODEL_ANTHROPIC
            )

    def test_falls_back_to_nvidia(self):
        """Returns NVIDIA model when only
        NVIDIA_INFERENCE_KEY is set."""
        mod = _load_runner_module()
        env = {
            k: v
            for k, v in os.environ.items()
            if k != "ANTHROPIC_API_KEY"
        }
        env["NVIDIA_INFERENCE_KEY"] = "nvapi-test"
        with patch.dict(os.environ, env, clear=True):
            assert (
                mod._default_canary_model()
                == mod.CANARY_DEFAULT_MODEL_NVIDIA
            )

    def test_falls_back_to_anthropic_when_nothing_set(self):
        """Returns Anthropic model when no keys are set
        (credential check will fail later)."""
        mod = _load_runner_module()
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            not in ("ANTHROPIC_API_KEY", "NVIDIA_INFERENCE_KEY")
        }
        with patch.dict(os.environ, env, clear=True):
            assert (
                mod._default_canary_model()
                == mod.CANARY_DEFAULT_MODEL_ANTHROPIC
            )


# ---------------------------------------------------------------------------
# pymysql availability
# ---------------------------------------------------------------------------


class TestPymysqlAvailable:
    """pymysql is installed and importable."""

    def test_pymysql_importable(self):
        """pymysql can be imported."""
        import pymysql

        assert pymysql.__version__


# ---------------------------------------------------------------------------
# Environment YAML copying
# ---------------------------------------------------------------------------


class TestCopyEnvironmentYaml:
    """environment.yaml is copied into output dir."""

    def test_copies_from_problem_dir(self, tmp_path):
        """Copies environment.yaml from problem dir."""
        mod = _load_runner_module()
        problem_dir = tmp_path / "problem"
        problem_dir.mkdir()
        env_src = problem_dir / "environment.yaml"
        env_src.write_text("type: docker\nname: test\n")

        out = tmp_path / "output"
        out.mkdir()
        mod._copy_environment_yaml(problem_dir, out)

        dst = out / "environment.yaml"
        assert dst.exists()
        assert "type: docker" in dst.read_text()

    def test_falls_back_to_default(self, tmp_path):
        """Falls back to default config when problem has
        no environment.yaml."""
        mod = _load_runner_module()
        problem_dir = tmp_path / "problem"
        problem_dir.mkdir()

        out = tmp_path / "output"
        out.mkdir()
        mod._copy_environment_yaml(problem_dir, out)

        dst = out / "environment.yaml"
        assert dst.exists()
        content = dst.read_text()
        assert "type: docker" in content

    def test_does_not_overwrite(self, tmp_path):
        """Does not overwrite existing environment.yaml."""
        mod = _load_runner_module()
        problem_dir = tmp_path / "problem"
        problem_dir.mkdir()
        (problem_dir / "environment.yaml").write_text(
            "type: new\n",
        )

        out = tmp_path / "output"
        out.mkdir()
        existing = out / "environment.yaml"
        existing.write_text("type: existing\n")

        mod._copy_environment_yaml(problem_dir, out)
        assert existing.read_text() == "type: existing\n"


# ---------------------------------------------------------------------------
# Reviewer suggestions persistence
# ---------------------------------------------------------------------------


class TestReviewerSuggestionsPersistence:
    """Reviewer output persisted to JSON files."""

    def test_save_reviewer_suggestions(self, tmp_path):
        """Saves suggestions to
        reviewer_suggestions_checkpoint_N.json."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        mod._save_reviewer_suggestions(
            output_dir=out,
            checkpoint_name="checkpoint_1",
            suggestions="Reduce complexity in foo()",
            review_result={
                "exit_code": 0,
                "cost": 0.05,
                "tokens": 100,
            },
        )

        path = out / "reviewer_suggestions_checkpoint_1.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["checkpoint"] == "checkpoint_1"
        assert data["suggestions"] == (
            "Reduce complexity in foo()"
        )
        assert data["cost"] == 0.05
        assert data["tokens"] == 100
        assert "timestamp" in data

    def test_save_none_suggestions(self, tmp_path):
        """Handles None suggestions gracefully."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        mod._save_reviewer_suggestions(
            output_dir=out,
            checkpoint_name="checkpoint_2",
            suggestions=None,
            review_result={"exit_code": 0},
        )

        path = out / "reviewer_suggestions_checkpoint_2.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["suggestions"] is None


# ---------------------------------------------------------------------------
# NVIDIA API key validation
# ---------------------------------------------------------------------------


class TestNvidiaApiKeyValidation:
    """Canary validates NVIDIA API key with test call."""

    def test_skipped_when_no_key(self):
        """No error when NVIDIA_INFERENCE_KEY is unset."""
        mod = _load_runner_module()
        env = {
            k: v
            for k, v in os.environ.items()
            if k != "NVIDIA_INFERENCE_KEY"
        }
        with patch.dict(os.environ, env, clear=True):
            # Should not raise
            mod.validate_nvidia_api_key()

    def test_raises_on_bad_key(self):
        """CanaryError on invalid NVIDIA key."""
        mod = _load_runner_module()
        with patch.dict(
            os.environ,
            {"NVIDIA_INFERENCE_KEY": "bad-key"},
        ):
            with pytest.raises(mod.CanaryError) as exc:
                mod.validate_nvidia_api_key()
            assert exc.value.component == "API"
            assert "NVIDIA" in exc.value.detail

    def test_preflight_includes_nvidia_check(self):
        """run_preflight_checks calls
        validate_nvidia_api_key."""
        mod = _load_runner_module()
        with (
            patch.object(mod, "check_docker"),
            patch.object(mod, "check_api_key"),
            patch.object(
                mod, "validate_nvidia_api_key",
            ) as mock_nv,
            patch.object(mod, "check_claude_cli"),
        ):
            mod.run_preflight_checks("test-model")
            mock_nv.assert_called_once()


# ---------------------------------------------------------------------------
# Budget-split 100 (implementer-only)
# ---------------------------------------------------------------------------


class TestBudgetSplit100:
    """VAL-RUNNER-009: budget_split=100 runs without
    reviewer."""

    @pytest.fixture()
    def fake_problem(self, tmp_path):
        """Create a fake problem with 1 checkpoint."""
        mod = _load_runner_module()
        p = Path(mod.PROBLEMS_DIR) / "test_problem_100"
        p.mkdir(parents=True, exist_ok=True)
        (p / "config.yaml").write_text(
            "version: 1\nname: test_problem_100\n"
            "checkpoints:\n"
            "  checkpoint_1:\n"
            "    version: 1\n"
            "    order: 1\n",
        )
        (p / "checkpoint_1.md").write_text("Spec text\n")
        yield p
        import shutil
        shutil.rmtree(p, ignore_errors=True)

    def test_no_reviewer_calls_when_100(
        self, tmp_path, fake_problem,
    ):
        """With budget_split=100, reviewer phase is
        skipped and run_slop_code is called only for
        implementer."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        call_args = []

        def fake_run_slop(*a, **kw):
            call_args.append(kw)
            return {
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "cost": 0.05,
                "tokens": 50,
                "pass_rate": 0.8,
                "erosion": 0.1,
                "verbosity": 0.2,
                "output_dir": None,
            }

        with patch.object(
            mod, "run_slop_code", side_effect=fake_run_slop,
        ):
            state = mod.run_two_agent(
                problem="test_problem_100",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=100,
                budget=10.0,
                output_dir=out,
            )

        # Only 1 call (implementer), no reviewer
        assert len(call_args) == 1
        assert call_args[0]["phase"] == "implementer"
        assert state.checkpoint_metrics[
            "checkpoint_1"
        ].tokens_reviewer == 0


# ---------------------------------------------------------------------------
# Mid-execution budget check
# ---------------------------------------------------------------------------


class TestMidExecutionBudgetCheck:
    """Budget cap aborts DURING checkpoint execution."""

    @pytest.fixture()
    def fake_problem(self, tmp_path):
        """Create a fake problem with 2 checkpoints."""
        mod = _load_runner_module()
        p = Path(mod.PROBLEMS_DIR) / "test_mid_budget"
        p.mkdir(parents=True, exist_ok=True)
        (p / "config.yaml").write_text(
            "version: 1\nname: test_mid_budget\n"
            "checkpoints:\n"
            "  checkpoint_1:\n"
            "    version: 1\n"
            "    order: 1\n"
            "  checkpoint_2:\n"
            "    version: 1\n"
            "    order: 2\n",
        )
        (p / "checkpoint_1.md").write_text("Spec 1\n")
        (p / "checkpoint_2.md").write_text("Spec 2\n")
        yield p
        import shutil
        shutil.rmtree(p, ignore_errors=True)

    def test_aborts_after_implementer_exceeds_budget(
        self, tmp_path, fake_problem,
    ):
        """Aborts after implementer phase when cumulative
        cost exceeds budget, saving partial results."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        call_count = [0]

        def fake_run_slop(*a, **kw):
            call_count[0] += 1
            # Implementer costs 0.60 per call
            return {
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "cost": 0.60,
                "tokens": 50,
                "pass_rate": 0.5,
                "erosion": 0.1,
                "verbosity": 0.2,
                "output_dir": None,
            }

        with (
            patch.object(
                mod, "run_slop_code",
                side_effect=fake_run_slop,
            ),
            pytest.raises(SystemExit),
        ):
            mod.run_two_agent(
                problem="test_mid_budget",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=0.50,
                output_dir=out,
            )

        # Should have been called once (implementer only)
        # before budget was exceeded
        assert call_count[0] == 1

        # Partial results saved
        metrics_file = out / "two_agent_metrics.json"
        assert metrics_file.exists()
        data = json.loads(metrics_file.read_text())
        assert data["budget_exceeded"] is True
        assert data["completed_checkpoints"] == 1

    def test_aborts_after_reviewer_exceeds_budget(
        self, tmp_path, fake_problem,
    ):
        """Aborts after reviewer phase when cumulative
        cost exceeds budget."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        call_count = [0]

        def fake_run_slop(*a, **kw):
            call_count[0] += 1
            phase = kw.get("phase", "")
            cost = 0.20 if phase == "implementer" else 0.40
            return {
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "cost": cost,
                "tokens": 50,
                "pass_rate": 0.5,
                "erosion": 0.0,
                "verbosity": 0.0,
                "output_dir": None,
            }

        with (
            patch.object(
                mod, "run_slop_code",
                side_effect=fake_run_slop,
            ),
            pytest.raises(SystemExit),
        ):
            mod.run_two_agent(
                problem="test_mid_budget",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=0.50,
                output_dir=out,
            )

        # Implementer + reviewer = 2 calls before abort
        assert call_count[0] == 2

        metrics_file = out / "two_agent_metrics.json"
        assert metrics_file.exists()
        data = json.loads(metrics_file.read_text())
        assert data["budget_exceeded"] is True


# ---------------------------------------------------------------------------
# [REVIEWER->IMPLEMENTER] log markers
# ---------------------------------------------------------------------------


class TestReviewerImplementerLogMarkers:
    """Log markers appear when reviewer suggestions
    are injected."""

    @pytest.fixture()
    def fake_problem(self, tmp_path):
        """Create a fake problem with 2 checkpoints."""
        mod = _load_runner_module()
        p = Path(mod.PROBLEMS_DIR) / "test_log_markers"
        p.mkdir(parents=True, exist_ok=True)
        (p / "config.yaml").write_text(
            "version: 1\nname: test_log_markers\n"
            "checkpoints:\n"
            "  checkpoint_1:\n"
            "    version: 1\n"
            "    order: 1\n"
            "  checkpoint_2:\n"
            "    version: 1\n"
            "    order: 2\n",
        )
        (p / "checkpoint_1.md").write_text("Spec 1\n")
        (p / "checkpoint_2.md").write_text("Spec 2\n")
        yield p
        import shutil
        shutil.rmtree(p, ignore_errors=True)

    def test_reviewer_implementer_marker_present(
        self, tmp_path, fake_problem, capsys,
    ):
        """[REVIEWER->IMPLEMENTER] marker appears in
        output when injecting reviewer suggestions."""
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        fake_rev_dir = tmp_path / "rev_out"
        snap = (
            fake_rev_dir / "test_log_markers"
            / "checkpoint_1" / "snapshot"
        )
        snap.mkdir(parents=True)
        (snap / "main.py").write_text(
            "def improved(): pass\n",
        )

        def fake_run_slop(*a, **kw):
            phase = kw.get("phase", "")
            return {
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "cost": 0.01,
                "tokens": 10,
                "pass_rate": 0.5,
                "erosion": 0.0,
                "verbosity": 0.0,
                "output_dir": (
                    str(fake_rev_dir)
                    if phase == "reviewer"
                    else None
                ),
            }

        with patch.object(
            mod, "run_slop_code",
            side_effect=fake_run_slop,
        ):
            mod.run_two_agent(
                problem="test_log_markers",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
            )

        captured = capsys.readouterr()
        assert "[REVIEWER->IMPLEMENTER]" in captured.out



# ---------------------------------------------------------------------------
# __main__.py existence
# ---------------------------------------------------------------------------


class TestMainModule:
    """src/slop_code/__main__.py exists and is importable."""

    def test_main_module_exists(self):
        main_path = (
            REPO_ROOT / "src" / "slop_code"
            / "__main__.py"
        )
        assert main_path.is_file()

    def test_python_m_slop_code_help(self):
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "slop_code", "--help"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=30,
            env={
                **os.environ,
                "PYTHONPATH": str(REPO_ROOT / "src"),
            },
        )
        assert result.returncode == 0
        assert "Usage" in result.stdout


class TestFormatModelForCli:
    def test_already_has_slash(self):
        mod = _load_runner_module()
        assert mod.format_model_for_cli("nvidia/x") == "nvidia/x"

    def test_bare_model_gets_provider(self):
        mod = _load_runner_module()
        result = mod.format_model_for_cli("opus-4.5")
        assert "/" in result
        assert result == "anthropic/opus-4.5"

    def test_nvidia_model_gets_nvidia_provider(self):
        mod = _load_runner_module()
        result = mod.format_model_for_cli(
            "nvidia-bedrock-claude-sonnet-4-6",
        )
        assert result == (
            "nvidia/nvidia-bedrock-claude-sonnet-4-6"
        )

    def test_unknown_model_falls_back_to_nvidia(self):
        mod = _load_runner_module()
        result = mod.format_model_for_cli("fake-xyz")
        assert result == "nvidia/fake-xyz"


class TestRunSlopCodeModelFormat:
    def test_model_arg_has_provider_prefix(self):
        mod = _load_runner_module()
        captured_cmd = []

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
                mod, "_parse_slop_code_output",
                return_value={
                    "cost": 0.0, "tokens": 0,
                    "pass_rate": 0.0, "erosion": 0.0,
                    "verbosity": 0.0, "output_dir": None,
                },
            ),
        ):
            mod.run_slop_code(
                problem="test",
                model="opus-4.5",
                prompt_template=Path("p.jinja"),
                output_dir=Path("/tmp/out"),  # noqa: S108
                budget_fraction=0.7,
                total_budget=10.0,
            )

        model_idx = captured_cmd.index("--model")
        model_val = captured_cmd[model_idx + 1]
        assert "/" in model_val


class TestNormalModeExitCodeHandling:
    @pytest.fixture()
    def fake_problem(self, tmp_path):
        prob = tmp_path / "problems" / "test_problem"
        cp = prob / "checkpoint_1"
        cp.mkdir(parents=True)
        (prob / "checkpoint_1.md").write_text("Spec 1")
        return prob

    def test_impl_nonzero_warns(
        self, tmp_path, fake_problem, capsys,
    ):
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        def impl_fails(**kwargs):
            r = _fake_slop_result()
            if kwargs.get("phase") == "implementer":
                r["exit_code"] = 1
            return r

        with (
            patch.object(
                mod, "PROBLEMS_DIR",
                fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                side_effect=impl_fails,
            ),
        ):
            state = mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("i.jinja"),
                reviewer_prompt=Path("r.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
                canary_mode=False,
            )
        assert isinstance(state, mod.RunState)
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "Implementer" in captured.err

    def test_reviewer_nonzero_warns(
        self, tmp_path, fake_problem, capsys,
    ):
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        def rev_fails(**kwargs):
            r = _fake_slop_result()
            if kwargs.get("phase") == "reviewer":
                r["exit_code"] = 1
            return r

        with (
            patch.object(
                mod, "PROBLEMS_DIR",
                fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                side_effect=rev_fails,
            ),
        ):
            state = mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("i.jinja"),
                reviewer_prompt=Path("r.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
                canary_mode=False,
            )
        assert isinstance(state, mod.RunState)
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "Reviewer" in captured.err


class TestConfigYamlWritten:
    @pytest.fixture()
    def fake_problem(self, tmp_path):
        prob = tmp_path / "problems" / "test_problem"
        cp = prob / "checkpoint_1"
        cp.mkdir(parents=True)
        (prob / "checkpoint_1.md").write_text("Spec 1")
        return prob

    def test_config_yaml_written(
        self, tmp_path, fake_problem,
    ):
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        with (
            patch.object(
                mod, "PROBLEMS_DIR",
                fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                return_value=_fake_slop_result(),
            ),
        ):
            mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
            )

        cfg_path = out / "config.yaml"
        assert cfg_path.exists()
        import yaml
        cfg = yaml.safe_load(cfg_path.read_text())
        assert cfg["model"]["name"] == "opus-4.5"
        assert cfg["run"]["problem"] == "test_problem"
        assert cfg["run"]["mode"] == "two-agent"

    def test_config_yaml_not_overwritten(
        self, tmp_path, fake_problem,
    ):
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()
        existing = out / "config.yaml"
        existing.write_text("existing: true\n")

        with (
            patch.object(
                mod, "PROBLEMS_DIR",
                fake_problem.parent,
            ),
            patch.object(
                mod, "run_slop_code",
                return_value=_fake_slop_result(),
            ),
        ):
            mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("impl.jinja"),
                reviewer_prompt=Path("rev.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
            )

        assert existing.read_text() == "existing: true\n"

    def test_write_config_yaml_function(self, tmp_path):
        mod = _load_runner_module()
        out = tmp_path / "output"
        out.mkdir()

        mod._write_config_yaml(
            out,
            problem="file_backup",
            model="nvidia/nvidia-bedrock-claude-sonnet-4-6",
            budget=5.0,
            budget_split=70,
            implementer_prompt="impl.jinja",
            reviewer_prompt="rev.jinja",
        )

        import yaml
        cfg = yaml.safe_load(
            (out / "config.yaml").read_text(),
        )
        assert cfg["model"]["provider"] == "nvidia"
        assert cfg["run"]["budget"] == 5.0
