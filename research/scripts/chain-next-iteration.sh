#!/bin/bash
# chain-next-iteration.sh — Deterministic budget gate for research loop continuation
#
# Called as the LAST step of mol-research-iteration formula.
# Checks budget remaining in Dolt. If sufficient, creates and slings the
# next iteration bead. If exhausted, notifies Mayor for shutdown.
#
# This is the ONLY mechanism that keeps experiments flowing.
# It is deterministic — no LLM compliance required.

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
    # Log to research log
    $BD note sc-research-log "BUDGET GATE: Remaining \$$REMAINING <= \$$BUDGET_THRESHOLD. Research loop halted. Mayor notified for shutdown."
    exit 0
fi

# 3. Budget sufficient — create and sling next iteration
echo "Budget sufficient. Creating next iteration bead."

# Count existing iterations for numbering
ITER_COUNT=$($BD list --parent sc-research-log 2>/dev/null | grep -c "Research Iteration" || echo "0")
NEXT_ITER=$((ITER_COUNT + 1))

BEAD_ID=$($BD create "Research Iteration $NEXT_ITER" \
    --label "research-iteration" \
    --parent sc-research-log \
    --description "Autonomous research iteration. Read PRIOR_FINDINGS.md and research log. Run orient → plan → execute → analyze cycle. Budget: \$$REMAINING remaining." \
    2>&1 | grep -oP 'sc-\S+' | head -1)

if [ -z "$BEAD_ID" ]; then
    echo "ERROR: Failed to create iteration bead."
    $GT escalate -s HIGH "chain-next-iteration: failed to create bead"
    exit 1
fi

echo "Created bead: $BEAD_ID"
echo "Slinging to $RIG..."

$GT sling "$BEAD_ID" "$RIG" \
    --formula mol-research-iteration \
    --no-convoy \
    -m "Iteration $NEXT_ITER. Budget: \$$REMAINING. Continue research loop."

echo "Next iteration slung. Chain continues."

# Log to research log
$BD note sc-research-log "CHAIN: Iteration $NEXT_ITER dispatched (bead $BEAD_ID). Budget: \$$REMAINING remaining."

exit 0
