# Experiment Report: sc-hypotheses.286 — circuit_eval

## Hypothesis

Two-agent (implementer + reviewer) workflow improves pass rate and code quality
compared to single-agent baseline on iterative coding tasks.

## Setup

- **Problem**: circuit_eval
- **Model**: local-sonnet-4.6
- **Budget**: $5.00
- **Budget split**: 60/40 (implementer/reviewer)
- **Implementer prompt**: configs/prompts/default_implementer.jinja
- **Hypothesis ID**: sc-hypotheses.286
- **Date**: 2026-04-05

## Results

### Baseline (Single-Agent)

| Checkpoint | Pass Rate | Cost   | LOC | Verbosity | Erosion |
|------------|-----------|--------|-----|-----------|---------|
| CP1        | 100%      | $0.95  | 597 | 0.059     | 0.626   |
| CP2        | 100%      | $0.31  | 788 | 0.044     | 0.630   |
| CP3        | 60% (error) | $0.17 | 788 | 0.044   | 0.630   |

- Total cost: ~$1.43 (3 checkpoints)
- CP3 state was "error" with no code changes from CP2

### Two-Agent

The two-agent arm produced severely degraded results:

**Reviewer pass (0851 run):**
All checkpoints (CP1-CP5) produced 0% pass rate with LOC=0.
The reviewer agent failed to produce any implementation code.

**Implementer re-run (0910 run):**
CP1 produced LOC=574 but 0% pass rate (0/36 tests).

**Two-agent aggregate** (from two_agent_metrics.json):
- Completed checkpoints: 1
- Pass rate: 60.1% (cp1 only, from the implementer's perspective)
- Cumulative cost: $2.79
- Pipeline timed out at 3600s

### Comparison

| Metric              | Baseline       | Two-Agent      |
|---------------------|---------------|----------------|
| Best pass rate      | 100% (CP1-2)  | 60.1% (CP1)   |
| Checkpoints reached | 3              | 1 (timeout)    |
| Total cost          | $1.43          | $2.79          |
| Cost per checkpoint | $0.48          | $2.79          |

## Analysis

The two-agent arm failed catastrophically on circuit_eval. The reviewer agent
produced no code (LOC=0) across all its checkpoints, indicating a fundamental
failure in the reviewer-as-coder workflow for this problem. The pipeline timed
out at 3600s with only 1 checkpoint completed by the two-agent arm.

The baseline performed well on CP1-CP2 (100% pass rate) but stalled at CP3
with 60% pass and no code changes, suggesting the agent gave up or hit a
complexity wall.

No data was inserted into Dolt because the pipeline's completion criteria
were not met (both arms needed valid metrics).

## Cost Analysis

- Budget allocated: $5.00
- Baseline consumed: $1.43
- Two-agent consumed: $2.79
- Total: $4.22 / $5.00

## Conclusion: INCONCLUSIVE

Both arms failed to complete: the two-agent arm timed out with the reviewer
producing no code, and the baseline stalled at checkpoint 3. The experiment
provides no usable comparison data. The circuit_eval problem appears to be
challenging for the reviewer workflow, as the reviewer agent consistently
failed to produce implementation code.
