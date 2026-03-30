# Run 96b223 Summary

## Current state
- **Best composite:** 0.765 (iteration 6)
- **Current config:** 1 review cycle, 20 turns/batch, text-only reviewer (max-turns=1, 20K context), anti-rewrite coder prompt, longest-text fallback extraction
- **Iterations completed:** 9 (0-8)
- **Budget remaining:** ~$575
- **Provisional keeps pending:** none

## Top findings
1. Anti-rewrite coder instruction is the single most impactful change: prevents LOC explosions
2. Text-only reviewer (max-turns=1) is better than tool-using reviewer (max-turns=3); context injection eliminates the need for tools
3. 20 turns/batch is the sweet spot; 30 turns regresses (LOC explosions return)
4. Composite improved from baseline 0.343 to 0.765 (2.2x), driven by pass_rate (0.572->0.923) and erosion reduction (0.707->0.511)
5. LOC explosions remain the primary failure mode, typically at checkpoints 3-4

## Composite history (keeps only)
| Iter | Composite | Pass | Erosion | Verb | Cost | Key change |
|------|-----------|------|---------|------|------|------------|
| baseline | 0.343 | 0.572 | 0.707 | 0.057 | $3.68 | single-agent claude_code |
| 0 | 0.690 | 0.879 | 0.622 | 0.007 | $9.01 | unmodified reviewer_coder |
| 2 | 0.730 | 0.911 | 0.556 | 0.045 | $8.12 | 1 review cycle |
| 5 | 0.739 | 0.859 | 0.383 | 0.015 | $5.58 | text-only reviewer |
| **6** | **0.765** | **0.923** | **0.511** | **0.015** | **$7.41** | **20 turns/batch, anti-rewrite** |

## Dead ends (don't revisit)
- 3 review cycles: destructive rewrites
- Stream-based review extraction (tool_use events mixed with text)
- File-based review extraction (reviewer doesn't write the file)
- Small context for reviewer (< 10K)
- 30 turns/batch: LOC explosions return
- Reviewer max-turns=3: reverts to tool use, worse results (iter 8: 0.561)

## Promising directions not yet tried
- Add planning phase before first coder batch (the MapCoder insight)
- Skip review for checkpoints where previous pass rate was high
- Stronger LOC explosion prevention (e.g., coder prompt referencing prior LOC count)
- Run tests in container and inject results into reviewer context
