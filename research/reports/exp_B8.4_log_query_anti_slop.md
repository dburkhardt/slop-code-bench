# Exp B8.4: log_query anti-slop replication

**Hypothesis:** sc-hypotheses.281 (H-prompt-only: Single-agent anti-slop prompt reduces verbosity at zero cost overhead)
**Problem:** log_query
**Model:** claude_code_local/local-claude-sonnet-4-6
**Mode:** single-agent (baseline)
**Prompt:** configs/prompts/anti_slop.jinja
**Budget:** $5 (actual spend: $10.46)
**Dolt row ID:** 656

## Run Summary

| Checkpoint | Pass Rate | Erosion | Verbosity |
|------------|-----------|---------|-----------|
| 1          | 0.9851    | 0.2516  | 0.0556    |
| 2          | 0.9807    | 0.5286  | 0.0579    |
| 3          | 0.9695    | 0.5039  | 0.0539    |
| 4          | 0.9666    | 0.6406  | 0.0591    |
| 5          | 0.9286    | 0.6364  | 0.0594    |

**Aggregate:** pass_rate=0.9661, erosion_slope=0.0882, verbosity_slope=0.0009

## Observations

- Checkpoints 1-4 completed normally. Checkpoint 5 timed out after 1800s but evaluation still ran on the partial snapshot.
- Pass rate degrades gradually from 98.5% to 92.9% across checkpoints, a typical pattern for iterative refinement.
- Erosion jumps sharply between CP1 (0.25) and CP2 (0.53), then stabilizes around 0.50 to 0.64. The anti-slop prompt does not prevent structural erosion from increasing.
- Verbosity remains low and flat across all checkpoints (0.054 to 0.059), consistent with the hypothesis that the anti-slop prompt constrains verbosity.
- Verbosity slope is near-zero (0.0009), suggesting the anti-slop prompt successfully prevents verbosity growth across iterations.

## Technical Notes

- The default per-checkpoint streaming timeout (600s) was insufficient for checkpoints 2+. Increased agent timeout to 1800s via `configs/agents/claude_code.yaml`.
- Total cost ($10.46) exceeded the $5 budget because Claude Code's internal cost tracking allowed continuation past the limit.
- Run duration: 6750s (~1h52m).
- Output directory: `outputs/baseline_claude_code_local/local-claude-sonnet-4-6_log_query_20260405_081702`
