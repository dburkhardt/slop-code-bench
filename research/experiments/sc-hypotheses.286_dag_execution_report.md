# Experiment Report: dag_execution Two-Agent at 60/40

**Hypothesis ID:** sc-hypotheses.286  
**Problem:** dag_execution (3 checkpoints)  
**Model:** local-sonnet-4.6  
**Budget:** $5/arm  
**Budget split:** 60/40 (implementer/reviewer)  
**Date:** 2026-04-05  

## Summary

Both single-agent and two-agent arms failed completely on dag_execution. The single-agent baseline timed out on checkpoint 1 without producing any code. The two-agent implementer pass completed all 3 checkpoints but achieved 0% pass rate. The two-agent reviewer pass completed checkpoints 1-2 but timed out on checkpoint 3, also achieving 0% pass rate throughout. No test passed across either arm.

## Results

### Baseline (Single-Agent)

| CP | State | Pass Rate | Cost | Duration |
|----|-------|-----------|------|----------|
| 1  | error (timeout) | 0.00 | $0.00 | 932s |
| 2  | skipped | - | - | - |
| 3  | skipped | - | - | - |

The baseline Claude Code process timed out on checkpoint 1 after 932 seconds (15.5 minutes). No code was produced, no cost was incurred (usage reporting failed), and checkpoints 2-3 were skipped.

### Two-Agent Implementer Pass

| CP | State | Pass Rate | Tests (passed/total) | Cost | Duration |
|----|-------|-----------|---------------------|------|----------|
| 1  | ran   | 0.00      | 0/33                | $0.05 | 7s |
| 2  | ran   | 0.00      | 0/41                | $0.68 | 367s |
| 3  | ran   | 0.00      | 0/51                | $0.06 | 16s |

The implementer completed all checkpoints but produced code that failed every test. The very short duration on CP1 (7s) and CP3 (16s) suggests the agent may have hit cost limits or errored quickly. CP2 ran for 367s, suggesting more substantial work was attempted.

### Two-Agent Reviewer Pass

| CP | State | Pass Rate | Tests (passed/total) | Cost | Duration |
|----|-------|-----------|---------------------|------|----------|
| 1  | ran   | 0.00      | 0/33                | $1.78 | 575s |
| 2  | ran   | 0.00      | 0/41                | $1.20 | 320s |
| 3  | error | 0.00      | 0/51                | $1.14 | 641s |

The reviewer spent significantly more budget per checkpoint than the implementer but failed to improve pass rates. CP3 timed out after 641s.

### Cost Summary

| Arm | Total Cost |
|-----|-----------|
| Baseline (single) | $0.00 (timed out, no usage reported) |
| Two-agent implementer | $0.79 |
| Two-agent reviewer | $4.12 |
| **Total two-agent** | **$4.91** |

## Observations

1. **Complete failure on both arms.** dag_execution requires building a custom DSL parser for pipeline definitions with features including typed parameters, expression evaluation (for/while/if), task dependency resolution, success criteria, and structured output. This level of complexity exceeds what Sonnet 4.6 can achieve within the budget and time constraints.

2. **Baseline timeout.** The single-agent arm timed out on checkpoint 1 without even starting to write code. This suggests the agent spent all its time reasoning about the specification rather than producing a solution.

3. **Implementer produced non-functional code.** Despite completing all 3 checkpoints, 0/125 total tests passed. The 7-second CP1 duration suggests the implementer may have produced a skeleton rather than a working implementation.

4. **Reviewer unable to salvage.** The reviewer spent $4.12 across 3 checkpoints but could not fix the fundamental implementation issues. This is consistent with the hypothesis that reviewer passes are more effective at reducing slop than at fixing broken implementations.

5. **Problem difficulty.** dag_execution is among the hardest problems in the benchmark. The custom DSL with nested expressions, type system, and task orchestration requires hundreds of lines of parser and interpreter code. The 0% pass rate across all arms suggests this problem may be at or beyond the frontier of what current models can solve in a single session.

## Conclusion

**INCONCLUSIVE** for the two-agent hypothesis. Neither arm produced functional code, so comparing single-agent vs two-agent quality metrics is not meaningful. dag_execution appears to be too difficult for Sonnet 4.6 to solve within a $5 budget, regardless of the agent architecture.

## Dolt Status

No data was inserted into the Dolt experiments table. The pipeline's metric extraction failed because the baseline produced no output and the two-agent arm's metrics could not be parsed into the expected format. Raw results are preserved in the checkpoint_results.jsonl files in the output directories.
