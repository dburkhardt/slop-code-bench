# SlopCodeBench Reviewer-Coder Optimization

This is an experiment to have an LLM autonomously optimize a multi-agent coding system on the SlopCodeBench benchmark.

## Overview

You are optimizing a reviewer-coder agent — a two-agent system where a coding agent (Claude Code) alternates with a reviewer agent that reads the codebase and suggests quality
improvements. The goal is to maximize a composite score that balances test pass rate against code quality degradation (erosion and verbosity).

The benchmark (SlopCodeBench) evaluates coding agents on iterative, multi-checkpoint tasks where agents extend their own prior code as specifications evolve. The key finding from the
paper is that prompt-based mitigations don't prevent code erosion — only structural interventions (like multi-agent review) can help.

## Setup

1. **Generate your run ID.** Every autoresearch session gets a unique 6-character hex ID. Generate it once at startup and use it everywhere:
   ```
   RUN_ID=$(python3 -c "import secrets; print(secrets.token_hex(3))")
   echo "Run ID: $RUN_ID"
   ```

2. **Create your run directory:**
   ```
   mkdir -p autoresearch/runs/$RUN_ID
   ```

3. **Create your worktree** (required if other autoresearch agents may be running concurrently):
   ```bash
   # Create an isolated worktree with its own branch
   git worktree add .claude-worktrees/$RUN_ID -b optloop/$RUN_ID
   cd .claude-worktrees/$RUN_ID

   # Each worktree needs its own venv since the package is installed in editable mode.
   # Without this, all agents share one venv and edits to agent.py in one worktree
   # silently affect benchmark runs in every other worktree.
   uv sync
   ```
   If you are the ONLY autoresearch agent, you can skip the worktree and just work on a branch:
   ```bash
   git checkout -b optloop/$RUN_ID
   ```
   If running in a worktree (launched by another agent), you are already isolated.

4. **Write your manifest** (`autoresearch/runs/$RUN_ID/manifest.yaml`). You know who you are from your system prompt — record it:
   ```yaml
   run_id: <RUN_ID>
   branch: optloop/<RUN_ID>
   started: <ISO 8601 timestamp>
   focus: <1-sentence description of what this run is exploring>
   budget: 750
   status: running

   # Who is running this autoresearch loop
   researcher:
     model: <your model name and ID, e.g., "Claude Opus 4.6 (claude-opus-4-6)">
     harness: <how you're running, e.g., "Claude Code CLI v2.0.51">
     context_window: <your context window, e.g., "1M tokens">

   # What model the benchmark agent under test uses
   benchmark_model: claude_code_local/sonnet-4.5
   ```

