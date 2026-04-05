# H287 Exp B6.4: file_merger replication run 1

**Hypothesis:** Two-agent benefit on file_merger replicates across additional runs (60/40 split, $5/arm).

**Bead:** sc-hypotheses.287.4

**Verdict:** NEGATIVE (two-agent achieves same peak pass rate as baseline, no improvement; timed out cycling on cp1)

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
| cp1 | 87.0% | 40/46 | $0.22 | error |
| cp2-4 | N/A | N/A | N/A | skipped |
| **Mean** | **87.0%** | | **$0.22** | |

The baseline timed out on cp1 at 620s but produced a strong implementation passing 40/46 tests. Only cp1 was reached before timeout.

### Two-Agent (60/40)

The two-agent runner ran 5 cycles on cp1 before hitting the 3600s timeout. It never advanced to cp2. The best pass rate matched the baseline (87.0%), achieved during the second implementer pass. Subsequent cycles degraded rather than improved.

| Cycle | Role | Pass Rate | Tests (passed/total) | Cost | LOC | State |
|-------|------|-----------|---------------------|------|-----|-------|
| 1 | Implementer | 15.2% | 7/46 | $0.00* | 0 | error |
| 1 | Reviewer | 15.2% | 7/46 | $0.08 | 0 | error |
| 2 | Implementer | **87.0%** | 40/46 | $0.26 | 510 | error |
| 2 | Reviewer | 87.0% | 40/46 | $0.34 | 548 | error |
| 3 | Implementer | 52.2% | 24/46 | $0.34 | 1302 | error |

*Cycle 1 implementer cost reported as $0.00 due to cost tracking through subprocess.

### Quality Metrics (Two-Agent, best result: Cycle 2)

| Metric | Implementer (cycle 2) | Reviewer (cycle 2) | Baseline |
|--------|----------------------|-------------------|----------|
| LOC | 510 | 548 | 440 |
| CC concentration | 0.483 | 0.455 | 0.431 |
| mass.high_cc_pct | 0.571 | 0.353 | N/A |
| Verbosity flags | 14 | 12 | 20 |
| Clone lines | 14 | 12 | 20 |

The reviewer slightly reduced verbosity (14 to 12 flagged lines) and LOC grew modestly (510 to 548), but no pass rate improvement occurred. The baseline produced cleaner code (440 LOC vs 510-548).

## Cost Analysis

| Metric | Baseline | Two-Agent |
|--------|---------|-----------|
| Total cost | $0.22 | $0.68 |
| Checkpoints with data | 1 | 1 (cp1 only) |
| Pipeline wall time | ~10 min | ~60 min (timed out) |
| Cost efficiency | $0.22/cp at 87% | $0.68/cp at 87% |

## Interpretation

Three findings from this replication run:

1. **Two-agent provides no pass rate benefit on file_merger cp1.** The baseline achieved 87.0% on its own. The two-agent system reached the same 87.0% during its second implementer pass, but the reviewer could not push beyond that ceiling. This contrasts with the metric_transform_lang result (H287.1) where the reviewer rescued a 37% implementer solution to 100%.

2. **Later cycles degrade rather than improve.** The third implementer pass dropped to 52.2% with 1302 LOC (2.5x the baseline). This pattern suggests the iterative feedback loop can amplify code bloat without improving correctness, particularly when the initial implementation is already strong.

3. **The 3600s timeout prevented checkpoint advancement.** All 5 cycles were spent on cp1. At $0.68 of the $5 budget, the runner had ample funds remaining but was time-constrained. file_merger cp1 appears to be a relatively easy problem where the single-agent approach is sufficient, making the two-agent overhead pure cost.

**Comparison with H287.1 (metric_transform_lang):** The metric_transform_lang baseline scored 37% on cp1, while the file_merger baseline scored 87%. The reviewer adds value when the implementer produces a weak initial solution (37%) but cannot improve an already-strong one (87%). This is consistent with the hypothesis that two-agent benefit depends on problem difficulty.

## Dolt Records

- Baseline: experiment id=633
- Two-agent: experiment id=634
- Budget updated: +$0.90

## Raw Data

- Baseline output: `outputs/baseline_claude_code_local/local-claude-sonnet-4-6_file_merger_20260405_042100/`
- Two-agent output: `outputs/two_agent_local-claude-sonnet-4-6_file_merger_20260405_043128_f06fb9a7648c/`
- Two-agent metrics: `two_agent_metrics.json` (cumulative_cost: $0.68, 2 completed checkpoints in metrics, 5 cycles run on cp1)
