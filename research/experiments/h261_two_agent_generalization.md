# H261: Two-Agent Benefit Generalizes to High-Checkpoint Problems

**Hypothesis:** Default two-agent (70/30) improves pass rate over single-agent on execution_server (6 checkpoints) and etl_pipeline (5 checkpoints), extending the pattern observed on the first 4 tested problems to higher-checkpoint problems.

**Predicted outcome:** Two-agent pass rate exceeds single-agent by 15-50pp on each problem, consistent with the range observed on the first 4 problems. Larger checkpoint count may show more benefit (reviewer prevents degradation) or less (cascading reviewer errors).

**Bead:** sc-hypotheses.261

**Verdict:** INCONCLUSIVE (budget mismatch invalidates comparison)

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

### execution_server (6 checkpoints)

| Metric | Baseline (single-agent) | Two-Agent (70/30) |
|--------|------------------------|-------------------|
| Total pass rate | 92.4% | 10.4% (budget exceeded after cp2) |
| cp1 pass rate | 95.6% (43/45) | 62.2% (28/45) |
| cp2 pass rate | 96.6% (56/58) | 0.0% (0/58) |
| cp3 pass rate | 93.2% (96/103) | 0.0% (0/103) |
| cp4 pass rate | 95.4% (144/151) | 0.0% (0/151) |
| cp5 pass rate | 95.2% (178/187) | 0.0% (0/187) |
| cp6 pass rate | 78.6% (55/70) | 0.0% (0/70) |
| Total cost | $2.71 | $5.16 (exceeded $5.00 limit) |
| Mean erosion | 0.60 | 0.52 (only 2 cp completed) |
| Reviewer tokens (cp1) | N/A | 2,404,911 |
| Reviewer tokens (cp2) | N/A | 0 |

### etl_pipeline (5 checkpoints)

| Metric | Baseline (single-agent) | Two-Agent (70/30) |
|--------|------------------------|-------------------|
| Total pass rate | 87.3% | 84.8% (budget exceeded after cp1) |
| cp1 pass rate | 85.4% (35/41) | 84.8% (139/164)* |
| cp2 pass rate | 90.4% (66/73) | N/A (not reached) |
| cp3 pass rate | 93.2% (109/117) | N/A (not reached) |
| cp4 pass rate | 82.8% (111/134) | N/A (not reached) |
| cp5 pass rate | 84.8% (139/164) | N/A (not reached) |
| Total cost | $2.62 | $5.33 (exceeded $5.00 limit) |
| Mean erosion | 0.62 | 0.67 (only 1 cp completed) |
| Reviewer tokens | N/A | 0 (reviewer never activated) |

*Note: The two-agent etl_pipeline metrics show cp1 pass_rate=0.848 but test counts (139/164) match baseline cp5, suggesting cross-contamination in the eval output. The two_agent_metrics.json confirms only 1 checkpoint completed.

## Interpretation

**The experiment is inconclusive due to a critical budget mismatch between arms.**

The experiment_pipeline.py applies the `--budget` parameter differently to each arm. The baseline receives `cost_limit=5.0` as a per-checkpoint limit (allowing up to $30 total for 6 checkpoints). The two-agent arm receives `budget=5.0` as a total budget across all checkpoints. This created a 6:1 budget asymmetry for execution_server and 5:1 for etl_pipeline.

As a result, the two-agent arm exhausted its budget after 1-2 checkpoints while the baseline completed all checkpoints cheaply ($2.62-$2.71 total). The two-agent arm's apparent failure reflects budget starvation, not reviewer ineffectiveness.

Additionally, the two-agent runner consumed $4.35 on execution_server checkpoint_1 alone (reviewer tokens = 2.4M), compared to $0.18 for the same checkpoint in baseline. The reviewer-coder interaction loop is far more expensive per checkpoint than single-agent execution.

**Observations despite the confound:**
1. Baseline single-agent performs very well on both problems (87-92% average pass rate) with low cost ($2.62-$2.71 for all checkpoints).
2. The two-agent pattern is approximately 20x more expensive per checkpoint (cp1: $4.35 vs $0.18 for execution_server).
3. Even on checkpoint_1 where the two-agent had budget, it underperformed baseline (62.2% vs 95.6% on execution_server).

## Confounds

- **CRITICAL: Budget mismatch between arms.** Baseline gets $5/checkpoint; two-agent gets $5 total. This invalidates any direct pass-rate comparison. The pipeline bug is in `experiment_pipeline.py:run_baseline()` which passes budget as `agent.cost_limits.cost_limit` (per-checkpoint) vs `run_two_agent()` which passes it as `--budget` (total across all checkpoints).
- **Output directory cross-contamination.** Both baselines wrote to the same shared model directory (`local-claude-sonnet-4-6/claude_code-2.0.51_default_implementer_none_20260402T1640/`). The pipeline's reported baseline pass rates (0.0) are artifacts of directory detection failures. The two-agent etl_pipeline checkpoint_results.jsonl also contains execution_server baseline data.
- N=1 per condition per problem (no variance estimation)
- Reviewer tokens = 0 for etl_pipeline two-agent, meaning the reviewer never activated (budget exhausted before reviewer step)
- Using local-claude-sonnet-4-6 via local OAuth, which may have different latency/cost characteristics than API-based providers

## Run Artifacts

### Output Directories
- Baseline (shared): `outputs/local-claude-sonnet-4-6/claude_code-2.0.51_default_implementer_none_20260402T1640/`
- Two-agent execution_server: `outputs/two_agent_local-claude-sonnet-4-6_execution_server_20260402_164029_af005decffbe/`
- Two-agent etl_pipeline: `outputs/two_agent_local-claude-sonnet-4-6_etl_pipeline_20260402_164029_c2d64d54733c/`

### Key Files
- Baseline checkpoint_results.jsonl: contains both problems' results
- Two-agent two_agent_metrics.json: authoritative per-problem metrics (use these over checkpoint_results.jsonl which has cross-contamination)
- execution_server two-agent: 2/6 checkpoints completed, budget_exceeded=true, cumulative_cost=$5.16
- etl_pipeline two-agent: 1/5 checkpoints completed, budget_exceeded=true, cumulative_cost=$5.33
