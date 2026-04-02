# H240: Structured Review Reduces Verbosity

**Hypothesis:** Structured reviewer prompts that explicitly target verbosity will reduce the verbosity slope compared to baseline.

**Predicted outcome:** Two-agent with structured review prompt yields lower verbosity slope than baseline across 3+ problems, with at least 15% reduction.

**Bead:** sc-hypotheses.240

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
| Problems | file_backup, circuit_eval, code_search | file_backup, circuit_eval, code_search |

**Note:** The original bead specified `todo_app` but that problem does not exist in the benchmark. Substituted with `circuit_eval` and `code_search` to reach the 3-problem minimum. These problems have not been tested with the anti-slop reviewer in any prior experiment (H200, H203, H206, H218), providing fully independent evidence for two of three problems. `file_backup` is shared across prior experiments for cross-validation.

## Relationship to Prior Experiments

| Experiment | Problems | Status |
|-----------|----------|--------|
| H200 | file_backup, etl_pipeline, log_query | Complete |
| H203 | (single-problem config) | Complete |
| H206 | file_backup, etl_pipeline, database_migration | Complete |
| H218 | file_backup, log_query, dag_execution | Complete |
| **H240** | **file_backup, circuit_eval, code_search** | **This experiment** |

H240 extends the evidence base to two entirely new problems (circuit_eval, code_search) that no prior anti-slop experiment has tested.

## Key Difference from Default Reviewer

The anti-slop reviewer (`research/prompts/anti-slop-reviewer.jinja`) specifically targets:

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
    --hypothesis-id sc-hypotheses.240

# circuit_eval
python research/runner/experiment_pipeline.py \
    --problem circuit_eval \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.240

# code_search
python research/runner/experiment_pipeline.py \
    --problem code_search \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.240
```

### Using run configs (via slop-code CLI)

```bash
# Baselines
python -m slop_code run --config configs/runs/h240_file_backup_baseline.yaml
python -m slop_code run --config configs/runs/h240_circuit_eval_baseline.yaml
python -m slop_code run --config configs/runs/h240_code_search_baseline.yaml

# Two-agent with anti-slop reviewer
python -m slop_code run --config configs/runs/h240_file_backup_anti_slop.yaml
python -m slop_code run --config configs/runs/h240_circuit_eval_anti_slop.yaml
python -m slop_code run --config configs/runs/h240_code_search_anti_slop.yaml
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

### circuit_eval

| Metric | Baseline | Anti-Slop Two-Agent |
|--------|----------|-------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

### code_search

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
- file_backup overlaps with H200/H206/H218, providing cross-validation but not independent evidence for that specific problem.
- circuit_eval and code_search have not been tested in any prior two-agent experiment, so there is no prior baseline comparison available for those problems.

## Run Artifacts

_To be filled after experiment runs._
