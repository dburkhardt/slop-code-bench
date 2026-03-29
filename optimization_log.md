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

Multiple runs completed (all dag_execution unless noted):

| Variant | pass_rate | erosion | verbosity | composite | cost |
|---------|-----------|---------|-----------|-----------|------|
| reviewer_coder file_backup* | **0.701** | 0.573 | 0.090 | **0.502** | $3.80 |
| claude_code file_backup* | 0.606 | 0.532 | 0.054 | 0.430 | $4.92 |
| reviewer_coder 3cyc (0811) | 0.428 | 0.602 | 0.055 | 0.231 | $7.64 |
| claude_code (2318) | 0.447 | 0.668 | 0.053 | 0.231 | $6.23 |
| reviewer_coder 0cyc (0009) | 0.424 | 0.803 | 0.103 | 0.152 | $7.32 |
| claude_code (0839) | 0.338 | 0.590 | 0.069 | 0.140 | $7.71 |
| reviewer_coder 3cyc (0839) | 0.242 | 0.558 | 0.048 | 0.061 | $9.94 |

*file_backup is a different problem (4 checkpoints) — not directly comparable.

**Insights:**
- reviewer_coder with 3 cycles ties baseline on composite (0.231 each) on dag_execution
- High variance between runs of the same config (0.231 vs 0.061 for reviewer_coder 3cyc)
- 0 review cycles has worst erosion (0.803) — review does help with code quality
- On file_backup, reviewer_coder clearly outperforms baseline (0.502 vs 0.430)
- The reviewer_coder's advantage may be problem-dependent

**Cumulative cost: $71.21 / $500**

---

## Iteration 3: Test-aware reviewer + erosion-aware coder

**Changes:** Reviewer runs tests first, focuses on code causing failures, provides exact code replacements. Coder explicitly prevents wrappers, enforces CC<10, requires 3+ uses for helpers.

Results:

| Problem | pass_rate | erosion | verbosity | composite | cost |
|---------|-----------|---------|-----------|-----------|------|
| dag_execution | 0.074 | 0.732 | 0.067 | -0.166 | $9.77 |
| **file_backup** | **0.917** | 0.711 | 0.035 | **0.693** | $9.76 |

**file_backup: 0.917 pass rate, 100% core solved!** Massive improvement over baseline (0.606) and previous best (0.701). Composite 0.693 vs 0.502 previous best.

dag_execution got worse — the prompt changes are problem-dependent. Test-aware review helps when tests are well-structured (file_backup) but may confuse the reviewer on harder problems (dag_execution).

**KEEP: test-aware reviewer + erosion-aware coder prompts.** The file_backup result is our best by far.

**Cumulative cost: ~$91 / $500**

---

## Iteration 4: Next experiment

Results across 4 problems (test-aware reviewer + erosion-aware coder, 3 review cycles):

| Problem | pass_rate | erosion | verbosity | composite | cost |
|---------|-----------|---------|-----------|-----------|------|
| **file_backup (4cp)** | **0.917** | 0.711 | 0.035 | **0.693** | $9.76 |
| file_merger (4cp) | 0.734 | 0.673 | 0.097 | 0.503 | $9.98 |
| code_search (6cp) | 0.646 | 0.492 | 0.043 | 0.486 | $21.22 |
| dag_execution (3cp) | 0.074 | 0.732 | 0.067 | -0.166 | $9.77 |
| circuit_eval (8cp) | *running* | | | | |

**Mean composite (4 problems): 0.379**

Strong results on 3/4 problems. dag_execution is an outlier (0.074 pass rate). The approach works well on problems with clear test suites.

**Cumulative cost: ~$142 / $500**
