# Run 900e34 Summary

## Current state
- **Best composite:** 0.603 mean across 2 problems (iteration 1)
- **Current config:** Test-aware reviewer + erosion-aware coder with plan-first. 1 review cycle, 20 turns/batch, 150 step limit, reviewer max_turns=1.
- **Iterations completed:** 3 (0=baseline, 1=KEEP single cycle, 2=REVERT cleanup pass, 3=running plan-first)
- **Budget remaining:** ~$540 of $750
- **Provisional keeps pending:** none

## CRITICAL BUG
**rev_cycles=0 in all recent runs!** The reviewer runs but `_extract_review_text()` returns None — reviewer suggestions are NOT being fed back to the coder. The iter 1 improvement (0.603 composite) came from config changes (more turns + higher step limit), NOT from review. Must fix `_extract_review_text` or the review is useless overhead.

## Top findings
1. **Single review cycle is optimal.** 3 cycles eats 30% of step budget. 0 cycles has worst erosion. 1 cycle = sweet spot.
2. Test-aware reviewer + erosion-aware coder: strong across most problems (0.917 pass on file_backup, 0.788 on circuit_eval)
3. Post-coding cleanup/refactoring breaks tests — the refactoring agent doesn't understand the spec constraints

## Dead ends (don't revisit)
- 0 review cycles: worst erosion, no quality benefit
- 3 review cycles: cripples pass rate on hard/short problems
- Post-coding cleanup pass (iter 2): refactoring breaks tests, composite dropped from 0.603 to 0.373

## Promising directions not yet tried
- Adaptive review: skip review if mid-phase eval shows pass rate already high
- Tournament coding: run 2 coder batches with different strategies, reviewer picks the better
- Reviewer as gatekeeper: REJECT/APPROVE signal instead of suggestions
- Different review timing: review after LAST batch instead of first
