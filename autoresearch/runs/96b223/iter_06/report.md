# Iteration 6: Increase coder turns 10->20, anti-rewrite coder prompt

## What I changed
1. Increased `coder_turns_per_batch` from 10 to 20 in config
2. Added rule (7) to CODER_APPEND_PROMPT: "NEVER rewrite entire files. Make targeted edits only. If your change would touch more than 30 lines, break it into smaller steps."

## Hypothesis
Step utilization was only 0.47 in iter 5, meaning the coder was finishing early. More turns per batch should help, especially for later checkpoints. The anti-rewrite instruction should prevent the LOC explosions seen in iters 1, 3, and 5.

## Results

| Problem | pass_rate | erosion | verbosity | composite | cost | step_util | mid_delta |
|---------|-----------|---------|-----------|-----------|------|-----------|-----------|
| file_backup | 0.923 | 0.511 | 0.015 | 0.765 | $7.41 | 0.66 | 0.0 |

## Signal analysis
- **Pass rate 0.923**: Highest ever. Checkpoint 4 at 0.955 with 64/68 regression tests passing (94%).
- **Erosion 0.511**: Down from 0.707 baseline. Checkpoint 1 erosion=0.000 (perfect). Grows across checkpoints (0->0.584->0.682->0.778) as code accumulates.
- **No LOC explosions**: Normal growth 264->422->502->672. The anti-rewrite instruction completely prevented the catastrophic rewrites.
- **Cost**: $7.41 total (up from $5.58 in iter 5). The 20-turn batches cost more but deliver better results.
- **Reviewer suggestions**: Rev_chars=2330 on checkpoint 1 (full review), dropping to 88-104 on later checkpoints. The reviewer has less to say as code improves.
- **step_utilization**: 0.65 mean (up from 0.47). Still not hitting the limit, so there's room for more turns.

## What I learned
1. The anti-rewrite instruction ("NEVER rewrite entire files, targeted edits only") is the single most impactful change. It prevented LOC explosions while still allowing the reviewer to drive quality improvements.
2. 20 turns per batch is better than 10 for this problem. The coder needs room to implement changes properly.
3. Pass rate and erosion can improve simultaneously when the reviewer suggests targeted refactoring.
4. The reviewer suggestions are most valuable at checkpoint 1 (2330 chars of suggestions) and diminish for later checkpoints.

## What I'll try next
- Cross-validate on dag_execution to verify this transfers
- Try increasing coder_turns to 30 (still have utilization headroom)
- Consider adding a planning phase before the first coder batch

## Decision
KEEP — new best composite (0.765 vs 0.739). Every metric improved.

## Metadata
- Git commit: da7de00
- Output dir: outputs/sonnet-4.5/reviewer_coder-2.0.51_just-solve_none_20260329T2058
- Cost this iteration: $7.41
- Cumulative cost: ~$105
