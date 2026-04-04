# H287 Exp B6.1: metric_transform_lang replication run 1

**Hypothesis:** Two-agent benefit on metric_transform_lang replicates across additional runs (60/40 split, $5/arm).

**Bead:** sc-hypotheses.287.1

**Verdict:** MIXED (reviewer achieves 100% on cp1 but degrades severely on later checkpoints; baseline only completed 1 checkpoint)

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
| cp1 | 37.0% | 17/46 | $0.21 | error |
| cp2-5 | N/A | N/A | N/A | not reached |
| **Mean** | **37.0%** | | **$0.21** | |

The baseline timed out on cp1, producing a partial implementation that passed 17/46 tests. This matches prior runs where metric_transform_lang cp1 exceeds single-checkpoint time budgets for the implementer alone.

### Two-Agent (60/40)

The two-agent runner completed 1 implementer-reviewer cycle before the 3600s timeout. The implementer produced the same 37% cp1 result, then the reviewer substantially improved it to 100% on cp1. However, the improved cp1 code was carried forward through cp2-cp5 without further implementer work, and pass rates degraded sharply as new checkpoint specs diverged from the cp1-only implementation.

| Checkpoint | Role | Pass Rate | Tests (passed/total) | Cost | State |
|-----------|------|-----------|---------------------|------|-------|
| cp1 | Implementer | 37.0% | 17/46 | $0.00* | error |
| cp1 | Reviewer | **100.0%** | 46/46 | $1.30 | ran |
| cp2 | Reviewer | 59.2% | 58/98 | $0.67 | ran |
| cp3 | Reviewer | 13.5% | 22/163 | $1.14 | ran |
| cp4 | Reviewer | 11.6% | 26/225 | $0.87 | ran |
| cp5 | Reviewer | 6.8% | 5/74 | $0.31 | error |
| **Mean (reviewer)** | | **38.2%** | | **$4.28** | |

*Implementer cost reported as $0.00 due to cost tracking through the two-agent runner subprocess.

### Quality Metrics (Two-Agent Reviewer)

| Checkpoint | LOC | Erosion | Verbosity |
|-----------|-----|---------|-----------|
| cp1 | 1058 | 0.646 | 0.032 |
| cp2 | 1042 | 0.663 | 0.033 |
| cp3 | 1021 | 0.661 | 0.033 |
| cp4 | 976 | 0.640 | 0.035 |
| cp5 | 976 | 0.640 | 0.035 |

LOC decreased slightly across checkpoints (1058 to 976) as the reviewer trimmed code. Erosion remained stable around 0.65. Verbosity stayed low at ~0.03.

## Cost Analysis

| Metric | Baseline | Two-Agent |
|--------|---------|-----------|
| Total cost | $0.21 | $4.28 |
| Checkpoints with data | 1 | 5 |
| Pipeline wall time | ~10 min | ~60 min (timed out) |

## Interpretation

Three findings from this replication run:

1. **Reviewer achieves 100% on cp1, confirming the H286 finding.** The reviewer agent transformed a 37% implementer solution into a fully passing cp1 implementation. This replicates the prior observation that reviewers can rescue poor initial implementations at the cost of additional compute.

2. **Pass rates decay monotonically across later checkpoints.** With no additional implementer work, the cp1-optimized code scored 59% on cp2, 14% on cp3, 12% on cp4, and 7% on cp5. This confirms that reviewer improvements are checkpoint-specific and do not generalize to evolving specifications. The two-agent runner's timeout prevented the implementer from iterating on cp2+.

3. **The 60/40 split at $5 is insufficient for metric_transform_lang.** The implementer arm ($3/checkpoint) produces the same 37% partial solution as the baseline ($5 total), and the reviewer arm ($2/checkpoint) can fix cp1 but runs out of compute before cycling back through cp2-cp5 with a new implementer pass. This problem needs either higher budget or a wider budget split favoring the implementer.

**Comparison with H286 run:** The H286 metric_transform_lang experiment also saw baseline at 37% cp1 and reviewer breakthrough to ~98% on cp1. This run's reviewer achieved 100% (vs 97.8%), a consistent result. The decay pattern on cp2-cp5 is new data not available in H286.

## Dolt Records

- Baseline: experiment id=604
- Two-agent: experiment id=605
- Budget updated: +$4.50

## Raw Data

- Baseline output: `outputs/baseline_claude_code_local/local-claude-sonnet-4-6_metric_transform_lang_20260404_195841/`
- Two-agent output: `outputs/two_agent_local-claude-sonnet-4-6_metric_transform_lang_20260404_200943_383089742fc6/`
- Two-agent metrics: `two_agent_metrics.json` (cumulative_cost: $4.28, 1 completed implementer-reviewer cycle)
