# H224: Structured Review Reduces Verbosity

**Hypothesis:** Structured reviewer prompts that explicitly target verbosity will reduce the verbosity slope compared to baseline.

**Predicted outcome:** Two-agent with structured review prompt yields lower verbosity slope than baseline across 3+ problems.

**Testable claim:** Structured reviewer prompts reduce verbosity slope by at least 15%.

**Bead:** sc-hypotheses.224

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
| Problems | file_backup, dag_execution, code_search | file_backup, dag_execution, code_search |

**Note:** The original bead specified `todo_app` but that problem does not exist in the benchmark. Substituted `dag_execution` and `code_search` to reach the 3-problem minimum required by the predicted outcome. These problems were chosen to complement earlier experiments (H200 covered etl_pipeline/log_query, H206 covered etl_pipeline/database_migration).

## Relationship to H200 and H206

H200 and H206 test the same core hypothesis with overlapping problem sets. H224 extends the evidence by running the anti-slop reviewer on two previously untested problems (dag_execution, code_search) while retaining file_backup as the shared anchor.

## Key Difference from Default Reviewer Experiments

Previous two-agent experiments (H2/H3) used the default reviewer prompt. This experiment uses the anti-slop reviewer (`research/prompts/anti-slop-reviewer.jinja`), which specifically targets:

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
    --hypothesis-id sc-hypotheses.224

# dag_execution
python research/runner/experiment_pipeline.py \
    --problem dag_execution \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.224

# code_search
python research/runner/experiment_pipeline.py \
    --problem code_search \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.224
```

### Using run configs (via slop-code CLI)

```bash
# Baselines
python -m slop_code run --config configs/runs/h224_file_backup_baseline.yaml
python -m slop_code run --config configs/runs/h224_dag_execution_baseline.yaml
python -m slop_code run --config configs/runs/h224_code_search_baseline.yaml

# Two-agent with anti-slop reviewer
python -m slop_code run --config configs/runs/h224_file_backup_anti_slop.yaml
python -m slop_code run --config configs/runs/h224_dag_execution_anti_slop.yaml
python -m slop_code run --config configs/runs/h224_code_search_anti_slop.yaml
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

### dag_execution

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

## Run Artifacts

_To be filled after experiment runs._
