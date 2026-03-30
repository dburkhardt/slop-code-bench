# Run 834ed3 Summary

## Current state
- **Best composite:** 0.770 (iteration 0), expected range ~0.72-0.77
- **Current config:** planning on all checkpoints, 1 review cycle, 20 turns/batch, step_limit=100, text-only reviewer (max-turns=1, 20K context), anti-rewrite coder prompt
- **Iterations completed:** 4 (iter 0-3)
- **Budget remaining:** ~$688
- **Provisional keeps pending:** none

## Top findings
1. Planning + anti-rewrite + text-only reviewer produces expected composite ~0.74 (range 0.718-0.770)
2. LOC explosions at cp3 happen in ~50% of runs (iter 1: 10554, iter 3: 7571). Stochastic.
3. LOC budget as prompt instruction doesn't work
4. step_limit increase (100->150) doesn't improve composite, just increases cost
5. High variance between runs (stdev ~0.04)
6. Claude CLI hangs sometimes (dag_execution, eve_route_planner)

## Composite history
| Iter | Composite | Pass | Erosion | Verb | Cost | Key change |
|------|-----------|------|---------|------|------|------------|
| baseline | 0.505 | 0.680 | 0.499 | 0.083 | $4.77 | single-agent claude_code |
| **0** | **0.770** | **0.881** | **0.315** | **0.055** | **$5.79** | **planning + anti-rewrite + text-only reviewer** |
| 1 | 0.699 | 0.724 | 0.061 | 0.022 | $7.80 | REVERT: LOC budget (explosion) |
| 2 | 0.718 | 0.846 | 0.394 | 0.034 | $8.42 | replicate (variance test) |
| 3 | 0.733 | 0.853 | 0.325 | 0.077 | $9.68 | REVERT: step_limit 150 (no improvement) |

## Dead ends (don't revisit)
- LOC budget as prompt instruction
- step_limit increase (100->150)
- Skip-planning on cp2+

## Promising directions not yet tried
- Cap final coder batch turns at 25 (prevent runaway final batch)
- 2 review cycles with text-only reviewer (vs current 1 cycle)
- Stronger anti-rewrite: add per-file diff limit to coder prompt
- Focus optimization on a different problem (file_backup has high variance)
