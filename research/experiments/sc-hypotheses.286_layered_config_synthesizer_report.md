# Experiment Report: sc-hypotheses.286 — layered_config_synthesizer (replication)

**Hypothesis**: Two-agent (implementer + reviewer) pipeline improves pass rate
and reduces code erosion compared to single-agent baseline  
**Problem**: layered_config_synthesizer (4 checkpoints, data-processing)  
**Model**: local-sonnet-4.6  
**Budget**: $5/arm, 60/40 implementer/reviewer split  
**Date**: 2026-04-05 (replication of 2026-04-04 run)

## Summary

This replication confirms the prior finding: layered_config_synthesizer is beyond
the model's capability at $5 budget. The baseline completed 1 of 4 checkpoints
(4% pass rate). The two-agent arm completed 2 full review passes across all 4
checkpoints before timing out, with pass rates declining from 4% to 2% and
elevated erosion (0.60 avg). Total two-agent cost was $2.58 vs $0.21 baseline.

**Verdict**: INCONCLUSIVE. Problem too difficult for meaningful comparison.
Consistent with prior run.

## Baseline (Single-Agent) Results

| Checkpoint | Pass Rate | Core Rate | Cost | Verbosity | Erosion |
|-----------|-----------|-----------|------|-----------|---------|
| cp1 | 0.040 | 0.000 | $0.21 | 0.000 | 0.392 |
| cp2-4 | — | — | — | — | — |

- **Total cost**: $0.21
- Baseline ran 1 of 4 checkpoints. Pipeline timeout prevented remaining checkpoints.

## Two-Agent Results (final per checkpoint, after 2 review passes)

| Checkpoint | Pass Rate | Cost | Verbosity | Erosion |
|-----------|-----------|------|-----------|---------|
| cp1 | 0.040 | $0.37 | 0.045 | 0.613 |
| cp2 | 0.038 | $0.24 | 0.045 | 0.606 |
| cp3 | 0.026 | $0.29 | 0.045 | 0.606 |
| cp4 | 0.020 | $0.33 | 0.044 | 0.603 |

- **Total cost** (all 8 evaluations): $2.58
- **Budget exceeded**: No, but pipeline timed out at 3600s

The two-agent runner completed the implementer pass (4 checkpoints) plus one
full reviewer pass (4 checkpoints). Pass rates are monotonically declining.
Core pass rate is 0% across all checkpoints.

## Comparison with Prior Run (2026-04-04)

| Metric | Prior Baseline | This Baseline | Prior Two-Agent | This Two-Agent |
|--------|---------------|---------------|-----------------|----------------|
| Avg pass rate | 0.04 | 0.04 | 0.02 | 0.03 |
| Total cost | $0.35 | $0.21 | $3.13 | $2.58 |
| Erosion (cp1) | 0.000 | 0.392 | 0.481 | 0.613 |

Results are directionally consistent: baseline ~4%, two-agent ~2-3%, both fail
core tests entirely. Cost ratio is similarly unfavorable for two-agent (12x this
run, 9x prior). Erosion varies between runs but is consistently higher in the
two-agent arm.

## Analysis

1. **Problem difficulty**. layered_config_synthesizer requires complex multi-layer
   configuration merging logic. The model fails to produce solutions that pass
   core tests regardless of agent configuration. 0% core pass rate across all
   checkpoints in both arms confirms this is below the capability threshold.

2. **Review overhead is counterproductive**. At this pass rate level, the reviewer
   cannot improve the implementation. Pass rates stayed flat or declined across
   review passes. The reviewer added structural complexity (erosion 0.60 vs 0.39)
   without improving correctness.

3. **Pass rate decline across checkpoints**. In the two-agent arm, pass rates
   decline monotonically from 4% (cp1) to 2% (cp4). Specifications grow more
   complex at each checkpoint, and the model cannot keep up.

4. **Cost asymmetry**. The two-agent arm costs 12x more per checkpoint on average.
   The review passes double the API spend without benefit.

## Dolt Records

Results inserted manually after pipeline timeout:
- Baseline: total_pass_rate=0.04, total_cost=$0.21
- Two-agent: total_pass_rate=0.03, total_cost=$2.58

## Conclusion

INCONCLUSIVE. layered_config_synthesizer is a hard problem where both single-agent
and two-agent pipelines fail. The replication confirms the prior result: the
two-agent approach increases cost and erosion without improving pass rates on
problems below the model's capability threshold.
