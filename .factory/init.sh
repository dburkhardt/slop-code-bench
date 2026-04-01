#!/usr/bin/env bash
set -euo pipefail

cd /home/ubuntu/git-repos/slop-code-bench

# Ensure dependencies are installed
uv sync --quiet 2>/dev/null || true

# Create results directory for experiment outputs
mkdir -p research/debug/results

# Verify Docker is running
docker info >/dev/null 2>&1 || echo "WARNING: Docker is not running"

# Verify NVIDIA API key is set
if [ -z "${NVIDIA_INFERENCE_KEY:-}" ]; then
  echo "WARNING: NVIDIA_INFERENCE_KEY is not set"
fi

# Check for strace availability
which strace >/dev/null 2>&1 || echo "NOTE: strace not found on host — may need to install or use alternative tracing"
