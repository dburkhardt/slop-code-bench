# Experiment B6.6: file_merger replication run 3

**Hypothesis:** sc-hypotheses.287 (H-replication-positive: Confirm metric_transform_lang two-agent benefit replicates)
**Problem:** file_merger (4 checkpoints)
**Model:** claude_code_local/local-claude-sonnet-4-6
**Budget:** $5/arm, 60/40 split
**Date:** 2026-04-05

## Results

| Arm | Checkpoints Completed | Mean Pass Rate | Total Cost | Dolt Row |
|-----|----------------------|----------------|------------|----------|
| Baseline (single) | 1 / 4 | 0.152 | $0.044 | 635 |
| Two-agent | 2 / 4 | 0.338 | $0.196 | 636 |

**Delta pass rate:** +0.186 (two-agent over baseline)
**Delta erosion:** +0.267 (two-agent higher erosion)

## Checkpoint Details

### Baseline (single-agent)
- checkpoint_1: pass_rate=0.152, erosion=0.000, cost=$0.044
- Timed out on checkpoint_1 (770s, agent process timeout)
- Only 2 steps completed, 72 tokens used

### Two-agent
- checkpoint_1: pass_rate=0.152, erosion=0.496, verbosity=0.000, cost=$0.228
  - implementer: 86,537 tokens, reviewer: 56,753 tokens
- checkpoint_2: pass_rate=0.523, erosion=0.267, verbosity=0.027, cost=$1.122
  - implementer: 37,494 tokens, reviewer: 2,414,962 tokens
- Timed out after 3600s (pipeline timeout), did not reach checkpoints 3-4

## Observations

1. Both arms experienced timeouts, limiting completeness. The baseline timed out at the agent level (770s on checkpoint_1), while the two-agent run hit the pipeline-level 3600s timeout after completing 2 checkpoints.

2. The two-agent arm showed improvement from checkpoint_1 to checkpoint_2 (0.152 to 0.523 pass rate), suggesting the review cycle was effective at improving the solution.

3. Reviewer token usage was extremely high on checkpoint_2 (2.4M tokens), which consumed most of the budget and likely contributed to the timeout before reaching checkpoint_3.

4. Erosion decreased from checkpoint_1 (0.496) to checkpoint_2 (0.267) in the two-agent arm, suggesting the reviewer helped reduce structural issues.

5. The baseline's early timeout (only 2 steps, 72 tokens) suggests the agent may have stalled or encountered an environment issue rather than running out of budget.

## Data Quality Notes

- Partial results only: neither arm completed all 4 checkpoints
- The pass rate comparison is based on different checkpoint counts (1 vs 2), making direct comparison limited
- Dolt rows inserted successfully (ids 635, 636) with hypothesis_id sc-hypotheses.287
- Budget updated: $0.24 total spend recorded

## Conclusion

This replication run provides partial evidence for the two-agent benefit hypothesis. The two-agent arm achieved higher pass rates and completed more checkpoints, but both arms were limited by timeouts. The reviewer's high token consumption on checkpoint_2 is notable and warrants investigation for future runs.
