# H233: Structured Review Reduces Verbosity

**Hypothesis:** Structured reviewer prompts that explicitly target verbosity will reduce the verbosity slope compared to baseline.

**Predicted outcome:** Two-agent with structured review prompt yields lower verbosity slope than baseline across 3+ problems, with at least 15% reduction.

**Bead:** sc-hypotheses.233

**Verdict:** PENDING

## Setup

| Parameter | Single-Agent (Baseline) | Two-Agent (Structured Review) |
|-----------|------------------------|-------------------------------|
| Agent type | claude_code | reviewer_coder |
| Model | opus-4.5 | opus-4.5 |
| Prompt | just-solve | just-solve |
| Reviewer prompt | N/A | research/prompts/anti-slop-reviewer.jinja |
| Step limit | 100/checkpoint | 100/checkpoint |
| Cost limit | $5.0/checkpoint | $5.0/checkpoint |
| Budget split | N/A | 70/30 (implementer/reviewer) |
| Review cycles | N/A | 3 |
| Coder turns/batch | N/A | 10 |
| Problems | file_backup, log_query, circuit_eval | file_backup, log_query, circuit_eval |

**Note:** The original bead specified `todo_app` but that problem does not exist in the benchmark. Substituted with `log_query` and added `circuit_eval` to reach the 3-problem minimum required by the predicted outcome. These problems differ from H206 (which used etl_pipeline, database_migration) to provide independent signal.

## Relationship to Prior Experiments

H200 tested structured review on file_backup, etl_pipeline, log_query using the anti-slop reviewer. H206 tested the same reviewer on file_backup, etl_pipeline, database_migration. H233 shares file_backup as a common anchor but uses log_query and circuit_eval to extend coverage to problems not tested in H206. Circuit_eval is fresh to the structured-review line of experiments.

## Primary Metric

**Verbosity slope** across checkpoints: measured as the slope of `{AST-Grep Flagged Lines + Clone Lines} / LOC` over successive checkpoints.

Secondary metrics: pass rate, erosion slope, total cost.

## How to Run

### Using experiment_pipeline.py (recommended)

Runs both baseline and two-agent arms, evaluates with `slop-code eval`, writes to Dolt:

```bash
# file_backup
python research/runner/experiment_pipeline.py \
    --problem file_backup \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.233

# log_query
python research/runner/experiment_pipeline.py \
    --problem log_query \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.233

# circuit_eval
python research/runner/experiment_pipeline.py \
    --problem circuit_eval \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.233
```

### Using two_agent_runner.py (two-agent arm only)

```bash
# file_backup
python research/runner/two_agent_runner.py \
    --problem file_backup \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja

# log_query
python research/runner/two_agent_runner.py \
    --problem log_query \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja

# circuit_eval
python research/runner/two_agent_runner.py \
    --problem circuit_eval \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja
```

### Using run configs (via slop-code CLI)

```bash
# Baselines
python -m slop_code run --config configs/runs/h233_file_backup_baseline.yaml
python -m slop_code run --config configs/runs/h233_log_query_baseline.yaml
python -m slop_code run --config configs/runs/h233_circuit_eval_baseline.yaml

# Two-agent with structured reviewer
python -m slop_code run --config configs/runs/h233_file_backup_structured_review.yaml
python -m slop_code run --config configs/runs/h233_log_query_structured_review.yaml
python -m slop_code run --config configs/runs/h233_circuit_eval_structured_review.yaml
```

## Results

_To be filled after experiment runs._

### file_backup

| Metric | Baseline | Structured Review Two-Agent |
|--------|----------|-----------------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

### log_query

| Metric | Baseline | Structured Review Two-Agent |
|--------|----------|-----------------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

### circuit_eval

| Metric | Baseline | Structured Review Two-Agent |
|--------|----------|-----------------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

## Interpretation

_To be filled after experiment runs._

## Confounds

- N=1 per condition per problem (no variance estimation)
- The anti-slop reviewer extracts suggestions via `_extract_review_text()`, which had a known bug in H2 (zero extraction). Verify reviewer_suggestion_chars > 0.
- Budget split means the implementer gets less budget than the single-agent baseline per checkpoint ($3.50 vs $5.00), which could affect pass rate independent of review quality.
- Cost comparisons must account for the reviewer consuming budget that could otherwise go to implementation.
- file_backup overlaps with H200 and H206; log_query overlaps with H200. circuit_eval is fresh to the structured-review line.

## Run Artifacts

_To be filled after experiment runs._
