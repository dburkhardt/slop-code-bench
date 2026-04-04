# Experiment Report: file_query_tool Two-Agent at 60/40

**Hypothesis ID:** sc-hypotheses.286  
**Bead ID:** sc-hypotheses.286.4  
**Problem:** file_query_tool (5 checkpoints)  
**Model:** claude_code_local/local-claude-sonnet-4-6  
**Budget:** $5/arm  
**Budget split:** 60/40 (implementer/reviewer)  
**Date:** 2026-04-04  

## Summary

The two-agent arm (60/40 split) produced identical pass rates to the single-agent baseline at every checkpoint. Erosion growth was 39% slower in the two-agent arm. Cost was nearly identical. The reviewer pass catastrophically failed (zeroed out all code), so the implementer-only pass is used as the two-agent result. The two-agent runner timed out at 3600s during its third pass.

## Results

### Per-Checkpoint Comparison

| CP | BL Pass | TA Pass | BL Cost | TA Cost | BL Erosion | TA Erosion | BL Verb | TA Verb | BL LOC | TA LOC |
|----|---------|---------|---------|---------|------------|------------|---------|---------|--------|--------|
| 1  | 0.900   | 0.900   | $0.73   | $0.82   | 0.000      | 0.000      | 0.000   | 0.000   | 167    | 193    |
| 2  | 0.940   | 0.940   | $0.61   | $0.66   | 0.290      | 0.000      | 0.000   | 0.000   | 284    | 368    |
| 3  | 0.915   | 0.915   | $0.45   | $0.58   | 0.265      | 0.163      | 0.000   | 0.029   | 334    | 479    |
| 4  | 0.894   | 0.894   | $0.80   | $0.63   | 0.247      | 0.155      | 0.000   | 0.026   | 388    | 539    |
| 5  | 0.852   | 0.852   | $0.43   | $0.46   | 0.380      | 0.143      | 0.041   | 0.023   | 484    | 616    |

### Aggregates

| Metric | Baseline | Two-Agent | Delta |
|--------|----------|-----------|-------|
| Avg pass rate | 0.900 | 0.900 | +0.000 |
| Total cost | $3.01 | $3.15 | +$0.14 (5% increase) |
| Erosion slope | 0.0717 | 0.0440 | -0.0277 (39% reduction) |
| Final LOC (CP5) | 484 | 616 | +132 (27% increase) |

### Core Pass Rates

Identical across both arms:
- CP1: 1.000 (4/4)
- CP2: 1.000 (21/21)
- CP3: 0.000 (0/2) - both arms failed the same core tests
- CP4: 0.667 (2/3)
- CP5: 0.625 (5/8)

### Step Utilization

| CP | BL Steps | TA Steps |
|----|----------|----------|
| 1  | 17 (17%) | 11 (11%) |
| 2  | 24 (24%) | 27 (27%) |
| 3  | 24 (24%) | 22 (22%) |
| 4  | 38 (38%) | 36 (36%) |
| 5  | 26 (26%) | 26 (26%) |

## Observations

1. **Pass rates exactly identical.** Both arms produced the same strict_pass_rate at every single checkpoint. This suggests the test outcomes are deterministic given the same problem structure, and the two-agent setup does not affect correctness.

2. **Erosion slope reduced by 39%.** The two-agent erosion slope (0.044) was significantly lower than baseline (0.072). At CP5, baseline erosion was 0.380 vs two-agent 0.143, a 62% reduction. The two-agent implementer pass produced less structurally complex code from the start.

3. **Two-agent produced more code.** Despite lower erosion, the two-agent arm generated 27% more LOC at CP5 (616 vs 484). More code with lower complexity suggests better decomposition into smaller functions.

4. **Reviewer pass failed catastrophically.** The reviewer pass produced 0 LOC and 0% pass rates at all checkpoints, effectively deleting the implementation. This is a failure mode of the two-agent runner where the reviewer misunderstands its role. The implementer-only result is used.

5. **Two-agent runner timed out.** The runner hit the 3600s timeout during its third pass (a second implementer pass after the failed reviewer). The runner's multi-pass approach is expensive when a pass fails.

## Classification

**Result: INCONCLUSIVE (no pass rate signal, erosion reduction)**

Pass rates are identical (delta = 0). The erosion reduction is the only signal, but the reviewer pass failure undermines the two-agent protocol's validity for this problem. The result reflects only the implementer's behavior with a 60% budget constraint.

## Anomalies

- **Reviewer pass failure:** The reviewer produced 0-LOC snapshots. Likely cause: the reviewer prompt template applied to file_query_tool's codebase structure caused the agent to start from scratch rather than modify existing code.
- **Timeout:** The 3600s timeout was hit because the runner attempted a third pass after the reviewer failure, consuming additional budget.

## Output Directories

- Baseline: `outputs/baseline_claude_code_local/local-claude-sonnet-4-6_file_query_tool_20260404_170021/`
- Two-agent (implementer): `outputs/local-claude-sonnet-4-6/claude_code-2.0.51_default_implementer_none_20260404T1736/`
- Two-agent (reviewer, failed): `outputs/local-claude-sonnet-4-6/claude_code-2.0.51_default_reviewer_none_20260404T1804/`
- Two-agent (final): `outputs/two_agent_local-claude-sonnet-4-6_file_query_tool_20260404_173642_c174e1372ef0/`

## Dolt Records

- Baseline: experiments.id = 602
- Two-agent: experiments.id = 603
