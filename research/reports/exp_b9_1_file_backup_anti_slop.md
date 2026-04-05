# Exp B9.1: file_backup anti-slop replication

**Hypothesis:** sc-hypotheses.281 (H-prompt-only: Single-agent anti-slop prompt reduces verbosity at zero cost overhead)
**Problem:** file_backup (4 checkpoints)
**Model:** claude_code_local/local-claude-sonnet-4-6
**Prompt:** configs/prompts/anti_slop.jinja
**Mode:** single-agent baseline only
**Budget:** $5.00
**Actual cost:** $3.13

## Results

| Checkpoint | Pass Rate | Verbosity | Erosion | LOC | Cost ($) | Steps |
|------------|-----------|-----------|---------|-----|----------|-------|
| 1          | 0.875     | 0.000     | 0.000   | 241 | 0.69     | 18    |
| 2          | 0.760     | 0.033     | 0.000   | 419 | 0.63     | 14    |
| 3          | 0.721     | 0.012     | 0.336   | 521 | 0.66     | 28    |
| 4          | 0.742     | 0.009     | 0.343   | 656 | 1.15     | 32    |

**Mean pass rate:** 0.7743
**Total cost:** $3.13
**Erosion slope:** 0.1365
**Verbosity slope:** 0.0005

## Observations

1. All 4 checkpoints completed successfully with no timeouts or skips.
   This is a full completion, unlike many prior anti-slop runs that timed out
   at checkpoint 3.

2. Verbosity was near zero throughout. Checkpoint 1 had exactly 0.0 verbosity,
   and later checkpoints stayed below 3.4%. The anti-slop prompt suppressed
   AST-Grep violations and clone lines effectively.

3. Structural erosion appeared at checkpoint 3 (0.336) and persisted into
   checkpoint 4 (0.343). At least one function exceeded CC > 10 in the later
   checkpoints, which is consistent with the file_backup problem requiring
   more complex logic for incremental backups and tar packing.

4. Pass rate declined from 87.5% at checkpoint 1 to 72.1% at checkpoint 3,
   then recovered slightly to 74.2% at checkpoint 4. The decline at
   checkpoints 2 and 3 suggests the agent struggled with the expanding spec
   (weekly scheduling, exclusion patterns, tar archives).

5. LOC grew steadily from 241 to 656 across checkpoints, reflecting genuine
   feature additions rather than bloat. The growth rate (2.7x over 4
   checkpoints) is moderate.

6. Cost per checkpoint was stable around $0.63 to $0.69 for the first three
   checkpoints, then rose to $1.15 for checkpoint 4. The total $3.13 is well
   within the $5 budget.

## Dolt Verification

Row inserted: experiments.id = 624
- problem_id: file_backup
- hypothesis_id: sc-hypotheses.281
- mode: single
- total_pass_rate: 0.7743
- total_cost: 3.13

## Output Directory

`outputs/baseline_claude_code_local/local-claude-sonnet-4-6_file_backup_20260405_012656/`
