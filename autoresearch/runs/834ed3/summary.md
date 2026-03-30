# Run 834ed3 Summary

## Current state
- **Best composite:** 0.770 (iteration 0), expected range ~0.72-0.77
- **Current config:** planning on all checkpoints, 1 review cycle, 20 turns/batch, text-only reviewer (max-turns=1, 20K context), anti-rewrite coder prompt
- **Iterations completed:** 3 (iter 0-2)
- **Budget remaining:** ~$698
- **Provisional keeps pending:** none

## Top findings
1. Planning + anti-rewrite + text-only reviewer produces expected composite ~0.74 (range 0.718-0.770)
2. LOC budget as prompt instruction does NOT work (coder ignores it)
3. High variance between runs (stdev ~0.04). Single runs unreliable for detecting small improvements.
4. Some claude CLI invocations hang indefinitely (dag_execution cp1, eve_route_planner cp3)
5. Reviewer effectiveness is stochastic (sometimes reduces erosion, sometimes doesn't)
6. step_utilization hits 1.00 on later checkpoints, suggesting more turns might help

## Composite history
| Iter | Composite | Pass | Erosion | Verb | Cost | Key change |
|------|-----------|------|---------|------|------|------------|
| baseline | 0.505 | 0.680 | 0.499 | 0.083 | $4.77 | single-agent claude_code |
| **0** | **0.770** | **0.881** | **0.315** | **0.055** | **$5.79** | **planning + anti-rewrite + text-only reviewer** |
| 1 | 0.699 | 0.724 | 0.061 | 0.022 | $7.80 | REVERT: skip-planning cp2+, LOC budget (explosion) |
| 2 | 0.718 | 0.846 | 0.394 | 0.034 | $8.42 | replicate of iter 0 (variance test) |

## Dead ends (don't revisit)
- LOC budget as prompt instruction: coder ignores it
- Skip-planning on cp2+: neutral
- Running replicates on same problem simultaneously (output dir collision)

## Promising directions not yet tried
- Increase step_limit (100 -> 150) for later checkpoints
- Two-pass coder: first pass implements, second pass refactors only
- Reviewer with test failure info injected (test-driven review)
- More aggressive anti-rewrite: reject code diffs >50 lines via reviewer
