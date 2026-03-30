# Run 96b223 Summary

## Current state
- **Best single run:** 0.791 (iter 11 rep 1, no LOC guard)
- **Best with LOC guard:** 0.714 (iter 14 rep 2)
- **Mean composite (guarded, 2 runs):** 0.701
- **Mean composite (unguarded, 4 runs):** 0.718 (range: 0.645-0.791)
- **Current config:** 1 review cycle, 20 turns/batch, text-only reviewer (max-turns=1, 20K context), anti-rewrite coder prompt, longest-text fallback extraction, recursive LOC explosion guard
- **Iterations completed:** 15 (0-14)
- **Budget remaining:** ~$385
- **Status:** Continuing

## Key results table (file_backup)
| Iter | Composite | Pass | Erosion | LOC explosion? | Key change |
|------|-----------|------|---------|----------------|------------|
| baseline | 0.343 | 0.572 | 0.707 | N/A | single-agent claude_code |
| 0 | 0.690 | 0.879 | 0.622 | No | unmodified reviewer_coder |
| 2 | 0.730 | 0.911 | 0.556 | No | 1 review cycle |
| 5 | 0.739 | 0.859 | 0.383 | Yes (cp3) | text-only reviewer |
| **6** | **0.765** | **0.923** | **0.511** | **No** | **20 turns/batch, anti-rewrite** |
| 9 | 0.670 | 0.781 | 0.369 | No | replicate of iter 6 |
| 11a | **0.791** | 0.879 | 0.248 | No | replicate |
| 11b | 0.645 | 0.795 | 0.496 | Yes (cp3) | replicate |
| 14a | 0.688 | 0.964 | 0.863 | No (guard) | recursive LOC guard |
| 14b | 0.714 | 0.917 | 0.676 | No (guard) | recursive LOC guard |

## Top findings
1. **Multi-batch structure** is the primary driver (baseline 0.343 -> 0.690)
2. **LOC explosions** are the main source of variance (~50% of unguarded runs). The guard eliminates them but doesn't improve mean composite.
3. **Text-only reviewer** (max-turns=1, context injected) produces real suggestions cheaply
4. **Anti-rewrite coder instruction** reduces but doesn't eliminate explosions
5. Improvements beyond the basic structure are marginal and within noise (0.69-0.79 band)
6. **Planning phase**, **3 review cycles**, **30 turns/batch**, and **reviewer max-turns=3** all hurt performance

## Dead ends
- Planning phase (iter 10: 0.389)
- 3 review cycles (iter 1: 0.584)
- 30 turns/batch (iter 7: 0.640)
- Reviewer max-turns=3 (iter 8: 0.561)
- LOC injection in prompt (iter 12: didn't prevent explosions)
- Non-recursive file operations (iter 13: missed subdirectory files)

## Promising directions not yet tried
- Reviewer focused specifically on erosion/complexity reduction
- Git commit between phases for better context tracking
- 2 review cycles (compromise between 1 and 3) with anti-rewrite guard
- Conditional review: skip if pass rate already high
