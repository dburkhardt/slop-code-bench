# Run 900e34 Summary

## Current state
- **Best composite:** 0.419 mean across 5 problems (0.565 excl dag_execution outlier) (iteration 0)
- **Current config:** Test-aware reviewer (runs tests first, focuses on failures) + erosion-aware coder (CC<10, no wrappers, modify in-place). 3 review cycles, 10 turns/batch, 100 step limit.
- **Iterations completed:** 0 (baseline from prior ad-hoc experiments)
- **Budget remaining:** ~$590 of $750
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
