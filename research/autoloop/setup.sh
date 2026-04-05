#!/usr/bin/env bash
set -euo pipefail

# ── One-time setup for the autoloop research system ──────────────
REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DOLT_DIR="${DOLT_DIR:-$HOME/.dolt-data/scbench}"

log() { echo "[setup] $*"; }

# 1. Python environment
log "Checking Python environment..."
cd "$REPO_DIR"
if ! command -v uv &>/dev/null; then
    log "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi
uv sync
log "Python environment ready."

# 2. Dolt
log "Checking Dolt..."
if ! command -v dolt &>/dev/null; then
    log "Installing Dolt..."
    sudo bash -c 'curl -L https://github.com/dolthub/dolt/releases/latest/download/install.sh | bash'
fi

if [ ! -d "$DOLT_DIR" ]; then
    log "Initializing Dolt database..."
    mkdir -p "$DOLT_DIR"
    cd "$DOLT_DIR" && dolt init

    dolt sql -q "
    CREATE TABLE budget (
        id INT PRIMARY KEY AUTO_INCREMENT,
        total_budget DECIMAL(8,2) NOT NULL DEFAULT 1000.00,
        spent DECIMAL(8,2) NOT NULL DEFAULT 0.00,
        remaining DECIMAL(8,2) NOT NULL DEFAULT 1000.00,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    INSERT INTO budget (total_budget, spent, remaining) VALUES (1000.00, 0.00, 1000.00);
    "
    dolt add .
    dolt commit -m "Initialize scbench database"
    log "Dolt database initialized."
else
    log "Dolt database exists at $DOLT_DIR"
fi

# 3. Claude CLI
log "Checking Claude CLI..."
if ! command -v claude &>/dev/null; then
    log "ERROR: claude CLI not found."
    exit 1
fi
echo "hello" | claude --print -s "Reply with just 'ok'" >/dev/null 2>&1 && log "Claude CLI works." || {
    log "ERROR: Claude CLI test failed. Check auth."
    exit 1
}

# 4. Docker
log "Checking Docker..."
if ! docker info >/dev/null 2>&1; then
    log "ERROR: Docker not running."
    exit 1
fi
log "Docker works."

# 5. jq + bc
for cmd in jq bc; do
    if ! command -v "$cmd" &>/dev/null; then
        log "Installing $cmd..."
        sudo apt-get install -y "$cmd"
    fi
done

# 6. Pipeline
log "Checking experiment pipeline..."
cd "$REPO_DIR"
uv run python research/runner/experiment_pipeline.py --help >/dev/null 2>&1 && log "Pipeline works." || {
    log "ERROR: experiment_pipeline.py failed."
    exit 1
}

# 7. Make scripts executable
chmod +x "$(dirname "$0")/research-loop.sh"

log ""
log "Setup complete. To start:"
log "  cd $REPO_DIR"
log "  tmux new -s research"
log "  ./research/autoloop/research-loop.sh 2>&1 | tee research.log"
