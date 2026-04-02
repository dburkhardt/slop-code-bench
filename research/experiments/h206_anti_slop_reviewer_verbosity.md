# H206: Structured Anti-Slop Review Reduces Verbosity

**Hypothesis:** Structured reviewer prompts that explicitly target verbosity will reduce the verbosity slope compared to baseline.

**Predicted outcome:** Two-agent with anti-slop reviewer prompt yields lower verbosity slope than baseline across 3 problems, with at least 15% reduction.

**Bead:** sc-hypotheses.206

**Verdict:** PENDING

## Setup

| Parameter | Single-Agent (Baseline) | Two-Agent (Anti-Slop) |
|-----------|------------------------|----------------------|
| Agent type | claude_code | reviewer_coder |
| Model | opus-4.5 | opus-4.5 |
| Prompt | just-solve | just-solve |
| Reviewer prompt | N/A | research/prompts/anti-slop-reviewer.jinja |
| Step limit | 100/checkpoint | 100/checkpoint |
| Cost limit | $5.0/checkpoint | $5.0/checkpoint |
| Budget split | N/A | 70/30 (implementer/reviewer) |
| Review cycles | N/A | 3 |
| Coder turns/batch | N/A | 10 |
| Problems | file_backup, etl_pipeline, database_migration | file_backup, etl_pipeline, database_migration |

**Note:** The original bead specified `todo_app` but that problem does not exist in the benchmark. Substituted with `etl_pipeline` and added `database_migration` to reach the 3-problem minimum required by the predicted outcome.

## Key Difference from H2/H3 Experiments

Previous two-agent experiments (H2 on log_query, H3 on circuit_eval, H-database_migration, H-dag_execution) used the **default reviewer prompt** (`configs/prompts/default_reviewer.jinja`). This experiment uses the **anti-slop reviewer** (`research/prompts/anti-slop-reviewer.jinja`), which specifically targets:

- Verbose comments and docstrings on obvious functions
- Defensive bloat (broad try/except, redundant null checks)
- Unrequested features (logging, config systems, CLI parsing)
- Trivial wrappers and single-use helpers
- Variable bloat (assigned once, used next line)
- Abstraction theater (base classes with one subclass)

The anti-slop prompt is more aggressive and verbosity-focused than the default reviewer, which targets general structural problems.

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
    --hypothesis-id sc-hypotheses.206

# etl_pipeline
python research/runner/experiment_pipeline.py \
    --problem etl_pipeline \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.206

# database_migration
python research/runner/experiment_pipeline.py \
    --problem database_migration \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.206
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

# etl_pipeline
python research/runner/two_agent_runner.py \
    --problem etl_pipeline \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja

# database_migration
python research/runner/two_agent_runner.py \
    --problem database_migration \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja
```

### Using run configs (via slop-code CLI)

```bash
# Baselines
python -m slop_code run --config configs/runs/h206_file_backup_baseline.yaml
python -m slop_code run --config configs/runs/h206_etl_pipeline_baseline.yaml
python -m slop_code run --config configs/runs/h206_database_migration_baseline.yaml

# Two-agent with anti-slop reviewer
python -m slop_code run --config configs/runs/h206_file_backup_anti_slop.yaml
python -m slop_code run --config configs/runs/h206_etl_pipeline_anti_slop.yaml
python -m slop_code run --config configs/runs/h206_database_migration_anti_slop.yaml
```

Note: the run configs launch individual arms. The two_agent_runner.py and experiment_pipeline.py handle the reviewer prompt injection and budget splitting internally.

## Results

_To be filled after experiment runs._

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

_To be filled after experiment runs._

## Confounds

- N=1 per condition per problem (no variance estimation)
- The anti-slop reviewer extracts suggestions via `_extract_review_text()`, which had a known bug in H2 (zero extraction). Verify reviewer_suggestion_chars > 0.
- Budget split means the implementer gets less budget than the single-agent baseline per checkpoint ($3.50 vs $5.00), which could affect pass rate independent of review quality.
- Cost comparisons must account for the reviewer consuming budget that could otherwise go to implementation.

## Run Artifacts

_To be filled after experiment runs._
