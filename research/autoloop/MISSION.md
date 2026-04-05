# Mission: SCBench Autonomous Research Loop

You are running an autonomous research loop for SCBench, a benchmark that
measures code quality erosion in LLM coding agents under iterative
specification refinement.

## What You Do

Run experiments comparing single-agent vs. two-agent (implementer + reviewer)
coding systems. Each iteration: check budget, plan experiments, run them in
parallel, analyze results, repeat until budget is exhausted or research
converges.

You do NOT write the loop yourself. The loop is a bash script. Your job is
to set it up and start it.

## Setup Steps

### 1. Clone and install

```bash
git clone https://github.com/dburkhardt/slop-code-bench.git ~/slop-code-bench
cd ~/slop-code-bench
```

Install dependencies:
```bash
# uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# Python deps
cd ~/slop-code-bench && uv sync

# Dolt (git-for-data database)
sudo bash -c 'curl -L https://github.com/dolthub/dolt/releases/latest/download/install.sh | bash'

# jq + bc
sudo apt-get install -y jq bc

# Docker (must already be installed and running)
docker info >/dev/null 2>&1 || { echo "ERROR: Docker not running"; exit 1; }
```

### 2. Initialize or migrate the Dolt database

**Fresh start:**
```bash
mkdir -p ~/.dolt-data/scbench
cd ~/.dolt-data/scbench && dolt init
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
dolt add . && dolt commit -m "Initialize scbench database"
```

The experiments table is created by `experiment_pipeline.py` on first run.
If it doesn't exist yet, create it manually (check `research/scripts/setup_dolt.sql`
for the schema).

### 3. Start Dolt server

```bash
cd ~/.dolt-data/scbench && dolt sql-server --port 3307 &
sleep 2
```

### 4. Verify the pipeline works

```bash
cd ~/slop-code-bench
uv run python research/runner/experiment_pipeline.py --help
```

If this fails, check Python dependencies and Docker.

### 5. Start the research loop

```bash
tmux new -s research
cd ~/slop-code-bench
./research/autoloop/research-loop.sh 2>&1 | tee research.log
# Ctrl-B D to detach
```

## Monitoring

Once the loop is running, you can detach from tmux and monitor:

```bash
# Budget
cd ~/.dolt-data/scbench && dolt sql -q "SELECT remaining FROM budget WHERE id = 1;"

# Experiment count
cd ~/.dolt-data/scbench && dolt sql -q "SELECT COUNT(*) FROM experiments;"

# Running experiments
ps aux | grep experiment_pipeline

# Latest analysis
ls -t ~/slop-code-bench/research/autoloop/results/analysis_*.md | head -1 | xargs cat

# Live log
tail -f ~/slop-code-bench/research.log
```

## If Something Goes Wrong

The loop is ~100 lines of bash at `research/autoloop/research-loop.sh`.
Read it. Common issues:

- **Dolt not running**: `cd ~/.dolt-data/scbench && dolt sql-server --port 3307 &`
- **Pipeline fails**: check Docker is running, check Python deps with `uv sync`
- **Planner returns bad JSON**: the loop retries after 30s, check the log
- **Loop died mid-batch**: restart it, crash recovery resumes the incomplete batch
- **Budget wrong**: recalculate from actual data:
  ```sql
  UPDATE budget SET
    spent = (SELECT COALESCE(SUM(total_cost), 0) FROM experiments WHERE results_valid = 1),
    remaining = total_budget - spent
  WHERE id = 1;
  ```

## What NOT To Do

- Do not write your own experiment loop. Use `research-loop.sh`.
- Do not run experiments manually unless debugging a specific failure.
- Do not modify the loop while it's running.
- Do not add orchestration complexity. The bash script is the system.

## Context

Read `research/LESSONS_LEARNED.md` for why this system is deliberately simple.
The previous system (Gas Town) spent $382 and produced 600 lines of issue
documentation. The system before that (scbench-mission) spent $215 and produced
all the actionable findings. This loop is designed to match scbench-mission's
simplicity while adding parallel execution and LLM-driven planning.
