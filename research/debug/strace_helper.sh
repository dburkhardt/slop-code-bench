#!/usr/bin/env bash
# ============================================================
# strace_helper.sh — Attach strace to the Claude process
#   running inside a Docker container.
#
# This script finds the Claude CLI process PID inside the
# specified container, then uses nsenter on the HOST to attach
# strace to that process in the container's PID namespace.
# Captures network and write syscalls with timestamps for a
# configurable duration (default: 5 minutes).
#
# Usage:
#   ./strace_helper.sh <container_name> [duration_seconds] [output_file]
#
# Arguments:
#   container_name    Name or ID of the Docker container
#   duration_seconds  How long to capture (default: 300 = 5 min)
#   output_file       Where to save strace output
#                     (default: research/debug/results/strace_output.txt)
#
# Requirements:
#   - strace must be installed on the host
#   - Docker must be running with the target container active
#   - The Claude process must be running inside the container
#   - May require root/sudo for nsenter or strace -p
#
# What it captures:
#   - Network syscalls: connect, sendto, recvfrom, sendmsg,
#     recvmsg, read, write on sockets
#   - Timestamps for each syscall (microsecond precision)
#   - This reveals whether the Claude process is blocked on a
#     single long read() or making multiple short network calls
#     during the 3-minute gaps.
#
# Example:
#   ./strace_helper.sh my_claude_container
#   ./strace_helper.sh my_claude_container 120 /tmp/strace.txt
# ============================================================
set -euo pipefail

CONTAINER="${1:-}"
DURATION="${2:-300}"
OUTPUT_FILE="${3:-research/debug/results/strace_output.txt}"

if [ -z "$CONTAINER" ]; then
    echo "Usage: $0 <container_name> [duration_seconds] [output_file]"
    echo ""
    echo "  container_name   Docker container running Claude CLI"
    echo "  duration_seconds How long to trace (default: 300)"
    echo "  output_file      Output path (default: research/debug/results/strace_output.txt)"
    exit 1
fi

OUTPUT_DIR="$(dirname "$OUTPUT_FILE")"
mkdir -p "$OUTPUT_DIR"

# Find the Claude process PID inside the container
echo "[strace_helper] Finding Claude process in container: $CONTAINER"

CLAUDE_PID_IN_CONTAINER=$(
    docker exec "$CONTAINER" ps aux 2>/dev/null \
    | grep -E '[c]laude' \
    | grep -v grep \
    | awk '{print $2}' \
    | head -1
) || true

if [ -z "$CLAUDE_PID_IN_CONTAINER" ]; then
    echo "[strace_helper] ERROR: No Claude process found in container $CONTAINER"
    echo "[strace_helper] Running processes:"
    docker exec "$CONTAINER" ps aux 2>/dev/null || true
    exit 1
fi

echo "[strace_helper] Claude PID inside container: $CLAUDE_PID_IN_CONTAINER"

# Get the container's init PID on the host (for nsenter)
CONTAINER_PID=$(
    docker inspect --format '{{.State.Pid}}' "$CONTAINER" 2>/dev/null
) || true

if [ -z "$CONTAINER_PID" ] || [ "$CONTAINER_PID" = "0" ]; then
    echo "[strace_helper] ERROR: Could not get container PID on host"
    exit 1
fi

echo "[strace_helper] Container init PID on host: $CONTAINER_PID"

# Resolve the Claude process PID in the host PID namespace.
# We use nsenter to enter the container's PID namespace and
# read /proc/<pid>/status to find the NSpid mapping, or we
# scan /proc on the host for the matching process.
echo "[strace_helper] Resolving host PID for Claude process..."

HOST_PID=""

