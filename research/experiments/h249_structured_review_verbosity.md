# H249: Structured Review Reduces Verbosity

**Hypothesis:** Structured reviewer prompts that explicitly target verbosity will reduce the verbosity slope compared to baseline.

**Predicted outcome:** Two-agent with structured review prompt yields lower verbosity slope than baseline across 3+ problems, with at least 15% reduction.

**Bead:** sc-hypotheses.249

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
| Problems | file_backup, code_search, file_merger | file_backup, code_search, file_merger |

**Note:** The original bead specified `todo_app` but that problem does not exist in the benchmark. Substituted with `code_search` and `file_merger` to reach the 3-problem minimum required by the predicted outcome. These problems have not been used in prior structured-review experiments (H200, H203, H206, H218, H221), adding diversity to the evidence base.

## Relationship to Prior Experiments

H249 tests the same core hypothesis as H200, H203, H206, H218, and H221 with fresh problem selections. All use the anti-slop reviewer (`research/prompts/anti-slop-reviewer.jinja`) targeting verbose comments, defensive bloat, unrequested features, trivial wrappers, single-use helpers, variable bloat, and abstraction theater.

Prior problem coverage:
- H200: file_backup (single problem)
- H203: file_backup (single problem, different config)
- H206: file_backup, etl_pipeline, database_migration
- H218: file_backup, dag_execution, log_query
- H221: file_backup, etl_pipeline, log_query
- H249 (this): file_backup, code_search, file_merger

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
    --hypothesis-id sc-hypotheses.249

# code_search
python research/runner/experiment_pipeline.py \
    --problem code_search \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.249

# file_merger
python research/runner/experiment_pipeline.py \
    --problem file_merger \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.249
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

# code_search
python research/runner/two_agent_runner.py \
    --problem code_search \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja

# file_merger
python research/runner/two_agent_runner.py \
    --problem file_merger \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja
```

### Using run configs (via slop-code CLI)

```bash
# Baselines
python -m slop_code run --config configs/runs/h249_file_backup_baseline.yaml
python -m slop_code run --config configs/runs/h249_code_search_baseline.yaml
python -m slop_code run --config configs/runs/h249_file_merger_baseline.yaml

# Two-agent with anti-slop reviewer
python -m slop_code run --config configs/runs/h249_file_backup_anti_slop.yaml
python -m slop_code run --config configs/runs/h249_code_search_anti_slop.yaml
python -m slop_code run --config configs/runs/h249_file_merger_anti_slop.yaml
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

### code_search

| Metric | Baseline | Anti-Slop Two-Agent |
|--------|----------|-------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

### file_merger

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
