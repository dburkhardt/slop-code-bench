# H218: Structured Review Reduces Verbosity

**Hypothesis:** Structured reviewer prompts that explicitly target verbosity will reduce the verbosity slope compared to baseline.

**Predicted outcome:** Two-agent with structured review prompt yields lower verbosity slope than baseline across 3+ problems, with at least 15% reduction.

**Bead:** sc-hypotheses.218

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
| Problems | file_backup, log_query, dag_execution | file_backup, log_query, dag_execution |

**Note:** The original bead specified `todo_app` but that problem does not exist in the benchmark. Substituted with `log_query` and `dag_execution` to reach the 3-problem minimum required by the predicted outcome. These problems were chosen to provide independent evidence from H206, which covers file_backup, etl_pipeline, and database_migration.

## Relationship to H200 and H206

H200 and H206 test the same core claim with different problem sets. H218 extends the evidence base by testing on `log_query` and `dag_execution`, which have not been tested with the anti-slop reviewer. `file_backup` is shared across all three for cross-validation.

## Key Difference from H2/H3 Experiments

Previous two-agent experiments (H2, H3) used the **default reviewer prompt** (`configs/prompts/default_reviewer.jinja`). This experiment uses the **anti-slop reviewer** (`research/prompts/anti-slop-reviewer.jinja`), which specifically targets:

- Verbose comments and docstrings on obvious functions
- Defensive bloat (broad try/except, redundant null checks)
- Unrequested features (logging, config systems, CLI parsing)
- Trivial wrappers and single-use helpers
- Variable bloat (assigned once, used next line)
- Abstraction theater (base classes with one subclass)

## Primary Metric

**Verbosity slope** across checkpoints: measured as the slope of `{AST-Grep Flagged Lines + Clone Lines} / LOC` over successive checkpoints.

Secondary metrics: pass rate, erosion slope, total cost.

## How to Run

### Using experiment_pipeline.py (recommended)

```bash
# file_backup
python research/runner/experiment_pipeline.py \
    --problem file_backup \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.218

# log_query
python research/runner/experiment_pipeline.py \
    --problem log_query \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.218

# dag_execution
python research/runner/experiment_pipeline.py \
    --problem dag_execution \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.218
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

# dag_execution
python research/runner/two_agent_runner.py \
    --problem dag_execution \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja
```

### Using run configs (via slop-code CLI)

```bash
# Baselines
python -m slop_code run --config configs/runs/h218_file_backup_baseline.yaml
python -m slop_code run --config configs/runs/h218_log_query_baseline.yaml
python -m slop_code run --config configs/runs/h218_dag_execution_baseline.yaml

# Two-agent with anti-slop reviewer
python -m slop_code run --config configs/runs/h218_file_backup_anti_slop.yaml
python -m slop_code run --config configs/runs/h218_log_query_anti_slop.yaml
python -m slop_code run --config configs/runs/h218_dag_execution_anti_slop.yaml
```

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

### log_query

| Metric | Baseline | Anti-Slop Two-Agent |
|--------|----------|-------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

### dag_execution

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
- file_backup overlaps with H206, providing cross-validation but not independent evidence for that specific problem.

## Run Artifacts

_To be filled after experiment runs._
