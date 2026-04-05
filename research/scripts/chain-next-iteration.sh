#!/bin/bash
# chain-next-iteration.sh — Deterministic budget gate for research loop continuation
#
# Called as the LAST step of mol-research-iteration formula.
# Checks budget remaining in Dolt. If sufficient, mails the Mayor to
# dispatch the next iteration. If exhausted, mails Mayor for shutdown.
#
# NOTE: Polecats cannot sling (gastown design constraint). This script
# mails the Mayor who CAN sling. The Mayor's CLAUDE.md tells it to
# dispatch immediately on receiving CHAIN_NEXT mail.
#
# This is the ONLY mechanism that keeps experiments flowing.
# It is deterministic — no LLM compliance required for the budget check.

set -euo pipefail

BUDGET_THRESHOLD=${BUDGET_THRESHOLD:-10}  # Stop when below this
RIG="scbench"
DOLT_DIR="$HOME/gt/.dolt-data/scbench"
GT="$(which gt)"
BD="$(which bd)"

# 1. Query budget remaining
REMAINING=$(cd "$DOLT_DIR" && dolt sql -q "SELECT remaining FROM budget WHERE id = 1;" -r csv 2>/dev/null | tail -1)

if [ -z "$REMAINING" ]; then
    echo "ERROR: Could not query budget. Dolt may be down."
    echo "Escalating to Mayor."
    $GT escalate -s HIGH "Budget query failed in chain-next-iteration. Dolt may be down."
    exit 1
fi

# Remove any decimal formatting issues
REMAINING_INT=$(echo "$REMAINING" | awk '{printf "%d", $1}')

echo "Budget remaining: \$$REMAINING (threshold: \$$BUDGET_THRESHOLD)"

# 2. Budget gate
if [ "$REMAINING_INT" -le "$BUDGET_THRESHOLD" ]; then
    echo "BUDGET EXHAUSTED. Remaining: \$$REMAINING <= threshold \$$BUDGET_THRESHOLD"
    echo "Notifying Mayor for shutdown sequence."
    $GT mail send mayor/ \
        -s "SHUTDOWN: Budget exhausted" \
        -m "Budget remaining: \$$REMAINING (threshold: \$$BUDGET_THRESHOLD). Research loop stopping. Please run shutdown sequence."
    $BD note sc-research-log "BUDGET GATE: Remaining \$$REMAINING <= \$$BUDGET_THRESHOLD. Research loop halted. Mayor notified for shutdown."
    exit 0
fi

# 3. Budget sufficient — mail Mayor to dispatch next iteration
echo "Budget sufficient. Mailing Mayor to dispatch next iteration."

# Count existing iterations for numbering
ITER_COUNT=$($BD list --parent sc-research-log 2>/dev/null | grep -c "Research Iteration" || echo "0")
NEXT_ITER=$((ITER_COUNT + 1))

$GT mail send mayor/ \
    -s "CHAIN_NEXT: Dispatch iteration $NEXT_ITER" \
    -m "Budget: \$$REMAINING remaining. Please dispatch next research iteration:

bd create \"Research Iteration $NEXT_ITER\" --label research-iteration --parent sc-research-log --description \"Autonomous research iteration. Budget: \$$REMAINING remaining.\"
gt sling <bead-id> scbench --formula mol-research-iteration -m \"Iteration $NEXT_ITER. Budget: \$$REMAINING.\"

This is automated — dispatch immediately, do not wait for confirmation."

$BD note sc-research-log "CHAIN: Iteration $NEXT_ITER requested. Budget: \$$REMAINING. Mayor mailed to dispatch."

# 4. Also request analysis of completed experiments from previous batch
echo "Requesting analysis polecat for previous batch results."

$GT mail send mayor/ \
    -s "DISPATCH_REQUEST: Analyze recent experiments" \
    -m "Please create and dispatch an analysis polecat:

bd create \"Analyze experiments (post-iteration $((NEXT_ITER - 1)))\" --label research-analyze --parent sc-research-log --description \"Analyze recent experiment results. Query Dolt, find patterns, file conclusion bead.\"
gt sling <bead-id> scbench --formula mol-research-analyze -m \"Analyze latest batch results\"

Dispatch immediately."

echo "Mayor mailed for both next iteration and analysis. Chain continues."
exit 0
