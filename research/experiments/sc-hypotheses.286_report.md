# Experiment Report: sc-hypotheses.286

## Hypothesis

Two-agent (implementer + reviewer) workflow on `migrate_configs` with Sonnet 4.6
produces higher pass rates and lower erosion than the single-agent baseline.

## Setup

- **Problem**: migrate_configs (5 checkpoints)
- **Model**: local-sonnet-4.6 (Claude Sonnet 4.6 via local proxy)
- **Budget**: $5.00 per arm
- **Budget split**: 60/40 (implementer/reviewer)
- **Implementer prompt**: configs/prompts/default_implementer.jinja
- **Reviewer prompt**: configs/prompts/default_reviewer.jinja

## Results

### Baseline (single-agent)

| Checkpoint | Pass Rate | Erosion | Verbosity | Cost |
|------------|-----------|---------|-----------|------|
| 1          | 0.957     | 0.246   | 0.000     | $0.59 |
| 2          | 0.941     | 0.428   | 0.014     | $0.31 |
| 3 (error)  | 0.617     | 0.428   | 0.014     | $0.17 |

- **Aggregate pass rate**: 0.8383
- **Total cost**: $1.08
- **Notes**: Checkpoint 3 errored (Claude Code process timed out). Code was unchanged
  from checkpoint 2, so evaluation ran against stale code. Checkpoints 4-5 were skipped.

### Two-agent

| Checkpoint | Pass Rate | Erosion | Verbosity | Cost |
|------------|-----------|---------|-----------|------|
| 1          | 0.725     | 0.379   | 0.027     | $2.62 |

- **Aggregate pass rate**: 0.7255
- **Total cost**: $2.62
- **Notes**: Run timed out after 3600s during checkpoint 2. Only 1 of 5 checkpoints
  completed. The two-agent workflow spent $2.62 on a single checkpoint vs $0.59 for
  the baseline on the same checkpoint, a 4.4x cost multiplier.

### Comparison

| Metric | Baseline | Two-Agent | Delta |
|--------|----------|-----------|-------|
| Pass rate (overall) | 0.8383 | 0.7255 | -0.1128 |
| Pass rate (cp1 only) | 0.957 | 0.725 | -0.232 |
| Erosion (cp1) | 0.246 | 0.379 | +0.133 |
| Verbosity (cp1) | 0.000 | 0.027 | +0.027 |
| Cost (cp1) | $0.59 | $2.62 | +$2.03 |
| Checkpoints completed | 3/5 | 1/5 | -2 |

## Analysis

The two-agent arm underperformed the baseline on every metric for checkpoint 1:
lower pass rate (0.725 vs 0.957), higher erosion (0.379 vs 0.246), higher verbosity
(0.027 vs 0.000), and 4.4x higher cost. The reviewer feedback loop did not improve
the solution quality.

The two-agent arm also completed fewer checkpoints (1 vs 3) before timing out.
The implementer-reviewer round-trips consume substantially more tokens and wall-clock
time, leaving less capacity for later checkpoints.

This result is consistent with earlier migrate_configs runs in sc-hypotheses.286 where
the two-agent arm achieved 0.95 pass rate at $1.51, suggesting high variance in the
two-agent workflow. The baseline is more consistent (0.84 in this run vs 0.83 in the
earlier run).

## Cost Analysis

- Baseline: $1.08 total ($0.36/checkpoint average)
- Two-agent: $2.62 total ($2.62/checkpoint, only 1 completed)
- Combined spend: $3.69
- Budget remaining after this experiment: $607.70

## Conclusion: INCONCLUSIVE

The two-agent arm's timeout and single-checkpoint completion make direct comparison
unreliable. On the one checkpoint that did complete, the single-agent baseline was
substantially better on all metrics. However, the high variance across runs (compare
with the earlier migrate_configs two-agent result of 0.95 pass rate) means a single
comparison is insufficient to draw conclusions. The hypothesis is neither supported
nor refuted by this data point alone.
