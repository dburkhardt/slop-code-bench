"""Tests for canary preflight gating.

VAL-PIPELINE-009: Canary preflight gates experiment dispatch.
If canary fails, subsequent formula steps do not execute.
Escalation triggered.
"""

from __future__ import annotations

import os
import subprocess
import textwrap
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_SCRIPT = (
    REPO_ROOT / "research" / "scripts" / "canary_preflight.sh"
)
RUNNER_PATH = (
    REPO_ROOT / "research" / "runner" / "two_agent_runner.py"
)
FORMULA_PATH = (
    REPO_ROOT
    / "research"
    / "formulas"
    / "mol-scbench-experiment.formula.toml"
)


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------

def _load_formula() -> dict:
    """Load and parse the experiment formula TOML."""
    with FORMULA_PATH.open("rb") as f:
        return tomllib.load(f)


def _run_bash(
    script: Path,
    *,
    env: dict[str, str] | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Run a bash script and return the result."""
    merged = {**os.environ, **(env or {})}
    cmd = ["/bin/bash", str(script)]
    return subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        env=merged,
        timeout=timeout,
        cwd=str(REPO_ROOT),
    )


def _make_fake_env(
    tmp_path: Path,
    runner_code: str,
    *,
    record_escalations: bool = False,
    extra_env: dict[str, str] | None = None,
) -> tuple[Path, dict[str, str]]:
    """Create a modified preflight script with a fake
    runner and (optionally) a stub gt, returning the
    script path and the env dict to use.
    """
    fake_runner = tmp_path / "fake_runner.py"
    fake_runner.write_text(runner_code)

    modified = PREFLIGHT_SCRIPT.read_text().replace(
        'RUNNER="$REPO_ROOT/research/runner/'
        'two_agent_runner.py"',
        f'RUNNER="{fake_runner}"',
    )
    mod_script = tmp_path / "preflight.sh"
    mod_script.write_text(modified)
    mod_script.chmod(0o755)

    stub_gt = tmp_path / "gt"
    if record_escalations:
        escalation_log = tmp_path / "escalation.log"
        stub_gt.write_text(textwrap.dedent(f"""\
            #!/bin/bash
            echo "$@" >> "{escalation_log}"
            exit 0
        """))
    else:
        stub_gt.write_text("#!/bin/bash\nexit 0\n")
    stub_gt.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        **(extra_env or {}),
    }
    return mod_script, env


# ----------------------------------------------------------------
# Script existence and structure
# ----------------------------------------------------------------


class TestPreflightScriptExists:
    """Basic sanity checks for the script."""

    def test_script_exists(self):
        assert PREFLIGHT_SCRIPT.exists(), (
            "canary_preflight.sh must exist at "
            "research/scripts/canary_preflight.sh"
        )

    def test_script_is_executable(self):
        assert os.access(PREFLIGHT_SCRIPT, os.X_OK), (
            "canary_preflight.sh must be executable"
        )

    def test_script_has_shebang(self):
        first_line = PREFLIGHT_SCRIPT.read_text().split(
            "\n"
        )[0]
        assert first_line.startswith("#!/"), (
            "canary_preflight.sh must have a shebang line"
        )

    def test_script_invokes_canary_flag(self):
        content = PREFLIGHT_SCRIPT.read_text()
        assert "--canary" in content, (
            "Script must invoke the runner with --canary"
        )

    def test_script_uses_gt_escalate(self):
        content = PREFLIGHT_SCRIPT.read_text()
        assert "gt escalate" in content, (
            "Script must use gt escalate on failure"
        )

    def test_script_escalates_at_high_severity(self):
        content = PREFLIGHT_SCRIPT.read_text()
        assert "--severity high" in content, (
            "Script must escalate at severity high"
        )


# ----------------------------------------------------------------
# Canary failure behavior
# ----------------------------------------------------------------


class TestPreflightFailure:
    """Canary failure prevents subsequent steps."""

    def test_nonzero_exit_on_canary_failure(
        self, tmp_path
    ):
        """When canary exits non-zero, preflight also
        exits non-zero."""
        script, env = _make_fake_env(
            tmp_path,
            textwrap.dedent("""\
                import sys
                print("CanaryError: Docker unavailable")
                sys.exit(1)
            """),
            extra_env={"HYPOTHESIS_ID": "sc-test-hyp"},
        )
        result = _run_bash(script, env=env)
        assert result.returncode != 0, (
            "Preflight must exit non-zero when canary "
            "fails"
        )
        assert "FAILED" in result.stdout

    def test_escalation_fired_on_failure(self, tmp_path):
        """Escalation at severity high fires when canary
        fails."""
        script, env = _make_fake_env(
            tmp_path,
            textwrap.dedent("""\
                import sys
                print("CanaryError: API key invalid")
                sys.exit(1)
            """),
            record_escalations=True,
            extra_env={"HYPOTHESIS_ID": "sc-hyp-123"},
        )
        _run_bash(script, env=env)

        escalation_log = tmp_path / "escalation.log"
        assert escalation_log.exists(), (
            "gt escalate must be called on failure"
        )
        log_content = escalation_log.read_text()
        assert "high" in log_content, (
            "Escalation must be at severity high"
        )
        assert "sc-hyp-123" in log_content, (
            "Escalation must reference hypothesis ID"
        )

    def test_canary_failure_blocks_implement_step(self):
        """A failed canary prevents implement-hypothesis
        from executing because the formula's dependency
        chain requires preflight to complete first.
        """
        formula = _load_formula()
        step_map = {s["id"]: s for s in formula["steps"]}

        # Preflight has no dependencies
        preflight = step_map["preflight"]
        assert "needs" not in preflight or (
            preflight["needs"] == []
        ), "Preflight step must have no dependencies"

        # implement-hypothesis depends on preflight
        impl = step_map["implement-hypothesis"]
        assert "preflight" in impl.get("needs", []), (
            "implement-hypothesis must depend on "
            "preflight"
        )

    def test_canary_cost_overrun_exits_nonzero(
        self, tmp_path
    ):
        """Budget overrun in canary causes non-zero
        exit."""
        script, env = _make_fake_env(
            tmp_path,
            textwrap.dedent("""\
                import sys
                print("WARNING: canary budget exceeded.")
                sys.exit(1)
            """),
        )
        result = _run_bash(script, env=env)
        assert result.returncode != 0

    def test_invalid_output_exits_nonzero(self, tmp_path):
        """Invalid runner output causes non-zero exit."""
        script, env = _make_fake_env(
            tmp_path,
            textwrap.dedent("""\
                import sys
                print("CanaryError: Evaluation failed")
                sys.exit(1)
            """),
        )
        result = _run_bash(script, env=env)
        assert result.returncode != 0


# ----------------------------------------------------------------
# Canary success behavior
# ----------------------------------------------------------------


class TestPreflightSuccess:
    """Canary success allows formula to proceed."""

    def test_zero_exit_on_canary_success(self, tmp_path):
        """When canary exits zero, preflight also exits
        zero."""
        script, env = _make_fake_env(
            tmp_path,
            textwrap.dedent("""\
                print("Canary: preflight OK")
                print("Canary: two-agent loop complete.")
                print("Canary PASSED.")
            """),
        )
        result = _run_bash(script, env=env)
        assert result.returncode == 0, (
            f"Preflight must exit 0 on success. "
            f"stderr: {result.stderr}"
        )
        assert "PASSED" in result.stdout

    def test_no_escalation_on_success(self, tmp_path):
        """No escalation fires when canary succeeds."""
        script, env = _make_fake_env(
            tmp_path,
            'print("Canary PASSED.")\n',
            record_escalations=True,
        )
        result = _run_bash(script, env=env)
        assert result.returncode == 0
        escalation_log = tmp_path / "escalation.log"
        assert not escalation_log.exists(), (
            "gt escalate must NOT be called on success"
        )

    def test_success_allows_next_step(self):
        """Successful canary means implement-hypothesis
        becomes the next ready step.
        """
        formula = _load_formula()
        step_map = {s["id"]: s for s in formula["steps"]}

        impl = step_map["implement-hypothesis"]
        assert impl["needs"] == ["preflight"], (
            "implement-hypothesis must depend only on "
            "preflight so it becomes next ready step"
        )

        # Full chain is linear from preflight
        chain = [
            "preflight",
            "implement-hypothesis",
            "peer-review",
            "run-experiments",
            "validate-results",
            "report",
        ]
        for i in range(1, len(chain)):
            step = step_map[chain[i]]
            assert chain[i - 1] in step.get(
                "needs", []
            ), (
                f"{chain[i]} must depend on "
                f"{chain[i - 1]}"
            )


# ----------------------------------------------------------------
# Environment variable handling
# ----------------------------------------------------------------


class TestPreflightEnvVars:
    """Environment variables control preflight behavior."""

    def test_hypothesis_id_passed_to_escalation(
        self, tmp_path
    ):
        """HYPOTHESIS_ID env var is used in --related flag
        of escalation."""
        script, env = _make_fake_env(
            tmp_path,
            "import sys; sys.exit(1)\n",
            record_escalations=True,
            extra_env={"HYPOTHESIS_ID": "sc-my-hypothesis"},
        )
        _run_bash(script, env=env)

        escalation_log = tmp_path / "escalation.log"
        log_content = escalation_log.read_text()
        assert "--related sc-my-hypothesis" in log_content

    def test_canary_budget_override(self, tmp_path):
        """CANARY_BUDGET env var overrides the default."""
        script, env = _make_fake_env(
            tmp_path,
            textwrap.dedent("""\
                import sys
                print(f"ARGS: {sys.argv}")
            """),
            extra_env={"CANARY_BUDGET": "0.25"},
        )
        result = _run_bash(script, env=env)
        assert result.returncode == 0
        assert "0.25" in result.stdout

    def test_canary_model_override(self, tmp_path):
        """CANARY_MODEL env var overrides the default."""
        script, env = _make_fake_env(
            tmp_path,
            textwrap.dedent("""\
                import sys
                print(f"ARGS: {sys.argv}")
            """),
            extra_env={"CANARY_MODEL": "nvidia-sonnet-4.6"},
        )
        result = _run_bash(script, env=env)
        assert result.returncode == 0
        assert "nvidia-sonnet-4.6" in result.stdout


# ----------------------------------------------------------------
# Formula dependency chain (structural verification)
# ----------------------------------------------------------------


class TestFormulaDependencyChain:
    """Verify formula structure enforces preflight
    gating."""

    def test_six_steps_present(self):
        formula = _load_formula()
        assert len(formula["steps"]) == 6

    def test_preflight_is_first_step(self):
        formula = _load_formula()
        assert formula["steps"][0]["id"] == "preflight"

    def test_all_steps_reachable_only_through_preflight(
        self,
    ):
        """Every step traces back to preflight in its
        dependency chain, so a failed preflight blocks
        everything."""
        formula = _load_formula()
        step_map = {s["id"]: s for s in formula["steps"]}

        for step in formula["steps"]:
            if step["id"] == "preflight":
                continue

            visited: set[str] = set()
            queue = [step["id"]]
            found_preflight = False

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                if current == "preflight":
                    found_preflight = True
                    break
                deps = step_map[current].get("needs", [])
                queue.extend(deps)

            assert found_preflight, (
                f"Step '{step['id']}' must be reachable "
                f"only through preflight"
            )

    def test_preflight_step_mentions_canary(self):
        formula = _load_formula()
        preflight = formula["steps"][0]
        assert "canary" in preflight[
            "description"
        ].lower()

    def test_preflight_step_mentions_escalate(self):
        formula = _load_formula()
        preflight = formula["steps"][0]
        desc = preflight["description"].lower()
        assert "escalate" in desc
        assert "high" in desc
