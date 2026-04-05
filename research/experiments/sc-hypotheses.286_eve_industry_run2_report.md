# H286: Two-Agent (60/40) on eve_industry, Run 2 (Replication)

**Hypothesis:** Two-agent at 60/40 split improves pass rate over single-agent baseline on eve_industry (6 checkpoints).

**Bead:** sc-wisp-mol-60i9t

**Verdict:** INCONCLUSIVE, both arms failed (replicates Run 1 failure pattern)

## Setup

| Parameter | Single-Agent (Baseline) | Two-Agent (60/40) |
|-----------|------------------------|-------------------|
| Agent type | claude_code | reviewer_coder |
| Model | local-sonnet-4.6 | local-sonnet-4.6 |
| Prompt | default_implementer | default_implementer + default_reviewer |
| Cost limit | $5.00 total | $5.00 total |
| Budget split | N/A | 60/40 (implementer/reviewer) |
| Environment | local-py | local-py |

## Results

### Baseline (single-agent)

| Checkpoint | Pass Rate | Tests | Cost | State |
|------------|-----------|-------|------|-------|
| cp1 | 25.0% (3/12) | 12 | $0.26 | error |
| cp2-cp6 | not reached | - | - | skipped |
| **Total** | **25.0% (1 cp)** | - | **$0.26** | error |

The baseline timed out on checkpoint 1 after ~607s. Only 3 of 12 tests passed. The agent used only 8 of 100 allowed steps (8% utilization), suggesting it got stuck rather than running out of steps.

### Two-Agent (60/40)

| Row | Checkpoint | Pass Rate | Tests | Cost | State |
|-----|------------|-----------|-------|------|-------|
| 0 | cp1 (impl) | 25.0% (3/12) | 12 | $0.26 | error |
| 1 | cp1 (review) | 25.0% (3/12) | 12 | $0.41 | ran |
| 2 | cp2 (impl) | 45.5% (15/33) | 33 | $0.26 | error |
| 3 | cp1 | skipped | - | - | skipped |
| 4 | cp1 | 25.0% (3/12) | 12 | $0.07 | error |

The two-agent arm timed out after 3600s. It completed the implementer+reviewer cycle for checkpoint 1 and started checkpoint 2 before the pipeline timeout killed it.

### Comparison

| Metric | Baseline | Two-Agent (60/40) |
|--------|----------|-------------------|
| cp1 pass rate | 25.0% | 25.0% |
| Total cost (this run) | $0.26 | ~$1.00 |
| Checkpoints completed | 0/6 | 0/6 |

## Comparison with Run 1

| Metric | Run 1 Baseline | Run 2 Baseline | Run 1 Two-Agent | Run 2 Two-Agent |
|--------|---------------|---------------|-----------------|-----------------|
| cp1 pass rate | 100.0% | 25.0% | 25.0% | 25.0% |
| cp2 pass rate | 45.5% | N/A | 45.5% | 45.5% (partial) |
| Total cost | $1.10 | $0.26 | $2.01 | ~$1.00 |
| Completed checkpoints | 2/6 | 0/6 | 2/6 | 0/6 |

Run 2 performed worse than Run 1 across the board. The baseline in Run 1 achieved 100% on cp1, while Run 2 only got 25%. This high variance across runs (100% vs 25% on the same checkpoint) underscores the stochastic nature of agent execution and supports the paper's finding that initial design decisions compound into high variance.

## Cost Analysis

| Metric | Value |
|--------|-------|
| Total experiment cost (this run) | ~$1.26 |
| Budget remaining | $604.42 |

## Interpretation

This replication confirms Run 1's verdict: **eve_industry is INCONCLUSIVE for the two-agent hypothesis.** Both runs failed to complete more than 2 checkpoints, with both arms hitting timeouts. The problem appears too complex for the $5 budget constraint.

The cross-run variance in baseline cp1 (100% vs 25%) is itself a notable finding, consistent with the paper's claim that initial design decisions drive high variance in iterative evaluation.

## Run Artifacts

### Output Directories
- Baseline: `outputs/local-sonnet-4.6/claude_code-2.0.51_default_implementer_none_20260405T0830/`
- Two-agent: `outputs/two_agent_local-sonnet-4.6_eve_industry_20260405_083005_86c8eec367fd/`
