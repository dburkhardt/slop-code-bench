# H2: Two-Agent (70/30) vs Single-Agent on log_query

**Hypothesis:** Default two-agent configuration (70% implementer / 30% reviewer budget split) achieves higher pass rate than single-agent on log_query.

**Predicted outcome:** Two-agent >= 5% higher pass rate with lower erosion slope.

**Verdict:** NOT SUPPORTED

## Setup

| Parameter | Single-Agent | Two-Agent |
|-----------|-------------|-----------|
| Agent type | claude_code | reviewer_coder |
| Model | nvidia-bedrock-claude-sonnet-4-6 | nvidia-bedrock-claude-sonnet-4-6 |
| Prompt | just-solve | just-solve |
| Step limit | 100/checkpoint | 100/checkpoint |
| Review cycles | N/A | 3 |
| Coder turns/batch | N/A | 10 |

## Results

### Core Pass Rates

| Checkpoint | Single-Agent | Two-Agent |
|-----------|-------------|-----------|
| 1 | 100% | 100% |
| 2 | 100% | 100% |
| 3 | 0% | 0% |
| 4 | not reached | 0% |
| 5 | not reached | 0% |

Both agents solve the first two checkpoints (basic parsing, filtering, projection; aggregation with GROUP BY) and fail starting at checkpoint 3 (CONFLATE joins). The failure point is identical, suggesting problem difficulty is the bottleneck.

### Strict Pass Rates

| Checkpoint | Single-Agent | Two-Agent |
|-----------|-------------|-----------|
| 1 | 97.8% (131/134) | 98.5% (132/134) |
| 2 | 98.1% (203/207) | 100.0% (207/207) |
| 3 | 79.8% (209/262) | 81.3% (213/262) |

Two-agent has marginally better strict pass rates (+0.7% on cp1, +1.9% on cp2, +1.5% on cp3). The cp2 difference is notable: two-agent achieved a perfect score.

### Cost

| Metric | Single-Agent | Two-Agent | Ratio |
|--------|-------------|-----------|-------|
| Total cost | $3.69 | $17.59 | 4.8x |
| Cost per checkpoint | $1.23 | $3.52 | 2.9x |
| Steps | 38 | 189 | 5.0x |
| Checkpoints completed | 3 | 5 | - |

### Code Quality

| Metric | Single-Agent | Two-Agent |
|--------|-------------|-----------|
| Mean verbosity | 0.077 | 0.066 |
| Mean erosion | 0.803 | 0.749 |
| Max cyclomatic complexity | 42 | 30 |
| LOC (final checkpoint) | 1086 | 894 |
| Lint errors per LOC | 0.139 | 0.100 |

Two-agent produces measurably cleaner code: lower verbosity (-14%), lower erosion (-7%), lower max CC, and fewer lint errors per LOC.

### Reviewer Effectiveness

The reviewer component had zero extracted suggestions across all checkpoints (reviewer_suggestion_chars=0). The _extract_review_text() method returned None every time, meaning the coder never received reviewer feedback. The reviewer ran and consumed ~10% of the budget but its output was not successfully piped back.

This means the observed quality differences come from the CODER_APPEND_PROMPT (which instructs clean, minimal code) rather than actual review feedback.

## Interpretation

1. **Pass rate claim: not supported.** Core pass rates are identical on comparable checkpoints. Both agents hit the same wall at checkpoint 3 (CONFLATE joins).

2. **Erosion claim: partially supported.** Two-agent produces lower erosion (0.749 vs 0.803) and lower verbosity (0.066 vs 0.077), but this is likely attributable to the coder system prompt rather than the review loop.

3. **Cost efficiency: strongly negative.** Two-agent costs 4.8x more for equivalent pass rates.

4. **Reviewer extraction bug.** The reviewer_coder agent ran review phases but failed to extract suggestions. This is a pipeline issue that should be investigated separately. With working feedback, results might differ.

## Run Artifacts

- Single-agent: `outputs/nvidia-bedrock-claude-sonnet-4-6/claude_code-2.0.51_just-solve_none_20260402T0112/`
- Two-agent: `outputs/nvidia-bedrock-claude-sonnet-4-6/reviewer_coder-2.0.51_just-solve_none_20260402T0320/`

## Confounds

- N=1 per condition (no variance estimation)
- Cost limit was not enforced by the agent runner
- Reviewer feedback extraction failed (reviewer_suggestion_chars=0)
- Checkpoint 3+ failure is shared, so the comparison is only meaningful for cp1-2
