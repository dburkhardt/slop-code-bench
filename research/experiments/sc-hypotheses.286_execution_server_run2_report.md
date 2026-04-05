# Experiment Report: sc-hypotheses.286 — execution_server (run 2) at 60/40

**Hypothesis**: H-coverage baseline coverage across all 20 problems to map threshold boundary  
**Problem**: execution_server (6 checkpoints)  
**Model**: local-sonnet-4.6 (Claude Code local)  
**Budget**: $5/arm, 60/40 implementer/reviewer split  
**Date**: 2026-04-05  

## Summary

This is a replication of the execution_server experiment from 2026-04-04.
The results are consistent with run 1: the two-agent arm degraded pass rates
severely while the single-agent baseline performed well. The baseline averaged
96.7% pass rate at $2.91 total cost. The two-agent arm (reviewer output)
averaged 21.0% pass rate at $5.09 combined cost, with the reviewer breaking
all tests from checkpoint 3 onward.

**Verdict**: REFUTED. The two-agent approach with the default reviewer prompt
at 60/40 budget split is harmful for execution_server. Consistent across
both runs.

## Baseline (Single-Agent) Results

| Checkpoint | Pass Rate | Core Rate | Erosion | Verbosity | Cost | LOC |
|-----------|-----------|-----------|---------|-----------|------|-----|
| cp1 | 0.956 | 0.947 | 0.674 | 0.040 | $0.11 | 202 |
| cp2 | 0.966 | 1.000 | 0.658 | 0.033 | $0.32 | 239 |
| cp3 | 0.961 | 0.938 | 0.732 | 0.000 | $0.81 | 352 |
| cp4 | 0.974 | 1.000 | 0.818 | 0.000 | $0.67 | 515 |
| cp5 | 0.973 | 0.964 | 0.807 | 0.013 | $0.50 | 602 |
| cp6 | 0.971 | 0.960 | 0.761 | 0.000 | $0.49 | 910 |

- **Mean pass rate**: 0.967
- **Total cost**: $2.91
- **Erosion slope**: +0.028 (slightly increasing)
- **Verbosity slope**: -0.007 (near-zero, slightly declining)

The baseline shows strong, stable performance across all 6 checkpoints.
Pass rates remain above 0.95 throughout. Erosion increases slightly as
the codebase grows from 202 to 910 LOC. Verbosity stays near zero.
These results are consistent with run 1 (0.944 mean pass rate, $2.33).

## Two-Agent Results

| Checkpoint | Pass Rate | Core Rate | Erosion | Verbosity | Cost | LOC |
|-----------|-----------|-----------|---------|-----------|------|-----|
| cp1 | 0.622 | 0.579 | 0.492 | 0.033 | $0.20 | 182 |
| cp2 | 0.638 | 0.429 | 0.509 | 0.029 | $0.17 | 210 |
| cp3 | 0.000 | 0.000 | 0.531 | 0.021 | $0.56 | 281 |
| cp4 | 0.000 | 0.000 | 0.696 | 0.016 | $0.71 | 385 |
| cp5 | 0.000 | 0.000 | 0.645 | 0.014 | $0.43 | 441 |
| cp6 | 0.000 | 0.000 | 0.645 | 0.014 | $0.11 | 441 |

- **Mean pass rate**: 0.210
- **Total cost (reviewer only)**: $2.18
- **Total cost (combined)**: $5.09
- **Erosion slope**: +0.038
- **Verbosity slope**: -0.004

The reviewer completed all 6 checkpoints (unlike run 1, where it only
completed 1). However, the reviewer broke the solution entirely from
checkpoint 3 onward (0% pass rate). Checkpoints 1-2 showed partial
functionality (62% and 64%) but still well below the baseline. The
reviewer also stalled at checkpoint 6, producing identical output to
checkpoint 5 (same LOC, same metrics) at minimal cost.

## Cross-Run Comparison

| Metric | Run 1 (Apr 4) | Run 2 (Apr 5) |
|--------|--------------|--------------|
| Baseline mean pass rate | 0.944 | 0.967 |
| Baseline total cost | $2.33 | $2.91 |
| Two-agent mean pass rate | 0.271 (1 cp) | 0.210 (6 cp) |
| Two-agent total cost | $5.10 | $5.09 |
| Reviewer degradation | -68.5 pp (cp1) | -75.7 pp (avg) |

Both runs show the same pattern: the reviewer degrades the solution.
Run 2 confirms this is not a budget artifact, since the reviewer completed
all checkpoints this time. The degradation is a property of the review
interaction, not just budget exhaustion.

## Analysis

1. **Reviewer degradation is consistent.** Across both runs, the reviewer
   lowers pass rates. In run 2, the damage is progressive: checkpoints 1-2
   retain partial functionality, but from checkpoint 3 onward, the reviewer
   introduces breaking changes that zero out all tests.

2. **The reviewer does reduce erosion.** Mean erosion dropped from 0.741
   (baseline) to 0.586 (two-agent), a 15-point improvement. The reviewer
   produces less structurally complex code, but at the cost of correctness.

3. **Budget is not the bottleneck.** Run 1 suggested budget geometry might
   explain the failure. Run 2, where the reviewer completed all checkpoints,
   confirms the problem is the review interaction itself, not budget.

4. **Cost roughly doubles.** The combined cost ($5.09) is 1.75x the baseline
   ($2.91), with no correctness benefit.

## Dolt Records

- Baseline: experiment id=646, total_pass_rate=0.97, total_cost=$2.91
- Two-agent: experiment id=647, total_pass_rate=0.21, total_cost=$5.09

## Conclusion

**REFUTED** for execution_server. The two-agent approach with the default
reviewer prompt at 60/40 split consistently degrades correctness. The reviewer
reduces structural erosion but breaks functional correctness, especially on
later checkpoints where the codebase is larger and more complex. This replicates
the run 1 finding with stronger evidence (full checkpoint coverage).
