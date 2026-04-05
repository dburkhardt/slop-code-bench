# Experiment Report: sc-hypotheses.286 — dynamic_config_service_api (Run 3)

**Hypothesis**: H-coverage baseline coverage across all 20 problems to map threshold boundary  
**Problem**: dynamic_config_service_api (4 checkpoints, Hard difficulty)  
**Model**: claude_code_local/local-sonnet-4.6  
**Budget**: $5/arm, 60/40 implementer/reviewer split  
**Date**: 2026-04-05  

## Summary

Both arms failed in this run. The baseline agent produced a minimal stub
(61 LOC, 1 step) on checkpoint 1, resulting in 0% pass rate across all 47
tests. The two-agent arm's reviewer managed 76.6% pass on checkpoint 1
(36/47 tests) but timed out before completing checkpoint 2, and the overall
pipeline hit its 3600s timeout. No data was inserted to Dolt from this run.

**Verdict**: INCONCLUSIVE. Neither arm completed the problem. Prior runs
(stored in Dolt) achieved 64% single-agent and 85% two-agent pass rates
for this problem, suggesting the failures are stochastic rather than
systematic.

## Baseline (Single-Agent) Results

| Checkpoint | Pass Rate | Core Rate | Erosion | Verbosity | Cost | LOC | Steps |
|-----------|-----------|-----------|---------|-----------|------|-----|-------|
| cp1 | 0.000 | 0.000 | 0.000 | 0.000 | $0.04 | 61 | 1 |
| cp2-4 | not reached | — | — | — | — | — | — |

- **Total cost**: $0.04
- **State**: error (all 47 tests produced "other_errors")

The baseline agent took only 1 step and produced a 61-line stub with 3
functions and 1 class. The cost ($0.04) indicates the agent barely engaged
with the problem. All 47 tests failed, likely due to import errors or
missing endpoints.

## Two-Agent Results

The two-agent arm ran the implementer first (using baseline output), then
passed the result to the reviewer for each checkpoint.

### Implementer Phase (same as baseline)
- Checkpoint 1: 0% pass, 61 LOC, $0.04

### Reviewer Phase
| Checkpoint | Pass Rate | Core Rate | Erosion | Verbosity | Cost | LOC | Steps |
|-----------|-----------|-----------|---------|-----------|------|-----|-------|
| cp1 (run 1) | 0.766 | 0.769 | 0.551 | 0.000 | $0.59 | 529 | 34 |
| cp1 (run 2) | 0.404 | 0.154 | 0.627 | 0.020 | $0.25 | 492 | 22 |
| cp2 | 0.237 | 0.158 | 0.627 | 0.020 | $0.14 | 492 | 7 |
| cp1 (run 3) | 0.000 | 0.000 | — | — | $0.06 | 0 | 2 |
| cp1 (run 4) | 0.000 | 0.000 | — | — | $0.06 | 0 | 2 |

The reviewer made multiple attempts across checkpoints. The best single
attempt achieved 76.6% pass rate on checkpoint 1, expanding the 61-line
stub to 529 LOC with 24 functions. However, later attempts degraded or
timed out. The pipeline ultimately exceeded its 3600s wall-clock limit.

Erosion was consistently high (0.55 to 0.63) across non-zero-LOC checkpoints,
with cc_max reaching 24. Verbosity remained near zero.

## Cost Analysis

| Arm | Total Cost | Checkpoints Completed |
|-----|-----------|----------------------|
| Baseline | $0.04 | 0 (error on cp1) |
| Two-agent | ~$1.14 (reviewer only) | 0 (reviewer timed out) |

The $5 budget was not exhausted. The failure mode was wall-clock timeout
(3600s for two-agent, 600s per checkpoint for the baseline agent), not
budget exhaustion.

## Comparison with Prior Runs

Prior runs for this problem (from Dolt):
- **Single-agent (prior)**: 64% total pass rate, $4.31 cost
- **Two-agent (prior)**: 85% total pass rate, $7.94 cost

The prior two-agent run exceeded the $5 budget but achieved a 21-point
improvement over single-agent. This run's failures appear to be stochastic
agent misbehavior (1-step exits, timeouts) rather than a systematic problem
with the experimental configuration.

## Conclusion

**INCONCLUSIVE**. The run produced no usable comparative data because both
arms failed due to agent-level errors (minimal engagement on baseline,
timeouts on reviewer). The prior successful runs suggest this problem is
tractable. Rerunning with increased per-checkpoint timeouts or retrying
may yield results.
