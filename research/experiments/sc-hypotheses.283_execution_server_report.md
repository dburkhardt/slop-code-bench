# Experiment Report: sc-hypotheses.283 — execution_server

## Hypothesis

H-replication: 60/40 budget split produces consistent positive pass-rate delta
on execution_server. Success criterion: >70% positive rate with mean delta >1pp.

## Setup

- **Problem**: execution_server
- **Model**: local-sonnet-4.6
- **Budget**: $5 per arm
- **Budget split**: 60/40 (implementer/reviewer)
- **Implementer prompt**: configs/prompts/default_implementer.jinja
- **Hypothesis ID**: sc-hypotheses.283

## Results

**INCONCLUSIVE** — Pipeline failed to complete. No data was inserted into Dolt.

### Pipeline Execution Summary

Three pipeline attempts were made. All three failed to produce complete results:

| Run | Start | Baseline | Two-Agent | Outcome |
|-----|-------|----------|-----------|---------|
| 1   | 08:26 | 3/4 checkpoints | 0 checkpoints | Process killed mid-run |
| 2   | 08:43 | 3/4 checkpoints | 0 checkpoints | Process killed mid-run |
| 3   | 09:05 | Output lost (save_dir bug) | Timed out at 3600s | Pipeline reported partial failure |

### Root Causes

1. **save_dir not respected**: `run_baseline()` passes `save_dir={output_dir}` and
   `save_template=.` as `--evaluate` overrides to `slop-code run`. The slop-code CLI
   does not honor these as top-level save path overrides. Output lands in the default
   location (`outputs/local-sonnet-4.6/...`) instead of the pipeline's expected
   `outputs/baseline_local-sonnet-4.6_...` directory.

2. **_find_latest_run_dir too shallow**: The fallback directory scanner only checks
   top-level children of `outputs/`. The actual baseline output is nested two levels
   deep (`outputs/local-sonnet-4.6/claude_code-.../execution_server/`), so the
   pipeline never finds its own baseline output.

3. **Two-agent timeout**: The two-agent runner runs implementer then reviewer
   sequentially. Under system load (10+ concurrent agent sessions), each phase
   takes 20-35 minutes. Combined wall clock exceeds the 3600s subprocess timeout
   in `run_two_agent()`.

### Partial Data Available

Despite pipeline failure, output directories exist with partial results:

- **Implementer (two-agent, T0907)**: 6 checkpoints completed, cost $1.91, final state: error (checkpoint timeout)
- **Reviewer (two-agent, T0940)**: 6 checkpoints completed, final state: completed
- **Baseline (T0826, T0843)**: 3 of 4 checkpoints completed each

These outputs were NOT evaluated (no `slop-code eval` run) and NOT inserted into Dolt.

## Cost Analysis

Estimated API spend across all three pipeline attempts:
- Run 1 baseline: ~$1.06 (incomplete)
- Run 2 baseline: ~$1.06 (incomplete)  
- Run 3 two-agent implementer: $1.91
- Run 3 two-agent reviewer: unknown (completed)
- Total estimated: ~$4-6 consumed with no usable results

## Conclusion

**INCONCLUSIVE** — No complete baseline vs. two-agent comparison was obtained for
execution_server. The experiment infrastructure has three bugs that prevent reliable
completion under concurrent load. These should be fixed before re-running:

1. Fix save_dir plumbing in run_baseline() so output lands where expected
2. Make _find_latest_run_dir search recursively or match the actual output structure
3. Increase two-agent subprocess timeout or run phases in parallel
