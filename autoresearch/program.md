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

3. **Create your git branch and worktree** (required if other autoresearch agents may be running):
   ```
   git checkout -b optloop/$RUN_ID
   ```
   If running in a worktree (launched by another agent), you are already isolated.

4. **Write your manifest** (`autoresearch/runs/$RUN_ID/manifest.yaml`). You know who you are from your system prompt — record it:
   ```yaml
   run_id: <RUN_ID>
   branch: optloop/<RUN_ID>
   started: <ISO 8601 timestamp>
   focus: <1-sentence description of what this run is exploring>
   budget: 500
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
   - optimization_log.md — shared log of all experiments across all runs
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

Parse results:
python3 -c "
import json, os, sys
outdir = sys.argv[1]
with open(os.path.join(outdir, 'checkpoint_results.jsonl')) as f:
    for line in f:
        d = json.loads(line)
        total = d.get('total_tests', 0)
        passed = d.get('passed_tests', 0)
        pr = passed/total if total else 0
        er = d.get('erosion') or 0
        vb = d.get('verbosity') or 0
        loc = d.get('loc', 0)
        steps = d.get('steps', 0)
        step_util = d.get('step_utilization') or 0
        cost = d.get('cost', 0)
        core_pr = d.get('core_pass_rate') or 0
        reg_p = d.get('regression_passed', 0)
        reg_t = d.get('regression_total', 0)
        churn = d.get('delta.churn_ratio') or 0
        la = d.get('lines_added', 0)
        lr = d.get('lines_removed', 0)
        imp_err = d.get('import_errors', 0)
        assert_err = d.get('assertion_errors', 0)
        timeout_err = d.get('timeout_errors', 0)
        other_err = d.get('other_errors', 0)
        # Agent telemetry (reviewer_coder only)
        phase_ct = d.get('phase_count', '')
        rev_frac = d.get('reviewer_cost_fraction', '')
        rev_cycles = d.get('reviewer_num_cycles', '')
        rev_chars = d.get('reviewer_suggestion_chars', '')
        mid_first = d.get('mid_phase_pass_rate_first', '')
        mid_last = d.get('mid_phase_pass_rate_last', '')
        mid_delta = d.get('mid_phase_pass_rate_delta', '')
        # Core metrics line
        print(f\"{d['problem']}/{d['checkpoint']}: pass={pr:.3f} core={core_pr:.3f} erosion={er:.3f} verb={vb:.3f} loc={loc} steps={steps} util={step_util:.2f} cost=\${cost:.2f}\")
        # Failure breakdown
        if imp_err or assert_err or timeout_err or other_err:
            print(f\"  failures: import={imp_err} assert={assert_err} timeout={timeout_err} other={other_err}\")
        # Regression and churn
        if reg_t:
            print(f\"  regression: {reg_p}/{reg_t} churn={churn:.3f} +{la}/-{lr}\")
        # Agent telemetry (reviewer_coder)
        if phase_ct:
            print(f\"  phases={phase_ct} rev_frac={rev_frac} rev_cycles={rev_cycles} rev_chars={rev_chars}\")
        if mid_first != '':
            print(f\"  mid_phase: first={mid_first} last={mid_last} delta={mid_delta}\")
" <output_dir>

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
      iter_00/
        agent.py                # snapshot of reviewer_coder/agent.py
        config.yaml             # snapshot of reviewer_coder.yaml
        report.md               # structured reflection (see template below)
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
<Interpret the diagnostic signals. What do import_errors, step_utilization, mid_phase_delta, churn_ratio, etc. tell you about WHY results moved?>

## What I learned
<The non-obvious insight from this iteration. Not just "it worked/didn't work" but WHY. What does this teach about the problem structure?>

## What I'll try next
<Concrete plan for the next iteration, informed by the signal analysis. If reverting, explain what alternative approach the signals suggest.>

## Decision
KEEP / REVERT — <reason>

## Metadata
- Git commit: <hash>
- Output dir: <path>
- Cost this iteration: $X.XX
- Cumulative cost: $X.XX
```

## Multi-agent coordination

Multiple autoresearch agents can run simultaneously. Each agent works on its own branch and writes to its own `autoresearch/runs/<run_id>/` directory.

### Isolation rules

1. **Branch isolation.** Each agent works on `optloop/<run_id>`. Never push directly to main. Merge via PR or fast-forward after human review.

2. **Shared read, isolated write.** All agents can READ `optimization_log.md` and other agents' `autoresearch/runs/` directories. Only write to your own `autoresearch/runs/<run_id>/`.

