# H265: Two-Agent Cost Efficiency vs Single-Agent Baseline Difficulty

**Hypothesis:** The cost-efficiency ratio (pass-rate gain per dollar of additional cost) of two-agent over single-agent is highest on problems where single-agent pass rate is between 5% and 30%, and lowest on problems where single-agent pass rate is 0% or above 40%.

**Predicted outcome:** Problems where single-agent scores 5-30% show the best pass-rate-per-dollar improvement. Problems where single-agent scores 0% may show large absolute gains but at high cost. Problems above 40% single-agent show minimal or negative cost-efficiency.

**Testable claim:** Cost-efficiency (delta pass rate / delta cost) of two-agent vs single-agent is not monotonically related to single-agent baseline; there is a sweet spot in the 5-30% range.

**Verdict:** PENDING

## Design

### Arms

For each of the 4 problems, we run two arms:

| Parameter | Baseline (single-agent) | Treatment (two-agent + default reviewer) |
|-----------|------------------------|------------------------------------------|
| Run config | `configs/runs/h265_<problem>_baseline.yaml` | `configs/runs/h265_<problem>_two_agent.yaml` |
| Agent type | claude_code | reviewer_coder |
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Implementer prompt | just-solve | just-solve |
| Reviewer prompt | N/A | `configs/prompts/default_reviewer.jinja` |
| Budget split | N/A | 70/30 |
| Review cycles | N/A | 3 |
| Coder turns/batch | N/A | 10 |

### Problems

| Problem | Expected single-agent difficulty | Rationale |
|---------|--------------------------------|-----------|
| log_query | Medium (known: cp1-2 pass, cp3+ fail) | Prior H2 data shows 0% at cp3+; tests mid-range |
| metric_transform_lang | Unknown | DSL parsing problem; likely moderate difficulty |
| trajectory_api | Unknown | API design problem; used in prior experiments |
| file_query_tool | Unknown | Query tool with multiple checkpoints |

### Primary metric

**Cost-efficiency ratio:** `delta_pass_rate / delta_cost`, where `delta_pass_rate = two_agent_pass_rate - baseline_pass_rate` and `delta_cost = two_agent_total_cost - baseline_total_cost`.

A positive ratio means two-agent gained pass rate per additional dollar spent. The hypothesis predicts this ratio peaks for problems where baseline pass rate falls in the 5-30% range.

### Secondary metrics

- **Absolute pass rate** per checkpoint (both arms)
- **Total cost** per arm
- **Erosion** (mass.high_cc_pct) to check for structural quality differences
- **Verbosity** (flagged lines + clone lines / LOC)

### Controls

Both arms use the same model (local-claude-sonnet-4-6), thinking mode (none), pass policy (any), and budget ($5.00 per arm). The only difference is the agent type and reviewer prompt.

## Execution

### Via experiment pipeline (runs both arms per problem)

```bash
python research/runner/experiment_pipeline.py \
  --problem log_query \
  --model local-claude-sonnet-4-6 \
  --budget 5.0 \
  --budget-split 70 \
  --reviewer-prompt configs/prompts/default_reviewer.jinja \
  --hypothesis-id sc-hypotheses.265

python research/runner/experiment_pipeline.py \
  --problem metric_transform_lang \
  --model local-claude-sonnet-4-6 \
  --budget 5.0 \
  --budget-split 70 \
  --reviewer-prompt configs/prompts/default_reviewer.jinja \
  --hypothesis-id sc-hypotheses.265

python research/runner/experiment_pipeline.py \
  --problem trajectory_api \
  --model local-claude-sonnet-4-6 \
  --budget 5.0 \
  --budget-split 70 \
  --reviewer-prompt configs/prompts/default_reviewer.jinja \
  --hypothesis-id sc-hypotheses.265

python research/runner/experiment_pipeline.py \
  --problem file_query_tool \
  --model local-claude-sonnet-4-6 \
  --budget 5.0 \
  --budget-split 70 \
  --reviewer-prompt configs/prompts/default_reviewer.jinja \
  --hypothesis-id sc-hypotheses.265
```

### Via individual run configs

```bash
# Baselines
slop-code run --config configs/runs/h265_log_query_baseline.yaml
slop-code run --config configs/runs/h265_metric_transform_lang_baseline.yaml
slop-code run --config configs/runs/h265_trajectory_api_baseline.yaml
slop-code run --config configs/runs/h265_file_query_tool_baseline.yaml

# Treatments
slop-code run --config configs/runs/h265_log_query_two_agent.yaml
slop-code run --config configs/runs/h265_metric_transform_lang_two_agent.yaml
slop-code run --config configs/runs/h265_trajectory_api_two_agent.yaml
slop-code run --config configs/runs/h265_file_query_tool_two_agent.yaml
```

## Analysis plan

1. Run both arms on all 4 problems and collect per-checkpoint metrics.
2. Compute single-agent baseline pass rate per problem.
3. Compute cost-efficiency ratio: `(two_agent_pass_rate - baseline_pass_rate) / (two_agent_cost - baseline_cost)` per problem.
4. Plot cost-efficiency ratio against baseline pass rate to test the sweet-spot prediction.
5. Check whether problems with baseline pass rate in the 5-30% range show the highest cost-efficiency.
6. Report secondary metrics (erosion, verbosity, absolute costs).

### Success criteria

The hypothesis is **supported** if:
- Problems with baseline pass rate in the 5-30% range show higher cost-efficiency ratios than problems with 0% or >40% baseline pass rate
- The relationship between baseline difficulty and cost-efficiency is non-monotonic (i.e., not simply "harder problems benefit more")

The hypothesis is **not supported** if:
- Cost-efficiency is monotonically related to baseline difficulty (harder always benefits more, or easier always benefits more)
- All problems show similar cost-efficiency regardless of baseline difficulty

## KB provenance

- sc-research-kb.214: 45% threshold suggests diminishing returns as single-agent improves
- sc-research-kb.212: MAS benefits depend on task characteristics; baseline difficulty is a key moderator
- Prior H2 results: log_query showed 4.8x cost for identical pass rates (cost-efficiency < 0)

## Results

*To be filled after execution.*
