# Exp B8.2: file_backup anti-slop replication

**Hypothesis:** sc-hypotheses.281 (H-prompt-only: Single-agent anti-slop prompt reduces verbosity at zero cost overhead)
**Problem:** file_backup (4 checkpoints)
**Model:** claude_code_local/local-claude-sonnet-4-6
**Prompt:** configs/prompts/anti_slop.jinja
**Mode:** single-agent baseline only
**Budget:** $5.00
**Actual cost:** $2.44

## Results

| Checkpoint | Pass Rate | Verbosity | Erosion | LOC | Cost ($) | Steps |
|------------|-----------|-----------|---------|-----|----------|-------|
| 1          | 0.875     | 0.000     | 0.000   | 269 | 0.85     | 17    |
| 2          | 0.760     | 0.000     | 0.000   | 438 | 0.69     | 17    |
| 3          | 0.074     | 0.000     | 0.332   | 517 | 0.45     | 27    |
| 4          | 0.742     | 0.000     | 0.308   | 656 | 0.45     | 19    |

**Mean pass rate:** 0.6125
**Total cost:** $2.44
**Erosion slope:** 0.1255
**Verbosity slope:** 0.0000

## Observations

1. All 4 checkpoints completed. Checkpoint 3 had a severe pass rate collapse
   to 7.4% due to 63 import errors, indicating a structural break in the
   solution that the agent introduced. Checkpoint 4 recovered to 74.2%,
   suggesting the checkpoint 3 failure was localized.

2. Verbosity was exactly zero across all checkpoints. The anti-slop prompt
   fully suppressed AST-Grep violations and clone lines. This is consistent
   with prior B9.x replication runs which also showed near-zero verbosity
   under the anti-slop prompt.

3. Structural erosion appeared at checkpoint 3 (0.332) and persisted into
   checkpoint 4 (0.308). At least one function exceeded CC > 10 in later
   checkpoints. The erosion slope (0.1255) is similar to the B9.1 run (0.1365).

4. The checkpoint 3 import error cluster (63 of 68 tests) suggests the agent
   broke a module boundary or introduced a circular import. Despite this, the
   quality analysis still ran, so the code was parseable but not executable.

5. Total cost ($2.44) was well under budget and lower than B9.1 ($3.13). The
   cheaper checkpoints 3 and 4 ($0.45 each) reflect either early termination
   or more efficient agent behavior.

6. LOC growth from 269 to 656 (2.4x over 4 checkpoints) is comparable to B9.1
   (241 to 656, 2.7x), indicating similar solution trajectories.

## Dolt Verification

Row inserted: experiments.id = 632
- problem_id: file_backup
- hypothesis_id: sc-hypotheses.281
- mode: single
- total_pass_rate: 0.61
- total_cost: 2.44