5. Read the in-scope files for full context:
   - src/slop_code/agent_runner/agents/reviewer_coder/agent.py — the agent you modify
   - configs/agents/reviewer_coder.yaml — numeric parameters
   - autoresearch/runs/*/manifest.yaml — other runs' metadata (for coordination)
   - src/slop_code/agent_runner/agents/claude_code/agent.py — parent class (modifiable if needed)
   - src/slop_code/agent_runner/agent.py — base Agent class with `self.telemetry` dict
   - autoresearch/runs/ — other autoresearch runs (read these to avoid duplicate work)

6. Verify the environment: uv sync, claude auth status, docker running.

7. Confirm and go.

## What you're optimizing

The composite score:
score = pass_rate - 0.3 * erosion - 0.3 * verbosity
Higher is better. pass_rate is the mean test pass rate across checkpoints. erosion measures complexity concentration in high-CC functions. verbosity measures redundant/duplicated code
 as a fraction of LOC.

The constraint: exactly two agents — a coder and a reviewer. No additional agent roles.

## Hard constraints

There are only two:

1. **Two agent personas.** There is a coder and a reviewer. No third role. But you can run multiple instances of either persona, and you can change everything about what each persona does, sees, and produces.
2. **Fixed budget.** The benchmark charges real API costs. Maximize the composite score for the dollars spent.

Everything else is open. The current code is one possible implementation, not a template to preserve.

## What you CAN modify

You have full control over `src/slop_code/agent_runner/agents/reviewer_coder/agent.py` and `configs/agents/reviewer_coder.yaml`. You may also modify `src/slop_code/agent_runner/agents/claude_code/agent.py` (the parent class) if your changes require it.

Some dimensions to explore (not exhaustive, not required):

- **Prompts**: REVIEWER_SYSTEM_PROMPT, CODER_APPEND_PROMPT, per-invocation prompts. Change what each agent focuses on, how suggestions are formatted, what context is injected.
- **Flow and orchestration**: The current run() is a rigid loop (code batch → review → repeat → final batch). You can restructure this however you want. Examples: planning phases before coding, test-driven review, adaptive cycle counts, reviewer-as-gatekeeper (reject and force rewrite), front-loaded vs back-loaded review.
- **Concurrency and parallelism**: The current implementation is strictly sequential. You can run multiple claude CLI processes concurrently if you manage workspace isolation (git branches, worktrees, temp directories, etc.). Examples: tournament coders (run 2 coders with different strategies, reviewer picks the better output), pipelined review (coder batch N runs while reviewer reviews batch N-1's snapshot).
- **Multiple instances**: Run multiple coder instances in parallel on the same checkpoint with different strategies. Run the reviewer multiple times with different focus areas. The "two personas" constraint means two roles, not two invocations.
- **Budget allocation**: How turns/cost are distributed across invocations. Front-load coding and skip late reviews. Give more budget to early checkpoints. Adaptive allocation based on intermediate results.
- **Information flow**: What the reviewer sees (full workspace, diff since last review, test results, specific files). What the coder receives from the reviewer (raw suggestions, prioritized list, rewritten code snippets, pass/fail gate signal). Whether agents see each other's history.
- **Workspace management**: Git operations between invocations (commit, branch, diff, stash). Snapshotting for parallel strategies. Using git history to give agents context about what changed.
- **Config parameters**: coder_turns_per_batch, num_review_cycles, step_limit, reviewer max_turns, or any new parameters you add.

## What you CANNOT modify

- The benchmark harness, evaluation pipeline, test suites, and problem specifications are all read-only
- src/slop_code/agent_runner/agent.py — avoid modifying (the telemetry dict is already there for you to use)
- Do not install new packages
- Both personas must use the `claude` CLI binary

## Baseline policy

The `claude_code` baseline (no review) is the control. Run it **once in iteration 0** on each problem you plan to use. Record the results in your run's `baseline.yaml`. Do NOT re-run the baseline every iteration — it wastes budget and the baseline doesn't change.

```bash
# Iteration 0 only: run baseline for comparison
nohup uv run slop-code run \
  --agent claude_code \
  --model claude_code_local/sonnet-4.5 \
  --environment local-py \
  --prompt just-solve \
  --problem dag_execution \
  > /tmp/optloop_${RUN_ID}_baseline.log 2>&1 &
```

Save baseline results in `autoresearch/runs/$RUN_ID/baseline.yaml`:
```yaml
problem: dag_execution
pass_rate: X.XXX
erosion: X.XXX
verbosity: X.XXX
composite: X.XXX
cost: $X.XX
output_dir: <path>
```

All subsequent iterations compare against this fixed baseline. If you switch to a new problem, run the baseline once for that problem too.

## Running an experiment

Each experiment runs the agent on a 3-checkpoint problem (~25-40 minutes, ~$3-8 per run). Launch as:

nohup uv run slop-code run \
  --agent reviewer_coder \
  --model claude_code_local/sonnet-4.5 \
  --environment local-py \
  --prompt just-solve \
  --problem <problem_name> \
  > /tmp/optloop_${RUN_ID}_iter_N.log 2>&1 &

Fast-iteration problems (3 checkpoints each): dag_execution, eve_route_planner, eve_jump_planner

Validation problem (4 checkpoints, use sparingly): file_backup

Parallelism: You can run 2-3 experiments simultaneously on DIFFERENT problems. To test config variants in parallel, create variant YAML files (e.g.,
configs/agents/reviewer_coder_v2.yaml) with type: reviewer_coder and different parameter values.

IMPORTANT: Always use nohup ... > logfile 2>&1 & to launch runs. Do NOT use tee or bare & — those get killed when tool sessions end.

## Extracting results

Results land in outputs/sonnet-4.5/<agent>-<version>_<prompt>_<thinking>_<timestamp>/.

Find the latest run:
ls -td outputs/sonnet-4.5/reviewer_coder-* | head -1

Parse results (human-readable):
```bash
OUTPUT_DIR=$(ls -td outputs/sonnet-4.5/reviewer_coder-* | head -1)
python3 autoresearch/parse_results.py "$OUTPUT_DIR"
```

Parse results (machine-readable JSON, for results.json):
```bash
python3 autoresearch/parse_results.py "$OUTPUT_DIR" --json
```

If checkpoint_results.jsonl doesn't exist, the run didn't complete — check the log file for errors.

## Understanding the signals

Every run produces rich telemetry. Use these signals to diagnose WHY an experiment succeeded or failed, not just whether the composite score moved.

**Core metrics (always present):**
- `pass_rate` / `core_pass_rate`: Overall and core-only test pass rates. Core tests are the minimum bar.
- `erosion`: Fraction of cyclomatic complexity mass in functions with CC>10. Higher = more complexity concentrated in monster functions.
- `verbosity`: Fraction of LOC that is duplicated or AST-grep flagged. Higher = more bloat.
- `loc`: Total logical lines. Watch for monotonic growth across checkpoints (bloat signal).
- `steps` / `step_utilization`: How many inference steps used vs the limit. `util=1.0` means the agent hit the wall every time and probably needed more budget.
- `cost`: Dollar cost per checkpoint.

**Failure diagnostics (always present):**
- `import_errors`: Tests failed because the code doesn't even import. The agent likely broke the file structure.
- `assertion_errors`: Tests ran but produced wrong output. Logic bugs.
- `timeout_errors`: Tests hung. Infinite loops or pathological algorithms.
- `other_errors`: Catch-all. Check `evaluation/report.json` for details.

**Regression tracking (checkpoints 2+):**
- `regression_passed / regression_total`: Prior checkpoint tests re-run. If this drops, the agent is breaking old functionality while adding new.
- `delta.churn_ratio`: (lines_added + lines_removed) / prior_loc. High churn means the agent is rewriting instead of extending. Review may cause destructive rewrites.

**Reviewer telemetry (reviewer_coder only):**
- `phase_count`: Total invocations (coder batches + reviewer passes). 7 = 3 coder + 3 reviewer + 1 final.
- `reviewer_cost_fraction`: What fraction of the checkpoint's cost went to reviewer passes. If >20%, review is eating too much budget.
- `reviewer_num_cycles`: How many review cycles produced extractable suggestions. If this is 0 when num_review_cycles>0, the reviewer's output isn't being parsed correctly.
- `reviewer_suggestion_chars`: Total chars of reviewer suggestions. Low chars = reviewer isn't finding much. Very high chars = reviewer is verbose.
- `mid_phase_pass_rate_first / last / delta`: Pass rate after the first coder batch vs after the final batch. If delta>0, the review cycles are helping correctness. If delta=0, review isn't translating to test improvement.

**How to use signals for decisions:**
- `step_utilization=1.0` everywhere? Increase `step_limit` or reduce review cycles to free up turns.
- `import_errors>0`? The agent isn't producing valid Python. Focus on the coder prompt, not review.
- `mid_phase_pass_rate_delta=0`? Reviews aren't improving correctness. Try test-driven review or skip reviews.
- `regression_passed` dropping across checkpoints? The agent is breaking prior work. Add regression awareness to the coder prompt.
- `reviewer_cost_fraction>0.2`? Reviews are expensive relative to coding. Reduce reviewer max_turns or cycle count.
- High `churn_ratio` after review? The coder is doing destructive rewrites based on suggestions. Tell the reviewer to suggest smaller, targeted changes.

## Artifact structure

Every autoresearch run saves structured artifacts for reproducibility and meta-analysis. The directory layout:

```
autoresearch/
  program.md                    # this file
  runs/
    <run_id>/                   # e.g., "a3f2c1"
      manifest.yaml             # run metadata (branch, focus, budget, status)
      baseline.yaml             # one-time baseline results
      iter_00/
        agent.py                # snapshot of reviewer_coder/agent.py
        config.yaml             # snapshot of reviewer_coder.yaml
        report.md               # structured reflection (see template below)
        results.json            # machine-readable scores (for meta-analysis)
        output_dir.txt          # path to outputs/sonnet-4.5/... for this iteration
      iter_01/
        ...
    <other_run_id>/
      ...
```

### Saving artifacts after each iteration

After every iteration (step 9 in the loop), save artifacts:

```bash
ITER_DIR="autoresearch/runs/${RUN_ID}/iter_$(printf '%02d' $ITER_NUM)"
mkdir -p "$ITER_DIR"

# Snapshot the agent code and config
cp src/slop_code/agent_runner/agents/reviewer_coder/agent.py "$ITER_DIR/agent.py"
cp configs/agents/reviewer_coder.yaml "$ITER_DIR/config.yaml"

# Record which output directory has the benchmark results
echo "<output_dir_path>" > "$ITER_DIR/output_dir.txt"
```

Then write `$ITER_DIR/results.json` (machine-readable, for meta-analysis):
```json
{
  "run_id": "<RUN_ID>",
  "iteration": 0,
  "decision": "keep",
  "composite": 0.231,
  "pass_rate": 0.447,
  "erosion": 0.668,
  "verbosity": 0.053,
  "cost": 6.23,
  "wall_clock_seconds": 1823,
  "step_utilization_mean": 0.95,
  "mid_phase_pass_rate_delta_mean": 0.0,
  "problems": ["dag_execution"],
  "output_dir": "<path>"
}
```

`wall_clock_seconds` is the elapsed time from launching the experiment to having parsed results. Track this by recording timestamps before and after the run.

Then write `$ITER_DIR/report.md` using the template below.

### Iteration report template

Every iteration MUST produce `report.md` with this structure:

```markdown
# Iteration N: <short description>

## What I changed
<Exactly what was modified and why. Reference specific lines/functions.>

## Hypothesis
<What I expected to happen and the reasoning behind it.>

## Results

| Problem | pass_rate | erosion | verbosity | composite | cost | step_util | mid_delta |
|---------|-----------|---------|-----------|-----------|------|-----------|-----------|
| ...     | ...       | ...     | ...       | ...       | ...  | ...       | ...       |

## Signal analysis
<Interpret the diagnostic signals. What do import_errors, step_utilization, mid_phase_delta, churn_ratio, etc. tell you about WHY results moved? When signals are ambiguous, read the benchmark agent's actual output to diagnose:
- Read snapshot/ files to see the generated code
- Read agent/reviewer_cycle_*.md to see what the reviewer suggested
- Read evaluation/report.json to see test failure tracebacks
Cite specific evidence from these files.>

## What I learned
<The non-obvious insight from this iteration. Not just "it worked/didn't work" but WHY. What does this teach about the problem structure?>

## What I'll try next
<Concrete plan for the next iteration, informed by the signal analysis. If reverting, explain what alternative approach the signals suggest.>

## Decision
KEEP / PROVISIONAL_KEEP / REVERT — <reason>
(PROVISIONAL_KEEP: composite dipped but signals are encouraging. N iterations remaining before mandatory revert.)

## Metadata
- Git commit: <hash>
- Output dir: <path>
- Cost this iteration: $X.XX
- Cumulative cost: $X.XX
```

## Multi-agent coordination

Multiple autoresearch agents can run simultaneously. Each agent works on its own branch and writes to its own `autoresearch/runs/<run_id>/` directory.

### Why isolation matters

The package is installed in **editable mode** (`uv sync` creates a link from `.venv` to `src/`). If two agents share the same `.venv`, edits to `reviewer_coder/agent.py` in one agent's branch are immediately visible to the other's benchmark runs. This silently corrupts experiments. Each concurrent agent MUST use a separate worktree with its own `uv sync`.

For **config-only** experiments (changing YAML parameters, not Python code), agents CAN share a worktree since different YAML files don't conflict. Always namespace variant configs with your run ID: `configs/agents/reviewer_coder_${RUN_ID}.yaml` and pass `--agent reviewer_coder_${RUN_ID}`. Never create generic names like `reviewer_coder_v2.yaml` that could collide with another agent.

### Isolation rules

1. **Worktree isolation.** Each concurrent agent works in `.claude-worktrees/<run_id>` with its own `.venv`. Each pushes to branch `optloop/<run_id>`. Never push directly to main.

2. **Shared read, isolated write.** All agents can READ other agents' `autoresearch/runs/` directories (on the main worktree or via `git fetch`). Only write to your own `autoresearch/runs/<run_id>/`.

3. **Check for conflicts before starting.** At the start of each iteration, read other agents' latest `report.md` files to see what they're working on. Avoid duplicate experiments. If another agent already tested your hypothesis, build on their results instead.

### Coordination workflow

At the START of each iteration:
```bash
# Check what other agents are doing
for run_dir in autoresearch/runs/*/; do
  if [ -f "$run_dir/manifest.yaml" ]; then
    echo "=== $(basename $run_dir) ==="
    cat "$run_dir/manifest.yaml"
    # Read their latest report
    latest=$(ls -td "$run_dir"/iter_* 2>/dev/null | head -1)
    if [ -f "$latest/report.md" ]; then
      echo "Latest report:"
      head -5 "$latest/report.md"
    fi
    echo
  fi
