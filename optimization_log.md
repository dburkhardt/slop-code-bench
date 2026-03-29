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

Results (dag_execution only — eve problems had 0/0 test evaluation issues):

| Variant | Problem | pass_rate | erosion | verbosity | composite | cost |
|---------|---------|-----------|---------|-----------|-----------|------|
| claude_code baseline | dag_execution | **0.447** | 0.668 | 0.053 | **0.231** | $6.23 |
| reviewer_coder (3 cycles, iter0) | dag_execution | 0.221 | 0.570 | 0.039 | 0.038 | $9.21 |

**Key finding:** claude_code baseline (0.447 pass, 0.231 composite) dramatically outperforms reviewer_coder with 3 review cycles (0.221 pass, 0.038 composite) on dag_execution. The review overhead eats turns and hurts correctness.

**Note:** eve_jump_planner and eve_route_planner had 0/0 test runs — evaluation broken for those problems with local-py environment. Switching to dag_execution only.

**Cumulative cost: $38.61**

---

## Iteration 2: No review cycles — does raw coder match baseline?

**Hypothesis:** reviewer_coder with 0 review cycles should match or exceed claude_code baseline since it's the same underlying binary.

| Variant | pass_rate | erosion | verbosity | composite | cost |
|---------|-----------|---------|-----------|-----------|------|
| claude_code baseline | **0.447** | 0.668 | 0.053 | **0.231** | $6.23 |
| no review (0 cycles) | 0.424 | 0.803 | 0.103 | 0.152 | $7.32 |
| 3 review cycles (iter0) | 0.221 | **0.570** | 0.039 | 0.038 | $9.21 |

**Insight:** 0 review cycles close to baseline on pass_rate but worse erosion/verbosity. 3 cycles kills pass_rate but best erosion. Sweet spot may be 1 cycle.

**Cumulative cost: $45.93**

---

## Iteration 3: 1 review cycle — the sweet spot?

**Hypothesis:** 1 review cycle gives enough cleanup to improve erosion without eating too many coding turns.

Running: reviewer_coder_1cycle on dag_execution
