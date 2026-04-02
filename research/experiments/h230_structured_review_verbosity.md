# H230: Structured Review Reduces Verbosity

**Hypothesis:** Structured reviewer prompts that explicitly target verbosity will reduce the verbosity slope compared to baseline.

**Predicted outcome:** Two-agent with structured review prompt yields lower verbosity slope than baseline across 3+ problems, with at least 15% reduction.

**Testable claim:** Structured reviewer prompts reduce verbosity slope by at least 15%.

**Bead:** sc-hypotheses.230

**Verdict:** PENDING

## Design

### Arms

| Parameter | Baseline (single-agent) | Treatment (two-agent + anti-slop) |
|-----------|------------------------|-----------------------------------|
| Agent type | claude_code | reviewer_coder |
| Model | opus-4.5 | opus-4.5 |
| Implementer prompt | just-solve | just-solve |
| Reviewer prompt | N/A | `research/prompts/anti-slop-reviewer.jinja` |
| Budget split | N/A | 70/30 |
| Review cycles | N/A | 3 |
| Coder turns/batch | N/A | 10 |
| Step limit | 100/checkpoint | 100/checkpoint |
| Cost limit | $5.0/checkpoint | $5.0/checkpoint |
| Thinking | none | none |
| Problems | file_backup, etl_pipeline, log_query | file_backup, etl_pipeline, log_query |

**Note:** The bead metadata specified `todo_app`, but no such problem exists in the benchmark. Substituted with `etl_pipeline` and `log_query` to reach the 3-problem minimum required by the predicted outcome.

### Primary metric

**Verbosity slope** across checkpoints. Verbosity is defined as `{AST-Grep Flagged Lines + Clone Lines} / LOC`.

The slope captures how quickly verbosity compounds through iterative specification refinement. A steeper slope means slop accumulates faster across checkpoints.

### Secondary metrics

- **Pass rate** (to confirm reviewer does not harm correctness)
- **Structural erosion** (mass.high_cc_pct)
- **Cost** (total and per-checkpoint)
- **LOC** (to detect whether the reviewer simply produces shorter code rather than less verbose code)

### Controls

Both arms use the same model (opus-4.5), thinking mode (none), pass policy (any), and environment (docker-python3.12-uv). The only difference is the agent type and reviewer prompt.

## Key difference from prior experiments

H200, H203, and H206 tested the same core hypothesis with different problem sets. H230 replicates the design on file_backup, etl_pipeline, and log_query to accumulate evidence across independent runs. If results are consistent with prior experiments, the combined evidence strengthens the claim. If results diverge, the discrepancy points to problem-specific confounds.

## Execution

### Via experiment pipeline (runs both arms)

```bash
# file_backup
python research/runner/experiment_pipeline.py \
    --problem file_backup \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.230

# etl_pipeline
python research/runner/experiment_pipeline.py \
    --problem etl_pipeline \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.230

# log_query
python research/runner/experiment_pipeline.py \
    --problem log_query \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.230
```

### Via individual run configs

```bash
# Baselines
slop-code run --config configs/runs/h230_file_backup_baseline.yaml
slop-code run --config configs/runs/h230_etl_pipeline_baseline.yaml
slop-code run --config configs/runs/h230_log_query_baseline.yaml

# Two-agent with anti-slop reviewer
slop-code run --config configs/runs/h230_file_backup_anti_slop.yaml
slop-code run --config configs/runs/h230_etl_pipeline_anti_slop.yaml
slop-code run --config configs/runs/h230_log_query_anti_slop.yaml
```

### Via run script

```bash
bash research/experiments/run_h230.sh
```

## Analysis plan

1. Compute per-checkpoint verbosity for both arms on all three problems.
2. Fit a linear slope to verbosity across checkpoints for each arm.
3. Compare slopes: the treatment should show a flatter (lower) verbosity slope.
4. Check that pass rates are comparable (the reviewer should not harm correctness).
5. Report cost overhead of the two-agent configuration.

### Success criteria

The hypothesis is **supported** if:
- Verbosity slope is at least 15% lower in the treatment arm across all three problems
- Pass rate does not degrade by more than 5% compared to baseline

## Confounds

- N=1 per condition per problem (no variance estimation without repeated runs)
- The anti-slop reviewer extracts suggestions via `_extract_review_text()`, which had a known bug in H2 (zero extraction). Verify reviewer_suggestion_chars > 0.
- Budget split means the implementer gets less budget than the single-agent baseline per checkpoint ($3.50 vs $5.00), which could affect pass rate independent of review quality.
- Cost comparisons must account for the reviewer consuming budget that could otherwise go to implementation.

## Results

### file_backup

| Metric | Baseline | Anti-Slop Two-Agent |
|--------|----------|-------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

### etl_pipeline

| Metric | Baseline | Anti-Slop Two-Agent |
|--------|----------|-------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

### log_query

| Metric | Baseline | Anti-Slop Two-Agent |
|--------|----------|-------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

## Interpretation

_To be filled after experiment runs._

## Run Artifacts

_To be filled after experiment runs._