done
```

If another agent is exploring the same dimension (e.g., both doing prompt tuning), pivot to a different dimension. The value of multiple agents is exploring different parts of the search space simultaneously.

### Completion and merge-back

When an agent finishes (budget exhausted or interrupted), it must merge its work back and clean up:

**Step 1: Update manifest** (`autoresearch/runs/$RUN_ID/manifest.yaml`):
```yaml
status: completed
best_composite: X.XXX
best_iteration: N
iterations: N
total_cost: $XX.XX
ended: <ISO 8601 timestamp>
summary: <1-2 sentence summary of what this run discovered>
```

**Step 2: Restore the best iteration's code.** The current branch may not have the best code (later iterations may have kept a worse-than-best result). Copy the best iteration's snapshot back into the package directory:
```bash
BEST_ITER=<best_iteration number from manifest, zero-padded>
cp autoresearch/runs/$RUN_ID/iter_${BEST_ITER}/agent.py \
   src/slop_code/agent_runner/agents/reviewer_coder/agent.py
cp autoresearch/runs/$RUN_ID/iter_${BEST_ITER}/config.yaml \
   configs/agents/reviewer_coder.yaml
```

**Step 3: Commit and push your final state:**
```bash
git add -A
git commit -m "[optloop/$RUN_ID] final: restore best iteration (iter $BEST_ITER, composite $BEST_COMPOSITE)"
git push origin optloop/$RUN_ID
```

**Step 4: Merge to main:**
```bash
# Switch to main
git checkout main
git pull origin main

