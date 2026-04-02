# H260: Minimal Reviewer (90/10) Captures Majority of Two-Agent Benefit

**Hypothesis:** A 90/10 budget split (minimal reviewer) captures at least 60% of the pass-rate improvement of 70/30 two-agent over single-agent, at substantially lower cost, because the reviewer's value comes from providing any feedback loop rather than from extensive review.

**Bead:** sc-hypotheses.260

**Testable claim:** 90/10 split achieves pass rates that are at least 60% of the way from single-agent to 70/30 two-agent, on file_backup and database_migration.

**Predicted outcome:** file_backup: 90/10 achieves 50% to 70% pass rate (vs 13% single, 76% two-agent 70/30). database_migration: 90/10 achieves 25% to 40% (vs 0% single, 46% two-agent 70/30). Cost per problem 20% to 40% lower than 70/30.

## Design

Three arms per problem. Baseline and 70/30 arms reuse existing run data where available.

| Parameter | Baseline (single-agent) | 70/30 (existing) | 90/10 (treatment) |
|-----------|------------------------|-------------------|-------------------|
| Agent type | claude_code | reviewer_coder | reviewer_coder |
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Implementer prompt | just-solve | just-solve | just-solve |
| Reviewer prompt | N/A | default_reviewer.jinja | default_reviewer.jinja |
| Budget split | N/A | 70/30 | 90/10 |
| Review cycles | N/A | 3 | 3 |
| Coder turns/batch | N/A | 10 | 10 |
| Step limit | 100/checkpoint | 100/checkpoint | 100/checkpoint |
| Budget | $5.00 | $5.00 | $5.00 |
| Thinking | none | none | none |

**Problems:** file_backup, database_migration

## Reviewer prompt

The treatment arm uses `configs/prompts/default_reviewer.jinja`, which targets structural problems, slop, unnecessary complexity, and code duplication. The default reviewer was chosen over the anti-slop or architecture reviewer to isolate the budget-split variable. Using the same reviewer prompt as the 70/30 reference arm ensures the only difference is how much budget the reviewer receives.

## Execution

### Via experiment pipeline (runs baseline + treatment per problem)

```bash
# file_backup
python research/runner/experiment_pipeline.py \
  --problem file_backup \
  --model local-claude-sonnet-4-6 \
  --budget 5.0 \
  --budget-split 90 \
  --reviewer-prompt configs/prompts/default_reviewer.jinja \
  --hypothesis-id sc-hypotheses.260

# database_migration
python research/runner/experiment_pipeline.py \
  --problem database_migration \
  --model local-claude-sonnet-4-6 \
  --budget 5.0 \
  --budget-split 90 \
  --reviewer-prompt configs/prompts/default_reviewer.jinja \
  --hypothesis-id sc-hypotheses.260
```

### Via individual run configs

```bash
# Baseline
slop-code run --config configs/runs/h260_file_backup_baseline.yaml
slop-code run --config configs/runs/h260_database_migration_baseline.yaml

# Treatment (90/10)
slop-code run --config configs/runs/h260_file_backup_90_10.yaml
slop-code run --config configs/runs/h260_database_migration_90_10.yaml
```

## Primary metrics

| Metric | How measured | Success criterion |
|--------|------------|-------------------|
| Pass rate | Per-checkpoint core pass rates | 90/10 achieves >= 60% of (70/30 - baseline) improvement |
| Cost | Total USD per arm | 90/10 costs 20% to 40% less than 70/30 |

## Secondary metrics

| Metric | How measured | Purpose |
|--------|------------|---------|
| Verbosity | AST-Grep Flagged Lines + Clone Lines / LOC | Does minimal review still reduce slop? |
| Structural erosion | mass.high_cc_pct slope | Does minimal review affect complexity? |
| Reviewer token usage | Per-checkpoint reviewer tokens | Confirms reviewer was budget-constrained |

## Analysis plan

1. Compute per-checkpoint pass rates for all three arms on both problems.
2. For each problem, calculate the 70/30 improvement over baseline: `delta_70_30 = pass_rate_70_30 - pass_rate_baseline`.
3. Calculate 90/10 improvement: `delta_90_10 = pass_rate_90_10 - pass_rate_baseline`.
4. Compute capture ratio: `delta_90_10 / delta_70_30`. If >= 0.60, the hypothesis is supported.
5. Compare total cost between 90/10 and 70/30 arms.
6. Report verbosity and erosion slopes as secondary observations.

## Success criteria

The hypothesis is **supported** if:
- On both problems, 90/10 captures >= 60% of the 70/30 improvement over baseline
- 90/10 costs at least 20% less than 70/30

## Confounds and controls

- N=1 per condition per problem. No variance estimation without repeated runs.
- 70/30 reference data may come from a different run date. Model behavior can drift between runs.
- At 10% budget, the reviewer may not have enough tokens to complete a meaningful review. If reviewer_suggestion_chars is 0, the feedback loop was never established.
- Both arms use the same reviewer prompt (default_reviewer.jinja) and the same model. The only experimental variable is budget_split.

## KB provenance

- sc-research-kb.215: Feedback loops trump prompt engineering; reviewer value may come from iteration cycle, not content depth
- sc-research-kb.211: Multi-agent failure research shows coordination overhead; minimal reviewer reduces overhead risk

## Results

*To be filled after execution.*
