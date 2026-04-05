# H286-B5-R2: Two-Agent (60/40) on eve_market_tools (Replication 2)

**Hypothesis:** Two-agent at 60/40 split improves pass rate over single-agent baseline on eve_market_tools (4 checkpoints).

**Bead:** sc-wisp-mol-21nwu (experiment molecule for sc-hypotheses.286)

**Verdict:** INCONCLUSIVE (both arms timed out; no Dolt insert)

## Setup

| Parameter | Single-Agent (Baseline) | Two-Agent (60/40) |
|-----------|------------------------|-------------------|
| Agent type | claude_code | reviewer_coder |
| Model | local-sonnet-4.6 | local-sonnet-4.6 |
| Prompt | default_implementer | default_implementer + default_reviewer |
| Cost limit | $5.00 per arm | $5.00 per arm |
| Budget split | N/A | 60/40 (implementer/reviewer) |
| Environment | local-py | local-py |

## Results

### Baseline (single-agent)

| Checkpoint | Pass Rate | Tests | Cost | Erosion | Verbosity |
|------------|-----------|-------|------|---------|-----------|
| cp1 | 30.0% (3/10) | 10 | $0.50 | 0.549 | 0.037 |
| cp2-cp4 | skipped (agent timed out) | - | - | - | - |

The baseline timed out after 605s on checkpoint 1. Only 16 of 100 allowed steps were used before timeout, suggesting the agent hit the per-checkpoint wall clock limit rather than the step limit.

### Two-Agent (60/40)

The two-agent arm produced 5 JSONL entries before the pipeline's 3600s timeout:

| Phase | Checkpoint | Pass Rate | Cost | LOC | Erosion | Verbosity |
|-------|------------|-----------|------|-----|---------|-----------|
| Implementer (iter 1) | cp1 | 30.0% (3/10) | $0.50 | 657 | 0.549 | 0.037 |
| Reviewer (iter 1) | cp1 | 0.0% (0/10) | $2.00 | 0 | 0.0 | 0.0 |
| Implementer (iter 2) | cp2 | 0.0% (0/28) | $0.41 | 0 | 0.0 | 0.0 |
| Reviewer (iter 2) | cp1 | 60.0% (6/10) | $0.44 | 638 | 0.826 | 0.016 |
| Final | cp1 | 30.0% (3/10) | $0.44 | 418 | 0.525 | 0.014 |

Total two-agent cost: ~$3.79.

### Comparison with Prior Run (Replication 1)

| Metric | R1 Baseline | R2 Baseline | R1 Two-Agent | R2 Two-Agent |
|--------|-------------|-------------|--------------|--------------|
| cp1 pass rate | 30.0% | 30.0% | 0.0% | 30.0% (best: 60%) |
| cp2 pass rate | 25.0% | skipped | 25.0% | 0.0% |
| Total cost | $1.23 | $0.50 | $2.21 | $3.79 |
| Checkpoints completed | 2/4 | 1/4 | 2/4 | 1/4 (partial) |

## Cost Analysis

| Metric | Baseline | Two-Agent |
|--------|----------|-----------|
| Total cost | $0.50 | $3.79 |
| Cost per checkpoint (cp1) | $0.50 | $3.79 |
| Cost multiplier | 1x | 7.6x |

## Interpretation

**The result is INCONCLUSIVE**, consistent with replication 1. Both arms timed out before completing even 2 of 4 checkpoints.

Three observations:

1. **Baseline cp1 pass rate is stable at 30% across both replications.** This consistency suggests 30% is a reliable estimate of single-agent capability on this problem's first checkpoint.

2. **Two-agent showed higher variance.** Replication 1 got 0% on cp1; replication 2 got 30% initially, peaked at 60% after reviewer intervention, then regressed to 30%. The reviewer sometimes helps (60% peak) but can also destroy progress (0% in R1). Erosion spiked from 0.549 to 0.826 during the best-performing reviewer pass, suggesting the reviewer introduced structural complexity while fixing functional issues.

3. **eve_market_tools remains too hard for reliable comparison.** Neither arm completed more than 1-2 of 4 checkpoints in either replication. The problem needs a higher budget or longer timeout to produce meaningful multi-checkpoint data.

## Confounds

- N=1 per condition per replication (2 total now).
- Both arms truncated by timeouts.
- The two-agent runner's multi-phase output makes canonical pass rate ambiguous.
- No Dolt insert for this replication (metrics extraction failed on incomplete runs).
- Prior Dolt data exists from R1: single pass=0.28, two-agent pass=0.13.

## Run Artifacts

### Output Directories
- Baseline: `outputs/local-sonnet-4.6/claude_code-2.0.51_default_implementer_none_20260405T0707/eve_market_tools/`
- Two-agent: `outputs/two_agent_local-sonnet-4.6_eve_market_tools_20260405_070713_6337a606fa63/`

### Budget Impact
- Total experiment cost: ~$4.29 ($0.50 baseline + $3.79 two-agent)
- No Dolt budget update (pipeline did not insert).
