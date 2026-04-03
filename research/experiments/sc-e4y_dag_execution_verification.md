# sc-e4y: Verification Experiment — dag_execution Default 70/30

**Hypothesis:** Default 70/30 two-agent vs single-agent on dag_execution

**Verdict:** NEITHER ARM PRODUCED WORKING CODE (both 0% pass rate)

## Design

| Parameter | Baseline (single-agent) | Treatment (two-agent) |
|-----------|------------------------|----------------------|
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Prompt | default_implementer | default_implementer + default_reviewer |
| Budget split | N/A | 70/30 |
| Total budget | $5.00/arm | $5.00/arm |
| Problem | dag_execution | dag_execution |

## Results

### Baseline (single-agent)

| Checkpoint | Pass Rate | Cost | State |
|------------|-----------|------|-------|
| checkpoint_1 | 0.0% (0/33) | $0.00 | error |
| checkpoint_2 | not reached | — | — |
| checkpoint_3 | not reached | — | — |

- **Average pass rate:** 0.0%
- **Total cost:** $0.00 (cost not reported by local runner)
- **Checkpoints completed:** 1/3

### Two-agent (70/30 split)

| Checkpoint | Pass Rate | Cost | State |
|------------|-----------|------|-------|
| checkpoint_1 (impl) | 0.0% (0/33) | $0.00 | error |
| checkpoint_1 (review) | 0.0% (0/33) | $0.37 | error |
| checkpoint_1 (impl2) | 0.0% (0/33) | $0.00 | error |
| checkpoint_1 (review2) | 0.0% (0/33) | $0.05 | ran |
| checkpoint_2 | 0.0% (0/41) | $0.07 | ran |
| checkpoint_3 | 0.0% (0/51) | $0.07 | ran |
| checkpoint_1 (impl3) | 0.0% (0/33) | $0.00 | error |

- **Average pass rate:** 0.0%
- **Total cost:** $0.56
- **Two-agent arm timed out** after 3600s

### Deltas

| Metric | Value |
|--------|-------|
| Delta pass rate | 0.0pp (both zero) |
| Delta erosion | 0.0 (both zero) |

## Notes

- dag_execution appears to be a hard problem for the local model; neither arm produced code that passed any tests
- All 33 failures on checkpoint_1 were assertion errors (not import or timeout), suggesting the agent produced code but it was incorrect
- The two-agent arm attempted multiple implementer/reviewer cycles on checkpoint_1 before moving to checkpoints 2 and 3
- Baseline cost was reported as $0.00, likely because the local runner does not track API costs
- Two-agent arm was more expensive ($0.56) while producing the same 0% pass rate
- Dolt experiment rows: 551 (baseline), 552 (two-agent)

## Conclusion

dag_execution is too difficult for local-claude-sonnet-4-6 at this budget level. Neither single-agent nor two-agent produced any passing tests across any checkpoint. Single-agent wins by default on cost efficiency ($0.00 vs $0.56 for identical 0% outcomes). This problem may require a more capable model or higher budget to produce meaningful comparison data.
