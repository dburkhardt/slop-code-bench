#!/bin/bash
set -e

export PATH="$PATH:/home/ubuntu/gopath/bin:/home/ubuntu/go/bin"
export GOROOT=/home/ubuntu/go
export GOPATH=/home/ubuntu/gopath

cd /home/ubuntu/git-repos/slop-code-bench

# Install Python dependencies
uv sync --quiet 2>/dev/null || true

# Ensure research directory structure exists
mkdir -p research/runner research/formulas research/prompts research/analysis

# Verify critical tools
command -v gt >/dev/null 2>&1 || { echo "ERROR: gt (Gas Town) not found in PATH"; exit 1; }
command -v bd >/dev/null 2>&1 || { echo "ERROR: bd (beads) not found in PATH"; exit 1; }
command -v dolt >/dev/null 2>&1 || { echo "ERROR: dolt not found"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found"; exit 1; }

echo "Environment ready."
