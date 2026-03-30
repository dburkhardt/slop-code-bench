# Run 96b223 Summary

## Current state
- **Best single run:** 0.791 (iter 11 rep 1)
- **Mean composite (4 runs):** 0.718 (range: 0.645-0.791)
- **Current config:** 1 review cycle, 20 turns/batch, text-only reviewer (max-turns=1, 20K context), anti-rewrite coder prompt, longest-text fallback extraction
- **Iterations completed:** 12 (0-11)
- **Budget remaining:** ~$530
- **Provisional keeps pending:** none

## Top findings
1. LOC explosions at checkpoint 3 are the primary source of variance. When no explosion occurs, composite is 0.77-0.79. When it does, 0.64-0.67.
2. The anti-rewrite coder instruction reduces explosion frequency but doesn't eliminate it (~50% of runs still have explosions)
3. True mean performance is ~0.718, a 2.1x improvement over baseline (0.343)
4. The reviewer produces real suggestions (rev_chars up to 3729) but doesn't consistently prevent LOC explosions
5. Planning phase hurts (iter 10: 0.389), 30 turns/batch hurts (iter 7: 0.640), 3 review cycles hurt (iter 1: 0.584)

## Composite history (all runs on file_backup)
| Iter | Composite | Notes |
|------|-----------|-------|
| baseline | 0.343 | single-agent claude_code |
| 0 | 0.690 | unmodified reviewer_coder |
| 1 | 0.584 | 3 cycles, broken extraction |
| 2 | 0.730 | 1 cycle |
| 5 | 0.739 | text-only reviewer |
| **6** | **0.765** | **20 turns/batch, anti-rewrite** |
| 7 | 0.640 | 30 turns/batch (worse) |
| 8 | 0.561 | max-turns=3 (worse) |
| **9** | **0.670** | same as iter 6, lower result |
| 10 | 0.389 | planning phase (much worse) |
| **11a** | **0.791** | replicate, no LOC explosion |
| **11b** | **0.645** | replicate, LOC explosion at cp3 |

## Dead ends (don't revisit)
- 3 review cycles, 30 turns/batch, reviewer max-turns=3, planning phase
- Stream-based extraction (broken by Claude Code format)
- File-based extraction (reviewer doesn't write file)

## Promising directions not yet tried
- LOC explosion prevention: inject prior LOC count into coder prompt ("current code is N lines, keep it under 2N")
- Git-based context: commit between phases, give coder a diff view
- Conditional review: only review if pass rate improved from coder batch
- Test injection: run tests via stream() and include results in reviewer context
