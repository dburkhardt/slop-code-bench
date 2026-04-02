# H263: Anti-Slop Reviewer Reduces Verbosity Without Hurting Pass Rate

**Hypothesis:** The anti-slop reviewer prompt produces lower verbosity (AST-grep violations + clone lines / LOC) than the default reviewer on file_backup and database_migration, while maintaining pass rates within 5pp of the default reviewer.

**Predicted outcome:** Verbosity slope reduced by 15-30% vs default reviewer. Pass rate within -5pp to +2pp of default. Effect may be larger on file_backup (more checkpoints for verbosity to accumulate) than database_migration.

**Testable claim:** Anti-slop reviewer produces lower verbosity_slope than default reviewer on file_backup and database_migration, with pass rate within 5pp.

**Bead:** sc-hypotheses.263

**Verdict:** PENDING

## Design

### Arms

| Parameter | Baseline (single-agent) | Treatment (two-agent + anti-slop) |
|-----------|------------------------|-----------------------------------|
| Run config | `configs/runs/h263_*_baseline.yaml` | `configs/runs/h263_*_anti_slop.yaml` |
| Agent type | claude_code | reviewer_coder |
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Implementer prompt | just-solve | just-solve |
| Reviewer prompt | N/A | `research/prompts/anti-slop-reviewer.jinja` |
| Budget split | N/A | 70/30 |
| Review cycles | N/A | 3 |
| Coder turns/batch | N/A | 10 |
| Step limit | 100/checkpoint | 100/checkpoint |
| Cost limit | $5.0/checkpoint | $5.0/checkpoint |
| Problems | file_backup, database_migration | file_backup, database_migration |

### Primary metric

**Verbosity** across checkpoints, defined as `{AST-Grep Flagged Lines + Clone Lines} / LOC`. The slope captures how verbosity compounds through iterative specification refinement. The anti-slop reviewer targets verbosity signals directly (verbose comments, defensive bloat, trivial wrappers), so it should produce a flatter slope.

### Secondary metrics

- **Pass rate** (must stay within 5pp of baseline)
- **Structural erosion** (mass.high_cc_pct)
- **Cost** (total and per-checkpoint)
- **LOC** (to distinguish genuine verbosity reduction from simply shorter code)

### Why these problems

file_backup (8 checkpoints) gives the most room for verbosity to accumulate across iterations. database_migration (5 checkpoints) provides a second problem with enough checkpoints to measure a slope. Both are specified in the hypothesis bead.

### Controls

Both arms use the same model (local-claude-sonnet-4-6), thinking mode (none), pass policy (any), and budget ($5.00 per arm). The only difference is the agent type and reviewer prompt.

## Execution

### Via experiment pipeline (runs both arms)

```bash
python research/runner/experiment_pipeline.py \
  --problem file_backup \
  --model local-claude-sonnet-4-6 \
  --budget 5.0 \
  --budget-split 70 \
  --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
  --hypothesis-id sc-hypotheses.263

python research/runner/experiment_pipeline.py \
  --problem database_migration \
  --model local-claude-sonnet-4-6 \
  --budget 5.0 \
  --budget-split 70 \
  --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
  --hypothesis-id sc-hypotheses.263
```

### Via individual run configs

```bash
# Baseline
slop-code run --config configs/runs/h263_file_backup_baseline.yaml
slop-code run --config configs/runs/h263_database_migration_baseline.yaml

# Treatment
slop-code run --config configs/runs/h263_file_backup_anti_slop.yaml
slop-code run --config configs/runs/h263_database_migration_anti_slop.yaml
```

### Via run script

```bash
bash research/experiments/run_h263.sh
```

## Analysis plan

1. Compute per-checkpoint verbosity for both arms on both problems.
2. Fit a linear slope to verbosity across checkpoints for each arm.
3. Compare slopes: the treatment should show a flatter (lower) verbosity slope.
4. Check that pass rates are comparable (within 5pp).
5. Report cost overhead of the two-agent configuration.
6. Compare against prior anti-slop experiments (H203, H206) which used opus-4.5 instead of local-claude-sonnet-4-6.

### Success criteria

The hypothesis is **supported** if:
- Verbosity slope is at least 15% lower in the treatment arm across both problems
- Pass rate does not degrade by more than 5pp compared to baseline

## KB provenance

- sc-research-kb.102: Non-functional quality paper shows quality optimization can reduce correctness; predicts potential tradeoff
- sc-research-kb.215: Feedback loops trump prompt engineering; sets baseline expectation that prompt variant may have small effect

## Confounds

- N=1 per condition per problem (no variance estimation)
- Budget split means the implementer gets less budget than the single-agent baseline per checkpoint ($3.50 vs $5.00), which could affect pass rate independent of review quality
- The anti-slop reviewer's suggestions are extracted via `_extract_review_text()`, which had a known bug in H2 (zero extraction). Verify reviewer_suggestion_chars > 0 in run artifacts.
- Prior experiments (H203, H206) used opus-4.5; this uses local-claude-sonnet-4-6. Model differences may confound comparison with earlier results.

## Results

*To be filled after execution.*

### file_backup

| Metric | Baseline | Anti-Slop Two-Agent |
|--------|----------|-------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

### database_migration

| Metric | Baseline | Anti-Slop Two-Agent |
|--------|----------|-------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

## Interpretation

*To be filled after execution.*

## Run Artifacts

*To be filled after execution.*
