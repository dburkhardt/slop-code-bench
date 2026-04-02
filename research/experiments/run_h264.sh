#!/usr/bin/env bash
# Run all H264 experiment arms (sc-hypotheses.264)
# Architecture reviewer reduces structural erosion on long-sequence problems
#
# Each invocation runs both baseline (single-agent) and treatment
# (two-agent with architecture reviewer) on the given problem.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNNER="${REPO_ROOT}/research/runner/experiment_pipeline.py"

PROBLEMS=(circuit_eval execution_server)
MODEL="local-claude-sonnet-4-6"
BUDGET=5.0
BUDGET_SPLIT=70
REVIEWER_PROMPT="research/prompts/architecture-reviewer.jinja"
HYPOTHESIS_ID="sc-hypotheses.264"

for problem in "${PROBLEMS[@]}"; do
    echo "========================================="
    echo "H264: Running ${problem}"
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

echo "H264: All problems complete."
