# Experiment Report: H-coverage eve_jump_planner (sc-hypotheses.286.7)

## Overview

| Field | Value |
|-------|-------|
| Problem | eve_jump_planner |
| Model | claude_code_local/local-claude-sonnet-4-6 |
| Budget | $5/arm |
| Budget Split | 60/40 (implementer/reviewer) |
| Hypothesis | sc-hypotheses.286 (baseline coverage across 20 problems) |
| Date | 2026-04-05 |

## Baseline (Single-Agent)

The single-agent baseline timed out on checkpoint 1 after 1107 seconds. The agent received the full EVE Online Jump Freighter planner specification but could not produce a working solution within the time limit. Checkpoints 2 and 3 were skipped.

| Checkpoint | Pass Rate | State | Cost | Steps | LOC |
|------------|-----------|-------|------|-------|-----|
| 1 | 0.0% (0/11) | error | $0.00 | 0 | 0 |
| 2 | -- | skipped | -- | -- | -- |
| 3 | -- | skipped | -- | -- | -- |

**Totals:** Mean pass rate = 0.0%, Total cost = $0.00 (local model, no API cost reported), Duration = 1107s

**Quality metrics:** All zeros. The agent produced no evaluable code in the snapshot directory before the timeout.

### Observations

The specification is unusually complex: it requires parsing compressed EVE Online SDE data files, computing 3D distances in light-years using double precision, implementing a pathfinding algorithm with a multi-criteria midpoint selection heuristic, and computing jump fatigue/cooldown with ceiling rounding. The agent spent its entire budget on a single long generation step (step 0: 143s API, step 1: 964s API) without completing the code.

## Two-Agent (60/40 Split)

The two-agent arm ran two full orchestration cycles before hitting the 3600s pipeline timeout. Neither cycle produced code that passed any tests.

### Cycle 1 (Checkpoint 1)

| Phase | Pass Rate | Cost | Steps | Duration |
|-------|-----------|------|-------|----------|
| Implementer | 0.0% (0/11) | $0.00 | 0 | 968s (timeout) |
| Reviewer | 0.0% (0/11) | $0.12 | 9 | 665s |

The implementer timed out, producing no evaluable code. The reviewer attempted 9 steps at a cost of $0.12 (193K tokens) but could not produce passing code from nothing.

### Cycle 2 (Checkpoint 1, second iteration)

| Phase | Pass Rate | Cost | Steps | Duration |
|-------|-----------|------|-------|----------|
| Implementer | 0.0% (0/11) | $0.00 | 0 | 1062s (timeout) |
| Reviewer | 0.0% (0/11) | $0.24 | 18 | 707s |

The second iteration repeated the pattern: implementer timeout, reviewer unable to recover. The reviewer's effort doubled (18 steps, 456K tokens, $0.24) compared to cycle 1.

### Two-Agent Cost Breakdown

- Cumulative cost: $0.36
- Completed orchestration cycles: 2 (both on checkpoint 1)
- Checkpoints 2-3 were never attempted
- No code was produced in any snapshot directory

## Comparison

| Metric | Baseline | Two-Agent |
|--------|----------|-----------|
| Checkpoints completed | 0 | 0 |
| cp1 pass rate | 0.0% | 0.0% |
| Mean pass rate | 0.0% | 0.0% |
| Total cost | $0.00 | $0.36 |
| Duration | 1107s | >3600s (pipeline timeout) |
| Code produced | No | No |

## Key Findings

1. **eve_jump_planner is unsolvable at $5 budget with sonnet-4-6.** Neither arm produced any passing tests across any checkpoint. The problem requires domain-specific knowledge (EVE Online SDE format, bzip2 CSV parsing) combined with algorithmic complexity (pathfinding with fatigue mechanics), making it one of the hardest problems in the benchmark.

2. **The specification exceeds the agent's single-step generation capacity.** The baseline agent spent over 16 minutes on a single API call and still timed out. This suggests the spec length and complexity overwhelm the model's ability to produce a complete implementation in the allowed time.

3. **Two-agent overhead with no benefit.** The two-agent arm spent $0.36 and over 3600 seconds for the same zero-pass outcome. The reviewer cannot add value when the implementer fails to produce code.

4. **Zero LOC in all snapshots.** The agent process timed out before any code was written to the snapshot directory. This is distinct from problems where code is produced but fails tests; here, the agent never finished generating a response.

5. **The reviewer escalates cost on empty input.** In cycle 2, the reviewer spent 18 steps and $0.24 attempting to work from an empty codebase, double the effort of cycle 1. The two-agent runner should detect zero-LOC implementer output and skip the reviewer pass.

## Data Verification

Both baseline and two-agent experiment rows were inserted into the Dolt `experiments` table with hypothesis_id `sc-hypotheses.286`. Verified 2 rows present for problem_id `eve_jump_planner`.

## Conclusion

eve_jump_planner represents a ceiling problem for sonnet-4-6 at the $5 budget: the specification is too complex for the agent to produce any code within the time limits. Both arms score identically at 0% pass rate with zero LOC. The two-agent arm's only distinguishing feature is higher cost ($0.36 vs $0.00) from futile reviewer attempts. This problem may require either a more capable model, a higher budget, or a decomposed approach where the spec is broken into smaller subtasks. It serves as a useful lower bound in the H-coverage baseline, marking the threshold where the agent cannot engage with the problem at all.
