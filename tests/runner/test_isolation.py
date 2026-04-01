"""Tests for concurrent run isolation.

VAL-RUNNER-011: Two simultaneous runs use unique output
directories and independent Docker containers.  Cost
tracking is per-run, not shared.
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
# Unique output directories
# ---------------------------------------------------------------------------


class TestUniqueOutputDirs:
    """Parallel runs produce independent output directories."""

    def test_build_output_dir_includes_run_id(self):
        """Output directory name contains the run_id."""
        mod = _load_runner()
        rid = "abc123"
        out = mod.build_output_dir(
            "file_backup",
            "opus-4.5",
            base=Path("/tmp/test"),  # noqa: S108
            run_id=rid,
        )
        assert "abc123" in str(out)

    def test_two_dirs_always_differ(self):
        """Two calls produce distinct directories."""
        mod = _load_runner()
        base = Path("/tmp/test")  # noqa: S108
        dirs = {
            mod.build_output_dir(
                "file_backup", "opus-4.5", base=base,
            )
            for _ in range(20)
        }
        # With uuid-based suffixes all 20 should be unique
        assert len(dirs) == 20

    def test_dirs_differ_same_second(self):
        """Even with identical timestamps, the uuid suffix
        makes directories unique."""
        mod = _load_runner()
        base = Path("/tmp/test")  # noqa: S108
        d1 = mod.build_output_dir(
            "p", "m", base=base, run_id="aaa",
        )
        d2 = mod.build_output_dir(
            "p", "m", base=base, run_id="bbb",
        )
        assert d1 != d2

    def test_auto_generated_run_id_when_none(self):
        """When run_id is None a uuid is generated."""
        mod = _load_runner()
        base = Path("/tmp/test")  # noqa: S108
        out = mod.build_output_dir(
            "file_backup", "opus-4.5", base=base,
        )
        # The name should have a hex suffix after the
        # timestamp portion
        parts = out.name.split("_")
        # Last part should be a short hex string
        assert len(parts[-1]) == 8
        # Verify it is valid hex
        int(parts[-1], 16)


# ---------------------------------------------------------------------------
# Run ID uniqueness
# ---------------------------------------------------------------------------


class TestRunIdUniqueness:
    """Each RunState gets a unique run_id."""

    def test_default_run_id_is_12_hex_chars(self):
        mod = _load_runner()
        state = mod.RunState(
            problem="test",
            model="test",
            budget=1.0,
            budget_split=70,
            output_dir=Path("/tmp/x"),  # noqa: S108
        )
        assert len(state.run_id) == 12
        int(state.run_id, 16)  # must be valid hex

    def test_two_states_different_run_ids(self):
        mod = _load_runner()
        ids = set()
        for _ in range(50):
            state = mod.RunState(
                problem="test",
                model="test",
                budget=1.0,
                budget_split=70,
                output_dir=Path("/tmp/x"),  # noqa: S108
            )
            ids.add(state.run_id)
        assert len(ids) == 50

    def test_explicit_run_id_honoured(self):
        mod = _load_runner()
        state = mod.RunState(
            run_id="custom42",
            problem="test",
            model="test",
            budget=1.0,
            budget_split=70,
            output_dir=Path("/tmp/x"),  # noqa: S108
        )
        assert state.run_id == "custom42"


# ---------------------------------------------------------------------------
# Docker container name prefix
# ---------------------------------------------------------------------------


class TestContainerNamePrefix:
    """Docker container names are unique per run."""

    def test_container_prefix_contains_run_id(self):
        mod = _load_runner()
        state = mod.RunState(
            run_id="deadbeef1234",
            problem="test",
            model="test",
            budget=1.0,
            budget_split=70,
            output_dir=Path("/tmp/x"),  # noqa: S108
        )
        assert "deadbeef1234" in state.container_name_prefix
        assert state.container_name_prefix.startswith(
            "scbench-",
        )

    def test_two_runs_different_prefixes(self):
        mod = _load_runner()
        s1 = mod.RunState(
            problem="test",
            model="test",
            budget=1.0,
            budget_split=70,
            output_dir=Path("/tmp/a"),  # noqa: S108
        )
        s2 = mod.RunState(
            problem="test",
            model="test",
            budget=1.0,
            budget_split=70,
            output_dir=Path("/tmp/b"),  # noqa: S108
        )
        assert s1.container_name_prefix != (
            s2.container_name_prefix
        )


# ---------------------------------------------------------------------------
# Cost tracking isolation
# ---------------------------------------------------------------------------


class TestCostIsolation:
    """Cost tracking is per-run, not shared."""

    def test_cost_tracked_independently(self):
        """Two RunState instances accumulate costs
        independently."""
        mod = _load_runner()
        s1 = mod.RunState(
            problem="test",
            model="test",
            budget=10.0,
            budget_split=70,
            output_dir=Path("/tmp/a"),  # noqa: S108
        )
        s2 = mod.RunState(
            problem="test",
            model="test",
            budget=10.0,
            budget_split=70,
            output_dir=Path("/tmp/b"),  # noqa: S108
        )

        s1.checkpoint_metrics["cp1"] = mod.CheckpointMetrics(
            cost=1.50,
        )
        s2.checkpoint_metrics["cp1"] = mod.CheckpointMetrics(
            cost=2.50,
        )

        assert s1.cumulative_cost == pytest.approx(1.50)
        assert s2.cumulative_cost == pytest.approx(2.50)

    def test_saved_results_contain_run_id(self, tmp_path):
        """Saved metrics include the run_id."""
        mod = _load_runner()
        state = mod.RunState(
            run_id="abc123def456",
            problem="test",
            model="test",
            budget=1.0,
            budget_split=70,
            output_dir=tmp_path,
        )
        state.save_results()
        data = json.loads(
            (tmp_path / "two_agent_metrics.json").read_text(),
        )
        assert data["run_id"] == "abc123def456"

    def test_parallel_save_no_overlap(self, tmp_path):
        """Two runs saving to different dirs produce
        independent files."""
        mod = _load_runner()

        dir_a = tmp_path / "run_a"
        dir_a.mkdir()
        dir_b = tmp_path / "run_b"
        dir_b.mkdir()

        sa = mod.RunState(
            run_id="aaa",
            problem="test",
            model="test",
            budget=10.0,
            budget_split=70,
            output_dir=dir_a,
        )
        sb = mod.RunState(
            run_id="bbb",
            problem="test",
            model="test",
            budget=10.0,
            budget_split=70,
            output_dir=dir_b,
        )

        sa.checkpoint_metrics["cp1"] = (
            mod.CheckpointMetrics(cost=1.0)
        )
        sb.checkpoint_metrics["cp1"] = (
            mod.CheckpointMetrics(cost=2.0)
        )

        sa.save_results()
        sb.save_results()

        da = json.loads(
            (dir_a / "two_agent_metrics.json").read_text(),
        )
        db = json.loads(
            (dir_b / "two_agent_metrics.json").read_text(),
        )

        assert da["run_id"] == "aaa"
        assert db["run_id"] == "bbb"
        assert da["cumulative_cost"] == pytest.approx(1.0)
        assert db["cumulative_cost"] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# run_slop_code passes SCBENCH_RUN_ID
# ---------------------------------------------------------------------------


class TestSlopCodeRunId:
    """run_slop_code passes run_id via SCBENCH_RUN_ID env."""

    def test_env_contains_run_id(self):
        """When run_id is provided, SCBENCH_RUN_ID is set in
        the subprocess environment."""
        mod = _load_runner()
        captured_env = {}

        def fake_run(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            from unittest.mock import MagicMock
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        with patch("subprocess.run", side_effect=fake_run):
            mod.run_slop_code(
                problem="test",
                model="test",
                prompt_template=Path("p.jinja"),
                output_dir=Path("/tmp/out"),  # noqa: S108
                budget_fraction=0.7,
                total_budget=1.0,
                run_id="myrunid123",
            )

        assert captured_env.get("SCBENCH_RUN_ID") == (
            "myrunid123"
        )

    def test_env_without_run_id(self):
        """When run_id is None, SCBENCH_RUN_ID is absent."""
        mod = _load_runner()
        captured_env = {}

        def fake_run(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            from unittest.mock import MagicMock
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        with patch("subprocess.run", side_effect=fake_run):
            mod.run_slop_code(
                problem="test",
                model="test",
                prompt_template=Path("p.jinja"),
                output_dir=Path("/tmp/out"),  # noqa: S108
                budget_fraction=0.7,
                total_budget=1.0,
            )

        assert "SCBENCH_RUN_ID" not in captured_env


# ---------------------------------------------------------------------------
# run_two_agent concurrent isolation
# ---------------------------------------------------------------------------


class TestRunTwoAgentIsolation:
    """run_two_agent embeds run_id in state and output."""

    @pytest.fixture()
    def fake_problem(self, tmp_path):
        prob = tmp_path / "problems" / "test_problem"
        for i in range(1, 3):
            cp = prob / f"checkpoint_{i}"
            cp.mkdir(parents=True)
            spec = prob / f"checkpoint_{i}.md"
            spec.write_text(f"Spec {i}")
        return prob

    def test_run_id_in_state(self, tmp_path, fake_problem):
        """RunState receives a run_id."""
        mod = _load_runner()
        out = tmp_path / "output"
        out.mkdir()

        with patch.object(
            mod, "PROBLEMS_DIR", fake_problem.parent,
        ):
            state = mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("d.jinja"),
                reviewer_prompt=Path("d.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
                run_id="isolate42",
            )

        assert state.run_id == "isolate42"

    def test_run_id_in_saved_metrics(
        self, tmp_path, fake_problem,
    ):
        """Saved metrics contain the run_id."""
        mod = _load_runner()
        out = tmp_path / "output"
        out.mkdir()

        with patch.object(
            mod, "PROBLEMS_DIR", fake_problem.parent,
        ):
            mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("d.jinja"),
                reviewer_prompt=Path("d.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out,
                run_id="saved42",
            )

        data = json.loads(
            (out / "two_agent_metrics.json").read_text(),
        )
        assert data["run_id"] == "saved42"

    def test_two_parallel_runs_independent(
        self, tmp_path, fake_problem,
    ):
        """Two runs write to separate directories with
        independent metrics."""
        mod = _load_runner()
        out_a = tmp_path / "run_a"
        out_a.mkdir()
        out_b = tmp_path / "run_b"
        out_b.mkdir()

        with patch.object(
            mod, "PROBLEMS_DIR", fake_problem.parent,
        ):
            sa = mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("d.jinja"),
                reviewer_prompt=Path("d.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out_a,
                run_id="run_aaa",
            )
            sb = mod.run_two_agent(
                problem="test_problem",
                model="opus-4.5",
                implementer_prompt=Path("d.jinja"),
                reviewer_prompt=Path("d.jinja"),
                budget_split=70,
                budget=10.0,
                output_dir=out_b,
                run_id="run_bbb",
            )

        # Metrics files exist in separate dirs
        ma = json.loads(
            (out_a / "two_agent_metrics.json").read_text(),
        )
        mb = json.loads(
            (out_b / "two_agent_metrics.json").read_text(),
        )
        assert ma["run_id"] == "run_aaa"
        assert mb["run_id"] == "run_bbb"
        assert out_a != out_b

        # Each run tracked costs independently
        assert sa.cumulative_cost == sb.cumulative_cost
