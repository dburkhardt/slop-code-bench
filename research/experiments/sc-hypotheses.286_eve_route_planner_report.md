# Experiment Report: H-coverage eve_route_planner (sc-hypotheses.286.3)

## Overview

| Field | Value |
|-------|-------|
| Problem | eve_route_planner |
| Model | claude_code_local/local-claude-sonnet-4-6 |
| Budget | $5/arm |
| Budget Split | 60/40 (implementer/reviewer) |
| Hypothesis | sc-hypotheses.286 (baseline coverage across 20 problems) |
| Date | 2026-04-04 |

## Baseline (Single-Agent)

The single-agent baseline timed out on checkpoint 1 after ~620 seconds and 7 steps. No further checkpoints were attempted.

| Checkpoint | Pass Rate | State | Cost | Steps |
|------------|-----------|-------|------|-------|
| 1 | 45.45% (5/11) | error | $0.22 | 7 |
| 2 | -- | skipped | -- | -- |
| 3 | -- | skipped | -- | -- |

**Totals:** Mean pass rate = 45.45%, Total cost = $0.22

**Quality metrics:** Erosion and verbosity both 0.0 (insufficient code produced for meaningful measurement). The agent's code passed 5 of 10 functionality tests and 0 of 1 core tests.

### Observations

The agent spent most of its 620s wall-clock time waiting for responses, completing only 7 steps before timing out. The $0.22 cost is far below the $5 budget, indicating the timeout was a wall-clock constraint, not a budget constraint. The 0/1 core test failure suggests the fundamental implementation was incomplete.

## Two-Agent (60/40 Split)

The two-agent arm completed 2 of 3 checkpoint orchestration loops before the pipeline-level 3600s timeout terminated the run.

### Per-Checkpoint Results

| Checkpoint | Phase | Pass Rate | Cost | Tokens |
|------------|-------|-----------|------|--------|
| 1 | Implementer | 45.45% (5/11) | $0.21 | 339,034 |
| 1 | Reviewer | 45.45% (5/11) | $0.13 | 109,993 |
| 2 | Implementer | 45.45% (5/11) | $0.20 | 329,905 |
| 2 | Reviewer | 45.45% (5/11) | $0.18 | 329,084 |

**Totals:** Cumulative cost = $0.71, Mean pass rate = 45.45%

### Observations

Pass rates were identical across all four phases (implementer and reviewer, checkpoints 1 and 2). The reviewer failed to improve on the implementer's output in either checkpoint. Erosion and verbosity remained at 0.0 throughout, consistent with the agent producing minimal or no code changes.

The 0/1 core test failure persisted across all phases, suggesting the fundamental architectural approach was incorrect and neither agent role could correct it within the time budget.

## Comparison

| Metric | Baseline | Two-Agent |
|--------|----------|-----------|
| Checkpoints completed | 1 (error) | 2 (timeout) |
| cp1 pass rate | 45.45% | 45.45% |
| cp2 pass rate | -- | 45.45% |
| Mean pass rate | 45.45% | 45.45% |
| Total cost | $0.22 | $0.71 |
| Delta pass rate | -- | 0.0 |
| Delta erosion | -- | 0.0 |

## Key Findings

1. **No improvement from two-agent configuration.** Pass rates were identical (45.45%) across both arms and all phases. The reviewer added no value on this problem, suggesting the implementation challenges were beyond what targeted review could address.

2. **eve_route_planner is resistant to the current agent approach.** Both arms failed the core test, indicating a fundamental gap in the agent's ability to implement the route planning logic correctly. The 45.45% pass rate came entirely from functionality tests (5/10), with 0/1 core tests passing.

3. **Low cost utilization.** The baseline used only $0.22 of its $5 budget, and the two-agent arm used $0.71. Both were constrained by wall-clock timeouts rather than budget limits, suggesting eve_route_planner triggers slow agent behavior (likely complex reasoning or repeated failed attempts).

4. **Reviewer token usage was disproportionate on checkpoint 2.** The reviewer consumed 329,084 tokens on checkpoint 2 (nearly matching the implementer's 329,905), up from 109,993 on checkpoint 1. This 3x increase suggests the reviewer attempted more extensive modifications on checkpoint 2, but without any pass rate improvement.

## Data Verification

Both baseline and two-agent experiment rows were inserted into the Dolt `experiments` table with hypothesis_id `sc-hypotheses.286` and problem_id `eve_route_planner`. Row IDs: 600 (baseline), 601 (two-agent).

## Conclusion

For eve_route_planner at the $5 budget with 60/40 split, the two-agent configuration provides no measurable benefit over the single-agent baseline. Both achieve 45.45% pass rate with 0% core test passage. The problem appears to require a fundamentally different implementation strategy that neither the implementer nor the reviewer could discover within the timeout constraints. Eve_route_planner represents a problem where the two-agent review pattern adds cost ($0.71 vs $0.22) without improving outcomes.
