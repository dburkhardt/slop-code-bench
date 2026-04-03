# sc-y7u: Verification Experiment — eve_industry Default 70/30

**Hypothesis:** Verification: default 70/30 two-agent vs single-agent on eve_industry

**Verdict:** SINGLE-AGENT WINS (incomplete data, but directionally clear)

## Design

| Parameter | Baseline (single-agent) | Treatment (two-agent) |
|-----------|------------------------|----------------------|
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Prompt | default_implementer | default_implementer + default_reviewer |
| Budget split | N/A | 70/30 |
| Total budget | $5.00/arm | $5.00/arm |
| Problem | eve_industry | eve_industry |

## Results

### Baseline (single-agent)

| Checkpoint | Pass Rate | Cost | Erosion | Verbosity |
|------------|-----------|------|---------|-----------|
| checkpoint_1 | 100.0% | $0.44 | 0.473 | 0.0% |
| checkpoint_2 | 45.5% (error) | $0.32 | 0.473 | 0.0% |
| checkpoint_3-6 | not reached (timeout) | — | — | — |

- **Average pass rate:** 72.73%
- **Total cost:** $0.75
- **Checkpoints completed:** 2/6

### Two-agent (70/30 split)

| Checkpoint | Pass Rate | Cost | Erosion | Verbosity |
|------------|-----------|------|---------|-----------|
| checkpoint_1 | 45.5% (merged) | $1.76 | 0.876 | 7.4% |
| checkpoint_2+ | not reached (template error + timeout) | — | — | — |

- **Average pass rate:** 45.5%
- **Total cost:** $1.76
- **Checkpoints completed:** 1/6

### Deltas

| Metric | Value |
|--------|-------|
| Delta pass rate | -27.3pp (two-agent worse) |
| Delta cost | +$1.01 (two-agent more expensive) |
| Cost per pass-rate point (baseline) | $0.01/pp |
| Cost per pass-rate point (two-agent) | $0.04/pp |

## Notes

- eve_industry is a domain-heavy problem (EVE Online industry calculator) with complex data file parsing and business logic
- Baseline achieved 100% on checkpoint_1 but timed out on checkpoint_2 without modifying its solution (0 lines changed)
- Two-agent implementer completed 2 checkpoints, reviewer completed 2 checkpoints, but assembly stalled after cp1 due to a Jinja2 template syntax error in the reviewer prompt for subsequent checkpoints
- The two-agent arm's higher erosion (0.876 vs 0.473) and nonzero verbosity (7.4%) suggest the reviewer pass introduced structural degradation
- Dolt connection was lost during the original pipeline run; results were manually re-inserted as experiment rows 533 (baseline) and 534 (two-agent)

## Conclusion

Single-agent outperforms two-agent on eve_industry at default 70/30 split, both in pass rate (72.7% vs 45.5%) and cost efficiency ($0.01/pp vs $0.04/pp). The two-agent arm also showed higher structural erosion. However, both arms failed to complete more than 2 of 6 checkpoints, limiting the strength of this conclusion. The template error in the reviewer prompt contributed to the two-agent arm's early termination.
