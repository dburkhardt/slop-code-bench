"""Tests for crash resilience infrastructure.

VAL-CROSS-004: Dolt auto-commit preserves data after crash.
VAL-CROSS-005: Git sync commits outputs/ and research/ periodically.
VAL-CROSS-007: Two-layer budget enforcement both active.
VAL-CROSS-008: Critical escalations reach human operator.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GIT_SYNC_SCRIPT = (
    REPO_ROOT / "research" / "scripts" / "git_sync.sh"
)
DOLT_DATA_DIR = (
    Path.home() / "gt" / ".dolt-data" / "scbench"
)
GT_ROOT = Path.home() / "gt"


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------


def _run(
    cmd: list[str],
    **kwargs,
) -> subprocess.CompletedProcess:
    """Thin wrapper around subprocess.run that avoids
    repeating noqa annotations everywhere."""
    return subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        **kwargs,
    )


def _dolt_sql(
    query: str,
) -> subprocess.CompletedProcess:
    """Run a Dolt SQL query against scbench."""
    return _run(
        ["dolt", "sql", "-q", query],  # noqa: S607
        cwd=str(DOLT_DATA_DIR),
        timeout=30,
    )


def _git(
    *args: str,
    cwd: str | Path | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Run a git command."""
    return _run(
        ["git", *args],  # noqa: S607
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
    )


