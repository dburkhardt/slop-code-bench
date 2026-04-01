#!/bin/bash
# Minimal reproduction of the ~3-minute delay observed in SCBench experiments.
#
# This script runs the Claude CLI inside a Docker container via the NVIDIA
# inference endpoint and measures per-step latency. The delay appears after
# the agent runs its first few Bash commands.
#
# Expected: Steps involving Bash tool use show ~3 minute gaps.
# On the developer's laptop (Anthropic direct API), these complete in seconds.
#
# Prerequisites:
#   - NVIDIA_INFERENCE_KEY environment variable set
#   - Docker running
#   - Claude CLI v2.0.51+ installed inside the Docker image
#
# Usage:
#   NVIDIA_INFERENCE_KEY=sk-*** ./repro-3min-delay.sh

set -euo pipefail

IMAGE="slop-code:claude_code-2.0.51-python3.12"
MODEL="aws/anthropic/bedrock-claude-sonnet-4-6"
BASE_URL="https://inference-api.nvidia.com"

# Check prerequisites
if [ -z "${NVIDIA_INFERENCE_KEY:-}" ]; then
    echo "ERROR: NVIDIA_INFERENCE_KEY not set"
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker not available"
    exit 1
fi

echo "=== Minimal repro: Claude CLI 3-minute delay ==="
echo "Model: $MODEL"
echo "Endpoint: $BASE_URL"
echo "Image: $IMAGE"
echo ""

# Start a container
CONTAINER=$(docker run -d "$IMAGE" sleep infinity)
echo "Container: $CONTAINER"

# Run Claude CLI with a simple task that will trigger Bash tool use
echo ""
echo "Starting Claude CLI at $(date +%H:%M:%S)..."
echo "Watch for ~3-minute gaps between steps."
echo ""

START=$(date +%s)

docker exec \
    --env "NVIDIA_INFERENCE_KEY=$NVIDIA_INFERENCE_KEY" \
    --env "ANTHROPIC_AUTH_TOKEN=$NVIDIA_INFERENCE_KEY" \
    --env "ANTHROPIC_BASE_URL=$BASE_URL" \
    --env "DISABLE_AUTOUPDATER=1" \
    --env "DISABLE_NON_ESSENTIAL_MODEL_CALLS=1" \
    "$CONTAINER" \
    claude --output-format stream-json --verbose \
        --model "$MODEL" \
        --max-turns 15 \
        --permission-mode bypassPermissions \
        --print -- \
        'Create a Python script called hello.py that prints "Hello World".
         Then create a venv, install requests, and run the script.
         Then modify it to fetch https://httpbin.org/get and print the status code.
         Run it again to verify.' \
    2>/dev/null | while IFS= read -r line; do
        # Parse stream-json output for step timing
        TYPE=$(echo "$line" | python3 -c "import sys,json; print(json.loads(sys.stdin.readline()).get('type',''))" 2>/dev/null || echo "")
        if [ "$TYPE" = "result" ]; then
            NOW=$(date +%s)
            ELAPSED=$((NOW - START))
            COST=$(echo "$line" | python3 -c "import sys,json; print(f'\${json.loads(sys.stdin.readline()).get(\"total_cost_usd\",0):.4f}')" 2>/dev/null || echo "?")
            TURNS=$(echo "$line" | python3 -c "import sys,json; print(json.loads(sys.stdin.readline()).get('num_turns',0))" 2>/dev/null || echo "?")
            echo "[${ELAPSED}s] DONE turns=$TURNS cost=$COST"
        elif [ "$TYPE" = "assistant" ]; then
            NOW=$(date +%H:%M:%S)
            # Check if it's a tool use
            TOOL=$(echo "$line" | python3 -c "
import sys,json
msg = json.loads(sys.stdin.readline()).get('message',{})
for block in msg.get('content',[]):
    if block.get('type') == 'tool_use':
        print(block.get('name','?'))
        break
" 2>/dev/null || echo "")
            if [ -n "$TOOL" ]; then
                echo "[$NOW] Tool: $TOOL"
            fi
        fi
    done

END=$(date +%s)
TOTAL=$((END - START))
echo ""
echo "Total time: ${TOTAL}s"

# Cleanup
docker rm -f "$CONTAINER" >/dev/null 2>&1
echo "Container removed"
