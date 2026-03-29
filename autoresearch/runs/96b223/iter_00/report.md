# Iteration 0: Unmodified reviewer_coder baseline

## What I changed
No changes to agent code or config. This is the initial run to establish the reviewer_coder baseline on file_backup.

## Hypothesis
The reviewer_coder agent, with its structured multi-batch approach (3 coder batches + 3 reviews + 1 final), should outperform the single-invocation claude_code baseline by catching and fixing quality issues through review.

## Results

| Problem | pass_rate | erosion | verbosity | composite | cost | step_util | mid_delta |
|---------|-----------|---------|-----------|-----------|------|-----------|-----------|
| file_backup | 0.879 | 0.622 | 0.007 | 0.690 | $9.01 | 0.88 | 0.0 |

Baseline (claude_code): composite=0.343, pass=0.572, erosion=0.707, verb=0.057, cost=$3.68

## Signal analysis
The reviewer_coder achieved a massive composite improvement (0.690 vs 0.343), but the improvement comes entirely from the multi-batch coder structure, not from review:

- **rev_cycles=0, rev_chars=0**: The reviewer is invoked (phase_count=7, reviewer_cost_fraction=0.09) but its suggestions are never extracted. The `_extract_review_text` method searches for `type=result` payloads with a `result` field, but the reviewer's claude CLI invocation with `--max-turns 3` likely spends all turns on tool use (reading files, running tests) without producing a final text response, leaving the `result` field empty.

- **mid_phase all zeros**: The mid-phase pytest evaluation isn't finding or running tests. All mid_phase_pass_rate values are 0.0, suggesting test file discovery fails in the workspace.

- **step_utilization**: 0.59 on checkpoint 1, then 0.98-1.00 on later checkpoints. The agent is hitting the turn limit on later checkpoints, suggesting more budget would help.

- **Why it works anyway**: The multi-batch structure gives the coder 4 separate invocations with fresh context windows. Each coder_batch gets 10 turns, plus the final batch gets remaining turns. This prevents the coder from going down wrong paths for too long, and the intermediate reviewer invocations (even though suggestions aren't extracted) force a natural pause and context break.

- **Regression tracking**: checkpoint_2 has 26/32 regression pass (81%), checkpoint_3 has 44/50 (88%), checkpoint_4 has 60/68 (88%). Solid regression stability.

- **Pass rate degradation**: Mild (0.812 -> 0.880 -> 0.912 -> 0.910). The agent maintains or improves pass rate across checkpoints, unlike the baseline (0.812 -> 0.600 -> 0.471 -> 0.404).

## What I learned
The multi-batch coder structure is highly effective even without working review. The key insight is that breaking the work into smaller invocations prevents catastrophic drift. The baseline spends all 100 turns in a single context window and progressively loses track of prior requirements. The reviewer_coder gives the coder fresh context 4 times, each with a focused task.

The 9% cost overhead from non-functional reviewers is pure waste. If review can be fixed to actually extract and inject suggestions, there's potential for further improvement. The erosion (0.622) is still high, suggesting the reviewer could help reduce complexity.

## What I'll try next
Fix the reviewer extraction issue by increasing reviewer max-turns from 3 to 5 to give it room to produce a text response after doing tool work. Also investigate the mid-phase eval failure. If fixing review works, the reviewer can target the erosion problem specifically.

## Decision
KEEP — massive improvement over baseline (0.690 vs 0.343), establishes new best score.

## Metadata
- Git commit: pending
- Output dir: outputs/sonnet-4.5/reviewer_coder-2.0.51_just-solve_none_20260329T1611
- Cost this iteration: $9.01
- Cumulative cost: $19.65 (including baselines: $3.68 file_backup + $6.96 dag_execution)
