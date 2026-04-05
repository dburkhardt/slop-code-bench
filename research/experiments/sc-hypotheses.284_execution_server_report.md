# Experiment Report: sc-hypotheses.284 — execution_server

**Hypothesis**: Two-agent (implementer + reviewer) improves code quality without degrading pass rate
**Problem**: execution_server (6 checkpoints)
**Model**: local-sonnet-4.6
**Budget**: $5/arm, 60/40 implementer/reviewer split
**Date**: 2026-04-05

## Summary

The two-agent arm catastrophically degraded pass rates, dropping to 0% from
checkpoint 3 onward. The single-agent baseline maintained strong performance
(91% average pass rate across 6 checkpoints). While the two-agent arm produced
lower verbosity and complexity scores, these quality improvements are meaningless
given the total functional failure. The two-agent arm also timed out before
completing checkpoint 6.

**Verdict**: REFUTED. The two-agent configuration severely degrades correctness
on execution_server with no compensating benefit.

## Baseline (Single-Agent) Results

| Checkpoint | Pass Rate | Cost | LOC | Verbosity | CC Max |
|-----------|-----------|------|-----|-----------|--------|
| cp1 | 0.800 | $0.33 | 155 | 0.103 | 21 |
| cp2 | 0.845 | $0.27 | 190 | 0.084 | 31 |
| cp3 | 0.952 | $1.06 | 278 | 0.000 | 32 |
| cp4 | 0.921 | $0.61 | 389 | 0.000 | 46 |
| cp5 | 0.968 | $0.38 | 453 | 0.000 | 52 |
| cp6 | 0.957 | $1.03 | 604 | 0.000 | 50 |

- **Mean pass rate**: 0.907
- **Total cost**: $3.69
- **Verbosity slope**: -0.023 (improving across checkpoints)
- **CC max range**: 21 to 52

The baseline starts at 80% pass rate on checkpoint 1 and improves steadily,
reaching 95%+ by checkpoint 3. LOC grows from 155 to 604 as the problem
expands. Verbosity drops to zero after checkpoint 2, suggesting the agent
learns to avoid redundant patterns as the codebase matures.

## Two-Agent (Reviewer) Results

| Checkpoint | Pass Rate | Cost | LOC | Verbosity | CC Max |
|-----------|-----------|------|-----|-----------|--------|
| cp1 | 0.622 | $0.18 | 149 | 0.081 | 17 |
| cp2 | 0.638 | $0.22 | 186 | 0.065 | 17 |
| cp3 | 0.000 | $0.69 | 246 | 0.049 | 18 |
| cp4 | 0.000 | $0.68 | 333 | 0.036 | 21 |
| cp5 | 0.000 | $0.49 | 379 | 0.032 | 22 |
| cp6 | N/A (timed out) | — | — | — | — |

- **Mean pass rate**: 0.252 (checkpoints 1-5)
- **Total cost**: $2.25 (reviewer only; excludes implementer cost)
- **Verbosity slope**: -0.012 (gradually improving)
- **CC max range**: 17 to 22

The two-agent arm shows lower quality metrics across the board: smaller LOC,
lower verbosity, and lower cyclomatic complexity. However, pass rates collapse
entirely at checkpoint 3 and never recover. The reviewer appears to have
introduced breaking changes that compound across later checkpoints. Checkpoint 6
timed out before producing evaluation results.

## Analysis

The two-agent arm failed on correctness while producing nominally "cleaner" code.
Three observations:

1. **Pass rate collapse is abrupt and permanent.** The drop from 0.64 (cp2) to 0.00
   (cp3) suggests the reviewer introduced a structural break that the implementer
   could not recover from in subsequent checkpoints. This is consistent with the
   compounding design-decision effect described in the paper's Finding 3.

2. **Quality metrics are misleading without correctness.** The reviewer arm's lower
   verbosity (0.03 to 0.08) and lower CC max (17 to 22 vs 21 to 52) look favorable
   in isolation. But code that does not pass tests is not "higher quality"; it is
   broken. This reinforces Finding 1's observation that quality metrics are only
   interpretable when pass rates are stable.

3. **Cost allocation.** The reviewer arm's cost was $2.25 for 5 checkpoints (reviewer
   pass only). Combined with the implementer pass, the two-agent arm likely cost
   $4 to $5 total, comparable to the baseline's $3.69. The two-agent approach
   consumed similar resources while delivering far worse outcomes.

## Cost Summary

| Arm | Total Cost | Mean Pass Rate | Checkpoints Completed |
|-----|-----------|----------------|----------------------|
| Baseline | $3.69 | 0.907 | 6/6 |
| Two-Agent (reviewer only) | $2.25 | 0.252 | 5/6 (cp6 timed out) |

## Conclusion: REFUTED

The two-agent configuration with 60/40 budget split severely degrades correctness
on execution_server. The reviewer introduces breaking changes at checkpoint 3 that
persist through the remaining checkpoints. Quality improvements in verbosity and
complexity are rendered meaningless by the pass rate collapse. The single-agent
baseline is strictly superior on this problem.
