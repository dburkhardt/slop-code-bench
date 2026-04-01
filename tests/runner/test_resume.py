"""Tests for crash-resume behaviour.

VAL-RUNNER-012: Re-running after crash detects existing output
and resumes from next incomplete checkpoint.  Completed
checkpoint results are not overwritten (same timestamps /
content).  Runner logs indicate resumption.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Module loader
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    REPO_ROOT / "research" / "runner" / "two_agent_runner.py"
)


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "two_agent_runner", str(RUNNER_PATH),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["two_agent_runner"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# detect_completed_checkpoints
# ---------------------------------------------------------------------------


class TestDetectCompletedCheckpoints:
    """detect_completed_checkpoints reads prior metrics."""

    def test_returns_empty_when_no_file(self, tmp_path):
        mod = _load_runner()
        result = mod.detect_completed_checkpoints(tmp_path)
        assert result == {}

    def test_returns_empty_for_invalid_json(self, tmp_path):
        mod = _load_runner()
        (tmp_path / "two_agent_metrics.json").write_text(
            "not json{{{",
        )
        result = mod.detect_completed_checkpoints(tmp_path)
        assert result == {}

    def test_returns_empty_for_empty_checkpoints(
        self, tmp_path,
    ):
        mod = _load_runner()
        payload = {"checkpoints": {}}
        (tmp_path / "two_agent_metrics.json").write_text(
            json.dumps(payload),
        )
        result = mod.detect_completed_checkpoints(tmp_path)
        assert result == {}

    def test_loads_completed_checkpoints(self, tmp_path):
        mod = _load_runner()
        payload = {
            "checkpoints": {
                "checkpoint_1": {
                    "pass_rate": 0.9,
                    "erosion": 0.1,
                    "verbosity": 0.05,
                    "tokens_implementer": 500,
                    "tokens_reviewer": 200,
                    "cost": 0.02,
                },
                "checkpoint_2": {
                    "pass_rate": 0.8,
                    "erosion": 0.2,
                    "verbosity": 0.1,
                    "tokens_implementer": 600,
                    "tokens_reviewer": 300,
                    "cost": 0.03,
                },
            },
        }
        (tmp_path / "two_agent_metrics.json").write_text(
            json.dumps(payload),
        )
        result = mod.detect_completed_checkpoints(tmp_path)
        assert len(result) == 2
        assert result["checkpoint_1"].pass_rate == pytest.approx(
            0.9,
        )
        assert result["checkpoint_2"].cost == pytest.approx(
            0.03,
        )

    def test_skips_malformed_checkpoint_entry(self, tmp_path):
        """A checkpoint with bad data is skipped, others load."""
        mod = _load_runner()
        payload = {
            "checkpoints": {
                "checkpoint_1": {
                    "pass_rate": 0.9,
                    "erosion": 0.1,
                    "verbosity": 0.05,
                    "tokens_implementer": 500,
                    "tokens_reviewer": 200,
                    "cost": 0.02,
                },
                "checkpoint_2": "not a dict",
            },
        }
        (tmp_path / "two_agent_metrics.json").write_text(
            json.dumps(payload),
        )
        result = mod.detect_completed_checkpoints(tmp_path)
        assert len(result) == 1
        assert "checkpoint_1" in result


# ---------------------------------------------------------------------------
# load_resume_state
# ---------------------------------------------------------------------------


class TestLoadResumeState:
    """load_resume_state returns full prior metrics."""

    def test_returns_none_when_no_file(self, tmp_path):
        mod = _load_runner()
        assert mod.load_resume_state(tmp_path) is None

    def test_returns_none_for_bad_json(self, tmp_path):
        mod = _load_runner()
        (tmp_path / "two_agent_metrics.json").write_text("{{{")
        assert mod.load_resume_state(tmp_path) is None

    def test_loads_full_state(self, tmp_path):
        mod = _load_runner()
        payload = {
            "problem": "file_backup",
            "model": "opus-4.5",
            "checkpoints": {"checkpoint_1": {}},
        }
        (tmp_path / "two_agent_metrics.json").write_text(
            json.dumps(payload),
        )
        state = mod.load_resume_state(tmp_path)
        assert state is not None
        assert state["problem"] == "file_backup"


# ---------------------------------------------------------------------------
# run_two_agent with resume
# ---------------------------------------------------------------------------


class TestRunTwoAgentResume:
    """Resume integration: completed checkpoints are skipped
    and their metrics preserved."""

    @pytest.fixture()
    def fake_problem(self, tmp_path):
        """Create a fake problem with 3 checkpoints."""
        prob = tmp_path / "problems" / "test_problem"
        for i in range(1, 4):
            cp_dir = prob / f"checkpoint_{i}"
            cp_dir.mkdir(parents=True)
            spec = prob / f"checkpoint_{i}.md"
            spec.write_text(f"Spec for checkpoint {i}")
        return prob

    def test_resume_skips_completed(
        self, tmp_path, fake_problem,
    ):
        """Checkpoints already in metrics are not re-run."""
        mod = _load_runner()

        out_dir = tmp_path / "output"
        out_dir.mkdir()

        # Write prior results with checkpoint_1 completed
        prior = {
            "checkpoints": {
                "checkpoint_1": {
                    "pass_rate": 0.95,
                    "erosion": 0.05,
                    "verbosity": 0.02,
                    "tokens_implementer": 800,
                    "tokens_reviewer": 400,
                    "cost": 0.04,
                },
            },
        }
        (out_dir / "two_agent_metrics.json").write_text(
            json.dumps(prior),
        )

        # Patch PROBLEMS_DIR to use our fixture
        with patch.object(
            mod, "PROBLEMS_DIR", fake_problem.parent,
        ):
            state = mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("dummy.jinja"),
                reviewer_prompt=Path("dummy.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out_dir,
            )

        # checkpoint_1 preserved with original metrics
        cp1 = state.checkpoint_metrics["checkpoint_1"]
        assert cp1.pass_rate == pytest.approx(0.95)
        assert cp1.tokens_implementer == 800
        assert cp1.cost == pytest.approx(0.04)

        # checkpoint_2 and checkpoint_3 were run (placeholder
        # values since no real invocation)
        assert "checkpoint_2" in state.checkpoint_metrics
        assert "checkpoint_3" in state.checkpoint_metrics
        assert len(state.checkpoint_metrics) == 3

    def test_completed_not_overwritten(
        self, tmp_path, fake_problem,
    ):
        """Timestamps and content of completed checkpoints
        remain unchanged after resume."""
        mod = _load_runner()

        out_dir = tmp_path / "output"
        out_dir.mkdir()

        original_metrics = {
            "pass_rate": 0.95,
            "erosion": 0.05,
            "verbosity": 0.02,
            "tokens_implementer": 800,
            "tokens_reviewer": 400,
            "cost": 0.04,
        }
        prior = {
            "checkpoints": {
                "checkpoint_1": original_metrics,
            },
            "timestamp": "2026-03-01T00:00:00+00:00",
        }
        metrics_file = out_dir / "two_agent_metrics.json"
        metrics_file.write_text(json.dumps(prior))

        with patch.object(
            mod, "PROBLEMS_DIR", fake_problem.parent,
        ):
            mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("dummy.jinja"),
                reviewer_prompt=Path("dummy.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out_dir,
            )

        # The file is rewritten (save_results), but the
        # checkpoint_1 metrics inside are identical.
        saved = json.loads(metrics_file.read_text())
        cp1 = saved["checkpoints"]["checkpoint_1"]
        assert cp1 == original_metrics

    def test_resume_logs_message(
        self, tmp_path, fake_problem, capsys,
    ):
        """Runner echoes a resume message to stdout."""
        mod = _load_runner()

        out_dir = tmp_path / "output"
        out_dir.mkdir()

        prior = {
            "checkpoints": {
                "checkpoint_1": {
                    "pass_rate": 0.9,
                    "erosion": 0.0,
                    "verbosity": 0.0,
                    "tokens_implementer": 0,
                    "tokens_reviewer": 0,
                    "cost": 0.0,
                },
            },
        }
        (out_dir / "two_agent_metrics.json").write_text(
            json.dumps(prior),
        )

        with patch.object(
            mod, "PROBLEMS_DIR", fake_problem.parent,
        ):
            mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("dummy.jinja"),
                reviewer_prompt=Path("dummy.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out_dir,
            )

        captured = capsys.readouterr()
        assert "resuming" in captured.out.lower()

    def test_no_resume_on_fresh_directory(
        self, tmp_path, fake_problem,
    ):
        """A fresh output directory does not trigger resume."""
        mod = _load_runner()

        out_dir = tmp_path / "output"
        out_dir.mkdir()

        with patch.object(
            mod, "PROBLEMS_DIR", fake_problem.parent,
        ):
            state = mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("dummy.jinja"),
                reviewer_prompt=Path("dummy.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out_dir,
            )

        # All 3 checkpoints run from scratch
        assert len(state.checkpoint_metrics) == 3

    def test_all_completed_no_work(
        self, tmp_path, fake_problem,
    ):
        """When all checkpoints are already done, no new work
        is performed and results are preserved."""
        mod = _load_runner()

        out_dir = tmp_path / "output"
        out_dir.mkdir()

        prior = {
            "checkpoints": {
                f"checkpoint_{i}": {
                    "pass_rate": 0.9,
                    "erosion": 0.0,
                    "verbosity": 0.0,
                    "tokens_implementer": 100 * i,
                    "tokens_reviewer": 50 * i,
                    "cost": 0.01 * i,
                }
                for i in range(1, 4)
            },
        }
        (out_dir / "two_agent_metrics.json").write_text(
            json.dumps(prior),
        )

        with patch.object(
            mod, "PROBLEMS_DIR", fake_problem.parent,
        ):
            state = mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("dummy.jinja"),
                reviewer_prompt=Path("dummy.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out_dir,
            )

        assert len(state.checkpoint_metrics) == 3
        assert state.checkpoint_metrics[
            "checkpoint_1"
        ].tokens_implementer == 100

    def test_resume_accumulates_cost_correctly(
        self, tmp_path, fake_problem,
    ):
        """Cumulative cost includes both resumed and new
        checkpoint costs."""
        mod = _load_runner()

        out_dir = tmp_path / "output"
        out_dir.mkdir()

        prior = {
            "checkpoints": {
                "checkpoint_1": {
                    "pass_rate": 0.9,
                    "erosion": 0.0,
                    "verbosity": 0.0,
                    "tokens_implementer": 500,
                    "tokens_reviewer": 200,
                    "cost": 0.05,
                },
            },
        }
        (out_dir / "two_agent_metrics.json").write_text(
            json.dumps(prior),
        )

        with patch.object(
            mod, "PROBLEMS_DIR", fake_problem.parent,
        ):
            state = mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("dummy.jinja"),
                reviewer_prompt=Path("dummy.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out_dir,
            )

        # Resumed cost (0.05) + 2 new checkpoints (0.0 each
        # in placeholder mode)
        assert state.cumulative_cost == pytest.approx(0.05)
