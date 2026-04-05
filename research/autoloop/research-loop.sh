#!/usr/bin/env bash
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
DOLT_DIR="${DOLT_DIR:-$HOME/.dolt-data/scbench}"
RESULTS_DIR="${REPO_DIR}/research/autoloop/results"
PROMPTS_DIR="$(dirname "$0")"
MAX_CONCURRENT="${MAX_CONCURRENT:-3}"
MIN_BUDGET=10
LOOP_PAUSE=30  # seconds between iterations
ITERATION=0

mkdir -p "$RESULTS_DIR"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

query_dolt() {
    cd "$DOLT_DIR" && dolt sql -r json -q "$1" 2>/dev/null
}

# ── Crash recovery ────────────────────────────────────────────────
BATCH_FILE="$RESULTS_DIR/.current_batch.json"
RESUME=false
if [ -f "$BATCH_FILE" ]; then
    log "Found incomplete batch from previous run. Resuming."
    RESUME=true
fi

# ── Main loop ─────────────────────────────────────────────────────
while true; do
    ITERATION=$((ITERATION + 1))
    log "=== Iteration $ITERATION ==="

    # Step 1: Budget gate (deterministic)
    REMAINING=$(query_dolt "SELECT remaining FROM budget WHERE id=1;" | jq -r '.[0].remaining')
    log "Budget remaining: \$$REMAINING"

    if (( $(echo "$REMAINING < $MIN_BUDGET" | bc -l) )); then
        log "Budget below \$$MIN_BUDGET. Stopping."
        break
    fi

    # Step 2: Plan or resume
    if [ "$RESUME" = true ]; then
        log "Resuming from saved batch..."
        BATCH_JSON=$(cat "$BATCH_FILE")
        RESUME=false
    else
        # Gather experiment history for the planner
        EXPERIMENT_DATA=$(query_dolt "
            SELECT problem_id, mode, budget_split, total_pass_rate, delta_pass_rate,
                   total_cost, results_valid, reviewer_prompt, erosion_slope
            FROM experiments
            ORDER BY created_at DESC
            LIMIT 200;
        ")
        EXPERIMENT_COUNT=$(query_dolt "SELECT COUNT(*) as n FROM experiments;" | jq -r '.[0].n')
        PROBLEM_LIST=$(ls "$REPO_DIR/problems/" | tr '\n' ', ')

        log "Planning next batch ($EXPERIMENT_COUNT experiments so far)..."
        PLAN_INPUT=$(cat <<PLANEOF
Budget remaining: \$$REMAINING
Experiments run so far: $EXPERIMENT_COUNT
Available problems: $PROBLEM_LIST

Recent experiment data (JSON):
$EXPERIMENT_DATA
PLANEOF
        )

        BATCH_JSON=$(echo "$PLAN_INPUT" | claude --print -s "$(cat "$PROMPTS_DIR/plan-prompt.md")" 2>/dev/null)

        # Validate JSON
        if ! echo "$BATCH_JSON" | jq -e '.[0].problem' >/dev/null 2>&1; then
            log "ERROR: Planner returned invalid JSON. Retrying in ${LOOP_PAUSE}s..."
            log "Raw output (first 500 chars): $(echo "$BATCH_JSON" | head -c 500)"
            sleep "$LOOP_PAUSE"
            continue
        fi

        # Save batch for crash recovery
        echo "$BATCH_JSON" > "$BATCH_FILE"
    fi

    BATCH_SIZE=$(echo "$BATCH_JSON" | jq 'length')
    log "Running $BATCH_SIZE experiments (max $MAX_CONCURRENT concurrent)..."

    # Step 3: Run experiments in parallel
    echo "$BATCH_JSON" | jq -c '.[]' | while read -r exp; do
        PROB=$(echo "$exp" | jq -r '.problem')
        MODEL=$(echo "$exp" | jq -r '.model // "local-sonnet-4.6"')
        BUDGET=$(echo "$exp" | jq -r '.budget_per_arm // "5.0"')
        SPLIT=$(echo "$exp" | jq -r '.budget_split // "60"')
        RPROMPT=$(echo "$exp" | jq -r '.reviewer_prompt // ""')
        HYPO=$(echo "$exp" | jq -r '.hypothesis // ""')

        ARGS="--problem $PROB --model $MODEL --budget $BUDGET --budget-split $SPLIT"
        [ -n "$RPROMPT" ] && [ "$RPROMPT" != "null" ] && ARGS="$ARGS --reviewer-prompt $RPROMPT"
        [ -n "$HYPO" ] && [ "$HYPO" != "null" ] && ARGS="$ARGS --hypothesis-id $HYPO"

        echo "$ARGS"
    done | xargs -P "$MAX_CONCURRENT" -I {} bash -c "
        cd '$REPO_DIR' && uv run python research/runner/experiment_pipeline.py {} 2>&1 | \
            sed 's/^/[exp \$\$] /'
    "

    log "All experiments in batch $ITERATION complete."

    # Clear crash-recovery file
    rm -f "$BATCH_FILE"

    # Step 4: Analyze results
    log "Analyzing results..."
    LATEST_DATA=$(query_dolt "
        SELECT problem_id, mode, budget_split, total_pass_rate, delta_pass_rate,
               baseline_pass_rate, total_cost, erosion_slope, results_valid,
               reviewer_prompt, created_at
        FROM experiments
        ORDER BY created_at DESC
        LIMIT 30;
    ")

    ANALYSIS=$(echo "$LATEST_DATA" | claude --print -s "$(cat "$PROMPTS_DIR/analyze-prompt.md")" 2>/dev/null)

    # Write analysis
    TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    echo "$ANALYSIS" > "$RESULTS_DIR/analysis_iter${ITERATION}_${TIMESTAMP}.md"
    log "Analysis written to analysis_iter${ITERATION}_${TIMESTAMP}.md"

    # Step 5: Brief pause, then loop
    log "Sleeping ${LOOP_PAUSE}s before next iteration..."
    sleep "$LOOP_PAUSE"
done

log "Research loop complete. $ITERATION iterations run."
