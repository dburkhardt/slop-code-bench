# Run 96b223 Summary

## Current state
- **Best composite:** 0.730 (iteration 2)
- **Current config:** 1 review cycle, 10 turns/batch, reviewer max-turns=5, file-based suggestion extraction (just implemented)
- **Iterations completed:** 3 (0, 1, 2)
- **Budget remaining:** ~$696
- **Provisional keeps pending:** none

## Top findings
1. Multi-batch coder structure provides massive improvement over single-invocation baseline (0.730 vs 0.343 on file_backup), with the majority of gain from pass_rate (0.911 vs 0.572)
2. One review cycle better than three: less destructive rewrites, cheaper, better composite (0.730 vs 0.638)
3. Reviewer text extraction via stream parsing is fundamentally broken because Claude Code streaming sends text and tool_use as separate events; file-based extraction implemented but not yet tested
4. The improvement transfers to dag_execution (0.248 vs baseline 0.140)
5. Mid-phase evaluation not working (all zeros)

## Dead ends (don't revisit)
- 3 review cycles: causes destructive rewrites (iter 1, churn=19.254)
- Stream-based review text extraction: Claude Code sends text and tool_use as separate events, so we can't distinguish preamble from review text

## Promising directions not yet tried
- File-based review extraction (just implemented, testing in iter 3)
- Add planning phase before first coder batch
- Front-load review only for checkpoint 1 (skip on later checkpoints)
- Adaptive review: skip review if pass rate is high after coder batch
- Test-driven review: inject test failure info into reviewer prompt
- Increase coder_turns_per_batch from 10 to 15 (since we have budget headroom at util=0.74)
