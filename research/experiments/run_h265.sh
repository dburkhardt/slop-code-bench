#!/usr/bin/env bash
# Run all H265 experiment arms (sc-hypotheses.265)
# Two-agent cost efficiency varies with single-agent baseline difficulty
#
# Each invocation runs both baseline (single-agent) and treatment
# (two-agent with default reviewer) on the given problem.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNNER="${REPO_ROOT}/research/runner/experiment_pipeline.py"

PROBLEMS=(log_query metric_transform_lang trajectory_api file_query_tool)
MODEL="local-claude-sonnet-4-6"
BUDGET=5.0
BUDGET_SPLIT=70
REVIEWER_PROMPT="configs/prompts/default_reviewer.jinja"
HYPOTHESIS_ID="sc-hypotheses.265"

for problem in "${PROBLEMS[@]}"; do
    echo "========================================="
    echo "H265: Running ${problem}"
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

echo "H265: All problems complete."
