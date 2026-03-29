# Iteration 1: Fix reviewer extraction (max-turns 3->5, text fallback)

## What I changed
1. Increased reviewer `--max-turns` from 3 to 5
2. Added explicit instruction in REVIEWER_SYSTEM_PROMPT to end with plain text summary
3. Added fallback extraction in `_extract_review_text` to find assistant text when result payload is empty

## Hypothesis
The reviewer was being invoked but suggestions were never extracted (rev_cycles=0 in iter 0). By giving more turns and adding a text fallback, the reviewer should produce actionable suggestions that improve quality.

## Results

| Problem | pass_rate | erosion | verbosity | composite | cost | step_util | mid_delta |
|---------|-----------|---------|-----------|-----------|------|-----------|-----------|
| file_backup (rep1) | 0.819 | 0.602 | 0.004 | 0.638 | $9.42 | 0.95 | 0.0 |
| file_backup (rep2 partial) | 0.769 | 0.614 | 0.002 | 0.584 | $9.55 | 0.95 | 0.0 |

Note: Both replicates wrote to the same output directory (timestamp collision). Checkpoint 4 results are from rep 2, corrupting rep 1 data.

## Signal analysis
- **rev_cycles=3, rev_chars=242-331**: Reviewer extraction now working, but the extracted text is WRONG. The fallback grabs preamble text from assistant messages containing tool_use blocks ("I'll help you review the code quality. Let me start by exploring...") instead of the actual review suggestions.
- **Checkpoint 3 catastrophe**: LOC exploded from 366 to 7381 (churn=19.254). The coder did a massive rewrite. Even though the reviewer suggestions were just preamble text, the coder treated them as instructions and restructured everything.
- **Erosion paradox**: Erosion decreased slightly (0.614 vs 0.622) because the 7381-LOC codebase has many small functions, but this is misleading; the code is bloated.
- **Pass rate regression**: 0.769 vs 0.879 in iter 0. The destructive rewrite at checkpoint 3 broke functionality.
- **reviewer_cost_fraction**: 12-16% (up from 9%) due to more turns. More expensive review for worse results.

## What I learned
1. The fallback text extraction grabs text from assistant messages with tool_use blocks, which is just preamble. Need to filter for pure-text assistant messages (no tool_use blocks).
2. Even garbage reviewer suggestions (preamble text) cause the coder to do destructive rewrites. The coder interprets any reviewer input as permission to restructure.
3. Replicates must be staggered or use different config names to avoid output directory collisions.

## What I'll try next
1. Fix extraction to skip assistant messages containing tool_use blocks (done in code)
2. Reduce num_review_cycles from 3 to 1 to limit destructive review impact
3. Add coder instructions to make MINIMAL changes from reviewer suggestions
4. Consider: is review even helping? The non-review multi-batch structure (iter 0) scored 0.690.

## Decision
REVERT — composite dropped from 0.690 to 0.584-0.638. Reviewer extraction grabbing wrong text.

## Metadata
- Git commit: 9cbdbcc
- Output dir: outputs/sonnet-4.5/reviewer_coder-2.0.51_just-solve_none_20260329T1713
- Cost this iteration: $19.00 (two replicates)
- Cumulative cost: $38.65
