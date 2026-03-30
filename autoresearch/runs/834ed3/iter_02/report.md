# Iteration 2: Variance test (replicate iter 0 config)

## What I changed
No code changes. Same config as iter 0. Ran 2 file_backup replicates + 1 eve_route_planner for cross-validation.

## Hypothesis
Need to understand if iter 0's 0.770 is repeatable or a lucky run.

## Results

| Problem | pass_rate | erosion | verbosity | composite | cost | step_util | mid_delta |
|---------|-----------|---------|-----------|-----------|------|-----------|-----------|
| file_backup (iter 0) | 0.881 | 0.315 | 0.055 | 0.770 | $5.79 | 0.59 | 0.0 |
| file_backup (iter 2) | 0.846 | 0.394 | 0.034 | 0.718 | $8.42 | 0.75 | 0.0 |
| eve_route_planner | - | - | - | - | killed | - | stuck |

## Signal analysis
- **Variance confirmed**: 0.770 vs 0.718 (delta=0.052). The config produces composites in the 0.70-0.77 range.
- **Erosion increased**: 0.394 vs 0.315. Erosion trajectory: 0.000 -> 0.307 -> 0.581 -> 0.688. Unlike iter 0 which saw erosion decrease (cp1:0.433 -> cp3:0.125), this run shows monotonic increase. The reviewer didn't actively reduce complexity this time.
- **step_utilization higher**: cp3 and cp4 both hit 1.00 (vs 0.53 in iter 0). The agent used all turns, suggesting it needed more budget on later checkpoints.
- **Replicates collided**: Both replicates wrote to the same output dir (same launch timestamp). Lesson learned: stagger launches or use different problem names.
- **eve_route_planner stuck**: Got to cp3 ($6.95 cost) then the claude process hung. Killed after 40+ minutes without progress. This is the second time a run got stuck (dag_execution in iter 1 also stuck). This may be a claude CLI bug or a problem-specific issue.

## What I learned
1. The iter 0 config's expected composite is approximately 0.74 (average of 0.770 and 0.718). High variance (stdev ~0.04) means single runs are unreliable for detecting small improvements.
2. Erosion behavior varies significantly between runs. Sometimes the reviewer reduces complexity (iter 0), sometimes it doesn't (iter 2). The reviewer's effectiveness is stochastic.
3. Some problems/checkpoints cause the claude CLI to hang indefinitely. This happened twice (dag_execution cp1, eve_route_planner cp3). Need to investigate if this is a problem-specific issue or a general reliability problem.
4. Never run replicates on the same problem simultaneously - they share output directories.

## What I'll try next
The config is solid (expected composite ~0.74 vs baseline 0.505). To push further:
- Try increasing step_limit to give the coder more room on later checkpoints
- Or try a more targeted reviewer that injects specific test failure info

## Decision
KEEP (as replicate data). Config unchanged, confirms the range is 0.718-0.770.

## Metadata
- Git commit: 1e651bc
- Output dir: outputs/sonnet-4.5/reviewer_coder-2.0.51_just-solve_none_20260330T0207
- Cost this iteration: ~$22 (two replicates $8.42 each, eve ~$7 before killed)
- Cumulative cost: ~$52
