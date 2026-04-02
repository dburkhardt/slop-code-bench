# H261: Two-Agent Benefit Generalizes to High-Checkpoint Problems

**Hypothesis:** Default two-agent (70/30) improves pass rate over single-agent on execution_server (6 checkpoints) and etl_pipeline (5 checkpoints), extending the pattern observed on the first 4 tested problems to higher-checkpoint problems.

**Predicted outcome:** Two-agent pass rate exceeds single-agent by 15-50pp on each problem, consistent with the range observed on the first 4 problems. Larger checkpoint count may show more benefit (reviewer prevents degradation) or less (cascading reviewer errors).

**Bead:** sc-hypotheses.261

**Verdict:** PENDING

## Setup

| Parameter | Single-Agent (Baseline) | Two-Agent (70/30) |
|-----------|------------------------|-------------------|
| Agent type | claude_code | reviewer_coder |
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Prompt | just-solve | just-solve |
| Reviewer prompt | N/A | configs/prompts/default_reviewer.jinja |
| Step limit | 100/checkpoint | 100/checkpoint |
| Cost limit | $5.0/checkpoint | $5.0/checkpoint |
| Budget split | N/A | 70/30 (implementer/reviewer) |
| Review cycles | N/A | 3 |
| Coder turns/batch | N/A | 10 |
| Problems | execution_server, etl_pipeline | execution_server, etl_pipeline |
| Environment | local-py | local-py |

## KB Provenance

- sc-research-kb.211: Multi-agent failure research warns cascading errors may worsen on longer sequences
- sc-research-kb.94: LoCoBench-Agent confirms later-checkpoint degradation is robust; more checkpoints = more reviewer opportunity

## Primary Metric

**Total pass rate** per problem: fraction of checkpoints where the agent produces a passing solution.

Secondary metrics: verbosity slope, erosion slope, total cost, reviewer_suggestion_chars (to verify reviewer is functional).

## How to Run

### Using experiment_pipeline.py (recommended)

```bash
# execution_server
uv run python research/runner/experiment_pipeline.py \
    --problem execution_server \
    --model local-claude-sonnet-4-6 \
    --budget 5.0 \
    --budget-split 70 \
    --reviewer-prompt configs/prompts/default_reviewer.jinja \
    --environment configs/environments/local-py.yaml \
    --hypothesis-id sc-hypotheses.261

# etl_pipeline
uv run python research/runner/experiment_pipeline.py \
    --problem etl_pipeline \
    --model local-claude-sonnet-4-6 \
    --budget 5.0 \
    --budget-split 70 \
    --reviewer-prompt configs/prompts/default_reviewer.jinja \
    --environment configs/environments/local-py.yaml \
    --hypothesis-id sc-hypotheses.261
```

## Results

_To be filled after experiment runs._

### execution_server

| Metric | Baseline | Two-Agent (70/30) |
|--------|----------|-------------------|
| Total pass rate | | |
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total cost | | |

### etl_pipeline

| Metric | Baseline | Two-Agent (70/30) |
|--------|----------|-------------------|
| Total pass rate | | |
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total cost | | |

## Interpretation

_To be filled after experiment runs._

## Confounds

- N=1 per condition per problem (no variance estimation)
- Budget split means the implementer gets less budget than the single-agent baseline per checkpoint ($3.50 vs $5.00), which could affect pass rate independent of review quality
- Verify reviewer_suggestion_chars > 0 to confirm reviewer feedback extraction is functional (known bug in H2)
- Cascading errors in longer sequences (sc-research-kb.211) could counteract reviewer benefits
- Using local-claude-sonnet-4-6 (cheaper model) rather than opus-4.5 used in some prior experiments

## Run Artifacts

_To be filled after experiment runs._
