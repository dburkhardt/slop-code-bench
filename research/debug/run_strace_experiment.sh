#!/usr/bin/env bash
# ============================================================
# run_strace_experiment.sh — Run a Claude CLI experiment with
#   concurrent /proc-based syscall polling AND strace capture.
#
# Starts a BASELINE container (Test A config), launches Claude
# CLI, then polls /proc/<pid>/syscall and /proc/<pid>/net/tcp
# every 0.5s. Also attempts strace attachment for richer data.
#
# This combined approach ensures we capture syscall data even
# if strace cannot attach (permission issues). The key question:
# during 3-minute gaps, is Claude blocked on a single long
# read() or making multiple short network calls?
#
# Usage:
#   ./research/debug/run_strace_experiment.sh
#
# Output:
#   research/debug/results/strace_output.txt
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/results"
OUTPUT_FILE="$RESULTS_DIR/strace_output.txt"
PROC_POLL_FILE="$RESULTS_DIR/proc_poll_output.txt"
IMAGE="slop-code:claude_code-2.0.51-python3.12"
MODEL="aws/anthropic/bedrock-claude-sonnet-4-6"
BASE_URL="https://inference-api.nvidia.com"
TASK="Create hello.py that prints hello world, create a venv, run it, then modify it to also print the current date, run again."
MAX_TURNS=8
TIMEOUT_SECS=900

mkdir -p "$RESULTS_DIR"

KEY="${NVIDIA_INFERENCE_KEY:-}"
if [ -z "$KEY" ]; then
    echo "ERROR: NVIDIA_INFERENCE_KEY not set"
    exit 1
fi

echo "=== Strace Experiment ==="
echo "Date: $(date -Iseconds)"
echo "Output: $OUTPUT_FILE"

# Start container
echo "[1/5] Starting container..."
CID=$(docker run -d "$IMAGE" sleep infinity)
echo "  Container: ${CID:0:12}"