3. **Append-only shared log.** When logging to `optimization_log.md`, prefix your iteration header with your run ID:
   ```
   ## [a3f2c1] Iteration N: <description>
   ```
   This prevents confusion when multiple agents append to the same file.

4. **Check for conflicts before starting.** At the start of each iteration, read other agents' latest `report.md` files to see what they're working on. Avoid duplicate experiments. If another agent already tested your hypothesis, build on their results instead.

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

### Merging results

When an agent finishes (budget exhausted or interrupted), update `manifest.yaml` with completion fields:
```yaml
status: completed
best_composite: X.XXX
best_iteration: N
iterations: N
total_cost: $XX.XX
ended: <ISO 8601 timestamp>
summary: <1-2 sentence summary of what this run discovered>
```

The human merges promising branches into main. Agents should NOT merge each other's work.

## Logging results

Append every experiment to optimization_log.md with this format (prefix with your run ID):

## [RUN_ID] Iteration N: <short description>

**Hypothesis:** <what you expect and why>
**Change:** <exactly what you modified>
**Git commit:** <short hash>

| Problem | pass_rate | erosion | verbosity | composite | cost | step_util | mid_delta |
|---------|-----------|---------|-----------|-----------|------|-----------|-----------|
| <name>  | X.XXX     | X.XXX   | X.XXX     | X.XXX     | $X.XX| X.XX      | X.XXX     |

**Diagnostics:** <1-2 sentences using signals to explain WHY composite moved.>
**Decision:** KEEP / REVERT
**Cumulative spend:** $XX.XX

## The experiment loop

LOOP FOREVER:

1. Read state: Check optimization_log.md, your previous reports in autoresearch/runs/$RUN_ID/, and other agents' latest reports to understand where things stand.
2. Decide what to try: Pick ONE change based on results so far. Use the diagnostic signals from the last iteration to guide your choice (see "How to use signals for decisions" above). Prioritize structural changes (flow, timing, what agents see) over prompt tweaks — the SlopCodeBench paper shows prompts alone don't fix erosion. Check other agents' runs to avoid duplicating their work.
3. Make the change in reviewer_coder.py or reviewer_coder.yaml.
4. Git commit: [optloop/$RUN_ID] iter N: <description>
5. Run the experiment: Launch on 1-3 problems in parallel using nohup. Redirect all output to log files.
6. Wait for completion: Poll with grep "Run Summary" /tmp/optloop_*.log every few minutes. A run is done when "Run Summary" appears. If a run takes >60 minutes, something is wrong —
kill it and treat as failure.
7. Parse results: Extract metrics from the output directory using the parsing snippet above.
8. Keep or discard:
  - If composite improved over best-so-far: KEEP. Update best score.
  - If composite worsened or unchanged: REVERT with git revert HEAD. Commit: [optloop/$RUN_ID] iter N: REVERT — <reason>
  - BEFORE deciding, check the diagnostic signals to understand WHY. A revert without a diagnosis teaches you nothing. Check: Did step_utilization hit 1.0? Did import_errors spike? Did mid_phase_delta show review helping? Did churn_ratio explode?
9. Save artifacts and write the iteration report:
  - Copy agent.py and config.yaml to autoresearch/runs/$RUN_ID/iter_NN/
  - Write report.md using the template above
  - Append summary to optimization_log.md (prefixed with [$RUN_ID])
10. Push to origin: git push origin optloop/$RUN_ID
11. Check budget: If cumulative spend > $500, stop. Update manifest.yaml status to "completed".

## Key research insights to guide experiments

- Agyn (72.2% SWE-bench): Manager/Researcher/Engineer/Reviewer — the reviewer can reject and send work back, not just suggest. Dynamic cycle count based on quality.
- MapCoder: Plan→Code→Debug cycle with plan-derived debugging. Planning before coding dramatically helps.
- SlopCodeBench paper: Prompt strategies set cleaner starting points but the degradation slope is unchanged. Structural interventions are needed.
- Common patterns that work: test-driven review (run tests first), planning phases, before/after code snippets in suggestions, front-loaded review (early reviews matter most).

## Budget

Hard ceiling: $500 per run. Track cumulative spend in every log entry and in your manifest. Stop when exceeded.

## NEVER STOP

Once the loop begins, do NOT pause to ask the human anything. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human is likely asleep. You are autonomous. If
 you run out of ideas, re-read the research insights above, look at what's worked and what hasn't in the log, read other agents' reports for inspiration, try combining near-misses, try more radical structural changes. The loop
runs until the budget is exhausted or the human interrupts you.
