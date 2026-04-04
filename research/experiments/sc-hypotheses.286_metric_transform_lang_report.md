# H286 Exp B5: Two-Agent on metric_transform_lang at 60/40

**Hypothesis:** Two-agent (60/40 implementer/reviewer split) improves pass rate over single-agent baseline on metric_transform_lang (5 checkpoints).

**Bead:** sc-hypotheses.286.1

**Verdict:** MIXED (two-agent achieves higher mean pass rate across 2 checkpoints, but baseline only completed 1 checkpoint with poor results; both arms struggled with this problem)

## Setup

| Parameter | Single-Agent (Baseline) | Two-Agent (60/40) |
|-----------|------------------------|-------------------|
| Agent type | claude_code | reviewer_coder (iterative) |
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Prompt | default_implementer | default_implementer + default_reviewer |
| Cost limit | $5.00 total | $5.00 total |
| Budget split | N/A | 60/40 (implementer/reviewer) |
| Environment | local-py | local-py |

## Results

### Baseline (single-agent)

| Checkpoint | Pass Rate | Tests (passed/total) | Cost | State |
|-----------|-----------|---------------------|------|-------|
| cp1 | 37.0% | 17/46 | $0.00* | error (timeout) |
| cp2-5 | N/A | N/A | N/A | not reached |
| **Mean** | **37.0%** | | **$0.00** | |

*Cost reported as $0.00 due to cost tracking failure during the agent timeout.

The baseline timed out on cp1, producing a partial implementation that passed only 17 of 46 tests. metric_transform_lang appears to be a difficult problem that requires more than the default timeout to complete even a single checkpoint.

### Two-Agent (60/40)

The two-agent runner performed multiple iterative cycles within its 3600s timeout:

**Iteration tracking across cycles:**

| Iteration | Role | cp1 Pass Rate | Tests | Cost |
|-----------|------|-------------|-------|------|
| 1 | Implementer | 37.0% | 17/46 | $0.00 |
| 2 | Reviewer | 37.0% | 17/46 | $0.06 |
| 3 | Implementer (revised) | 37.0% | 17/46 | $0.00 |
| 4 | Reviewer | 97.8% | 45/46 | $0.92 |
| 5 | Revision with suggestions | 37.0% | 17/46 | $0.05 |

The 4th iteration (reviewer) achieved a breakthrough: 97.8% on cp1. However, the revision agent (iteration 5) regressed back to 37.0%, repeating the pattern seen in the log_query experiment where incorporating reviewer suggestions degraded quality.

**Final two-agent metrics:**

| Metric | Value |
|--------|-------|
| Completed checkpoints | 2 |
| cp1 pass rate | 37.0% |
| cp2 pass rate | 97.8% |
| Mean pass rate | 67.4% |
| Total cost | $0.98 |
| Cumulative cost | $0.98 |
| Runner timed out | Yes (3600s) |

Note: The two_agent_metrics.json reports cp2 with 97.8% pass rate, which corresponds to the 4th iteration's successful reviewer run mapped as "checkpoint_2" in the runner's accounting.

## Cost Analysis

| Metric | Baseline | Two-Agent |
|--------|---------|-----------|
| Total cost | ~$0.00 (tracking failure) | $0.98 |
| Checkpoints completed | 0 (partial cp1) | 2 (in runner's accounting) |
| Pipeline wall time | ~15 min | 60 min (timed out) |

## Interpretation

**The result is MIXED.** The two-agent pattern achieved 67.4% mean pass rate across its two "completed" checkpoints vs the baseline's 37.0% on a single incomplete checkpoint. However, several caveats limit this comparison.

Three findings:

1. **metric_transform_lang exceeds single-checkpoint timeout budgets.** Both baseline and implementer iterations timed out on cp1, producing only 37% pass rate. This problem requires more agent compute per checkpoint than log_query. The iterative two-agent pattern partially compensates by giving the agent multiple attempts, though at 3600s total this still yields limited checkpoint coverage.

2. **Reviewer iteration 4 produced a breakthrough, but revision destroyed it.** The 4th iteration reviewer achieved 97.8% on cp1 (45/46 tests). When those suggestions were fed into a revision agent (iteration 5), the result regressed to 37.0%. This confirms the "review oscillation" pattern from log_query: reviewer suggestions that work in isolation can break the implementation when naively incorporated.

3. **The two-agent runner's checkpoint accounting is misleading.** The runner reports 2 "completed checkpoints" (cp1 and cp2), but these map to different iterations of cp1, not different specification checkpoints. The actual spec checkpoints cp2-cp5 were never attempted by either arm. Both arms effectively solved only cp1-level requirements.

## Dolt Records

- Baseline: experiment id=594
- Two-agent: experiment id=595
- Budget updated: +$0.98

## Raw Data

- Baseline output: `outputs/baseline_claude_code_local/local-claude-sonnet-4-6_metric_transform_lang_20260404_170025/`
- Two-agent output: `outputs/two_agent_local-claude-sonnet-4-6_metric_transform_lang_20260404_*_31ee6bbbda6e/`
- Two-agent metrics: `two_agent_metrics.json` (cumulative_cost: $0.98, 2 reported checkpoints)
