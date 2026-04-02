#!/usr/bin/env bash
# Run all H260 experiment arms (sc-hypotheses.260)
# Minimal reviewer (90/10) captures majority of two-agent benefit at lower cost
#
# Each invocation runs both baseline (single-agent) and treatment
# (two-agent with 90/10 budget split) on the given problem.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNNER="${REPO_ROOT}/research/runner/experiment_pipeline.py"

PROBLEMS=(file_backup database_migration)
MODEL="local-claude-sonnet-4-6"
BUDGET=5.0
BUDGET_SPLIT=90
REVIEWER_PROMPT="configs/prompts/default_reviewer.jinja"
HYPOTHESIS_ID="sc-hypotheses.260"

for problem in "${PROBLEMS[@]}"; do
    echo "========================================="
    echo "H260: Running ${problem}"
    echo "========================================="
    python "${RUNNER}" \
        --problem "${problem}" \
        --model "${MODEL}" \
        --budget "${BUDGET}" \
        --budget-split "${BUDGET_SPLIT}" \
        --reviewer-prompt "${REVIEWER_PROMPT}" \
        --hypothesis-id "${HYPOTHESIS_ID}"
    echo ""
done

echo "H260: All problems complete."
