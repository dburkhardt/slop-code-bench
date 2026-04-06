#!/bin/bash
# run_experiment.sh — Wrapper that runs experiment_pipeline.py with proper timeout
# This exists because LLM polecats often ignore timeout instructions in formulas.
# The script handles the timeout internally so the polecat just needs to call it.
#
# Usage: bash research/runner/run_experiment.sh \
#   --problem <id> --model <model> --budget <usd> --budget-split <pct> \
#   --hypothesis-id <id> --use-dolt
#
# All arguments are passed through to experiment_pipeline.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Activate venv if present
if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
    source "$REPO_ROOT/.venv/bin/activate"
fi

echo "=== run_experiment.sh: starting pipeline ==="
echo "Arguments: $@"
echo "Timeout: 90 minutes (built-in)"
echo "Working dir: $REPO_ROOT"

cd "$REPO_ROOT/research/runner"

# Run with 90-minute timeout (5400 seconds)
# The pipeline writes to Dolt incrementally, so even if killed,
# partial results are preserved.
timeout 5400 python experiment_pipeline.py "$@"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
    echo "WARNING: Pipeline timed out after 90 minutes"
    echo "Partial results may have been written to Dolt"
elif [ $EXIT_CODE -ne 0 ]; then
    echo "ERROR: Pipeline exited with code $EXIT_CODE"
else
    echo "SUCCESS: Pipeline completed normally"
fi

exit $EXIT_CODE
