# Experiment Report: sc-hypotheses.286 — execution_server at 60/40

**Hypothesis**: H-coverage baseline coverage across all 20 problems to map threshold boundary  
**Problem**: execution_server (6 checkpoints)  
**Model**: claude_code_local/local-claude-sonnet-4-6  
**Budget**: $5/arm, 60/40 implementer/reviewer split  
**Date**: 2026-04-04  

## Summary

The two-agent arm exceeded its $5 budget after completing only 1 of 6
checkpoints. The reviewer consumed the entire remaining budget on
checkpoint 1 and degraded the pass rate from 0.956 (implementer-only)
to 0.271. The single-agent baseline completed all 6 checkpoints within
budget at $2.33 total, averaging 94.4% pass rate.

**Verdict**: INCONCLUSIVE for the two-agent comparison. The 60/40 split
at $5 total is insufficient for execution_server's review overhead. The
baseline data is valid and complete.

## Baseline (Single-Agent) Results

| Checkpoint | Pass Rate | Core Rate | Erosion | Verbosity | Cost | LOC |
|-----------|-----------|-----------|---------|-----------|------|-----|
| cp1 | 0.933 | 0.947 | 0.759 | 0.000 | $0.12 | 191 |
| cp2 | 0.948 | 1.000 | 0.670 | 0.000 | $0.28 | 230 |
| cp3 | 0.922 | 0.812 | 0.586 | 0.000 | $0.55 | 396 |
| cp4 | 0.947 | 1.000 | 0.664 | 0.000 | $0.49 | 577 |
| cp5 | 0.957 | 1.000 | 0.666 | 0.000 | $0.39 | 688 |
| cp6 | 0.957 | 0.960 | 0.649 | 0.012 | $0.50 | 966 |

- **Mean pass rate**: 0.944
- **Total cost**: $2.33
- **Erosion slope**: -0.014 (slightly improving)
- **Verbosity slope**: 0.002 (near-zero)

The baseline shows strong, stable performance. Pass rates stay above 0.92
across all checkpoints. Erosion decreases slightly over time, and verbosity
remains near zero until a small uptick at checkpoint 6. LOC grows from 191
to 966 as the problem's requirements expand.

## Two-Agent Results

| Metric | Value |
|--------|-------|
| Checkpoints completed | 1 of 6 |
| Budget exceeded | Yes ($5.10 spent) |
| cp1 pass rate | 0.271 |
| cp1 erosion | 0.423 |
| cp1 verbosity | 0.012 |
| Implementer tokens (cp1) | 7,059,135 |
| Reviewer tokens (cp1) | 2,481,102 |

The reviewer consumed approximately $2 of budget on checkpoint 1 alone
(40% of $5). Together with the implementer's full run across all 6
checkpoints ($3.06), total spend reached $5.10, exceeding the $5 cap.

The reviewer degraded checkpoint 1 pass rate from 0.956 to 0.271, a
68-percentage-point drop. This suggests the reviewer introduced
regressions rather than improvements.

## Analysis

Three factors contributed to the failure:

1. **Budget geometry mismatch**. The implementer ran all 6 checkpoints
   first at $3.06, leaving only ~$1.94 for the reviewer. At 40% of $5,
   the reviewer's nominal allocation was $2.00, but the implementer
   already consumed 61% of the total budget. A per-checkpoint budget
   enforcement would prevent this.

2. **Reviewer degradation**. Even on the one checkpoint the reviewer
   completed, it lowered the pass rate from 0.956 to 0.271. The reviewer
   prompt may not be well-suited for execution_server's complexity, or
   the review cycle may be introducing conflicting changes.

3. **execution_server is a large problem**. With 6 checkpoints growing
   from 191 to 966 LOC, the token overhead per review cycle is
   substantial. The 60/40 split leaves insufficient review budget for
   problems of this size.

## Dolt Records

- Baseline: experiment id=585, total_pass_rate=0.94, total_cost=$2.33
- Two-agent: experiment id=586, total_pass_rate=0.27, total_cost=$5.10

## Recommendations

- Consider a higher total budget ($10+) for 6-checkpoint problems with
  a two-agent approach.
- Investigate per-checkpoint budget enforcement instead of aggregate caps.
- The reviewer degradation on cp1 warrants a closer look at the default
  reviewer prompt for execution_server.
