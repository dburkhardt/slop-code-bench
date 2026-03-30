# Run 96b223 Summary

## Bottom line
The multi-batch coder structure is the only reliable lever. Everything else (reviewer suggestions, LOC guards, context injection, planning phases, prompt engineering) is noise or actively harmful. The reviewer serves as a cheap phase separator, not an analyst.

## Final config
- 1 review cycle, 20 turns/batch, reviewer max-turns=3
- Clean agent code (~450 LOC, down from ~850 at peak complexity)
- CODER_APPEND_PROMPT with anti-rewrite instruction
- Longest-text fallback for reviewer extraction

## Performance (file_backup, 8 runs across iters 6-19)
- **Mean composite: ~0.70** (range 0.61-0.79)
- **Mean pass rate: ~0.87** (range 0.78-0.96)
- **Mean erosion: ~0.55** (range 0.25-0.86)
- **Baseline: 0.343** (2.0x improvement)

## Performance (dag_execution, 4 cross-validation runs)
- **Mean composite: ~0.28** (range 0.25-0.35)
- **Baseline: 0.140** (2.0-2.5x improvement)

## What works (ranked by effect size)
1. **Multi-batch structure** (+0.35 composite). Breaking 100 turns into coder(20) + reviewer(3) + coder_final(77) prevents context drift. The fresh context on each invocation is the mechanism.
2. **Anti-rewrite coder prompt** (reduces LOC explosion frequency from ~70% to ~40%). The instruction "NEVER rewrite entire files. Make targeted edits only" is the only prompt change that moves the needle.
3. **1 review cycle** (+0.04 over 3 cycles). Fewer cycles = more turns for coding = better results.

## What doesn't work
- Reviewer suggestions (broken or working, makes no difference to composite)
- LOC guards (eliminate explosions but don't improve mean)
- Context injection into reviewer (extra I/O for zero gain)
- Planning phases (actively harmful, -0.30 composite)
- Complexity-focused reviewer prompt (breaks pass rate)
- 2+ review cycles (too much budget on review)
- 25+ turns/batch (less room for final batch)

## Variance analysis
LOC explosions at checkpoint 3 occur in ~40-50% of runs, driven by the coder creating package structures in subdirectories. When no explosion: composite ~0.72-0.79. With explosion: ~0.61-0.68. No prompt or structural intervention reliably prevents this.

## Spend: ~$240 / $750 budget across 19 iterations
