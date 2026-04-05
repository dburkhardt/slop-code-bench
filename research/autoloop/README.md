# Autoloop: Autonomous Research Loop

A minimal research automation system for SCBench. Replaces Gas Town's
multi-agent orchestration with ~100 lines of bash.

See `research/LESSONS_LEARNED.md` for why this exists.

## Architecture

```
research-loop.sh
  │
  ├─ Budget gate ──── dolt sql (deterministic, no LLM)
  │
  ├─ Plan ─────────── claude --print (one-shot, fresh context)
  │
  ├─ Execute ──────── xargs -P 3 experiment_pipeline.py (parallel)
  │
  ├─ Analyze ──────── claude --print (one-shot, fresh context)
  │
  └─ loop ↺
```

Two LLM calls per iteration, both stateless. Everything else is bash.

## Usage

```bash
# One-time setup
./research/autoloop/setup.sh

# Start Dolt server (if not running)
cd ~/.dolt-data/scbench && dolt sql-server --port 3307 &

# Run in tmux
tmux new -s research
./research/autoloop/research-loop.sh 2>&1 | tee research.log
```

## Configuration

Environment variables (all optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `REPO_DIR` | auto-detected | Path to slop-code-bench repo |
| `DOLT_DIR` | `~/.dolt-data/scbench` | Path to Dolt database |
| `MAX_CONCURRENT` | 3 | Max parallel experiments |

## Crash Recovery

If the loop dies mid-batch, the planned experiments are saved in
`results/.current_batch.json`. On restart, the loop resumes the
incomplete batch instead of re-planning.

## Monitoring

```bash
# Budget
cd ~/.dolt-data/scbench && dolt sql -q "SELECT remaining FROM budget WHERE id = 1;"

# What's running
ps aux | grep experiment_pipeline

# Latest analysis
ls -t research/autoloop/results/analysis_*.md | head -1 | xargs cat

# Live log
tail -f research.log
```

## Migration from Gas Town

Copy the Dolt database to preserve existing experiment data:

```bash
cp -r ~/gt/.dolt-data/scbench ~/.dolt-data/scbench

# Fix known data quality issues
cd ~/.dolt-data/scbench
dolt sql -q "UPDATE experiments SET total_pass_rate = total_pass_rate / 100 WHERE total_pass_rate > 1;"
dolt sql -q "UPDATE budget SET spent = (SELECT COALESCE(SUM(total_cost), 0) FROM experiments WHERE results_valid = 1), remaining = total_budget - (SELECT COALESCE(SUM(total_cost), 0) FROM experiments WHERE results_valid = 1) WHERE id = 1;"
dolt add . && dolt commit -m "Normalize data from Gas Town migration"
```

## Files

| File | Purpose |
|------|---------|
| `research-loop.sh` | Main loop (~100 lines) |
| `plan-prompt.md` | System prompt for the planning LLM call |
| `analyze-prompt.md` | System prompt for the analysis LLM call |
| `setup.sh` | One-time dependency/environment setup |
| `results/` | Analysis reports and crash-recovery state |
