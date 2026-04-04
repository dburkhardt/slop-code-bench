# H286-B5: Two-Agent (60/40) on eve_industry

**Hypothesis:** Two-agent at 60/40 split improves pass rate over single-agent baseline on eve_industry (6 checkpoints).

**Bead:** sc-hypotheses.286.9

**Verdict:** INCONCLUSIVE (both arms errored mid-run; insufficient data for a fair comparison)

## Setup

| Parameter | Single-Agent (Baseline) | Two-Agent (60/40) |
|-----------|------------------------|-------------------|
| Agent type | claude_code | reviewer_coder |
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Prompt | default_implementer | default_implementer + default_reviewer |
| Cost limit | $5.00 total | $5.00 total |
| Budget split | N/A | 60/40 (implementer/reviewer) |
| Environment | local-py | local-py |

## Results

### Baseline (single-agent)

| Checkpoint | Pass Rate | Tests | Cost | Erosion | Verbosity |
|------------|-----------|-------|------|---------|-----------|
| cp1 | 100.0% (12/12) | 12 | $0.72 | 0.649 | 0.0 |
| cp2 | 45.5% (15/33) | 33 | $0.38 | 0.649 | 0.0 |
| cp3-cp6 | skipped (timeout on cp2) | - | - | - | - |
| **Mean** | **72.7% (2/6 cp)** | - | **$1.10** | - | - |

The baseline completed checkpoint 1 perfectly but timed out on checkpoint 2 (Claude Code process timeout after ~638s). Checkpoints 3 through 6 were skipped.

### Two-Agent (60/40)

| Checkpoint | Pass Rate | Tests | Cost | Erosion | Verbosity |
|------------|-----------|-------|------|---------|-----------|
| cp1 | 25.0% (3/12) | 12 | $1.25 | 0.429 | 0.0 |
| cp2 | 45.5% (15/33) | 33 | $0.76 | 0.684 | 0.0 |
| cp3-cp6 | timed out (3600s limit) | - | - | - | - |
| **Mean** | **35.2% (2/6 cp)** | - | **$2.01** | - | - |

The two-agent runner completed the implementer+reviewer loop for 2 checkpoints before the pipeline's 3600s timeout killed it. The two_agent_metrics.json shows cumulative cost of $2.01.

After the timeout, checkpoint_results.jsonl shows that a third iteration ran checkpoints 1-6 with pass rates of 22% to 25%, suggesting the reviewer's modifications degraded code quality.

### Comparison (on completed checkpoints)

| Metric | Baseline | Two-Agent (60/40) | Delta |
|--------|----------|-------------------|-------|
| cp1 pass rate | 100.0% | 25.0% | -75.0pp |
| cp2 pass rate | 45.5% | 45.5% | 0.0pp |
| Mean pass rate | 72.7% | 35.2% | -37.5pp |
| Total cost | $1.10 | $2.01 | +$0.91 |
| Checkpoints completed | 2/6 | 2/6 | 0 |
| cp1 cost | $0.72 | $1.25 | +$0.53 |

## Cost Analysis

| Metric | Baseline | Two-Agent |
|--------|----------|-----------|
| Cost per completed checkpoint | $0.55 avg | $1.01 avg |
| Total cost | $1.10 | $2.01 |
| Cost multiplier | 1x | 1.8x per cp |
| Implementer tokens (cp1) | N/A | 1,747,371 |
| Reviewer tokens (cp1) | N/A | 402,948 |
| Reviewer tokens (cp2) | N/A | 2,080,740 |

The two-agent pattern is ~1.8x more expensive per checkpoint than the baseline, less extreme than the 5x-13x seen in the H261 experiments. This is likely because the 60/40 split allocates less reviewer budget than the 70/30 default.

## Token Observations

Checkpoint 2 shows zero implementer tokens and 2.08M reviewer tokens, suggesting the reviewer consumed the entire checkpoint 2 budget. This aligns with the implementer erroring on cp2 (timeout), leaving only the reviewer to operate on the stale cp1 code.

## Interpretation

**The result is INCONCLUSIVE** because both arms failed to complete more than 2 of 6 checkpoints. The baseline timed out on checkpoint 2; the two-agent run hit the pipeline's 3600s wall clock limit.

Two preliminary observations:

1. **The two-agent pattern degraded cp1 quality from 100% to 25%.** The reviewer's modifications broke passing code. The baseline achieved a perfect 12/12 on cp1, while the two-agent run scored only 3/12 after the reviewer edited the implementer's work.

2. **eve_industry is a difficult problem for both approaches.** Both arms failed on checkpoint 2 (an SDE-based industry calculation problem with 33 tests). The baseline got 45.5% before timing out; the two-agent got the same 45.5% before the pipeline timeout.

## Confounds

- N=1 per condition (no variance estimation).
- Both arms were truncated by timeouts, so we compare only the first 2 of 6 checkpoints.
- The baseline timeout was per-checkpoint (agent timeout), while the two-agent timeout was total wall clock (3600s pipeline limit). Different timeout mechanisms may have affected results differently.
- The baseline used default_implementer prompt (not just-solve), which includes the reviewer-oriented framing. This is the standard two-agent pipeline configuration.

## Run Artifacts

### Output Directories
- Baseline: `outputs/baseline_claude_code_local/local-claude-sonnet-4-6_eve_industry_20260404_152208/`
- Two-agent: `outputs/two_agent_local-claude-sonnet-4-6_eve_industry_20260404_153945_b3a4dedf10f7/`

### Dolt Experiment IDs
- Baseline: 583
- Two-agent: 584

### Budget Impact
- Total experiment cost: $3.11 ($1.10 + $2.01)
- Budget remaining: $657.94
