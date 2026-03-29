# Run 96b223 Summary

## Current state
- **Best composite:** 0.765 (iteration 6)
- **Current config:** 1 review cycle, 20 turns/batch, text-only reviewer (max-turns=1, 20K context), anti-rewrite coder prompt
- **Iterations completed:** 7 (0-6)
- **Budget remaining:** ~$645
- **Provisional keeps pending:** none

## Top findings
1. Anti-rewrite coder instruction is the single most impactful change: prevents LOC explosions while allowing targeted quality improvements
2. Text-only reviewer (max-turns=1 with injected source) produces real, actionable suggestions cheaply (2-7% of cost)
3. 20 turns per batch with 1 review cycle is the sweet spot for file_backup
4. Composite improved from baseline 0.343 to 0.765 (2.2x improvement), driven by both pass_rate (0.572->0.923) and erosion reduction (0.707->0.511)
5. Reviewer suggestions most valuable at checkpoint 1; diminish for later checkpoints

## Composite history
| Iter | Composite | Pass | Erosion | Verb | Cost | Key change |
|------|-----------|------|---------|------|------|------------|
| baseline | 0.343 | 0.572 | 0.707 | 0.057 | $3.68 | single-agent claude_code |
| 0 | 0.690 | 0.879 | 0.622 | 0.007 | $9.01 | unmodified reviewer_coder |
| 2 | 0.730 | 0.911 | 0.556 | 0.045 | $8.12 | 1 review cycle |
| 5 | 0.739 | 0.859 | 0.383 | 0.015 | $5.58 | text-only reviewer, 20K context |
| **6** | **0.765** | **0.923** | **0.511** | **0.015** | **$7.41** | **20 turns/batch, anti-rewrite** |

## Dead ends (don't revisit)
- 3 review cycles: destructive rewrites
- Stream-based review extraction: broken by Claude Code streaming format
- File-based review extraction: reviewer doesn't write the file
- Small context for reviewer (< 10K): reviewer asks for complete code

## Promising directions not yet tried
- Cross-validate iter 6 config on dag_execution
- Increase coder_turns to 30 (utilization is 0.66, still has headroom)
- Add planning phase before first coder batch
- Increase reviewer context to include test results (needs container exec)
- Try 2 review cycles with anti-rewrite safeguard
