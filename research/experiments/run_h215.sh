#!/usr/bin/env bash
# Run all H215 experiment arms (sc-hypotheses.215)
# Structured review reduces verbosity
#
# Each invocation runs both baseline (single-agent) and treatment
# (two-agent with anti-slop reviewer) on the given problem.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNNER="${REPO_ROOT}/research/runner/experiment_pipeline.py"

PROBLEMS=(file_backup trajectory_api migrate_configs)
MODEL="opus-4.5"
BUDGET=10.0
BUDGET_SPLIT=70
REVIEWER_PROMPT="research/prompts/anti-slop-reviewer.jinja"
HYPOTHESIS_ID="sc-hypotheses.215"

for problem in "${PROBLEMS[@]}"; do
    echo "========================================="
    echo "H215: Running ${problem}"
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

echo "H215: All problems complete."
