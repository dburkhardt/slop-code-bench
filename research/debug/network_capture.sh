#!/usr/bin/env bash
# ============================================================
# network_capture.sh — Capture HTTPS traffic inside a Docker
#   container using tcpdump.
#
# Usage:
#   ./network_capture.sh start <container_name>
#       Installs tcpdump (if missing), then starts a background
#       packet capture on port 443 saving to /tmp/capture.pcap
#       inside the container.
#
#   ./network_capture.sh stop <container_name> [output_path]
#       Stops the running tcpdump, copies the pcap file from
#       the container to the host. Default output_path is
#       research/debug/results/capture.pcap
#
# Requirements:
#   - Docker must be running
#   - The target container must be running
#   - Container must allow root execution (for apt-get)
#
# Example:
#   ./network_capture.sh start my_container
#   # ... let the experiment run ...
#   ./network_capture.sh stop my_container ./results/capture.pcap
# ============================================================
set -euo pipefail

ACTION="${1:-}"
CONTAINER="${2:-}"
OUTPUT_PATH="${3:-research/debug/results/capture.pcap}"

if [ -z "$ACTION" ] || [ -z "$CONTAINER" ]; then
    echo "Usage: $0 {start|stop} <container_name> [output_path]"
    echo ""
    echo "  start  Install tcpdump and begin capture on port 443"
    echo "  stop   Stop capture and extract pcap to host"
    exit 1
fi

install_tcpdump() {
    echo "[network_capture] Installing tcpdump in container: $CONTAINER"
    docker exec -u root "$CONTAINER" \
        sh -c 'apt-get update -qq && apt-get install -y -qq tcpdump >/dev/null 2>&1' \
        || { echo "[network_capture] ERROR: Failed to install tcpdump"; exit 1; }
    echo "[network_capture] tcpdump installed successfully"
}

start_capture() {
    # Check if tcpdump is already installed
    if ! docker exec -u root "$CONTAINER" which tcpdump >/dev/null 2>&1; then
        install_tcpdump
    fi

    # Kill any existing tcpdump to avoid duplicates
    docker exec -u root "$CONTAINER" \
        sh -c 'pkill tcpdump 2>/dev/null || true'

    # Start capture in the background
    echo "[network_capture] Starting packet capture on port 443"
    docker exec -d -u root "$CONTAINER" \
        tcpdump -i any -w /tmp/capture.pcap port 443

    # Verify it started
    sleep 1
    if docker exec -u root "$CONTAINER" pgrep tcpdump >/dev/null 2>&1; then
        echo "[network_capture] Capture running (pid: $(docker exec -u root "$CONTAINER" pgrep tcpdump))"
        echo "[network_capture] Output: /tmp/capture.pcap (inside container)"
    else
        echo "[network_capture] ERROR: tcpdump failed to start"
        exit 1
    fi
}

stop_capture() {
    echo "[network_capture] Stopping capture in container: $CONTAINER"

    # Send SIGTERM so tcpdump flushes its buffer
    docker exec -u root "$CONTAINER" \
        sh -c 'pkill -TERM tcpdump 2>/dev/null || true'
    sleep 2

    # Extract pcap from container
    OUTPUT_DIR="$(dirname "$OUTPUT_PATH")"
    mkdir -p "$OUTPUT_DIR"

    echo "[network_capture] Copying pcap to: $OUTPUT_PATH"
    docker cp "$CONTAINER:/tmp/capture.pcap" "$OUTPUT_PATH" \
        || { echo "[network_capture] ERROR: Failed to copy pcap"; exit 1; }

    FILE_SIZE=$(wc -c < "$OUTPUT_PATH")
    echo "[network_capture] Extracted $FILE_SIZE bytes to $OUTPUT_PATH"
}

case "$ACTION" in
    start)
        start_capture
        ;;
    stop)
        stop_capture
        ;;
    *)
        echo "Unknown action: $ACTION"
        echo "Usage: $0 {start|stop} <container_name> [output_path]"
        exit 1
        ;;
esac
