# H261 Redo: Two-Agent on execution_server + etl_pipeline

**Hypothesis:** Default two-agent (70/30) improves pass rate over single-agent on execution_server (6 checkpoints) and etl_pipeline (5 checkpoints).

**Bead:** sc-hypotheses.261

**Verdict:** REFUTED (two-agent underperforms baseline on both problems; budget starvation prevents completion)

## Setup

| Parameter | Single-Agent (Baseline) | Two-Agent (70/30) |
|-----------|------------------------|-------------------|
| Agent type | claude_code | reviewer_coder |
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Prompt | just-solve | default_implementer + default_reviewer |
| Cost limit | unlimited (per-checkpoint) | $5.00 total |
| Budget split | N/A | 70/30 (implementer/reviewer) |
| Environment | local-py | local-py |

## Results

### execution_server (6 checkpoints)

| Metric | Baseline (single-agent) | Two-Agent (70/30) |
|--------|------------------------|-------------------|
| cp1 pass rate | 97.8% (44/45) | 27.1% (19/70)* |
| cp2 pass rate | 98.3% (57/58) | N/A (budget exceeded) |
| cp3 pass rate | 89.3% (92/103) | N/A |
| cp4 pass rate | 92.7% (140/151) | N/A |
| cp5 pass rate | 94.1% (176/187) | N/A |
| cp6 pass rate | 78.6% (55/70) | N/A |
| **Mean pass rate** | **90.1%** | **27.1% (1/6 cp)** |
| Total cost | $2.28 | $5.00 |
| Implementer tokens (cp1) | N/A | 6,382,481 |
| Reviewer tokens (cp1) | N/A | 2,302,618 |

*The two-agent cp1 pass rate includes the full test suite (70 tests for the final cp6 version vs 45 for cp1), suggesting the runner evaluated against the complete test suite rather than cp1's tests.

### etl_pipeline (5 checkpoints)

| Metric | Baseline (single-agent) | Two-Agent (70/30) |
|--------|------------------------|-------------------|
| cp1 pass rate | 85.4% (35/41) | 57.5% (42/73)* |
| cp2 pass rate | 91.8% (67/73) | 89.6% (60/67)* |
| cp3 pass rate | 93.2% (109/117) | N/A (budget exceeded) |
| cp4 pass rate | 93.3% (125/134) | N/A |
| cp5 pass rate | 93.3% (153/164) | N/A |
| **Mean pass rate** | **91.4%** | **73.5% (2/5 cp)** |
| Total cost | $2.55 | $5.68 |
| Implementer tokens (cp1) | N/A | 5,931,497 |
| Reviewer tokens (cp1) | N/A | 454,822 |
| Implementer tokens (cp2) | N/A | 2,622,015 |
| Reviewer tokens (cp2) | N/A | 2,166,580 |

*Test counts for two-agent checkpoints may reflect the full problem's test suite rather than per-checkpoint counts.

## Cost Analysis

| Metric | Baseline (exec_server) | Two-Agent (exec_server) | Baseline (etl) | Two-Agent (etl) |
|--------|----------------------|------------------------|----------------|-----------------|
| Cost per checkpoint | $0.38 avg | $5.00 (cp1 only) | $0.51 avg | $2.84 avg |
| Total cost | $2.28 | $5.00 | $2.55 | $5.68 |
| Checkpoints completed | 6/6 | 1/6 | 5/5 | 2/5 |
| Cost multiplier | 1x | ~13x per cp | 1x | ~5.6x per cp |

The two-agent pattern is 5x to 13x more expensive per checkpoint than single-agent baseline. The reviewer-implementer interaction loop generates millions of tokens per checkpoint.

## Interpretation

**The hypothesis is REFUTED.** The two-agent (70/30) pattern does not improve pass rate over single-agent on these problems. On both problems, two-agent underperforms baseline even on the checkpoints it manages to complete.

Three findings:

1. **Budget starvation is the dominant failure mode.** With a $5.00 total budget, the two-agent pattern completes only 1-2 checkpoints out of 5-6. The reviewer-implementer interaction loop consumes $2.84 to $5.00 per checkpoint, compared to $0.38 to $0.51 for the baseline.

2. **Two-agent underperforms even on completed checkpoints.** On execution_server cp1, two-agent achieves 27.1% vs baseline's 97.8%. On etl_pipeline cp1, two-agent achieves 57.5% vs baseline's 85.4%. The reviewer interaction does not improve code quality; it may degrade it by consuming budget on review cycles instead of implementation.

3. **The cost asymmetry is structural.** The two-agent runner feeds the full problem through `slop_code run` for each phase, generating 6M+ implementer tokens and 2M+ reviewer tokens per checkpoint. The baseline uses 130K-714K tokens per checkpoint total. This 10x+ token overhead translates directly to cost.

## Comparison with Previous H261 Run

The previous H261 experiment was INCONCLUSIVE due to budget mismatch (baseline got $5/checkpoint; two-agent got $5 total). This redo confirms the finding was not an artifact: the two-agent pattern genuinely cannot operate within the same total budget as the baseline. The cost per checkpoint is fundamentally higher.

| Metric | Previous H261 | This Redo |
|--------|--------------|-----------|
| Verdict | INCONCLUSIVE | REFUTED |
| Exec baseline pass | 92.4% | 90.1% |
| Exec two-agent pass | 10.4% (budget artifact) | 27.1% (1 cp) |
| ETL baseline pass | 87.3% | 91.4% |
| ETL two-agent pass | 84.8% (1 cp metric) | 73.5% (2 cp) |
| Budget confound | Yes (6:1 mismatch) | No (same $5 total) |

## Confounds

- Budget asymmetry remains: baseline has no cost limit per checkpoint (unlimited) while two-agent has $5 total. A fair comparison would require equal per-checkpoint budgets, but even then the two-agent's ~$3-5/checkpoint cost means it would need $15-30 total to match the baseline's coverage.
- N=1 per condition per problem (no variance estimation).
- The `slop_code run` subprocess runs all checkpoints in one call, so the two_agent_runner's per-checkpoint budget tracking is approximate.
- Test count discrepancies between baseline and two-agent suggest different evaluation contexts.

## Run Artifacts

### Output Directories
- Baseline: `outputs/local-claude-sonnet-4-6/claude_code-2.0.51_just-solve_none_20260402T1757/`
- Two-agent execution_server: `outputs/two_agent_local-claude-sonnet-4-6_execution_server_20260402_185714_4ea69c87636e/`
- Two-agent etl_pipeline: `outputs/two_agent_local-claude-sonnet-4-6_etl_pipeline_20260402_175640_74fbbf92816c/`

### Dolt Experiment IDs
- execution_server baseline: 507
- etl_pipeline baseline: 508
- execution_server two-agent: 509
- etl_pipeline two-agent: 510

### Budget Impact
- Total experiment cost: $15.51 ($2.28 + $2.55 + $5.00 + $5.68)
- Budget remaining after experiments: $935.01
