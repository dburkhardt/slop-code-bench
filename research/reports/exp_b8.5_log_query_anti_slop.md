# Exp B8.5: log_query anti-slop replication

**Hypothesis:** sc-hypotheses.281
**Problem:** log_query (5 checkpoints)
**Model:** claude_code_local/local-claude-sonnet-4-6
**Prompt:** configs/prompts/anti_slop.jinja
**Mode:** single-agent baseline only
**Budget:** $5.00
**Actual cost:** $0.82

## Results

| Checkpoint | Pass Rate | Verbosity | Erosion | Cost ($) |
|------------|-----------|-----------|---------|----------|
| 1          | 0.978     | 0.025     | 0.434   | 0.710    |
| 2          | 0.667     | 0.025     | 0.434   | 0.114    |
| 3          | (skipped) | -         | -       | -        |
| 4          | (skipped) | -         | -       | -        |
| 5          | (skipped) | -         | -       | -        |

**Mean pass rate (2 checkpoints):** 0.8221
**Total cost:** $0.82

## Observations

1. Checkpoint 1 performed well at 97.8% pass rate with low verbosity (2.5%)
   but moderate structural erosion (43.4%). The agent produced 475 LOC across
   4 files with 42 symbols, max CC of 16, and 2 high-complexity functions.

2. Checkpoint 2 regressed to 66.7% overall pass rate. Core tests scored 0%
   (0/5) and functionality tests scored only 9.6% (3/64), while regression
   tests held at 97.8% (131/134). The agent used only 7 steps ($0.11 cost)
   and produced zero code changes (0 lines added/removed), suggesting it
   failed to implement the GROUP BY and aggregation features from the
   checkpoint 2 spec.

3. Verbosity and erosion were unchanged between checkpoints because the agent
   made no code modifications in checkpoint 2. This is an artifact of the
   implementation failure, not evidence of stability.

4. The anti-slop prompt kept verbosity low (2.5%) in checkpoint 1, with zero
   AST-grep violations and only 12 clone lines. This is consistent with other
   anti-slop runs showing reduced verbosity.

5. The Dolt connection was lost during the pipeline's INSERT step, requiring
   manual re-insertion of results (row ID 645).

## Dolt verification

4 rows exist for hypothesis sc-hypotheses.281 + problem log_query:
- Row 612: single mode, pass rate 0.65, cost $0.96
- Row 613: two-agent mode, pass rate 0.68, cost $1.70
- Row 619: single mode, pass rate 0.97, cost $0.97
- Row 645: single mode, pass rate 0.82, cost $0.82 (this run)
