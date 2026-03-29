# Reviewer-Coder Optimization Log

**Budget:** $500 | **Spent so far:** $0.00

## Prior results (file_backup, 4 checkpoints, Sonnet 4.5)

| Agent | pass_rate | erosion | verbosity | composite | cost |
|-------|-----------|---------|-----------|-----------|------|
| claude_code (baseline) | 0.606 | 0.532 | 0.054 | 0.430 | $4.92 |
| reviewer_coder v1 | 0.701 | 0.573 | 0.090 | 0.502 | $3.80 |

**Composite formula:** `pass_rate - 0.3 * erosion - 0.3 * verbosity`

---

## Iteration 0: Baselines on fast problems

**Config:** `coder_turns_per_batch=10, num_review_cycles=3, step_limit=100`

| Problem | pass_rate | erosion | verbosity | composite | cost |
|---------|-----------|---------|-----------|-----------|------|
| dag_execution | 0.000 | 0.570 | 0.039 | -0.183 | $9.21 |
| eve_jump_planner | 0.000 | 0.086 | 0.012 | -0.029 | $5.71 |
| eve_route_planner | 0.000 | 0.792 | 0.070 | -0.259 | $8.62 |

**Cumulative cost: $23.54**

---

## Iteration 1: Is review helping or hurting?

**Hypothesis:** With 0% pass rate, the 3 review cycles are eating turns the coder needs to get basics working. Test: no review (0 cycles), single review (1 cycle), and a claude_code baseline.

Running in parallel:
- dag_execution: claude_code baseline
- eve_jump_planner: reviewer_coder with num_review_cycles=0, coder_turns_per_batch=25
- eve_route_planner: reviewer_coder with num_review_cycles=1, coder_turns_per_batch=20