cleanup() {
    echo "[cleanup] Stopping container ${CID:0:12}..."
    docker rm -f "$CID" >/dev/null 2>&1 || true
    # Kill background jobs
    jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT

# Start Claude CLI in background
echo "[2/5] Launching Claude CLI (background)..."
docker exec \
    --env "ANTHROPIC_AUTH_TOKEN=$KEY" \
    --env "ANTHROPIC_BASE_URL=$BASE_URL" \
    --env "DISABLE_AUTOUPDATER=1" \
    --env "DISABLE_NON_ESSENTIAL_MODEL_CALLS=1" \
    --env "FORCE_AUTO_BACKGROUND_TASKS=1" \
    --env "ENABLE_BACKGROUND_TASKS=1" \
    "$CID" \
    claude \
    --output-format stream-json \
    --verbose \
    --model "$MODEL" \
    --max-turns "$MAX_TURNS" \
    --permission-mode bypassPermissions \
    --print -- \
    "$TASK" \
    > "$RESULTS_DIR/strace_experiment_stdout.jsonl" 2>&1 &
CLAUDE_DOCKER_EXEC_PID=$!
echo "  docker exec PID: $CLAUDE_DOCKER_EXEC_PID"

# Wait for Claude process to start in the container
echo "[3/5] Waiting for Claude process inside container..."
CLAUDE_PID_IN_CONTAINER=""
for i in $(seq 1 30); do
    sleep 2
    # Claude may appear as 'claude' or 'node.*claude'
    CLAUDE_PID_IN_CONTAINER=$(
        docker exec "$CID" ps aux 2>/dev/null \
        | grep -E '[c]laude' \
        | awk '{print $2}' \
        | head -1
    ) || true
    if [ -n "$CLAUDE_PID_IN_CONTAINER" ]; then
        echo "  Found Claude PID in container: $CLAUDE_PID_IN_CONTAINER (after ${i}x2s)"
        break
    fi
done

if [ -z "$CLAUDE_PID_IN_CONTAINER" ]; then
    echo "  WARNING: Could not find Claude process in container"
    echo "  Processes in container:"
    docker exec "$CID" ps aux 2>/dev/null || true
    echo "  ERROR: No Claude process found."
    exit 1
fi

# Find the host PID for the Claude process
echo "[4/5] Resolving host PID..."

# Method: read NSpid from /proc in container
NSPID_LINE=$(
    docker exec "$CID" cat "/proc/$CLAUDE_PID_IN_CONTAINER/status" 2>/dev/null \
    | grep '^NSpid:' || true
)
echo "  NSpid line: $NSPID_LINE"

# Get container short ID for cgroup matching
CONTAINER_LONG_ID=$(docker inspect --format '{{.Id}}' "$CID" 2>/dev/null)
CONTAINER_SHORT_ID="${CONTAINER_LONG_ID:0:12}"
CONTAINER_INIT_PID=$(docker inspect --format '{{.State.Pid}}' "$CID" 2>/dev/null)
echo "  Container init PID on host: $CONTAINER_INIT_PID"

# Find host PID by scanning /proc for matching NSpid
HOST_PID=""
for pid_dir in /proc/[0-9]*; do
    pid=$(basename "$pid_dir")
    if [ -f "/proc/$pid/status" ] 2>/dev/null; then
        nspid_line=$(grep -E '^NSpid:' "/proc/$pid/status" 2>/dev/null || true)
        if [ -n "$nspid_line" ]; then
            ns_pid=$(echo "$nspid_line" | awk '{print $NF}')
            if [ "$ns_pid" = "$CLAUDE_PID_IN_CONTAINER" ]; then
                cgroup_file="/proc/$pid/cgroup"
                if [ -f "$cgroup_file" ]; then
                    if grep -q "$CONTAINER_SHORT_ID" "$cgroup_file" 2>/dev/null; then
                        HOST_PID="$pid"
                        break
                    fi
                fi
            fi
        fi
    fi
done

if [ -z "$HOST_PID" ]; then
    echo "  WARNING: Could not find host PID via /proc scan"
    echo "  Trying alternative: find child of container init PID"
    # Try to find it by listing children of the container init
    HOST_PID=$(
        pgrep -P "$CONTAINER_INIT_PID" -a 2>/dev/null \
        | grep -i node \
        | awk '{print $1}' \
        | head -1
    ) || true
fi

if [ -z "$HOST_PID" ]; then
    echo "  WARNING: Could not resolve host PID"
    echo "  Falling back to /proc polling inside container"
fi

echo "  Host PID for Claude: ${HOST_PID:-unknown}"

# Initialize output file with header
{
    echo "# Strace/Syscall Experiment Output"
    echo "# Date: $(date -Iseconds)"
    echo "# Container: ${CID:0:12}"
    echo "# Claude PID in container: $CLAUDE_PID_IN_CONTAINER"
    echo "# Host PID: ${HOST_PID:-unknown}"
    echo "# Container init PID: $CONTAINER_INIT_PID"
    echo "#"
    echo "# This file contains syscall-level tracing data"
    echo "# collected during a live Claude CLI experiment."
    echo "# The goal: determine if during 3-minute gaps,"
    echo "# Claude is blocked on one long read() or making"
    echo "# multiple short network calls."
    echo ""
} > "$OUTPUT_FILE"

# Start /proc polling in background (works without privileges)
echo "[5/5] Starting syscall monitoring..."
{
    echo "=== /proc-based syscall polling ==="
    echo "Polling every 0.5s for up to ${TIMEOUT_SECS}s"
    echo "Start time: $(date -Iseconds)"
    echo ""

    POLL_COUNT=0
    POLL_MAX=$((TIMEOUT_SECS * 2))
    PREV_SYSCALL=""
    BLOCKED_START=""
    BLOCKED_SYSCALL=""

    while [ $POLL_COUNT -lt $POLL_MAX ]; do
        # Check if experiment is still running
        if ! kill -0 "$CLAUDE_DOCKER_EXEC_PID" 2>/dev/null; then
            echo "[$(date +%H:%M:%S.%N)] Experiment finished"
            break
        fi

        NOW=$(date +%H:%M:%S.%N)

        # Poll /proc/PID/syscall inside container
        SYSCALL=$(
            docker exec "$CID" cat "/proc/$CLAUDE_PID_IN_CONTAINER/syscall" 2>/dev/null || echo "N/A"
        )

        # Poll /proc/PID/net/tcp for socket states
        # (only every 5s to reduce overhead)
        TCP_INFO=""
        if [ $((POLL_COUNT % 10)) -eq 0 ]; then
            TCP_INFO=$(
                docker exec "$CID" cat "/proc/$CLAUDE_PID_IN_CONTAINER/net/tcp" 2>/dev/null \
                | awk 'NR>1 {print $4}' \
                | sort | uniq -c | sort -rn \
                | head -5 || echo "N/A"
            )
        fi

        # Parse syscall info
        SYSCALL_NUM=$(echo "$SYSCALL" | awk '{print $1}')
        SYSCALL_ARGS=$(echo "$SYSCALL" | awk '{$1=""; print $0}' | xargs)

        # Detect blocked state transitions
        if [ "$SYSCALL_NUM" != "$PREV_SYSCALL" ]; then
            if [ -n "$BLOCKED_START" ]; then
                echo "[$NOW] Unblocked from $BLOCKED_SYSCALL (was blocked since $BLOCKED_START)"
            fi
            BLOCKED_START="$NOW"
            BLOCKED_SYSCALL="$SYSCALL_NUM"
            echo "[$NOW] syscall=$SYSCALL_NUM args=$SYSCALL_ARGS"
        fi

        # Every 10 polls (5s), print a summary line
        if [ $((POLL_COUNT % 10)) -eq 0 ]; then
            echo "[$NOW] [POLL #$POLL_COUNT] syscall=$SYSCALL_NUM (blocked_since=$BLOCKED_START)"
            if [ -n "$TCP_INFO" ] && [ "$TCP_INFO" != "N/A" ]; then
                echo "[$NOW] TCP states: $TCP_INFO"
            fi
        fi

        PREV_SYSCALL="$SYSCALL_NUM"
        POLL_COUNT=$((POLL_COUNT + 1))
        sleep 0.5
    done

    echo ""
    echo "=== Polling complete ==="
    echo "End time: $(date -Iseconds)"
    echo "Total polls: $POLL_COUNT"
} >> "$OUTPUT_FILE" 2>&1 &
POLL_PID=$!
echo "  /proc poller PID: $POLL_PID"

# Attempt strace attachment (may fail without root)
if [ -n "$HOST_PID" ]; then
    echo "  Attempting strace on host PID $HOST_PID..."
    {
        echo ""
        echo "=== strace output ==="
        echo "Attached to host PID $HOST_PID"
        echo "Tracing: network,read,write syscalls"
        echo "Start time: $(date -Iseconds)"
        echo ""
    } >> "$OUTPUT_FILE"

    # Try strace - may need sudo
    timeout "$TIMEOUT_SECS" \
        strace -p "$HOST_PID" \
            -e trace=network,read,write \
            -tt -T \
        >> "$OUTPUT_FILE" 2>&1 &
    STRACE_PID=$!
    echo "  strace PID: $STRACE_PID"

    # If strace fails immediately (permission denied), try sudo
    sleep 2
    if ! kill -0 "$STRACE_PID" 2>/dev/null; then
        echo "  strace failed, trying with sudo..."
        {
            echo ""
            echo "=== strace output (sudo) ==="
            echo "Retrying with sudo on host PID $HOST_PID"
            echo "Start time: $(date -Iseconds)"
            echo ""
        } >> "$OUTPUT_FILE"

        timeout "$TIMEOUT_SECS" \
            sudo strace -p "$HOST_PID" \
                -e trace=network,read,write \
                -tt -T \
            >> "$OUTPUT_FILE" 2>&1 &
        STRACE_PID=$!
        echo "  sudo strace PID: $STRACE_PID"
    fi
else
    echo "  Skipping strace (no host PID)"
    STRACE_PID=""
fi

# Wait for experiment to complete
echo ""
echo "Waiting for experiment to complete (timeout: ${TIMEOUT_SECS}s)..."
EXPERIMENT_START=$(date +%s)
wait "$CLAUDE_DOCKER_EXEC_PID" 2>/dev/null || true
EXPERIMENT_END=$(date +%s)
EXPERIMENT_DURATION=$((EXPERIMENT_END - EXPERIMENT_START))
echo "Experiment completed in ${EXPERIMENT_DURATION}s"

# Stop polling and strace
kill "$POLL_PID" 2>/dev/null || true
if [ -n "${STRACE_PID:-}" ]; then
    kill "$STRACE_PID" 2>/dev/null || true
    sudo kill "$STRACE_PID" 2>/dev/null || true
fi
sleep 2

# Append experiment output summary
{
    echo ""
    echo "=== Experiment Output Summary ==="
    echo "Duration: ${EXPERIMENT_DURATION}s"
    echo "Stdout lines: $(wc -l < "$RESULTS_DIR/strace_experiment_stdout.jsonl" || echo 0)"
    echo ""
    echo "=== Experiment JSON Events ==="
    python3 -c "
import json, sys
events = []
for line in open('$RESULTS_DIR/strace_experiment_stdout.jsonl'):
    line = line.strip()
    if not line:
        continue
    try:
        d = json.loads(line)
        events.append(d.get('type', 'unknown'))
    except:
        pass
print(f'Total JSON events: {len(events)}')
for t in set(events):
    print(f'  {t}: {events.count(t)}')
" 2>/dev/null || echo "  (could not parse JSON events)"
} >> "$OUTPUT_FILE"

echo ""
echo "=== Results ==="
if [ -f "$OUTPUT_FILE" ]; then
    LINE_COUNT=$(wc -l < "$OUTPUT_FILE")
    echo "Output: $OUTPUT_FILE ($LINE_COUNT lines)"
    echo ""
    echo "--- First 30 lines ---"
    head -30 "$OUTPUT_FILE"
    echo ""
    echo "--- Last 20 lines ---"
    tail -20 "$OUTPUT_FILE"
else
    echo "ERROR: No output file created"
fi
