# Iteration 2: Reduce review cycles to 1, minimal-change coder prompt

## What I changed
1. Reduced `num_review_cycles` from 3 to 1 in config
2. Updated CODER_APPEND_PROMPT to emphasize MINIMAL changes from reviewer suggestions
3. Fixed `_extract_review_text` to skip assistant messages with tool_use blocks (still didn't work, see below)

## Hypothesis
Three review cycles cause destructive rewrites (iter 1 saw churn=19.254 at checkpoint 3). One cycle should give the benefit of review with less destruction. Minimal-change instructions should prevent the coder from over-interpreting suggestions.

## Results

| Problem | pass_rate | erosion | verbosity | composite | cost | step_util | mid_delta |
|---------|-----------|---------|-----------|-----------|------|-----------|-----------|
| file_backup | 0.911 | 0.556 | 0.045 | 0.730 | $8.12 | 0.74 | 0.0 |
| dag_execution | 0.481 | 0.729 | 0.048 | 0.248 | $7.62 | 0.77 | 0.0 |

## Signal analysis
- **New best on file_backup** (0.730 vs 0.690 in iter 0). Pass rate jumped to 0.911 from 0.879, erosion dropped to 0.556 from 0.622.
- **Reviewer still extracting preamble**: rev_chars=109-111, still grabbing "I'll help you review the code quality..." The tool_use filter doesn't work because Claude Code streaming sends text and tool_use as separate events.
- **phases=3** (1 coder + 1 reviewer + 1 final). The reduced structure preserves more turns for coding, which explains lower step_utilization (0.74 vs 0.88).
- **No LOC explosion**: Max churn=1.471 at checkpoint 2, normal code growth (238->530->658->793).
- **dag_execution cross-validation**: composite=0.248, up from baseline 0.140. The improvement transfers to a different problem.
- **Lower cost**: $8.12 (down from $9.01) due to fewer review invocations.

## What I learned
1. One review cycle is better than three: less destructive, cheaper, still provides the multi-batch structure benefit.
2. The reviewer text extraction is fundamentally broken because Claude Code streaming sends text and tool_use as separate JSON events. A file-based approach is needed.
3. The composite improvement (0.690 -> 0.730) comes from: fewer wasted review turns = more coding budget + less reviewer-induced destruction.
4. The agent is NOT hitting step limits (util=0.52-1.00, mean 0.74), suggesting the budget allocation is healthier.

## What I'll try next
Replace stream-based review extraction with file-based: have the reviewer write suggestions to `.review_suggestions.md`, then read that file. This will finally deliver actual review content to the coder. Already implemented in the code; iter 3 will test it.

## Decision
KEEP — new best composite (0.730 vs 0.690). Transfers to dag_execution.

## Metadata
- Git commit: 7ca2d32
- Output dir: outputs/sonnet-4.5/reviewer_coder-2.0.51_just-solve_none_20260329T1809
- Cost this iteration: $15.74 (file_backup + dag_execution)
- Cumulative cost: $54.39
