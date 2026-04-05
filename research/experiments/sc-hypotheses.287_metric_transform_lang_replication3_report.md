# H287 Exp B6.3: metric_transform_lang replication run 3

**Hypothesis:** Two-agent benefit on metric_transform_lang replicates across additional runs (60/40 split, $5/arm).

**Bead:** sc-hypotheses.287.3

**Verdict:** CONSISTENT WITH PRIOR RUNS (reviewer rescues cp1 from 37% to 93-98%, pipeline times out before completing all 5 checkpoints)

## Setup

| Parameter | Single-Agent (Baseline) | Two-Agent (60/40) |
|-----------|------------------------|-------------------|
| Agent type | claude_code | reviewer_coder (iterative) |
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Prompt | default_implementer | default_implementer + default_reviewer |
| Cost limit | $5.00 total | $5.00 total |
| Budget split | N/A | 60/40 (implementer/reviewer) |
| Environment | local-py | local-py |

## Results

### Baseline (single-agent)

| Checkpoint | Pass Rate | Tests (passed/total) | Cost | State |
|-----------|-----------|---------------------|------|-------|
| cp1 | 37.0% | 17/46 | $0.00* | error |
| cp2-5 | N/A | N/A | N/A | not reached |
| **Mean** | **37.0%** | | **$0.00** | |

*Cost reported as $0.00 due to local model cost tracking. The baseline timed out on cp1, producing a partial implementation that passed 17/46 tests. This matches replication runs 1 and 2.

### Two-Agent (60/40)

The two-agent runner completed 3 reviewer passes before the 3600s pipeline timeout. The implementer produced the same 37% cp1 result. Reviewer pass 1 improved cp1 to 93.5% and partially completed cp2 (56.1%). Reviewer pass 2 failed to improve (37.0%), suggesting it received a stale snapshot. Reviewer pass 3 achieved 97.8% on cp1.

| Checkpoint | Role | Pass Rate | Tests (passed/total) | Cost | State |
|-----------|------|-----------|---------------------|------|-------|
| cp1 | Implementer | 37.0% | 17/46 | $0.00 | error |
| cp1 | Reviewer (pass 1) | **93.5%** | 43/46 | $1.86 | ran |
| cp2 | Reviewer (pass 1) | 56.1% | 55/98 | incl. above | ran |
| cp1 | Reviewer (pass 2) | 37.0% | 17/46 | $0.05 | error |
| cp1 | Reviewer (pass 3) | **97.8%** | 45/46 | $0.78 | ran |
| **Combined best** | | **93.5% (cp1), 56.1% (cp2)** | | **$2.69** | |

### Quality Metrics (Reviewer Pass 1)

| Checkpoint | LOC | Erosion (cc_concentration) | Verbosity (clone_ratio) | CC_sum |
|-----------|-----|---------------------------|------------------------|--------|
| cp1 | 680 | 0.551 | 0.075 | 284 |
| cp2 | 680 | 0.551 | 0.075 | 284 |

Quality metrics are identical for cp1 and cp2 because the reviewer did not modify the code between checkpoints on this pass. Reviewer pass 3 produced a larger solution (814 LOC, CC_sum=328, erosion=0.529, verbosity=0.082).

## Cost Analysis

| Metric | Baseline | Two-Agent |
|--------|---------|-----------|
| Total cost | $0.00 | $2.69 |
| Checkpoints with data | 1 | 2 (cp1 + partial cp2) |
| Pipeline wall time | ~17 min | ~56 min (timed out at 3600s) |

## Interpretation

Three findings from this replication run, all consistent with runs 1 and 2:

1. **Baseline reproduces the 37% ceiling on cp1.** Across all three replication runs plus the original H286 experiment, the single-agent baseline consistently produces 17/46 passing tests on metric_transform_lang cp1 before timing out. This is a stable, reproducible result.

2. **Reviewer improvement replicates in the 93-100% range.** Run 1 achieved 93.5%/100%, run 3 achieved 93.5%/97.8% across its reviewer passes. The reviewer reliably transforms the 37% implementer output into a near-complete cp1 solution. The variation between passes (93.5% vs 97.8%) reflects non-determinism in the reviewer agent.

3. **The 3600s pipeline timeout remains the binding constraint.** In all three runs, the two-agent pipeline times out before the implementer-reviewer cycle can iterate across cp2-cp5. The partial cp2 data (56.1% on pass 1) suggests the reviewer can make progress on later checkpoints, but the budget of 3600s wall time is insufficient to complete all 5 checkpoints.

**Cross-run comparison:**

| Run | Baseline cp1 | Best reviewer cp1 | Checkpoints completed | Total cost |
|-----|-------------|-------------------|----------------------|------------|
| H286 (original) | 37.0% | 97.8% | 1 | N/A |
| Run 1 | 37.0% | 100.0% | 1 (+ partial cp2-5) | $4.28 |
| Run 3 (this) | 37.0% | 97.8% | 1 (+ partial cp2) | $2.69 |

## Dolt Records

- Baseline: experiment id=639
- Two-agent: experiment id=640

## Raw Data

- Baseline output: `outputs/baseline_claude_code_local/local-claude-sonnet-4-6_metric_transform_lang_20260405_041929/`
- Two-agent output: `outputs/two_agent_local-claude-sonnet-4-6_metric_transform_lang_20260405_043605_cd23180bfb8c/`
- Two-agent metrics: `two_agent_metrics.json` (cumulative_cost: $1.86, 1 completed checkpoint)
- Individual reviewer runs: `outputs/local-claude-sonnet-4-6/claude_code-2.0.51_default_reviewer_none_20260405T0449/` (pass 1), `outputs/local-claude-sonnet-4-6/claude_code-2.0.51_default_reviewer_none_20260405T0526/` (pass 3)
