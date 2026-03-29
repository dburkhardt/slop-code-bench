# SlopCodeBench Reviewer-Coder Optimization

This is an experiment to have an LLM autonomously optimize a multi-agent coding system on the SlopCodeBench benchmark.

## Overview

You are optimizing a reviewer-coder agent — a two-agent system where a coding agent (Claude Code) alternates with a reviewer agent that reads the codebase and suggests quality
improvements. The goal is to maximize a composite score that balances test pass rate against code quality degradation (erosion and verbosity).

The benchmark (SlopCodeBench) evaluates coding agents on iterative, multi-checkpoint tasks where agents extend their own prior code as specifications evolve. The key finding from the
paper is that prompt-based mitigations don't prevent code erosion — only structural interventions (like multi-agent review) can help.

## Setup

1. Read the in-scope files for full context:
  - src/slop_code/agent_runner/agents/reviewer_coder/agent.py — the agent you modify. Prompts, flow logic, reviewer configuration.
  - configs/agents/reviewer_coder.yaml — numeric parameters (turns per batch, review cycles, step limit).
  - optimization_log.md — running log of all experiments and results.
  - src/slop_code/agent_runner/agents/claude_code/agent.py — parent class (modifiable if needed).
2. Verify the environment:
  - uv sync has been run
  - Docker is running
  - claude auth status shows logged in
  - The claude_code_local provider is configured in configs/providers.yaml
3. Initialize optimization_log.md with the baseline results if not already present.
4. Confirm and go.

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
- src/slop_code/agent_runner/agent.py (the Agent ABC)
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
  > /tmp/optloop_<label>.log 2>&1 &

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

## Logging results

Append every experiment to optimization_log.md with this format:

## Iteration N: <short description>

**Hypothesis:** <what you expect and why>
**Change:** <exactly what you modified>
**Git commit:** <short hash>

| Problem | pass_rate | erosion | verbosity | composite | cost |
|---------|-----------|---------|-----------|-----------|------|
| <name>  | X.XXX     | X.XXX   | X.XXX     | X.XXX     | $X.XX|

**Decision:** KEEP / REVERT
**Cumulative spend:** $XX.XX

## The experiment loop

LOOP FOREVER:

1. Read state: Check optimization_log.md and the current reviewer_coder.py / reviewer_coder.yaml to understand where things stand.
2. Decide what to try: Pick ONE change based on results so far. Prioritize structural changes (flow, timing, what agents see) over prompt tweaks — the SlopCodeBench paper shows
prompts alone don't fix erosion.
3. Make the change in reviewer_coder.py or reviewer_coder.yaml.
4. Git commit: [optloop] iter N: <description>
5. Run the experiment: Launch on 1-3 problems in parallel using nohup. Redirect all output to log files.
6. Wait for completion: Poll with grep "Run Summary" /tmp/optloop_*.log every few minutes. A run is done when "Run Summary" appears. If a run takes >60 minutes, something is wrong —
kill it and treat as failure.
7. Parse results: Extract pass_rate, erosion, verbosity from the output directory. Compute composite score.
8. Keep or discard:
  - If composite improved over best-so-far: KEEP. Update best score.
  - If composite worsened or unchanged: REVERT with git revert HEAD. Commit: [optloop] iter N: REVERT — <reason>
9. Log everything to optimization_log.md.
10. Push to origin: git push origin main
11. Check budget: If cumulative spend > $500, stop.

## Key research insights to guide experiments

- Agyn (72.2% SWE-bench): Manager/Researcher/Engineer/Reviewer — the reviewer can reject and send work back, not just suggest. Dynamic cycle count based on quality.
- MapCoder: Plan→Code→Debug cycle with plan-derived debugging. Planning before coding dramatically helps.
- SlopCodeBench paper: Prompt strategies set cleaner starting points but the degradation slope is unchanged. Structural interventions are needed.
- Common patterns that work: test-driven review (run tests first), planning phases, before/after code snippets in suggestions, front-loaded review (early reviews matter most).

## Budget

Hard ceiling: $500. Track cumulative spend in every log entry. Stop when exceeded.

## NEVER STOP

Once the loop begins, do NOT pause to ask the human anything. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human is likely asleep. You are autonomous. If
 you run out of ideas, re-read the research insights above, look at what's worked and what hasn't in the log, try combining near-misses, try more radical structural changes. The loop
runs until the budget is exhausted or the human interrupts you.
