# H243: Structured Review Reduces Verbosity

**Hypothesis:** Structured reviewer prompts that explicitly target verbosity will reduce the verbosity slope compared to baseline.

**Predicted outcome:** Two-agent with structured review prompt yields lower verbosity slope than baseline across 3+ problems, with at least 15% reduction.

**Bead:** sc-hypotheses.243

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
| Problems | file_backup, execution_server, code_search | file_backup, execution_server, code_search |

**Note:** The original bead specified `todo_app` but that problem does not exist in the benchmark. Substituted with `execution_server` and `code_search` to reach the 3-problem minimum required by the predicted outcome. These problems were chosen because they have not been tested with the anti-slop reviewer in prior hypotheses (H200 covers file_backup; H206 covers etl_pipeline, database_migration; H218 covers log_query, dag_execution). `file_backup` is retained from the bead specification and provides cross-validation with earlier experiments.

## Relationship to Prior Hypotheses

H200, H206, and H218 test the same core claim with overlapping but distinct problem sets. H243 extends the evidence base to `execution_server` and `code_search`, two problems with no prior anti-slop reviewer coverage. Combined with the earlier experiments, a positive result here would bring total coverage to 7 distinct problems.

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
    --hypothesis-id sc-hypotheses.243

# execution_server
python research/runner/experiment_pipeline.py \
    --problem execution_server \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.243

# code_search
python research/runner/experiment_pipeline.py \
    --problem code_search \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.243
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

# execution_server
python research/runner/two_agent_runner.py \
    --problem execution_server \
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
```

### Using run configs (via slop-code CLI)

```bash
# Baselines
python -m slop_code run --config configs/runs/h243_file_backup_baseline.yaml
python -m slop_code run --config configs/runs/h243_execution_server_baseline.yaml
python -m slop_code run --config configs/runs/h243_code_search_baseline.yaml

# Two-agent with anti-slop reviewer
python -m slop_code run --config configs/runs/h243_file_backup_anti_slop.yaml
python -m slop_code run --config configs/runs/h243_execution_server_anti_slop.yaml
python -m slop_code run --config configs/runs/h243_code_search_anti_slop.yaml
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

### execution_server

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

## Run Artifacts

_To be filled after experiment runs._
