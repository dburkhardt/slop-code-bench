# Exp B8.9: code_search anti-slop replication

**Hypothesis:** sc-hypotheses.281
**Problem:** code_search (5 checkpoints)
**Model:** claude_code_local/local-claude-sonnet-4-6
**Prompt:** configs/prompts/anti_slop.jinja
**Mode:** single-agent baseline only
**Budget:** $5.00
**Actual cost:** $0.53

## Results

| Checkpoint | Pass Rate | Verbosity | Erosion | Cost ($) |
|------------|-----------|-----------|---------|----------|
| 1          | 1.000     | 0.0       | 0.0     | 0.284    |
| 2          | 1.000     | 0.0       | 0.0     | 0.151    |
| 3          | 0.523     | 0.0       | 0.0     | 0.091    |
| 4          | (skipped) | -         | -       | -        |
| 5          | (skipped) | -         | -       | -        |

**Mean pass rate (3 checkpoints):** 0.8409
**Total cost:** $0.525

## Observations

1. The anti-slop prompt achieved zero verbosity and zero structural erosion
   across all completed checkpoints.

2. Checkpoint 3 timed out (Claude Code process timeout after ~18 min),
   causing checkpoints 4-5 to be skipped. The agent produced only 5 steps
   in checkpoint 3 (vs 9 in checkpoint 1), suggesting it stalled on a
   complex spec extension rather than producing verbose code.

3. The agent maintained a stable codebase: 182 LOC at checkpoint 1,
   growing only to 186 LOC by checkpoint 2, with no change at checkpoint 3
   (zero churn). This is consistent with anti-slop behavior: the agent
   avoided rewriting working code.

4. Code structure was clean: 6 functions, max CC of 7, no high-complexity
   symbols, no clone lines, no AST-grep violations.

## Dolt verification

4 rows exist for hypothesis sc-hypotheses.281 + problem code_search,
including 1 row inserted from this run (ID 620).

## Pipeline change

Added `--single-only` flag to `research/runner/experiment_pipeline.py`
to skip the two-agent arm when only the baseline is needed.
