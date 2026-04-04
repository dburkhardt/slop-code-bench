# Exp B5: code_search Two-Agent at 60/40 Budget Split

**Hypothesis:** H-coverage baseline coverage across all 20 problems to map threshold boundary. This experiment tests whether a 60/40 implementer/reviewer budget split affects pass rate or quality metrics relative to single-agent baseline on code_search.

**Bead:** sc-hypotheses.286.13

**Verdict:** INCONCLUSIVE (two-agent pass rate degraded vs baseline, but all 5 checkpoints completed)

## Setup

| Parameter | Single-Agent (Baseline) | Two-Agent (60/40) |
|-----------|------------------------|-------------------|
| Agent type | claude_code | two-agent (implementer + reviewer) |
| Model | local-sonnet-4.6 | local-sonnet-4.6 |
| Prompt | default_implementer | default_implementer + default_reviewer |
| Budget | $5.00 | $5.00 |
| Budget split | N/A | 60% implementer / 40% reviewer |
| Problem | code_search | code_search |
| Checkpoints | 5 | 5 |

## Results

### Per-Checkpoint Pass Rates

| Checkpoint | Baseline (single) | Two-Agent (60/40) |
|-----------|-------------------|-------------------|
| 1 | 1.000 | 0.023 |
| 2 | 1.000 | 0.545 |
| 3 | 0.523 | 0.545 |
| 4 | N/A (3 cp only) | 0.545 |
| 5 | N/A (3 cp only) | 0.545 |

**Note:** The baseline run (Dolt id=553) only completed 3 checkpoints. The two-agent run completed all 5.

### Aggregate Metrics

| Metric | Baseline | Two-Agent (60/40) | Delta |
|--------|----------|-------------------|-------|
| Mean pass rate | 0.84 | 0.4409 | -0.3991 |
| Total cost | $0.54 | $4.16 | +$3.62 |
| Erosion slope | 0.0 | 0.0596 | +0.0596 |
| Verbosity slope | N/A | 0.0 | N/A |

### Per-Checkpoint Cost

| Checkpoint | Cost |
|-----------|------|
| 1 | $0.84 |
| 2 | $0.70 |
| 3 | $0.46 |
| 4 | $0.34 |
| 5 | $1.82 |
| **Total** | **$4.16** |

### Per-Checkpoint Erosion and Verbosity

| Checkpoint | Erosion | Verbosity |
|-----------|---------|-----------|
| 1 | 0.0 | 0.0 |
| 2 | 0.0 | 0.0 |
| 3 | 0.0 | 0.0 |
| 4 | 0.0 | 0.0 |
| 5 | 0.298 | 0.0 |

### Token Usage

| Checkpoint | Implementer Tokens | Reviewer Tokens |
|-----------|-------------------|-----------------|
| 1 | 1,042,153 | 789,609 |
| 2 | 1,052,561 | 494,583 |
| 3 | 0 | 840,470 |
| 4 | 44,174 | 515,146 |
| 5 | 2,014,194 | 711,731 |

## Observations

1. The two-agent run at 60/40 completed all 5 checkpoints without exceeding the $5 budget, while the 70/30 run (Dolt id=554, prior experiment) scored 0% pass rate and only cost $0.38. The 60/40 split appears to allow more effective use of the budget.

2. Checkpoint 1 had a very low pass rate (0.023) for the two-agent arm, suggesting the reviewer may have introduced regressions on the first iteration where there was no prior context.

3. Checkpoints 2 through 5 all achieved the same pass rate (0.545), indicating the solution stabilized early and the reviewer's suggestions were incorporated but did not improve pass rates further.

4. Erosion appeared only at checkpoint 5 (0.298), suggesting late-stage complexity growth when the implementer had the largest budget allocation on the final checkpoint.

5. The baseline achieved a higher mean pass rate (0.84 vs 0.44), but this comparison is imperfect because the baseline only completed 3 checkpoints while the two-agent run completed all 5.

6. Checkpoint 3 shows 0 implementer tokens, suggesting the implementer did not make changes and the prior solution carried forward.

## Dolt References

- Baseline experiment: id=553 (single, code_search, local-sonnet-4.6)
- Two-agent 70/30: id=554 (two-agent, code_search, local-sonnet-4.6, 70/30)
- Two-agent 60/40: id=591 (two-agent, code_search, local-sonnet-4.6, 60/40)

## Output Directory

`outputs/two_agent_local-claude-sonnet-4-6_code_search_20260404_152544_20080e7e7207/`
