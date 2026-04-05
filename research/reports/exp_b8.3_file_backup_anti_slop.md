# Exp B8.3: file_backup anti-slop replication

**Hypothesis:** sc-hypotheses.281 (H-prompt-only: Single-agent anti-slop prompt reduces verbosity at zero cost overhead)
**Problem:** file_backup (4 checkpoints)
**Model:** claude_code_local/local-claude-sonnet-4-6
**Prompt:** configs/prompts/anti_slop.jinja
**Mode:** single-agent baseline only
**Budget:** $5.00
**Actual cost:** $3.23
**Dolt row ID:** 630

## Results

| Checkpoint | Pass Rate | Verbosity | Erosion | LOC | Cost ($) | Steps |
|------------|-----------|-----------|---------|-----|----------|-------|
| 1          | 0.875     | 0.000     | 0.403   | 262 | 0.88     | 15    |
| 2          | 0.760     | 0.044     | 0.277   | 451 | 0.72     | 20    |
| 3          | 0.735     | 0.000     | 0.507   | 530 | 0.67     | 23    |
| 4          | 0.719     | 0.000     | 0.485   | 677 | 0.96     | 23    |

**Mean pass rate:** 0.7723
**Total cost:** $3.23
**Erosion slope:** 0.0335
**Verbosity slope:** -0.0065

## Observations

1. All 4 checkpoints completed successfully with no timeouts or skips.
   The run consumed $3.23 of the $5.00 budget, well within limits.

2. Verbosity stayed near zero throughout. Only checkpoint 2 showed any
   verbosity (4.4%), driven by 20 clone lines in the code. All other
   checkpoints had 0.0% verbosity, indicating the anti-slop prompt
   effectively suppressed AST-Grep violations and code duplication.

3. Structural erosion was present from checkpoint 1 (0.403), dropped at
   checkpoint 2 (0.277), then rose to 0.507 at checkpoint 3 before
   settling at 0.485. The non-monotonic pattern suggests erosion is
   driven by the specific complexity of individual checkpoint features
   rather than accumulation over time.

4. Pass rate declined gradually from 87.5% to 71.9% across checkpoints.
   This is consistent with the file_backup problem's increasing spec
   complexity (weekly scheduling, exclusion patterns, tar archives,
   retention policies).

5. LOC grew from 262 to 677 (2.6x), reflecting genuine feature additions.
   Step counts stayed moderate (15 to 23), suggesting the agent worked
   efficiently without excessive iteration.

6. Compared to the prior B9.1 replication (pass rate 0.7743, cost $3.13),
   this run shows nearly identical performance: 0.7723 pass rate, $3.23
   cost. The close agreement across runs suggests the anti-slop prompt
   produces stable, reproducible results on this problem.

## Comparison with prior file_backup runs (sc-hypotheses.281)

| Run    | Mean Pass Rate | Total Cost | Verbosity (mean) | Notes              |
|--------|---------------|------------|-------------------|--------------------|
| B8.3   | 0.7723        | $3.23      | 0.011             | This run           |
| B9.1   | 0.7743        | $3.13      | 0.014             | Prior replication   |
| Row 614| 0.8100        | $2.23      | —                 | Earlier model name  |
| Row 626| 0.8200        | $3.36      | —                 | Earlier model name  |

The anti-slop prompt runs cluster around 77% pass rate at $3.13 to $3.23 cost.
Earlier runs under the old model name format show slightly higher pass rates (81-82%),
which may reflect model version differences or random variance across runs.
