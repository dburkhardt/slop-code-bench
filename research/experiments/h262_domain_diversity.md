# H262: Two-Agent Domain Diversity Test (eve_industry + file_merger)

**Hypothesis:** Default two-agent (70/30) improves pass rate over single-agent on eve_industry (6 checkpoints, game simulation) and file_merger (4 checkpoints, I/O-heavy), testing whether the two-agent pattern holds across diverse problem domains.

**Predicted outcome:** Two-agent improves by 10-50pp on each problem. Magnitude may differ depending on single-agent baseline difficulty for each domain.

**Testable claim:** Two-agent (70/30) achieves higher pass rate than single-agent on both eve_industry and file_merger.

**Verdict:** NOT SUPPORTED

## Design

### Arms

| Parameter | Baseline (single-agent) | Treatment (two-agent) |
|-----------|------------------------|----------------------|
| Run config | `configs/runs/h262_*_baseline.yaml` | `configs/runs/h262_*_two_agent.yaml` |
| Agent type | claude_code | reviewer_coder |
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Implementer prompt | default_implementer | default_implementer |
| Reviewer prompt | N/A | `configs/prompts/default_reviewer.jinja` |
| Budget split | N/A | 70/30 |
| Review cycles | N/A | 3 |
| Coder turns/batch | N/A | 10 |
| Problems | eve_industry, file_merger | eve_industry, file_merger |

### Primary metric

**Pass rate** (strict_pass_rate) across checkpoints. The hypothesis predicts the two-agent pattern universally improves pass rates regardless of problem domain.

### Secondary metrics

- **Structural erosion** (mass.high_cc_pct)
- **Verbosity** (AST-Grep Flagged Lines + Clone Lines / LOC)
- **Cost** (total and per-checkpoint)

## Execution

```bash
# Both problems run in parallel
uv run python research/runner/experiment_pipeline.py \
  --problem eve_industry \
  --model local-claude-sonnet-4-6 \
  --budget 5.0 \
  --budget-split 70 \
  --reviewer-prompt configs/prompts/default_reviewer.jinja \
  --hypothesis-id sc-hypotheses.262 \
  --no-dolt

uv run python research/runner/experiment_pipeline.py \
  --problem file_merger \
  --model local-claude-sonnet-4-6 \
  --budget 5.0 \
  --budget-split 70 \
  --reviewer-prompt configs/prompts/default_reviewer.jinja \
  --hypothesis-id sc-hypotheses.262 \
  --no-dolt
```

Both two-agent runs timed out at 3600s (the experiment_pipeline.py subprocess timeout).

## Results (Partial)

### eve_industry

| Checkpoint | Baseline Pass Rate | Two-Agent Pass Rate | Delta |
|------------|-------------------|--------------------|----|
| checkpoint_1 | 1.000 | 0.455 | -0.545 |
| checkpoint_2 | (not reached) | 0.182 | N/A |

| Metric | Baseline cp1 | Two-Agent cp1 | Two-Agent cp2 |
|--------|-------------|---------------|---------------|
| Erosion | 0.572 | 0.682 | 0.670 |
| Verbosity | 0.000 | 0.000 | 0.035 |
| Cost | $0.24 | $0.66 | $1.07 |

The baseline achieved 100% pass rate on checkpoint_1. The two-agent approach dropped to 45.5%, a 54.6pp decrease. Erosion was also higher in the two-agent arm (0.682 vs 0.572). The two-agent run cost 2.8x more per checkpoint.

### file_merger

| Checkpoint | Baseline Pass Rate | Two-Agent Pass Rate | Delta |
|------------|-------------------|--------------------|----|
| checkpoint_1 | 0.152 | 0.523 | +0.371 |

| Metric | Baseline cp1 | Two-Agent cp1 |
|--------|-------------|---------------|
| Erosion | 0.000 | 0.454 |
| Verbosity | 0.000 | 0.017 |
| Cost | $0.00 | $1.49 |

The baseline produced non-functional code (cost=$0.00, 15.2% pass rate from partial test passing). The two-agent approach achieved 52.3% pass rate. The improvement is real but the baseline comparison is unreliable due to the catastrophic agent failure.

## Analysis

The hypothesis is not supported. The results reveal domain-dependent behavior consistent with sc-research-kb.212 (MAS benefits depend on what the single-agent struggles with):

1. **When baseline is strong (eve_industry):** The reviewer adds overhead without benefit. The single-agent solved checkpoint_1 perfectly; the reviewer's additional passes introduced regressions, dropping pass rate to 45.5%.

2. **When baseline fails catastrophically (file_merger):** The two-agent approach improves results (52.3% vs 15.2%), but the baseline failure makes this comparison uninformative about the reviewer's value. The baseline agent may have hit an error or produced empty output.

3. **Cost inefficiency:** The two-agent approach costs 2.8x to 6.2x more per checkpoint. Even when it improves pass rates, the cost-effectiveness is questionable.

### Limitations

- Both two-agent runs timed out at 3600s, completing only 1-2 of 4-6 checkpoints
- Single repetition per condition (no statistical power)
- Baseline file_merger had a catastrophic failure (cost=0)
- Only checkpoint_1 is comparable across both conditions

## Output Directories

- Baseline: `outputs/local-claude-sonnet-4-6/claude_code-2.0.51_default_implementer_none_20260402T1642`
- Two-agent eve_industry: `outputs/two_agent_local-claude-sonnet-4-6_eve_industry_20260402_164158_ec6884139594`
- Two-agent file_merger: `outputs/two_agent_local-claude-sonnet-4-6_file_merger_20260402_164158_72e10cfbbbf8`
