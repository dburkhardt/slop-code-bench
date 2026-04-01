#!/bin/bash
# canary_preflight.sh — Preflight canary gate for the experiment formula.
#
# Runs the two-agent runner in canary mode.  If the canary
# fails (non-zero exit, invalid output, cost overrun) the
# script exits non-zero and fires a high-severity Gas Town
# escalation, which prevents subsequent formula steps from
# executing.
#
# Expected environment variables (optional):
#   HYPOTHESIS_ID  — bead ID of the hypothesis being tested
#                    (used in escalation --related flag)
#   CANARY_MODEL   — override canary model name
#   CANARY_BUDGET  — override canary budget (default $0.50)
#
# Usage:
#   bash research/scripts/canary_preflight.sh
#
# Exit codes:
#   0 — canary passed, safe to proceed
#   1 — canary failed, escalation fired

set -euo pipefail

export PATH="$PATH:/home/ubuntu/gopath/bin:/home/ubuntu/go/bin"
export GOROOT="${GOROOT:-/home/ubuntu/go}"
export GOPATH="${GOPATH:-/home/ubuntu/gopath}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNNER="$REPO_ROOT/research/runner/two_agent_runner.py"

HYPOTHESIS_ID="${HYPOTHESIS_ID:-}"
CANARY_MODEL="${CANARY_MODEL:-}"
CANARY_BUDGET="${CANARY_BUDGET:-0.50}"

# ── Build runner command ──────────────────────────────
CMD=(python3 "$RUNNER" --canary --budget "$CANARY_BUDGET")

if [ -n "$CANARY_MODEL" ]; then
    CMD+=(--model "$CANARY_MODEL")
fi

# ── Run canary ────────────────────────────────────────
echo "[preflight] Running canary (budget=\$$CANARY_BUDGET) ..."

CANARY_OUTPUT=""
CANARY_EXIT=0

CANARY_OUTPUT=$(cd "$REPO_ROOT" && "${CMD[@]}" 2>&1) || CANARY_EXIT=$?

if [ "$CANARY_EXIT" -eq 0 ]; then
    echo "[preflight] Canary PASSED."
    echo "$CANARY_OUTPUT" | tail -5
    exit 0
fi

# ── Canary failed — escalate and exit non-zero ───────
echo "[preflight] Canary FAILED (exit code $CANARY_EXIT)."
echo "[preflight] Output (last 20 lines):"
echo "$CANARY_OUTPUT" | tail -20

REASON="Preflight canary failed (exit $CANARY_EXIT)"
if echo "$CANARY_OUTPUT" | grep -q "CanaryError"; then
    # Extract the component name from CanaryError output
    COMPONENT=$(echo "$CANARY_OUTPUT" \
        | grep -oP '(?<=CanaryError: )\S+' \
        | head -1)
    if [ -n "$COMPONENT" ]; then
        REASON="Preflight canary failed: $COMPONENT (exit $CANARY_EXIT)"
    fi
fi

# Fire escalation via Gas Town
ESCALATE_CMD=(gt escalate "$REASON" --severity high)
if [ -n "$HYPOTHESIS_ID" ]; then
    ESCALATE_CMD+=(--related "$HYPOTHESIS_ID")
fi
ESCALATE_CMD+=(--reason "$CANARY_OUTPUT")

# Try escalation but do not let escalation failure mask
# the canary failure exit code.
if (cd ~/gt && "${ESCALATE_CMD[@]}" 2>&1); then
    echo "[preflight] Escalation fired at severity=high."
else
    echo "[preflight] WARNING: escalation command failed (non-fatal)."
fi

exit 1
