# Run 834ed3 Summary

## Current state
- **Best composite:** 0.770 (iteration 0)
- **Current config:** planning enabled on all checkpoints, 1 review cycle, 20 turns/batch, text-only reviewer (max-turns=1, 20K context), anti-rewrite coder prompt
- **Iterations completed:** 2 (iter 0-1)
- **Budget remaining:** ~$720
- **Provisional keeps pending:** none

## Top findings
1. Planning phase + anti-rewrite + text-only reviewer produces 0.770 composite, beating 96b223's best (0.765)
2. LOC budget as a prompt instruction does NOT work (ignored, LOC explosion 612->10554)
3. LOC explosions are stochastic -- same config can produce healthy growth or catastrophic rewrite
4. Erosion can decrease across checkpoints when reviewer actively targets complexity
5. Skip-planning on cp2+ is neutral (doesn't help or hurt)

## Composite history
| Iter | Composite | Pass | Erosion | Verb | Cost | Key change |
|------|-----------|------|---------|------|------|------------|
| baseline | 0.505 | 0.680 | 0.499 | 0.083 | $4.77 | single-agent claude_code |
| **0** | **0.770** | **0.881** | **0.315** | **0.055** | **$5.79** | **planning + anti-rewrite + text-only reviewer** |
| 1 | 0.699 | 0.724 | 0.061 | 0.022 | $7.80 | REVERT: skip-planning on cp2+, LOC budget (explosion) |

## Dead ends (don't revisit)
- LOC budget as prompt instruction: coder ignores it completely
- Skip-planning on cp2+: neutral, no benefit

## Promising directions not yet tried
- Replicate iter 0 to measure variance (is 0.770 repeatable?)
- Cap final coder batch turns (prevent runaway writing in last batch)
- Increase step_limit to 120-150 for harder problems
- Try eve_route_planner or eve_jump_planner for broader validation
- Two replicates in parallel to reduce noise
