# Run 834ed3 Summary

## Current state
- **Best composite:** 0.770 (iteration 0), with 0.767 (iter 5) as close second
- **Current config:** planning + 2 review cycles + 20 turns/batch + text-only reviewer
- **Iterations completed:** 6 (iter 0-5)
- **Budget remaining:** ~$643
- **Provisional keeps pending:** none

## Top findings
1. Planning + anti-rewrite + text-only reviewer produces expected composite ~0.74 (range 0.718-0.770)
2. 2 review cycles with text-only reviewer matches 1 cycle (0.767 vs 0.770) but costs ~70% more
3. LOC explosions at cp3 are stochastic (~50% of runs) and NOT preventable by prompt instructions
4. Capping final batch turns prevents explosions but causes high erosion (turns too few to refactor)
5. step_limit increase (100->150) adds cost without improving composite
6. LOC budget as prompt instruction is completely ignored by the coder

## Composite history
| Iter | Composite | Pass | Erosion | Verb | Cost | Key change |
|------|-----------|------|---------|------|------|------------|
| baseline | 0.505 | 0.680 | 0.499 | 0.083 | $4.77 | single-agent claude_code |
| **0** | **0.770** | **0.881** | **0.315** | **0.055** | **$5.79** | **planning + anti-rewrite + 1 review cycle** |
| 1 | 0.699 | 0.724 | 0.061 | 0.022 | $7.80 | REVERT: LOC budget (explosion) |
| 2 | 0.718 | 0.846 | 0.394 | 0.034 | $8.42 | replicate of iter 0 |
| 3 | 0.733 | 0.853 | 0.325 | 0.077 | $9.68 | REVERT: step_limit 150 |
| 4 | 0.550 | 0.763 | 0.708 | 0.000 | $4.45 | REVERT: final batch cap (too aggressive) |
| 5 | 0.767 | 0.871 | 0.339 | 0.009 | $9.78 | 2 review cycles (matches iter 0, costlier) |

## Dead ends (don't revisit)
- LOC budget as prompt instruction
- step_limit increase (100->150)
- Final batch turn cap (kills erosion)
- Skip-planning on cp2+

## Key finding: 1 cycle is optimal on cost-efficiency
Iter 0 (1 cycle): composite 0.770, cost $5.79
Iter 5 (2 cycles): composite 0.767, cost $9.78
Same quality, 70% more expensive. **Recommend reverting to 1 cycle.**

## Promising directions not yet tried
- Reduce coder_turns_per_batch from 20 to 15 (less rope for LOC explosions)
- Different planner prompt (more specific to iterative extension)
- Test on eve_jump_planner (3 checkpoints, faster iteration)