# Merge your branch (artifacts + best code)
git merge optloop/$RUN_ID --no-ff -m "Merge autoresearch run $RUN_ID: <summary>"
git push origin main
```

If the merge has conflicts (another agent merged first), resolve them:
- `autoresearch/runs/` — keep both directories, no conflict possible (different run IDs)
- `reviewer_coder/agent.py` or `reviewer_coder.yaml` — pick the version with the better composite score, or keep main's version and let the human decide

**Step 5: Clean up the worktree** (if using one):
```bash
cd /path/to/original/repo
git worktree remove .claude-worktrees/$RUN_ID
git branch -d optloop/$RUN_ID  # safe delete (already merged)
```

If another agent is still running, do NOT remove its worktree or branch.

## Logging results

All results live in your run directory. There is no shared `optimization_log.md`. Each run is self-contained:

- **Per-iteration detail:** `autoresearch/runs/$RUN_ID/iter_NN/report.md` (the full template from "Artifact structure" above)
- **Run summary:** `autoresearch/runs/$RUN_ID/manifest.yaml` (metadata + final stats)
- **Baseline reference:** `autoresearch/runs/$RUN_ID/baseline.yaml`

For cross-run comparison, read all manifests:
```bash
for f in autoresearch/runs/*/manifest.yaml; do
  echo "=== $(basename $(dirname $f)) ==="
  grep -E "focus|best_composite|status|total_cost|summary" "$f"
  echo
done
```

## The experiment loop

LOOP FOREVER:

1. **Read state.** Start each iteration by reading:
   - `autoresearch/runs/$RUN_ID/summary.md` (your running summary, see below)
   - The previous iteration's `report.md` for detailed context
   - Other agents' latest manifests/reports (to avoid duplicate work)

2. **Decide what to try.** Pick ONE change based on results so far. Use the diagnostic signals from the last iteration to guide your choice (see "How to use signals for decisions" above). Prioritize structural changes (flow, timing, what agents see) over prompt tweaks — the SlopCodeBench paper shows prompts alone don't fix erosion.

3. **Make the change** in reviewer_coder/agent.py or reviewer_coder.yaml (in your worktree if using one).

4. **Git commit:** `[optloop/$RUN_ID] iter N: <description>`

5. **Run the experiment.** Launch reviewer_coder on your primary problem. Run 2 replicates in parallel (same problem twice, or two different problems) to reduce noise. Do NOT re-run the baseline (see Baseline policy).
   ```bash
   nohup uv run slop-code run --agent reviewer_coder ... --problem dag_execution > /tmp/optloop_${RUN_ID}_iter${N}_rep1.log 2>&1 &
   nohup uv run slop-code run --agent reviewer_coder ... --problem dag_execution > /tmp/optloop_${RUN_ID}_iter${N}_rep2.log 2>&1 &
   ```

6. **Wait for completion.** Poll with `grep "Saved run summary" /tmp/optloop_${RUN_ID}_*.log` every few minutes. If a run takes >60 minutes, something is wrong — kill it and treat as failure.

7. **Parse results and diagnose.** Extract metrics from the output directory using the parsing snippet. Then **read the benchmark agent's actual output** to understand why:
   - Read `<output_dir>/<problem>/checkpoint_N/snapshot/` — the code the benchmark agent wrote. If erosion spiked, look at the code to see if it's a reviewer-induced rewrite or coder bloat.
   - Read `<output_dir>/<problem>/checkpoint_N/agent/reviewer_cycle_*.md` — what the reviewer suggested and whether it was sensible.
   - Read `<output_dir>/<problem>/checkpoint_N/evaluation/report.json` — full test failure details with tracebacks.
   - If you ran 2 replicates, average the composite scores. Only act on differences that are consistent across both.

8. **Keep, provisionally keep, or revert:**
   - **KEEP** if composite improved over best-so-far (averaged across replicates). Update best score.
   - **PROVISIONAL KEEP** if composite dipped but diagnostic signals are encouraging (e.g., failure type shifted from import_errors to assertion_errors, mid_phase_delta is positive, or the structural change needs budget tuning). You get 2 more iterations to show improvement before mandatory revert. Mark the iteration as `decision: provisional_keep` in results.json.
   - **REVERT** if composite worsened and signals don't suggest a path forward. Revert only the agent code and config, NOT the artifacts (see revert procedure below).

9. **Save artifacts, write report, update summary:**
   - Copy agent.py and config.yaml to `autoresearch/runs/$RUN_ID/iter_NN/`
   - Write `results.json` (machine-readable scores)
   - Write `report.md` using the template
   - **Update `summary.md`** (see "Running summary" below)

10. **Push:** `git push origin optloop/$RUN_ID`

11. **Cross-validate** every 3-4 iterations: run your current best config on a second problem (e.g., `eve_jump_planner` if you've been optimizing on `dag_execution`). If it doesn't transfer, log that finding and consider whether you're overfitting to the primary problem's structure.

12. **Check budget.** If cumulative spend > $750, stop. Run the "Completion and merge-back" procedure.

### Revert procedure

When reverting, only revert the agent code and config. Do NOT revert artifacts or reports.

```bash
# Revert only the source files, not the run artifacts
git checkout HEAD~1 -- src/slop_code/agent_runner/agents/reviewer_coder/agent.py
git checkout HEAD~1 -- configs/agents/reviewer_coder.yaml
git commit -m "[optloop/$RUN_ID] iter N: REVERT — <reason>"
```

This preserves your iteration reports and artifacts while restoring the code to the pre-experiment state.

### Running summary

Maintain `autoresearch/runs/$RUN_ID/summary.md` as a living document. Update it at the end of every iteration. This is your external memory — it prevents context decay over long runs.

```markdown
# Run <RUN_ID> Summary

## Current state
- **Best composite:** X.XXX (iteration N)
- **Current config:** <1-sentence description of what's active>
- **Iterations completed:** N
- **Budget remaining:** $XXX
- **Provisional keeps pending:** <list any, with iterations remaining>

## Top findings
1. <Most important thing learned so far>
2. <Second most important>
3. <Third>

## Dead ends (don't revisit)
- <Approach X failed because Y>
- <Approach Z failed because W>

## Promising directions not yet tried
- <Idea A, based on finding from iter N>
- <Idea B>
```

Keep this concise. The detail lives in individual `report.md` files; the summary is for orientation at the start of each iteration.

## Key research insights to guide experiments

- Agyn (72.2% SWE-bench): Manager/Researcher/Engineer/Reviewer — the reviewer can reject and send work back, not just suggest. Dynamic cycle count based on quality.
- MapCoder: Plan→Code→Debug cycle with plan-derived debugging. Planning before coding dramatically helps.
- SlopCodeBench paper: Prompt strategies set cleaner starting points but the degradation slope is unchanged. Structural interventions are needed.
- Common patterns that work: test-driven review (run tests first), planning phases, before/after code snippets in suggestions, front-loaded review (early reviews matter most).

## Budget

Hard ceiling: $750 per run (budget allows for replications). Track cumulative spend in results.json and in your manifest. Stop when exceeded.

## NEVER STOP

Once the loop begins, do NOT pause to ask the human anything. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human is likely asleep. You are autonomous. If
 you run out of ideas, re-read the research insights above, look at what's worked and what hasn't in the log, read other agents' reports for inspiration, try combining near-misses, try more radical structural changes. The loop
runs until the budget is exhausted or the human interrupts you.
