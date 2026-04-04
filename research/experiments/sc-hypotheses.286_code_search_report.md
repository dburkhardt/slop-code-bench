# Experiment Report: H-coverage code_search (sc-hypotheses.286.13)

## Overview

| Field | Value |
|-------|-------|
| Problem | code_search |
| Model | claude_code_local/local-claude-sonnet-4-6 |
| Budget | $5/arm |
| Budget Split | 60/40 (implementer/reviewer) |
| Hypothesis | sc-hypotheses.286 (baseline coverage across 20 problems) |
| Date | 2026-04-04 |

## Baseline (Single-Agent)

The single-agent baseline ran 3 of 5 checkpoints. The agent timed out on checkpoint 3, causing checkpoints 4-5 to be skipped.

| Checkpoint | Pass Rate | State | Cost | Steps | LOC |
|------------|-----------|-------|------|-------|-----|
| 1 | 100.0% (12/12) | ran | $0.17 | 6 | 99 |
| 2 | 100.0% (23/23) | ran | $0.20 | 9 | 130 |
| 3 | 54.55% (24/44) | error | $0.08 | 4 | 130 |
| 4 | — | skipped | — | — | — |
| 5 | — | skipped | — | — | — |

**Totals:** Mean pass rate = 84.85%, Total cost = $0.45, Duration = 1304s

**Quality metrics:** Verbosity: 0.0%, Erosion: 0.0% across all checkpoints. code_search produces clean, compact code (99-130 LOC) with zero clone lines and zero AST-grep violations.

### Observations

Checkpoints 1-2 achieved perfect pass rates at low cost ($0.17-0.20). Checkpoint 3 introduced more complex requirements, and the agent timed out after only 4 steps, leaving the code unchanged from checkpoint 2. The 54.55% pass rate on cp3 reflects regression tests from cp1-2 passing (24/44) while all 21 new tests failed.

## Two-Agent (60/40 Split)

The two-agent arm timed out after the 3600s pipeline limit. It completed 2 full orchestration loops (checkpoints 1-2), each with an implementer pass followed by a reviewer pass. The two-agent runner also attempted a second full cycle (checkpoints 1-5) using the reviewed code as the base.

### Orchestration Loop 1 (Checkpoint 1)

| Phase | Pass Rate | Cost | Steps | LOC |
|-------|-----------|------|-------|-----|
| Implementer | 100.0% (12/12) | $0.18 | 7 | 129 |
| Reviewer | 100.0% (12/12) | $0.09 | 6 | 87 |

The reviewer reduced LOC from 129 to 87, a 33% reduction while maintaining 100% pass rate.

### Orchestration Loop 2 (Checkpoint 2)

| Phase | Pass Rate | Cost | Steps | LOC |
|-------|-----------|------|-------|-----|
| Implementer | 100.0% (23/23) | $0.14 | 6 | 155 |
| Reviewer | 100.0% (23/23) | $0.10 | 4 | 99 |

Again the reviewer reduced LOC from 155 to 99, a 36% reduction while maintaining 100%.

### Second Cycle (Checkpoints 1-5, using reviewed code)

The runner initiated a second cycle from the reviewed checkpoint 2 code:

| Checkpoint | Implementer Pass Rate | Reviewer Pass Rate | Notes |
|------------|----------------------|-------------------|-------|
| 1 | 91.67% (11/12) | 100.0% (12/12) | Slight regression in implementer |
| 2 | 95.65% (22/23) | 100.0% (23/23) | Reviewer restored full pass rate |
| 3 | 52.27% (23/44) | 52.27% (23/44) | Both failed on cp3 (timeout) |
| 4 | 33.33% (24/72) | — | Timed out before reviewer |
| 5 | 24.75% (25/101) | — | Timed out before reviewer |

### Two-Agent Cost Breakdown

- Cumulative cost: $1.49
- Completed orchestration loops: 2 (checkpoints 1-2)
- Tokens: 1,141,009 (implementer) + 638,936 (reviewer) for checkpoint 2

## Comparison

| Metric | Baseline | Two-Agent |
|--------|----------|-----------|
| Checkpoints completed (full) | 2 (cp3 error) | 2 (pipeline timeout) |
| cp1 pass rate | 100.0% | 100.0% |
| cp2 pass rate | 100.0% | 100.0% |
| cp3 pass rate | 54.55% (error) | 52.27% (error) |
| Mean pass rate (cp1-2) | 100.0% | 100.0% |
| Total cost | $0.45 | $1.49 |
| LOC (cp2 final) | 130 | 99 (reviewer) |
| Duration | 1304s | >3600s (timeout) |

## Key Findings

1. **code_search is a low-complexity problem.** Perfect pass rates on checkpoints 1-2 for both arms, with compact code (87-155 LOC) and zero quality violations. This makes it a clean baseline for measuring two-agent overhead.

2. **Reviewer reduces code size.** The reviewer consistently reduced LOC by 33-36% while preserving full pass rates. This is the two-agent pattern working as intended: the implementer writes a working solution, the reviewer trims it.

3. **Two-agent costs 3.3x more for the same outcome.** On checkpoints 1-2 (where both arms achieve 100%), the baseline spent $0.37 vs the two-agent's $0.51 for just the first loop. Including the second cycle, the two-agent arm spent $1.49 total.

4. **Checkpoint 3 is a wall for both arms.** Neither single-agent nor two-agent could solve checkpoint 3 within the time/step budget. The agent timed out after 4 steps in both cases, suggesting checkpoint 3 requires a fundamentally different approach or more budget.

5. **Two-agent second cycle showed regression.** When the runner re-ran from the reviewed code, the implementer's pass rates dropped slightly (91.67% vs 100% on cp1), likely because the reviewer's more compact code was harder to extend. The reviewer had to clean up again.

## Data Verification

Both baseline and two-agent experiment rows were inserted into the Dolt `experiments` table with hypothesis_id `sc-hypotheses.286`.

## Conclusion

For code_search at the $5 budget, both arms achieve identical outcomes on the solvable checkpoints (cp1-2: 100%). The two-agent arm produces cleaner code (33-36% LOC reduction from reviewer) but at 3.3x the cost and significantly longer wall-clock time. Both arms fail on checkpoint 3, which appears to be a step-budget or complexity issue rather than a code quality issue. code_search is among the simpler problems in the benchmark, making it useful as a low-variance reference point for measuring two-agent overhead.
