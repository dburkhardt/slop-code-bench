# H-coverage: Baseline Coverage for migrate_configs (60/40 Split)

**Hypothesis:** Establish baseline coverage across problems to map threshold boundary. This experiment collects single-agent and two-agent (60/40 split) data for `migrate_configs`.

**Bead:** sc-hypotheses.286.6 (child of sc-hypotheses.286)

**Verdict:** DATA COLLECTED (partial: 3/5 checkpoints per arm)

## Setup

| Parameter | Single-Agent (Baseline) | Two-Agent |
|-----------|------------------------|-----------|
| Model | claude_code_local/local-claude-sonnet-4-6 | claude_code_local/local-claude-sonnet-4-6 |
| Prompt | default_implementer.jinja | default_implementer.jinja + default_reviewer.jinja |
| Budget | $5/arm | $5/arm |
| Budget split | N/A | 60/40 (implementer/reviewer) |
| Problem | migrate_configs | migrate_configs |
| Checkpoints completed | 3/5 | 3/5 |

## Results

### Pass Rates (per checkpoint)

| Checkpoint | Baseline | Two-Agent | Delta |
|------------|----------|-----------|-------|
| checkpoint_1 | 91.30% | 95.65% | +4.35pp |
| checkpoint_2 | 96.08% | 98.04% | +1.96pp |
| checkpoint_3 | 62.96% | 90.12% | +27.16pp |
| **Mean** | **83.45%** | **94.60%** | **+11.15pp** |

### Quality Metrics (per checkpoint)

| Checkpoint | Baseline Erosion | Two-Agent Erosion | Baseline Verbosity | Two-Agent Verbosity |
|------------|-----------------|-------------------|-------------------|-------------------|
| checkpoint_1 | 0.205 | 0.267 | 0.048 | 0.025 |
| checkpoint_2 | 0.397 | 0.328 | 0.053 | 0.016 |
| checkpoint_3 | 0.397 | 0.437 | 0.053 | 0.025 |

### Aggregate Metrics

| Metric | Baseline | Two-Agent | Delta |
|--------|----------|-----------|-------|
| Mean pass rate | 0.8345 | 0.9460 | +0.1115 |
| Erosion slope | 0.0964 | 0.0849 | -0.0115 |
| Verbosity slope | 0.0028 | 0.0003 | -0.0025 |
| Total cost | $1.59 | $1.51 | -$0.08 |

### Code Metrics

| Metric | Baseline (cp3) | Two-Agent (cp3) |
|--------|---------------|----------------|
| LOC | 528 | 668 |
| Functions | 25 | 33 |
| CC max | 16 | 27 |
| CC mean | 5.76 | 6.15 |
| High CC count | 3 | 3 |
| Clone lines | 28 | 17 |

## Dolt Records

- Baseline: experiments row id=641
- Two-agent: experiments row id=642

## Observations

1. The two-agent arm achieved substantially higher pass rates across all three completed checkpoints. The largest gain was at checkpoint_3 (+27.16pp), where the baseline agent failed to make meaningful progress on the new spec requirements while the two-agent approach adapted better.

2. Verbosity was consistently lower in the two-agent arm (mean 0.022 vs 0.051 for baseline), suggesting the reviewer reduced unnecessary code duplication.

3. Erosion slopes are similar between arms (0.0964 vs 0.0849), with the two-agent arm slightly lower. Both show increasing structural complexity across checkpoints.

4. The two-agent arm produced more code (668 LOC vs 528 LOC at checkpoint_3) but with fewer clone lines (17 vs 28). The higher CC max (27 vs 16) in the two-agent arm is a concern, as one function accumulated disproportionate complexity.

5. Both arms timed out before completing checkpoints 4 and 5. The baseline timed out during checkpoint_4 inference; the two-agent arm hit the 3600s pipeline timeout. Cost remained well under the $5 budget for both arms ($1.59 and $1.51 respectively for 3 checkpoints each).

6. The reviewer runs in the two-agent arm produced 0% pass rate and 0 LOC, as expected. The reviewer agent does not produce code directly; its value is reflected in the improved implementer output from the second iteration.

## Limitations

- Only 3 of 5 checkpoints completed for both arms due to timeout constraints.
- Checkpoint_3 was marked as "error" state in both arms, meaning the agent did not achieve full pass rate despite running. This makes the delta at checkpoint_3 partially driven by how gracefully each arm fails.
- The two-agent runner ran two full implementer iterations. The report uses the second iteration's results, which had the benefit of reviewer feedback.
