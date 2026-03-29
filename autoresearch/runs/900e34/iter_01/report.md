# Iteration 1: Single review cycle, more turns, higher step limit

## What I changed
- `num_review_cycles`: 3 → 1 (single early review instead of 3)
- `coder_turns_per_batch`: 10 → 20 (more coding room per batch)
- `step_limit`: 100 → 150 (more total headroom)
- Reviewer `--max-turns`: 3 → 1 (read + respond is sufficient)

## Hypothesis
Fewer review cycles frees turns for coding, fixing the dag_execution regression. More turns per batch gives the coder room to build momentum. Single review is enough to catch structural issues early.

## Results

| Problem | pass_rate | erosion | verbosity | composite | cost | step_util | mid_delta |
|---------|-----------|---------|-----------|-----------|------|-----------|-----------|
| file_backup | 0.923 | 0.778 | 0.036 | 0.679 | $7.74 | ~0.9 | N/A |
| dag_execution | 0.761 | 0.738 | 0.042 | 0.527 | $16.40 | ~0.9 | N/A |
| **Mean** | **0.842** | **0.758** | **0.039** | **0.603** | **$24.14** | | |

## Signal analysis
dag_execution went from 0.074 pass (iter 0, 3 cycles) to 0.761 (1 cycle). The 3-cycle config was spending ~30 of 100 steps on review, leaving only ~70 for coding across 3 checkpoints (~23 per checkpoint). With 1 cycle and 150 step limit, the coder gets ~130 coding steps across 3 checkpoints (~43 per checkpoint). That nearly doubles coding budget.

file_backup maintained its excellent pass rate (0.923 vs 0.917) with slightly worse erosion (0.778 vs 0.711). The erosion increase is expected — fewer review cycles mean less quality cleanup.

The cost on dag_execution ($16.40) is higher than iter 0 ($9.77) because the coder uses more of the 150 step budget. This is acceptable since the pass rate nearly 10x'd.

## What I learned
Review frequency has a huge impact on pass rate. 3 review cycles consume ~30% of the step budget for review overhead. On problems where the coder needs every step to implement the spec (like dag_execution with its complex dependency graph), this is devastating. 1 cycle is the sweet spot — enough to catch structural issues early without starving the coder.

## What I'll try next
- Run on more problems to validate (code_search, file_merger)
- Try reducing erosion without sacrificing pass rate (maybe a reviewer prompt focused specifically on CC reduction)
- Experiment with the reviewer running after the LAST batch instead of the first (review at the end to polish)

## Decision
KEEP — massive improvement on both problems. Mean composite 0.603 vs 0.419 (iter 0).

## Metadata
- Git commit: c6092b0
- Output dir: see output_dir.txt
- Cost this iteration: $24.14
- Cumulative cost: ~$185
