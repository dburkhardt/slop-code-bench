# H286-B5: Two-Agent (60/40) on eve_market_tools

**Hypothesis:** Two-agent at 60/40 split improves pass rate over single-agent baseline on eve_market_tools (4 checkpoints).

**Bead:** sc-hypotheses.286.2

**Verdict:** INCONCLUSIVE (both arms errored mid-run; both scored poorly even on completed checkpoints)

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
| cp1 | 30.0% (3/10) | 10 | $0.50 | 0.428 | 0.045 |
| cp2 | 25.0% (7/28) | 28 | $0.73 | 0.428 | 0.045 |
| cp3-cp4 | skipped (timeout on cp2) | - | - | - | - |
| **Mean** | **27.5% (2/4 cp)** | - | **$1.23** | - | - |

The baseline completed checkpoint 1 and timed out on checkpoint 2 (Claude Code process timeout). Checkpoints 3 and 4 were skipped.

### Two-Agent (60/40)

| Checkpoint | Pass Rate | Tests | Cost | Erosion | Verbosity |
|------------|-----------|-------|------|---------|-----------|
| cp1 | 0.0% (0/10) | 10 | $0.87 | 0.0 | 0.0 |
| cp2 | 25.0% (7/28) | 28 | $1.33 | 0.787 | 0.021 |
| cp3-cp4 | timed out (3600s limit) | - | - | - | - |
| **Mean** | **12.5% (2/4 cp)** | - | **$2.21** | - | - |

The two-agent runner completed 2 checkpoints before the pipeline's 3600s timeout. On checkpoint 1, the implementer produced code that failed all 10 tests (0% pass rate), suggesting a fundamental implementation error. On checkpoint 2, the system matched the baseline's 25%.

The checkpoint_results.jsonl shows multiple phases. After the reviewer modified cp1 code and the implementer re-ran, a later iteration achieved 30% on cp1 (matching baseline), but the canonical two_agent_metrics.json records cp1 at 0%.

### Comparison (on completed checkpoints)

| Metric | Baseline | Two-Agent (60/40) | Delta |
|--------|----------|-------------------|-------|
| cp1 pass rate | 30.0% | 0.0% | -30.0pp |
| cp2 pass rate | 25.0% | 25.0% | 0.0pp |
| Mean pass rate | 27.5% | 12.5% | -15.0pp |
| Total cost | $1.23 | $2.21 | +$0.98 |
| Checkpoints completed | 2/4 | 2/4 | 0 |

## Cost Analysis

| Metric | Baseline | Two-Agent |
|--------|----------|-----------|
| Cost per checkpoint | $0.62 avg | $1.10 avg |
| Total cost | $1.23 | $2.21 |
| Cost multiplier | 1x | 1.8x per cp |
| Implementer tokens (cp1) | N/A | 108,147 |
| Reviewer tokens (cp1) | N/A | 1,797,763 |
| Implementer tokens (cp2) | N/A | 343,875 |
| Reviewer tokens (cp2) | N/A | 1,500,103 |

The reviewer consumed far more tokens than the implementer on both checkpoints. On cp1, the reviewer used 16.6x more tokens than the implementer, suggesting extensive review cycles that ultimately failed to produce passing code.

## Interpretation

**The result is INCONCLUSIVE** because both arms failed to complete more than 2 of 4 checkpoints, and both scored poorly even on completed checkpoints.

Three observations:

1. **eve_market_tools is hard for both approaches.** The baseline achieved only 30% on cp1 and 25% on cp2. This is a difficult EVE Online SDE problem where even the single-agent struggles. Neither approach demonstrates competence on this problem.

2. **The two-agent pattern scored 0% on cp1.** The implementer produced fundamentally broken code that failed all 10 tests, while the baseline managed 30%. The reviewer's feedback did not help; it consumed 1.8M tokens without fixing the core issue.

3. **On cp2, both approaches converge at 25%.** This suggests the underlying difficulty is in the problem specification rather than the agent architecture, since both approaches hit the same ceiling.

## Confounds

- N=1 per condition (no variance estimation).
- Both arms truncated by timeouts after 2/4 checkpoints.
- The baseline timeout was per-checkpoint (agent timeout), while the two-agent timeout was total wall clock (3600s pipeline limit).
- Low baseline pass rates (27.5%) make delta comparisons less meaningful.
- The two_agent_metrics.json records cp1=0% from an early phase, but a later iteration achieved 30%. The multi-phase nature of the two-agent runner makes it unclear which pass rate is canonical.

## Run Artifacts

### Output Directories
- Baseline: `outputs/baseline_claude_code_local/local-claude-sonnet-4-6_eve_market_tools_20260404_170043/`
- Two-agent: `outputs/two_agent_local-claude-sonnet-4-6_eve_market_tools_20260404_172319_b8cece44a44e/`

### Dolt Experiment IDs
- Baseline: 596
- Two-agent: 597

### Budget Impact
- Total experiment cost: $3.44 ($1.23 + $2.21)
- Budget remaining: $649.36
