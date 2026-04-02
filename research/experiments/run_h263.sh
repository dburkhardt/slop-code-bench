#!/usr/bin/env bash
# Run all H263 experiment arms (sc-hypotheses.263)
# Anti-slop reviewer reduces verbosity without hurting pass rate
#
# Each invocation runs both baseline (single-agent) and treatment
# (two-agent with anti-slop reviewer) on the given problem.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNNER="${REPO_ROOT}/research/runner/experiment_pipeline.py"

PROBLEMS=(file_backup database_migration)
MODEL="local-claude-sonnet-4-6"
BUDGET=5.0
BUDGET_SPLIT=70
REVIEWER_PROMPT="research/prompts/anti-slop-reviewer.jinja"
HYPOTHESIS_ID="sc-hypotheses.263"

for problem in "${PROBLEMS[@]}"; do
    echo "========================================="
    echo "H263: Running ${problem}"
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

echo "H263: All problems complete."
