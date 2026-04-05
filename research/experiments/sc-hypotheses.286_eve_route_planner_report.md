# Experiment Report: sc-hypotheses.286 (eve_route_planner)

## Hypothesis

Experiment B8.6 (sc-hypotheses.286): Compare single-agent baseline vs two-agent
(implementer + reviewer) on eve_route_planner using local-sonnet-4.6.

## Setup

- **Problem**: eve_route_planner (3 checkpoints)
- **Model**: local-sonnet-4.6
- **Budget**: $5 total, 60/40 split (implementer/reviewer)
- **Implementer prompt**: configs/prompts/default_implementer.jinja
- **Hypothesis ID**: sc-hypotheses.286
- **Date**: 2026-04-05

## Results

**EXPERIMENT FAILED**: Neither arm produced complete results.

### Failure Details

1. **Two-agent arm**: Timed out after 3600s. The two_agent_runner.py orchestrates
   alternating implementer/reviewer runs across all checkpoints. With 3 checkpoints
   and alternating passes, the total runtime exceeded the 3600s timeout.

2. **Baseline arm**: slop-code output landed in the default directory structure
   (`outputs/local-sonnet-4.6/claude_code-*`) instead of the pipeline's expected
   `outputs/baseline_*` directory. The pipeline's `parse_eval_results` could not
   find the `checkpoint_results.jsonl` at the expected path, so metrics were empty.

3. **No Dolt insertion**: Both `baseline_row.pass_rates` and `ta_row.pass_rates`
   were empty lists, so the pipeline skipped INSERT for both arms.

### Partial Data (checkpoint_1 only)

All runs completed only checkpoint_1 of 3. Results were identical across all 4 runs:

| Run | Prompt | Pass Rate | Core Pass | Duration | Cost | Steps |
|-----|--------|-----------|-----------|----------|------|-------|
| Implementer #1 | default_implementer | 45.5% | 0.0% | 849s | $0.120 | 10 |
| Reviewer #1 | default_reviewer | 45.5% | 0.0% | 771s | $0.173 | 12 |
| Implementer #2 | default_implementer | 45.5% | 0.0% | 609s | $0.102 | 8 |
| Reviewer #2 | default_reviewer | 45.5% | 0.0% | 1167s | $0.148 | 11 |

All runs: 5/11 tests passed, 0/1 core tests passed, 6 assertion errors, state="error".
Quality metrics (LOC, CC, verbosity, erosion) all zero, suggesting the agent
produced no code files that the analysis pipeline could parse.

## Cost Analysis

- Budget allocated: $5.00
- Actual cost (partial runs): ~$0.54 (checkpoint_1 only across both arms)
- Budget decrease observed: $8.78 ($616.48 to $607.70), suggesting other experiments
  ran concurrently on the same budget pool

## Root Cause Analysis

Two issues prevented successful completion:

1. **save_dir override not respected by slop-code**: The pipeline passes
   `save_dir=<path>` and `save_template=.` as overrides, but slop-code wrote
   output to its default directory structure. This broke the pipeline's metric
   collection for the baseline arm.

2. **3600s timeout insufficient**: The two-agent runner needs to complete 3
   checkpoints with alternating implementer/reviewer passes. Each checkpoint
   takes 600-1200s per pass. With 3 checkpoints and 2 passes each, the minimum
   runtime is approximately 3600-7200s, exceeding the timeout.

## Conclusion

**INCONCLUSIVE**: The experiment infrastructure failed before producing
comparable results. The hypothesis cannot be evaluated.

### Replication Run (flint, 2026-04-05 08:21-09:22 UTC)

A second run reproduced the identical failure mode:
- Two-agent arm timed out at 3600s
- Baseline arm produced no metrics (same save_dir issue)
- Partial checkpoint_1 results: 45.5% pass rate, 0% core, all quality metrics zero
- Cost: ~$0.40 across partial runs (budget decreased from $607.70 to $604.42, concurrent runs)

Two independent runs confirm the infrastructure failures are systematic, not transient.

### Recommendations

- File a bug for the save_dir override not being respected by slop-code
- Increase two-agent timeout to at least 7200s for 3-checkpoint problems
- Consider running baseline and two-agent arms sequentially instead of in parallel
  to reduce resource contention
