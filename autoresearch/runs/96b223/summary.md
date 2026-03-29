# Run 96b223 Summary

## Current state
- **Best composite:** 0.739 (iteration 5)
- **Current config:** 1 review cycle, 10 turns/batch, text-only reviewer (max-turns=1, 20K source context injected)
- **Iterations completed:** 6 (0-5)
- **Budget remaining:** ~$640
- **Provisional keeps pending:** none

## Top findings
1. Text-only reviewer (max-turns=1 with injected source context) produces real suggestions and is very cheap (rev_frac=2-7%)
2. One review cycle with multi-batch structure is optimal; 3 cycles causes destructive rewrites
3. The coder sometimes over-reacts to reviewer suggestions, causing LOC explosions (checkpoint 3: 441->7433 in iter 5). This hurts pass rate but dramatically lowers erosion.
4. Erosion improvement is the main composite driver when reviewer works: 0.383 vs baseline 0.707
5. Step utilization is low (mean 0.47) suggesting the agent finishes early; could increase coder_turns_per_batch

## Composite history
| Iter | Composite | Pass | Erosion | Verb | Cost | Key change |
|------|-----------|------|---------|------|------|------------|
| baseline | 0.343 | 0.572 | 0.707 | 0.057 | $3.68 | single-agent claude_code |
| 0 | 0.690 | 0.879 | 0.622 | 0.007 | $9.01 | unmodified reviewer_coder |
| 1 | 0.584 | 0.769 | 0.614 | 0.002 | $9.55 | broken reviewer extraction |
| 2 | 0.730 | 0.911 | 0.556 | 0.045 | $8.12 | 1 review cycle, minimal-change prompt |
| 3 | 0.644 | 0.843 | 0.655 | 0.009 | $8.09 | file-based extraction (still broken) |
| 4 | 0.690 | 0.909 | 0.679 | 0.050 | $6.28 | text-only reviewer, truncated context |
| 5 | 0.739 | 0.859 | 0.383 | 0.015 | $5.58 | text-only reviewer, 20K context |

## Dead ends (don't revisit)
- 3 review cycles: causes destructive rewrites (iter 1, churn=19.254)
- Stream-based review text extraction: Claude Code sends text and tool_use as separate events
- File-based review extraction: reviewer doesn't write the file with limited turns
- Small context window for reviewer (4K chars): reviewer asks for complete code instead of reviewing

## Promising directions not yet tried
- Increase coder_turns_per_batch from 10 to 20 (utilization is low at 0.47)
- Add coder prompt to NEVER rewrite entire files (prevent LOC explosions)
- Skip review if checkpoint is early (review most valuable for later checkpoints where erosion compounds)
- Add test results to reviewer context (would require running tests in container)
- Front-load coding budget: give more turns to first coder batch, fewer to final
- Try 2 review cycles (compromise between 1 and 3)