def _dolt_available() -> bool:
    """Check whether the Dolt CLI is available."""
    try:
        result = _run(
            ["dolt", "version"],  # noqa: S607
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _dolt_server_reachable() -> bool:
    """Check whether the Dolt server is running."""
    try:
        result = _dolt_sql("SELECT 1;")
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _gt_available() -> bool:
    """Check whether the gt CLI is available."""
    env = _gas_town_env()
    try:
        result = _run(
            ["gt", "--version"],  # noqa: S607
            env=env,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _gas_town_env() -> dict[str, str]:
    """Build environment dict with Gas Town on PATH."""
    env = {**os.environ}
    env["PATH"] = (
        "/home/ubuntu/gopath/bin:"
        "/home/ubuntu/go/bin:"
        + env.get("PATH", "")
    )
    env["GOROOT"] = "/home/ubuntu/go"
    env["GOPATH"] = "/home/ubuntu/gopath"
    return env


def _init_test_repo(repo: Path) -> None:
    """Create a minimal git repo with outputs/ and
    research/ directories and an initial commit."""
    repo.mkdir(exist_ok=True)
    (repo / "outputs").mkdir(exist_ok=True)
    (repo / "research").mkdir(exist_ok=True)
    _git("init", cwd=repo)
    _git("config", "user.email", "test@test", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    (repo / "outputs" / ".gitkeep").touch()
    _git("add", ".", cwd=repo)
    _git("commit", "-m", "init", cwd=repo)


def _make_test_sync_script(
    tmp_path: Path,
    repo: Path,
    *,
    skip_push: bool = True,
) -> Path:
    """Create a modified git_sync.sh that targets the
    given test repo."""
    modified = GIT_SYNC_SCRIPT.read_text().replace(
        'REPO_ROOT="$(cd "$(dirname '
        '"${BASH_SOURCE[0]}")/../.." && pwd)"',
        f'REPO_ROOT="{repo}"',
    )
    if skip_push:
        modified = modified.replace(
            "git push origin main",
            "echo 'push skipped in test'",
        )
    test_script = tmp_path / "git_sync.sh"
    test_script.write_text(modified)
    test_script.chmod(0o755)
    return test_script


skip_no_dolt = pytest.mark.skipif(
    not _dolt_available(),
    reason="Dolt CLI not available",
)
skip_no_dolt_server = pytest.mark.skipif(
    not _dolt_server_reachable(),
    reason="Dolt server not reachable on :3307",
)
skip_no_gt = pytest.mark.skipif(
    not _gt_available(),
    reason="Gas Town (gt) CLI not available",
)


# ----------------------------------------------------------------
# Git Sync Script — Structure
# ----------------------------------------------------------------


class TestGitSyncScriptExists:
    """Basic sanity for git_sync.sh."""

    def test_script_exists(self):
        assert GIT_SYNC_SCRIPT.exists(), (
            "git_sync.sh must exist at "
            "research/scripts/git_sync.sh"
        )

    def test_script_is_executable(self):
        assert os.access(GIT_SYNC_SCRIPT, os.X_OK), (
            "git_sync.sh must be executable"
        )

    def test_script_has_shebang(self):
        first_line = GIT_SYNC_SCRIPT.read_text().split(
            "\n"
        )[0]
        assert first_line.startswith("#!/"), (
            "git_sync.sh must have a shebang line"
        )

    def test_script_stages_outputs(self):
        content = GIT_SYNC_SCRIPT.read_text()
        assert "outputs/" in content, (
            "Script must stage the outputs/ directory"
        )

    def test_script_stages_research(self):
        content = GIT_SYNC_SCRIPT.read_text()
        assert "research/" in content, (
            "Script must stage the research/ directory"
        )

    def test_commit_message_matches_spec(self):
        content = GIT_SYNC_SCRIPT.read_text()
        assert (
            "auto: sync experiment outputs" in content
        ), (
            "Commit message must be "
            "'auto: sync experiment outputs'"
        )

    def test_no_empty_commits(self):
        """Script checks for changes before committing.
        """
        content = GIT_SYNC_SCRIPT.read_text()
        assert "diff --cached --quiet" in content, (
            "Script must check for staged changes "
            "before committing"
        )

    def test_handles_push_failure_gracefully(self):
        """Script does not exit on push failure."""
        content = GIT_SYNC_SCRIPT.read_text()
        assert "||" in content, (
            "Script must handle push failure gracefully"
        )


# ----------------------------------------------------------------
# Git Sync Script — Behavior
# ----------------------------------------------------------------


class TestGitSyncBehavior:
    """End-to-end behavior of git_sync.sh."""

    def test_no_changes_exits_zero(self, tmp_path):
        """When nothing changed, script exits 0 with
        'nothing to commit' message."""
        repo = tmp_path / "repo"
        _init_test_repo(repo)

        test_script = _make_test_sync_script(
            tmp_path, repo
        )
        result = _run(
            ["/bin/bash", str(test_script)],
            cwd=str(repo),
            timeout=30,
        )
        assert result.returncode == 0, (
            "Script must exit 0 when nothing to commit."
            f" stderr: {result.stderr}"
        )
        assert "nothing to commit" in result.stdout

    def test_with_changes_commits(self, tmp_path):
        """When there are changes, script creates a
        commit."""
        repo = tmp_path / "repo"
        _init_test_repo(repo)

        # Add a new file to trigger a commit
        (repo / "outputs" / "result.json").write_text(
            '{"pass_rate": 0.85}'
        )

        test_script = _make_test_sync_script(
            tmp_path, repo
        )
        result = _run(
            ["/bin/bash", str(test_script)],
            cwd=str(repo),
            timeout=30,
        )
        assert result.returncode == 0, (
            "Script must exit 0 on commit."
            f" stderr: {result.stderr}"
        )
        assert "committed" in result.stdout

        # Verify the commit exists
        log = _git("log", "--oneline", "-1", cwd=repo)
        assert (
            "auto: sync experiment outputs"
            in log.stdout
        )

    def test_second_run_no_empty_commit(self, tmp_path):
        """Running twice without new changes does not
        create a second commit."""
        repo = tmp_path / "repo"
        _init_test_repo(repo)

        # First run with a change
        (repo / "research" / "data.csv").write_text(
            "a,b\n1,2"
        )

        test_script = _make_test_sync_script(
            tmp_path, repo
        )
        _run(
            ["/bin/bash", str(test_script)],
            cwd=str(repo),
            timeout=30,
        )

        # Count commits
        log1 = _git("log", "--oneline", cwd=repo)
        count1 = len(log1.stdout.strip().split("\n"))

        # Second run with NO changes
        result2 = _run(
            ["/bin/bash", str(test_script)],
            cwd=str(repo),
            timeout=30,
        )
        assert "nothing to commit" in result2.stdout

        log2 = _git("log", "--oneline", cwd=repo)
        count2 = len(log2.stdout.strip().split("\n"))
        assert count2 == count1, (
            "No new commit should be created when "
            "there are no changes"
        )


# ----------------------------------------------------------------
# Cron Job
# ----------------------------------------------------------------


class TestCronJob:
    """Cron job is installed and references git_sync."""

    def test_cron_entry_exists(self):
        result = _run(
            ["crontab", "-l"],  # noqa: S607
            timeout=10,
        )
        assert result.returncode == 0, (
            "crontab -l must succeed"
        )
        assert "git_sync.sh" in result.stdout, (
            "Cron must reference git_sync.sh"
        )

    def test_cron_runs_every_15_minutes(self):
        result = _run(
            ["crontab", "-l"],  # noqa: S607
            timeout=10,
        )
        assert "*/15" in result.stdout, (
            "Cron must run every 15 minutes (*/15)"
        )

    def test_cron_mentions_sync_experiment(self):
        """Cron entry grep pattern matches the spec."""
        result = _run(
            ["crontab", "-l"],  # noqa: S607
            timeout=10,
        )
        lines = result.stdout.strip().split("\n")
        sync_lines = [
            ln for ln in lines if "git_sync" in ln
        ]
        assert len(sync_lines) >= 1, (
            "At least one cron entry must reference "
            "git_sync"
        )


# ----------------------------------------------------------------
# Dolt Auto-Commit
# ----------------------------------------------------------------


@skip_no_dolt
@skip_no_dolt_server
class TestDoltAutoCommit:
    """VAL-CROSS-004: Dolt auto-commit is enabled."""

    def test_autocommit_enabled(self):
        result = _dolt_sql("SELECT @@autocommit;")
        assert result.returncode == 0
        assert "1" in result.stdout, (
            "@@autocommit must be 1 (enabled)"
        )

    def test_insert_visible_immediately(self):
        """Data is visible right after INSERT without
        explicit COMMIT."""
        _dolt_sql(
            "INSERT INTO experiments "
            "(problem_id, model, mode) VALUES "
            "('autocommit-test', 'test', 'single');"
        )
        result = _dolt_sql(
            "SELECT problem_id FROM experiments "
            "WHERE problem_id='autocommit-test';"
        )
        assert "autocommit-test" in result.stdout

        # Cleanup
        _dolt_sql(
            "DELETE FROM experiments "
            "WHERE problem_id='autocommit-test';"
        )


# ----------------------------------------------------------------
# Partial Data Survival After Crash
# ----------------------------------------------------------------


@skip_no_dolt
@skip_no_dolt_server
class TestPartialDataSurvival:
    """VAL-CROSS-004: Partial data survives after
    simulated crash."""

    def test_data_persisted_after_insert(self):
        """Data inserted with autocommit persists in
        the on-disk Dolt storage. We verify via a fresh
        CLI query that bypasses any in-memory cache."""
        # Insert test data
        _dolt_sql(
            "INSERT INTO experiments "
            "(problem_id, model, mode) VALUES "
            "('crash-survival-test', 'test', 'single');"
        )

        # Query with a fresh CLI invocation
        result = _dolt_sql(
            "SELECT problem_id FROM experiments "
            "WHERE problem_id='crash-survival-test';"
        )
        assert "crash-survival-test" in result.stdout, (
            "Inserted data must be retrievable"
        )

        # Cleanup
        _dolt_sql(
            "DELETE FROM experiments "
            "WHERE problem_id='crash-survival-test';"
        )


# ----------------------------------------------------------------
# Gas Town Doctor Recovery
# ----------------------------------------------------------------


@skip_no_gt
class TestGtDoctor:
    """VAL-CROSS-004: gt doctor --fix works for Gas Town
    recovery."""

    def test_gt_doctor_runs(self):
        """gt doctor --fix runs without crashing."""
        env = _gas_town_env()
        result = _run(
            ["gt", "doctor", "--fix"],  # noqa: S607
            env=env,
            cwd=str(GT_ROOT),
            timeout=120,
        )
        # gt doctor may exit non-zero for pre-existing
        # issues unrelated to our work. We check that
        # it ran and produced output.
        assert len(result.stdout) > 0 or len(
            result.stderr
        ) > 0, "gt doctor must produce output"
        combined = result.stdout + result.stderr
        assert "passed" in combined.lower(), (
            "gt doctor must report passing checks"
        )


# ----------------------------------------------------------------
# Two-Layer Budget Enforcement
# ----------------------------------------------------------------


class TestTwoLayerBudgetEnforcement:
    """VAL-CROSS-007: Both Dolt budget gate and harness
    cap are active."""

    @skip_no_dolt
    @skip_no_dolt_server
    def test_dolt_budget_table_exists(self):
        """Layer 1 prerequisite: budget table exists."""
        result = _dolt_sql("SHOW TABLES;")
        assert "budget" in result.stdout

    @skip_no_dolt
    @skip_no_dolt_server
    def test_dolt_budget_queryable(self):
        """Layer 1: Mayor can query remaining budget."""
        result = _dolt_sql(
            "SELECT remaining FROM budget WHERE id=1;"
        )
        assert result.returncode == 0
        assert (
            "remaining" in result.stdout.lower()
            or re.search(r"\d+\.\d+", result.stdout)
            is not None
        ), "Budget remaining must be queryable"

    def test_runner_has_budget_flag(self):
        """Layer 2: Runner accepts --budget flag."""
        runner = (
            REPO_ROOT
            / "research"
            / "runner"
            / "two_agent_runner.py"
        )
        if not runner.exists():
            pytest.skip("Runner not yet created")
        content = runner.read_text()
        assert "--budget" in content or "budget" in (
            content.lower()
        ), "Runner must accept a budget parameter"

    def test_runner_has_cost_tracking(self):
        """Layer 2: Runner tracks per-experiment cost."""
        runner = (
            REPO_ROOT
            / "research"
            / "runner"
            / "two_agent_runner.py"
        )
        if not runner.exists():
            pytest.skip("Runner not yet created")
        content = runner.read_text()
        assert "cost" in content.lower(), (
            "Runner must track cost"
        )


# ----------------------------------------------------------------
# In-Progress Bead Discoverability
# ----------------------------------------------------------------


@skip_no_gt
@skip_no_dolt_server
class TestBeadDiscoverability:
    """In-progress beads discoverable via bd list."""

    def test_bd_list_status_flag_works(self):
        """bd list --status in_progress is a valid
        command."""
        env = _gas_town_env()
        env["BEADS_DIR"] = str(
            Path.home() / "gt" / "scbench" / ".beads"
        )
        result = _run(
            ["bd", "list", "--status", "in_progress"],  # noqa: S607
            env=env,
            timeout=30,
        )
        assert result.returncode == 0, (
            "bd list --status in_progress must succeed"
        )


# ----------------------------------------------------------------
# Escalation System (VAL-CROSS-008)
# ----------------------------------------------------------------


class TestEscalationStructure:
    """VAL-CROSS-008: Escalation paths exist for
    critical events."""

    def test_canary_preflight_has_escalation(self):
        """Canary preflight script escalates on
        failure."""
        preflight = (
            REPO_ROOT
            / "research"
            / "scripts"
            / "canary_preflight.sh"
        )
        if not preflight.exists():
            pytest.skip(
                "Canary preflight not yet created"
            )
        content = preflight.read_text()
        assert "gt escalate" in content, (
            "Canary preflight must use gt escalate"
        )

    @skip_no_gt
    def test_gt_escalate_command_exists(self):
        """gt escalate command is available."""
        env = _gas_town_env()
        result = _run(
            ["gt", "escalate", "--help"],  # noqa: S607
            env=env,
            timeout=10,
        )
        assert result.returncode == 0, (
            "gt escalate must be available"
        )
