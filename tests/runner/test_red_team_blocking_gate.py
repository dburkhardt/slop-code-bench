"""Tests for Red Team review -> batch blocking gate.

Verifies that the Red Team's pre-dispatch workflow
correctly blocks a batch bead via a review bead until
the review is closed.

Exercises the full gate lifecycle:
  1. Create a batch bead.
  2. Create a review bead linked via
     ``bd link <batch> <review> --type blocks``.
  3. Verify batch is NOT in ``bd ready`` output.
  4. Close the review bead.
  5. Verify batch IS now in ``bd ready`` output.

Fulfills: VAL-GASTOWN-009, VAL-GASTOWN-013,
          VAL-ROLES-005.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

# ── Helpers ──────────────────────────────────────────

BEADS_DIR = str(
    Path("~").expanduser() / "gt" / "scbench" / ".beads"
)


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
    env["BEADS_DIR"] = BEADS_DIR
    return env


def _bd(*args: str) -> subprocess.CompletedProcess:
    """Run a bd (beads) command."""
    return subprocess.run(  # noqa: S603
        ["bd", *args],  # noqa: S607
        capture_output=True,
        text=True,
        env=_gas_town_env(),
        timeout=30,
    )


def _bd_available() -> bool:
    """Check whether the bd CLI is available."""
    try:
        result = _bd("--version")
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


skip_no_bd = pytest.mark.skipif(
    not _bd_available(),
    reason="bd (beads) CLI not available",
)


# ── Tests ────────────────────────────────────────────


@skip_no_bd
class TestRedTeamBlockingGate:
    """Verify the Red Team review -> batch blocking
    gate lifecycle."""

    def test_review_blocks_batch_until_closed(self):
        """Create batch, create review linked via
        blocks, verify batch not ready, close review,
        verify batch ready.

        Uses the correct ``bd link`` argument order:
        ``bd link <batch> <review> --type blocks``
        means "review blocks batch".
        """
        # Step 1: Create a batch bead
        batch_result = _bd(
            "create",
            "Gate Test: Proposed Batch",
            "--labels", "batch,gate-test",
            "--description",
            "Batch bead for blocking gate test.",
            "--silent",
        )
        assert batch_result.returncode == 0, (
            f"Failed to create batch: "
            f"{batch_result.stderr}"
        )
        batch_id = batch_result.stdout.strip()
        assert batch_id.startswith("sc-"), (
            f"Expected sc- prefix, got: {batch_id}"
        )

        # Step 2: Create a review bead
        review_result = _bd(
            "create",
            "Gate Test: Red Team Review",
            "--labels",
            "red-team-review,blocking,gate-test",
            "--description",
            "Red Team review bead for gate test.",
            "--silent",
        )
        assert review_result.returncode == 0, (
            f"Failed to create review: "
            f"{review_result.stderr}"
        )
        review_id = review_result.stdout.strip()
        assert review_id.startswith("sc-"), (
            f"Expected sc- prefix, got: {review_id}"
        )

        try:
            # Step 3: Link review so it blocks batch.
            # bd link <id1> <id2> means "id2 blocks id1"
            # so batch=id1, review=id2.
            link_result = _bd(
                "link",
                batch_id,
                review_id,
                "--type", "blocks",
            )
            assert link_result.returncode == 0, (
                f"Failed to link: {link_result.stderr}"
            )

            # Step 4: Verify batch NOT in bd ready
            ready_before = _bd("ready")
            assert ready_before.returncode == 0
            assert batch_id not in ready_before.stdout, (
                f"Batch {batch_id} should NOT appear "
                "in bd ready while review is open. "
                f"Output: {ready_before.stdout}"
            )

            # Step 5: Close the review bead
            close_result = _bd("close", review_id)
            assert close_result.returncode == 0, (
                f"Failed to close review: "
                f"{close_result.stderr}"
            )

            # Step 6: Verify batch IS in bd ready
            ready_after = _bd("ready")
            assert ready_after.returncode == 0
            assert batch_id in ready_after.stdout, (
                f"Batch {batch_id} should appear in "
                "bd ready after review is closed. "
                f"Output: {ready_after.stdout}"
            )
        finally:
            # Cleanup: close and delete both beads
            _bd("close", batch_id)
            _bd("delete", batch_id, "--force")
            _bd("close", review_id)
            _bd("delete", review_id, "--force")

    def test_review_bead_has_objections_structure(self):
        """Review beads support the required numbered
        objection format: problem / impact / fix."""
        # Create a review bead with structured objections
        review_result = _bd(
            "create",
            "Gate Test: Objection Format",
            "--labels", "red-team-review,gate-test",
            "--description",
            "Review bead for objection format test.",
            "--silent",
        )
        assert review_result.returncode == 0
        review_id = review_result.stdout.strip()

        try:
            # Add a note with the required format
            objection_text = (
                "## Red Team Review\n\n"
                "**Objection 1: Insufficient sample "
                "size**\n"
                "- Problem: Only 2 experiments planned "
                "per mode.\n"
                "- Impact: No statistical test viable "
                "at N=2.\n"
                "- Fix: Run at least 3 repetitions per "
                "problem.\n\n"
                "**Objection 2: Untested budget split**"
                "\n"
                "- Problem: Budget-split=80 never "
                "validated.\n"
                "- Impact: Reviewer starvation risk.\n"
                "- Fix: Use validated default (70).\n\n"
                "Objections filed: 2"
            )
            note_result = _bd(
                "note", review_id, objection_text,
            )
            assert note_result.returncode == 0, (
                f"Failed to add note: "
                f"{note_result.stderr}"
            )

            # Verify the note content is retrievable
            show_result = _bd("show", review_id)
            assert show_result.returncode == 0
            output = show_result.stdout
            assert "Objection 1" in output, (
                "Review bead should contain Objection 1"
            )
            assert "Problem:" in output, (
                "Objections must have Problem field"
            )
            assert "Impact:" in output, (
                "Objections must have Impact field"
            )
            assert "Fix:" in output, (
                "Objections must have Fix field"
            )
        finally:
            _bd("close", review_id)
            _bd("delete", review_id, "--force")

    def test_post_mortem_has_no_blocks_dependency(self):
        """Post-mortem beads do NOT create any blocking
        dependencies on downstream beads."""
        # Create a post-mortem bead (advisory only)
        pm_result = _bd(
            "create",
            "Gate Test: Post-Mortem",
            "--labels",
            "red-team-review,post-mortem,advisory,"
            "gate-test",
            "--description",
            "Advisory post-mortem for gate test.",
            "--silent",
        )
        assert pm_result.returncode == 0
        pm_id = pm_result.stdout.strip()

        try:
            # Verify no blocking dependencies exist
            show_result = _bd("show", pm_id, "--json")
            assert show_result.returncode == 0
            bead_data = json.loads(show_result.stdout)
            bead = (
                bead_data[0]
                if isinstance(bead_data, list)
                else bead_data
            )
            deps = bead.get("dependencies", [])
            blocking_deps = [
                d for d in deps
                if d.get("dependency_type") == "blocks"
            ]
            assert len(blocking_deps) == 0, (
                "Post-mortem beads must have NO "
                "blocking dependencies. Found: "
                f"{blocking_deps}"
            )
        finally:
            _bd("close", pm_id)
            _bd("delete", pm_id, "--force")
