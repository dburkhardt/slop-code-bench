# Experiment Report: H-coverage trajectory_api (sc-hypotheses.286.12)

## Overview

| Field | Value |
|-------|-------|
| Problem | trajectory_api |
| Model | claude_code_local/local-claude-sonnet-4-6 |
| Budget | $5/arm |
| Budget Split | 60/40 (implementer/reviewer) |
| Hypothesis | sc-hypotheses.286 (baseline coverage across 20 problems) |
| Date | 2026-04-04 |

## Baseline (Single-Agent)

The single-agent baseline ran 4 of 5 checkpoints. The agent timed out on checkpoint 4 (EBNF grammar/tool-use tracking), causing checkpoint 5 to be skipped.

| Checkpoint | Pass Rate | State | Cost | Steps | LOC |
|------------|-----------|-------|------|-------|-----|
| 1 | 93.75% (60/64) | ran | $1.12 | 19 | 546 |
| 2 | 86.99% (127/146) | ran | $0.82 | 18 | 866 |
| 3 | 90.23% (231/256) | ran | $0.69 | 20 | 1066 |
| 4 | 65.07% (231/355) | error | $0.08 | 4 | 1066 |
| 5 | — | skipped | — | — | — |

**Totals:** Mean pass rate = 84.01%, Total cost = $2.72

**Quality metrics (final evaluated checkpoint):**
- Verbosity: 5.25%
- Erosion (high_cc_pct): 72.25%
- CC max: 39, CC mean: 6.5
- Clone lines: 56, AST-grep violations: 0

### Observations

Checkpoint 4 introduced the EBNF grammar parsing feature, a major spec extension. The agent timed out after only 4 steps (of 100 allowed), spending $0.08. The code was unchanged from checkpoint 3, so checkpoint 4's pass rate reflects only regression tests passing (231/256 from prior checkpoints), with 0/99 new tests passing. This confirms trajectory_api checkpoint 4 is a complexity cliff.

## Two-Agent (60/40 Split)

The two-agent arm timed out after the overall 3600s pipeline limit. It completed only checkpoint 1 fully (implementer + reviewer cycle). The implementer's initial attempt at checkpoint 1 failed entirely (0/64 tests), but the reviewer agent rewrote the code and achieved 93.75% (60/64), matching the baseline.

### Implementer vs. Reviewer (Checkpoint 1)

| Phase | Pass Rate | Cost | Steps | LOC |
|-------|-----------|------|-------|-----|
| Implementer | 0.0% (0/64) | $0.25 | 4 | 211 |
| Reviewer | 93.75% (60/64) | $0.73 | 12 | 395 |

The implementer produced minimal, non-functional code (211 LOC, cc_max=43). The reviewer effectively started over and wrote a correct implementation (395 LOC). This consumed $0.98 for checkpoint 1 alone.

The pipeline then continued evaluating using the reviewer's code as the base for subsequent checkpoints (cp2: 93.15%, cp3: 94.53%, cp4: 68.45%), but the two-agent orchestration loop completed only checkpoint 1 before the 3600s timeout.

### Two-Agent Cost Breakdown

- Cumulative cost: $2.72
- Budget exceeded: No (under $5 limit)
- Completed orchestration loops: 1 (checkpoint 1 only)
- Tokens: 160,574 (implementer) + 2,009,786 (reviewer) for checkpoint 1

The reviewer consumed 12.5x more tokens than the implementer, suggesting the reviewer essentially rewrote the solution rather than performing targeted fixes.

## Comparison

| Metric | Baseline | Two-Agent |
|--------|----------|-----------|
| Checkpoints completed | 4 (cp5 skipped) | 1 (timeout) |
| cp1 pass rate | 93.75% | 93.75% (after reviewer) |
| cp2 pass rate | 86.99% | — (not reached in loop) |
| cp3 pass rate | 90.23% | — |
| Mean pass rate (evaluated) | 84.01% | 69.98%* |
| Total cost | $2.72 | $2.72 |
| Time to complete | 2215s | >3600s (timeout) |

*Two-agent mean includes the implementer's 0% on cp1, which inflates the denominator. Using only the reviewer's final results for each checkpoint would yield ~87.2%.

## Key Findings

1. **Two-agent is substantially slower for complex problems.** The implementer-reviewer loop doubled the wall-clock time per checkpoint. For trajectory_api, which has 5 checkpoints with escalating complexity, the two-agent arm could not finish in the 3600s budget.

2. **Checkpoint 4 is a complexity cliff.** Both arms failed on checkpoint 4 (EBNF grammar parsing). The baseline agent timed out after 4 steps. The two-agent arm never reached it in the orchestration loop.

3. **Reviewer compensated for implementer failure.** The implementer produced non-functional code on checkpoint 1, but the reviewer rewrote it to match baseline quality. This suggests the two-agent pattern adds resilience but at a significant time cost.

4. **Token efficiency is poor in two-agent mode.** The reviewer used 12.5x more tokens than the implementer for checkpoint 1, indicating a near-complete rewrite rather than targeted review. The 60/40 budget split allocated $3 to the implementer and $2 to the reviewer, but the actual work distribution was inverted.

## Data Verification

Both baseline and two-agent experiment rows were successfully inserted into the Dolt `experiments` table with hypothesis_id `sc-hypotheses.286`.

## Conclusion

For trajectory_api at the $5 budget, the single-agent baseline outperforms the two-agent (60/40) configuration on throughput (4 vs 1 completed checkpoint loops). Both achieve identical pass rates on checkpoint 1 (93.75%), but the two-agent arm cannot progress through the problem's 5 checkpoints within the time budget. The trajectory_api problem's escalating complexity, particularly the EBNF parsing in checkpoint 4, represents a boundary condition where neither configuration achieves full coverage.