# Method 1: Use /proc to find the host PID by scanning children
# of the container init process
for pid_dir in /proc/[0-9]*; do
    pid=$(basename "$pid_dir")
    # Check if this process is in the container's PID namespace
    if [ -f "/proc/$pid/status" ] 2>/dev/null; then
        nspid_line=$(grep -E '^NSpid:' "/proc/$pid/status" 2>/dev/null || true)
        if [ -n "$nspid_line" ]; then
            # NSpid line has host PID then namespace PID(s)
            ns_pid=$(echo "$nspid_line" | awk '{print $NF}')
            if [ "$ns_pid" = "$CLAUDE_PID_IN_CONTAINER" ]; then
                # Verify this process belongs to our container
                # by checking its cgroup
                cgroup_file="/proc/$pid/cgroup"
                if [ -f "$cgroup_file" ]; then
                    container_short_id=$(docker inspect --format '{{.Id}}' "$CONTAINER" 2>/dev/null | cut -c1-12)
                    if grep -q "$container_short_id" "$cgroup_file" 2>/dev/null; then
                        HOST_PID="$pid"
                        break
                    fi
                fi
            fi
        fi
    fi
done

# Method 2: Fallback — use nsenter to run strace directly in
# the container's PID namespace
if [ -z "$HOST_PID" ]; then
    echo "[strace_helper] Could not resolve host PID via /proc scan"
    echo "[strace_helper] Falling back to nsenter approach"

    echo "[strace_helper] Attaching strace via nsenter (duration: ${DURATION}s)"
    echo "[strace_helper] Output: $OUTPUT_FILE"
    echo "[strace_helper] Capturing network + write syscalls..."

    # nsenter into the container's PID and network namespace,
    # then strace the Claude process by its in-container PID
    timeout "$DURATION" \
        nsenter -t "$CONTAINER_PID" -p -n -- \
        strace -p "$CLAUDE_PID_IN_CONTAINER" \
            -e trace=network,write,read \
            -tt -T \
            -o "$OUTPUT_FILE" \
        2>&1 || STRACE_RC=$?

    STRACE_RC="${STRACE_RC:-0}"
    # Exit code 124 means timeout (expected — we set a duration)
    if [ "$STRACE_RC" -eq 124 ] || [ "$STRACE_RC" -eq 0 ]; then
        echo "[strace_helper] Capture complete (duration elapsed or process exited)"
    else
        echo "[strace_helper] strace exited with code $STRACE_RC"
        echo "[strace_helper] This may require root privileges. Try:"
        echo "  sudo $0 $CONTAINER $DURATION $OUTPUT_FILE"
    fi

    if [ -f "$OUTPUT_FILE" ]; then
        LINE_COUNT=$(wc -l < "$OUTPUT_FILE")
        echo "[strace_helper] Captured $LINE_COUNT syscall lines"
    fi
    exit "${STRACE_RC}"
fi

# Method 1 succeeded — attach strace directly by host PID
echo "[strace_helper] Host PID for Claude: $HOST_PID"
echo "[strace_helper] Attaching strace (duration: ${DURATION}s)"
echo "[strace_helper] Output: $OUTPUT_FILE"
echo "[strace_helper] Capturing network + write syscalls..."

timeout "$DURATION" \
    strace -p "$HOST_PID" \
        -e trace=network,write,read \
        -tt -T \
        -o "$OUTPUT_FILE" \
    2>&1 || STRACE_RC=$?

STRACE_RC="${STRACE_RC:-0}"
if [ "$STRACE_RC" -eq 124 ] || [ "$STRACE_RC" -eq 0 ]; then
    echo "[strace_helper] Capture complete (duration elapsed or process exited)"
else
    echo "[strace_helper] strace exited with code $STRACE_RC"
    echo "[strace_helper] This may require root privileges. Try:"
    echo "  sudo $0 $CONTAINER $DURATION $OUTPUT_FILE"
fi

if [ -f "$OUTPUT_FILE" ]; then
    LINE_COUNT=$(wc -l < "$OUTPUT_FILE")
    echo "[strace_helper] Captured $LINE_COUNT syscall lines"
fi
