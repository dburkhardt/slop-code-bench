# H209: Structured Review Reduces Verbosity

**Hypothesis:** Structured reviewer prompts that explicitly target verbosity will reduce the verbosity slope compared to baseline.

**Predicted outcome:** Two-agent with structured review prompt yields lower verbosity slope than baseline across 3+ problems, with at least 15% reduction.

**Bead:** sc-hypotheses.209

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
| Problems | file_backup, dynamic_config_service_api, trajectory_api | file_backup, dynamic_config_service_api, trajectory_api |

**Note:** The original bead specified `todo_app` but that problem does not exist in the benchmark. Substituted with `dynamic_config_service_api` and `trajectory_api` to reach the 3-problem minimum required by the predicted outcome. These problems have not been used in any prior experiment of this hypothesis family (H200, H203, H206, H218, H221, H224, H227, H230, H233, H240, H243, H246, H249, H252), providing fully independent evidence for two of three problems. `file_backup` is retained as the shared anchor for cross-validation.

## Relationship to Prior Experiments

H209 tests the same core hypothesis as H200, H203, H206, H218, H221, H224, H227, H230, H233, H240, H243, H246, H249, and H252. All use the anti-slop reviewer (`research/prompts/anti-slop-reviewer.jinja`), which targets verbose comments, defensive bloat, unrequested features, trivial wrappers, single-use helpers, variable bloat, and abstraction theater.

H209 extends the evidence base to `dynamic_config_service_api` and `trajectory_api`, two problems with no prior anti-slop reviewer coverage.

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
    --hypothesis-id sc-hypotheses.209

# dynamic_config_service_api
python research/runner/experiment_pipeline.py \
    --problem dynamic_config_service_api \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.209

# trajectory_api
python research/runner/experiment_pipeline.py \
    --problem trajectory_api \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.209
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

# dynamic_config_service_api
python research/runner/two_agent_runner.py \
    --problem dynamic_config_service_api \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja

# trajectory_api
python research/runner/two_agent_runner.py \
    --problem trajectory_api \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja
```

### Using run configs (via slop-code CLI)

```bash
# Baselines
python -m slop_code run --config configs/runs/h209_file_backup_baseline.yaml
python -m slop_code run --config configs/runs/h209_dynamic_config_service_api_baseline.yaml
python -m slop_code run --config configs/runs/h209_trajectory_api_baseline.yaml

# Two-agent with anti-slop reviewer
python -m slop_code run --config configs/runs/h209_file_backup_anti_slop.yaml
python -m slop_code run --config configs/runs/h209_dynamic_config_service_api_anti_slop.yaml
python -m slop_code run --config configs/runs/h209_trajectory_api_anti_slop.yaml
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

### dynamic_config_service_api

| Metric | Baseline | Anti-Slop Two-Agent |
|--------|----------|-------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

### trajectory_api

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
