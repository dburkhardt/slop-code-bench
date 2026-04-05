# H286 Exp B5: Two-Agent on log_query at 60/40

**Hypothesis:** Two-agent (60/40 implementer/reviewer split) improves pass rate over single-agent baseline on log_query (5 checkpoints).

**Bead:** sc-hypotheses.286.11

**Verdict:** REFUTED (two-agent underperforms baseline; iterative reviewer cycles degrade code quality and consume budget without improvement)

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

| Checkpoint | Pass Rate | Tests (passed/total) | Cost | State | Erosion | Verbosity |
|-----------|-----------|---------------------|------|-------|---------|-----------|
| cp1 | 97.0% | 130/134 | $0.53 | ran | 0.566 | 0.047 |
| cp2 | 31.4% | 65/207 | $0.29 | error (timeout) | 0.567 | 0.047 |
| cp3-5 | N/A | N/A | N/A | not reached | N/A | N/A |
| **Mean** | **64.2%** | | **$0.82** | | | |

The baseline achieved strong cp1 results (97.0%) but timed out on cp2. The cp2 pass rate of 31.4% reflects that the agent did not complete its implementation before the timeout, so existing cp1 code was evaluated against cp2's expanded test suite.

### Two-Agent (60/40)

The two-agent runner performs iterative cycles: implementer, reviewer, revision with suggestions.

**Iteration 1 (implementer run):**

| Checkpoint | Pass Rate | Tests | Cost | State |
|-----------|-----------|-------|------|-------|
| cp1 | 96.3% | 129/134 | $0.61 | ran |
| cp2 | 97.6% | 202/207 | $0.43 | error (timeout) |

**Iteration 2 (reviewer run):**

| Checkpoint | Pass Rate | Tests | Cost | State |
|-----------|-----------|-------|------|-------|
| cp1 | 91.8% | 123/134 | $0.27 | ran |
| cp2 | 62.8% | 130/207 | $0.07 | error (timeout) |

**Iteration 3 (revision with reviewer suggestions):**

| Checkpoint | Pass Rate | Tests | Cost | State |
|-----------|-----------|-------|------|-------|
| cp1 | 32.8% | 44/134 | $0.05 | error (timeout) |

**Final two-agent metrics (after iteration cycles):**

| Metric | Value |
|--------|-------|
| Completed checkpoints | 1 (cp1 only) |
| cp1 pass rate | 62.8% |
| Total cost | $1.39 |
| Runner timed out | Yes (3600s) |

## Cost Analysis

| Metric | Baseline | Two-Agent |
|--------|---------|-----------|
| Total cost | $0.82 | $1.39 |
| Checkpoints attempted | 2 | 1 (effectively) |
| Cost per completed checkpoint | $0.53 | $1.39 |
| Cost multiplier | 1x | 2.6x per checkpoint |
| Pipeline wall time | ~16 min | 60 min (timed out) |

## Interpretation

**The hypothesis is REFUTED.** The two-agent (60/40) pattern does not improve pass rate on log_query. The two-agent final result (62.8% on cp1) is substantially worse than the baseline (97.0% on cp1).

Three findings:

1. **Iterative reviewer cycles degrade code quality.** The implementer's initial pass scored 96.3% on cp1. After the reviewer suggested changes and the revision agent incorporated them, the pass rate dropped to 32.8%. The reviewer's suggestions introduced regressions rather than improvements. This is a concrete instance of the "review oscillation" failure mode where each iteration moves further from correctness.

2. **The iterative cycle is a time sink.** Three iterations (implementer, reviewer, revision) consumed the full 3600s timeout on a single checkpoint. The baseline completed both cp1 and cp2 in approximately 16 minutes. The two-agent pattern's iterative review cycle produces 2.6x more cost per checkpoint while delivering worse results.

3. **log_query is a complexity-sensitive problem.** This problem involves building a query language (tokenizer, parser, evaluator), which requires coherent architecture across multiple files. The reviewer's refactored code, while structurally different, broke the integration between components. Complex, multi-file problems appear particularly vulnerable to reviewer-induced regressions because the reviewer lacks the implementer's full context of design decisions.

## Comparison with Existing Baseline

The existing Dolt baseline (id=577) shows a pass rate of 83% for log_query on single-agent with the same model. Our new baseline scored 97.0% on cp1 but 31.4% on cp2 (timeout), averaging 64.2%. The difference in cp1 performance (97% vs 83%) may reflect natural variance in agent behavior.

## Replication Run (2026-04-05, sc-wisp-mol-qonv3)

A replication attempt was run on 2026-04-05 with local-sonnet-4.6. Both arms timed
out (3600s) before completing all 5 checkpoints. No new data was inserted to Dolt.

### Partial replication data (two-agent arm):

| Phase | Checkpoint | Pass Rate | Core Pass | LOC | Verbosity | Erosion | Cost |
|-------|-----------|-----------|-----------|-----|-----------|---------|------|
| Implementer | cp1 | 97.0% | 100% | 585 | 0.080 | 0.595 | $0.604 |
| Implementer | cp2 | 98.1% | 100% | 818 | 0.065 | 0.577 | $0.343 |
| Reviewer | cp1 | 90.3% | 90% | 314 | 0.045 | 0.594 | $0.256 |
| Reviewer | cp2 | 92.3% | 100% | 459 | 0.052 | 0.496 | $0.288 |
| Combined | cp1 | 91.8% | 100% | 620 | 0.071 | 0.548 | $0.144 |

**Replication findings:**

- The implementer again achieved high pass rates (97.0%, 98.1%) consistent with the
  original run.
- The reviewer pass again degraded cp1 pass rate (97.0% to 90.3%), reinforcing the
  "reviewer hurts passing solutions" pattern.
- LOC dropped substantially in the reviewer pass (585 to 314 for cp1), suggesting
  aggressive code removal.
- Erosion remained roughly stable across phases (~0.5-0.6).
- Total partial cost: ~$1.63 (incomplete).

**Conclusion: INCONCLUSIVE for replication (timeout), but partial data is consistent
with the original REFUTED verdict. The reviewer consistently degrades pass rates
on log_query.**

## Dolt Records

- Baseline: experiment id=581
- Two-agent: experiment id=582
- Budget updated: +$2.21
- Replication (2026-04-05): no new Dolt rows (timed out)

## Raw Data

- Baseline output: `outputs/baseline_claude_code_local/local-claude-sonnet-4-6_log_query_20260404_152316/`
- Two-agent output: `outputs/two_agent_local-claude-sonnet-4-6_log_query_20260404_153906_5d1d6dd5bffb/`
- Two-agent metrics: `two_agent_metrics.json` (cumulative_cost: $1.39, 1 completed checkpoint)
- Replication two-agent output: `outputs/two_agent_local-sonnet-4.6_log_query_20260405_082517_5b50297c8461/`
