# Run 900e34 Summary

## Current state
- **Best composite:** 0.603 mean across 2 problems (iteration 1)
- **Current config:** Test-aware reviewer + erosion-aware coder. **1 review cycle, 20 turns/batch, 150 step limit, reviewer max_turns=1.**
- **Iterations completed:** 1
- **Budget remaining:** ~$565 of $750
- **Provisional keeps pending:** none

## Top findings
1. Test-aware reviewer + erosion-aware coder massively improves file_backup (0.917 pass, 100% core) and circuit_eval (0.788 pass, 64.7% core)
2. 3 review cycles hurt dag_execution badly (0.074 pass vs 0.447 baseline) — review overhead eats turns on harder/shorter problems
3. 0 review cycles has worst erosion (0.803) — review does help code quality

## Dead ends (don't revisit)
- 0 review cycles: worst erosion, no quality benefit
- 3 review cycles on dag_execution: cripples pass rate

## Promising directions not yet tried
- 1 review cycle (single early review to catch structural issues, then coder gets all remaining turns)
- Adaptive review: skip review if pass rate is already high from mid-phase eval
- Reviewer max_turns=1 instead of 3 (read + respond is enough)
- Front-loaded review timing (review early, skip late)
- Increasing step_limit to 150+ to give more headroom
