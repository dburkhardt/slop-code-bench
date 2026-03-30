# Run 900e34 Summary

## Current state
- **Best composite:** 0.588 mean across dag_execution + file_backup (iteration 5)
- **Current config:** Test-aware reviewer + erosion-aware coder. 1 review cycle, 20 turns/batch, 150 step limit, reviewer max_turns=1. Fixed review extraction.
- **Iterations completed:** 8
- **Budget spent:** ~$250 of $750
- **Cross-validation running:** file_merger + code_search

## Top findings
1. **Single review cycle is optimal.** 3 cycles eats 30% of step budget. 0 cycles has worst erosion. 1 cycle = sweet spot.
2. **Review extraction fix was critical.** Prior to iter 4, reviewer output was silently discarded (rev_cycles=0). Fixing this improved erosion by 28% (0.758 → 0.613).
3. **Prompt engineering has diminishing/negative returns.** Plan-first, test-guarded review, spec-in-reviewer — all either neutral or harmful compared to the simple config.
4. **Config tuning had the biggest impact.** Going from 3 cycles/10 turns/100 steps to 1 cycle/20 turns/150 steps = biggest single improvement.
5. **Post-processing hurts.** Both cleanup pass and test-guarded review consumed turns and broke tests.

## Dead ends (don't revisit)
- 0 review cycles: worst erosion
- 3 review cycles: cripples pass rate
- Post-coding cleanup pass: refactoring breaks tests
- Test-guarded review: eats coding turns
- step_limit=200: agent finishes well under 150, more doesn't help
- Spec in reviewer prompt: slows runs, doesn't improve composite
- Plan-first prompt: helps erosion but hurts pass rate on dag_execution

## Best config snapshot
```yaml
type: reviewer_coder
binary: claude
permission_mode: bypassPermissions
version: 2.0.51
cost_limits:
  cost_limit: 0
  step_limit: 150
  net_cost_limit: 0
coder_turns_per_batch: 20
num_review_cycles: 1
```
+ test-aware REVIEWER_SYSTEM_PROMPT + erosion-aware CODER_APPEND_PROMPT + fixed _extract_review_text
