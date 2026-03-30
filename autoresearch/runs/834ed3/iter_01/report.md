# Iteration 1: Skip planning on cp2+, LOC budget anchoring

## What I changed
1. Added `_has_existing_code()` to skip planning phase on checkpoints 2+ (only plan on cp1 where architecture matters)
2. Added `_count_workspace_loc()` and LOC budget injection into coder prompt: "The codebase currently has N lines. Keep total under N*1.5+200 lines."
3. Injected prior LOC count into telemetry for tracking

## Hypothesis
Planning is only valuable for establishing initial architecture (cp1). Skipping it on cp2+ saves budget. LOC budget anchoring should prevent the bloat seen at cp4 in iter 0.

## Results

| Problem | pass_rate | erosion | verbosity | composite | cost | step_util | mid_delta |
|---------|-----------|---------|-----------|-----------|------|-----------|-----------|
| file_backup | 0.724 | 0.061 | 0.022 | 0.699 | $7.80 | 0.71 | 0.0 |
| dag_execution | - | - | - | - | killed | - | - |

## Signal analysis
- **LOC EXPLOSION at cp3**: 612 -> 10554 lines (churn=16.343). The LOC budget instruction (keep under 1118 lines) was completely ignored. The coder rewrote the entire codebase in a single batch.
- **Low erosion despite explosion**: 0.103 at cp3, 0.141 at cp4. The bloated code has low CC concentration, suggesting the agent distributed complexity broadly rather than concentrating it.
- **cp1 pass_rate dropped**: 0.625 vs 0.875 in iter 0. Planning was still active on cp1 (correctly). This is likely variance.
- **Skip-planning working correctly**: phases=4 on cp1 (with planner), phases=3 on cp2-4 (no planner).
- **step_utilization=1.00 on cp3 and cp4**: The agent hit the 100-turn limit. The LOC explosion consumed all available turns.
- **dag_execution stuck**: Killed after 40 minutes on cp1 with only $0.56 spent. Possibly a long-running claude invocation that never returned.

## What I learned
1. LOC budget as a prompt instruction does NOT work. The coder completely ignored the constraint ("keep under 1118 lines") and wrote 10554 lines. Prompt-based constraints are unreliable for preventing structural problems, which aligns with the paper's finding.
2. Skip-planning on cp2+ is neutral. It saves a few cents per checkpoint but doesn't meaningfully change outcomes.
3. LOC explosions are stochastic. iter 0 had healthy growth (538->1127), iter 1 exploded (612->10554) with essentially the same anti-rewrite instruction. The difference is variance in the coder's behavior.
4. When a LOC explosion happens, erosion stays low because the agent distributes complexity broadly. But pass_rate and cost suffer.

## What I'll try next
Revert to iter 0 code. The LOC budget approach failed. Instead, try:
- Run a replicate of iter 0 to measure variance
- Or try limiting max-turns for the final coder batch to prevent runaway writing

## Decision
REVERT -- composite 0.699 < 0.770 (iter 0). LOC explosion at cp3 destroyed the result.

## Metadata
- Git commit: 02c3256
- Output dir: outputs/sonnet-4.5/reviewer_coder-2.0.51_just-solve_none_20260330T0110
- Cost this iteration: $7.80 (file_backup only; dag killed)
- Cumulative cost: $30.30
