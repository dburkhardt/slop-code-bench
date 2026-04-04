# Experiment Report: sc-hypotheses.286 — layered_config_synthesizer at 60/40

**Hypothesis**: H-coverage baseline coverage across all 20 problems to map threshold boundary  
**Problem**: layered_config_synthesizer (4 checkpoints)  
**Model**: claude_code_local/local-claude-sonnet-4-6  
**Budget**: $5/arm, 60/40 implementer/reviewer split  
**Date**: 2026-04-04  

## Summary

Both arms performed very poorly on layered_config_synthesizer. The baseline
timed out on checkpoint 1 (620s agent timeout) and completed only 1 of 4
checkpoints with a 4.0% strict pass rate and 0% core pass rate. The two-agent
arm completed 2 of 4 checkpoints before the pipeline's 3600s timeout, with
pass rates of 2.6% (cp1) and 2.0% (cp2). Core pass rate was 0% across all
completed checkpoints in both arms.

**Verdict**: layered_config_synthesizer is beyond the model's capability at
this budget level. Neither arm produced meaningful results.

## Baseline (Single-Agent) Results

| Metric | Value |
|--------|-------|
| Checkpoints completed | 1 of 4 (timeout) |
| cp1 strict pass rate | 0.040 |
| cp1 core pass rate | 0.000 |
| cp1 erosion | 0.000 |
| cp1 verbosity | 0.052 |
| Total cost | $0.35 |
| Failure mode | Agent timeout at 620s on cp1 |

The agent spent its entire time budget on checkpoint 1 and still failed to
produce a solution that passes core tests. Checkpoints 2-4 were skipped.

## Two-Agent Results

| Checkpoint | Pass Rate | Core Rate | Erosion | Verbosity | Cost |
|-----------|-----------|-----------|---------|-----------|------|
| cp1 | 0.026 | 0.000 | 0.481 | 0.027 | $2.15 |
| cp2 | 0.020 | 0.000 | 0.321 | 0.000 | $0.98 |

- **Checkpoints completed**: 2 of 4 (pipeline timeout at 3600s)
- **Total cost**: $3.13
- **Budget exceeded**: No (but timed out)

The two-agent approach consumed $2.15 on cp1 alone (implementer + reviewer),
leaving only $1.87 for the remaining checkpoints. cp2 completed but the
pipeline timed out before cp3-4 could be processed. The reviewer on cp1
actually lowered the pass rate from the implementer's 4.0% to 2.6%.

## Implementer-Only Checkpoint Results

For reference, the implementer's standalone results across all 4 checkpoints:

| Checkpoint | Pass Rate | Core Rate | Cost | LOC | State |
|-----------|-----------|-----------|------|-----|-------|
| cp1 | 0.040 | 0.000 | $0.98 | 259 | ran |
| cp2 | 0.038 | 0.000 | $0.54 | 352 | ran |
| cp3 | 0.026 | 0.000 | $0.27 | 352 | error |
| cp4 | 0.020 | 0.000 | $0.25 | 356 | ran |

Pass rates decline monotonically from 4.0% to 2.0% across checkpoints.
LOC grows from 259 to 356 but no core tests pass at any checkpoint.

## Analysis

1. **Problem difficulty**. layered_config_synthesizer requires complex
   multi-layer configuration merging logic. The model fails to produce
   solutions that pass even basic core tests, regardless of the agent
   configuration. This places the problem below the capability threshold
   for Sonnet 4.6 at $5 budget.

2. **Review overhead is counterproductive at this pass rate**. When the
   base implementation fails all core tests, the reviewer cannot
   meaningfully improve it. The reviewer on cp1 consumed $1.19 of
   additional budget and lowered the pass rate from 4.0% to 2.6%.

3. **Timeout sensitivity**. The baseline's 620s agent timeout on cp1
   and the pipeline's 3600s overall timeout both indicate that the
   problem requires more compute time than allocated. The model
   may be stuck in retry loops.

## Dolt Records

- Baseline: experiment id=592, total_pass_rate=0.04, total_cost=$0.35
- Two-agent: experiment id=593, total_pass_rate=0.02, total_cost=$3.13

## Recommendations

- layered_config_synthesizer should be flagged as a "hard" problem for
  coverage mapping purposes.
- Consider higher budget ($10+) or a more capable model for this problem.
- The 0% core pass rate across all checkpoints suggests a fundamental
  capability gap, not a budget issue.
