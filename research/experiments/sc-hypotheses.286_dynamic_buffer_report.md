# Experiment Report: sc-hypotheses.286 / dynamic_buffer

## Hypothesis

Two-agent (implementer + reviewer) workflow produces higher-quality code with
comparable or better pass rates than single-agent baseline, at the cost of
higher API spend.

## Setup

- **Problem**: dynamic_buffer
- **Model**: local-sonnet-4.6
- **Budget**: $5.00
- **Budget split**: 60/40 (implementer/reviewer)
- **Implementer prompt**: configs/prompts/default_implementer.jinja
- **Reviewer prompt**: configs/prompts/default_reviewer.jinja
- **Hypothesis ID**: sc-hypotheses.286
- **Date**: 2026-04-05

## Results

### Baseline (single-agent)

| Checkpoint | Pass Rate | Cost | Duration | State |
|------------|-----------|------|----------|-------|
| checkpoint_1 | 0/30 (0%) | $0.00 | 985.6s | error (timeout) |
| checkpoint_2-4 | not reached | - | - | - |

The baseline agent timed out on checkpoint_1. The Claude Code process ran for
~16 minutes before being killed. No files were written to the working directory.
Cost reported as $0.00 (likely the API call was still streaming when killed).

### Two-agent

| Checkpoint | Stage | Pass Rate | Cost | Duration | State |
|------------|-------|-----------|------|----------|-------|
| checkpoint_1 | implementer | 0/30 (0%) | $0.00 | 985.6s | error (timeout) |
| checkpoint_1 | reviewer | 0/30 (0%) | $0.05 | 907.0s | error |
| checkpoint_2 | implementer | 0/30 (0%) | $0.00 | 1073.0s | error (timeout) |
| checkpoint_2 | reviewer | started but hit global 3600s timeout | - | - | - |
| checkpoint_3-4 | not reached | - | - | - | - |

The two-agent arm hit the global 3600s timeout. The implementer consistently
timed out on checkpoint_1 and checkpoint_2, producing empty snapshots.
The reviewer on checkpoint_1 ran for 3 steps ($0.05) but also produced no
usable output (0 LOC, 0 files in quality analysis).

### Data Insertion

No rows were inserted into the Dolt `experiments` table for dynamic_buffer.
The pipeline correctly detected that both arms failed with no usable metrics.

## Analysis

### Why both arms failed

1. **Problem complexity**: dynamic_buffer is a code-generator problem requiring
   inference of data transformations from input/output samples, then generating
   a streaming module with caching/resuming semantics in both Python and
   JavaScript. This is significantly more complex than typical problems.

2. **Timeout cascade**: The Claude Code agent's first API call took 134.6s
   (just the system step). The second call (actual code generation) never
   completed within the per-checkpoint timeout. The problem's long specification
   and multi-language requirements likely caused the model to generate very
   long responses that exceeded time limits.

3. **Empty snapshots**: Because the agent timed out before writing any files,
   all checkpoints show 0 LOC, 0 files, 0 symbols. There was nothing for
   the reviewer to review or the evaluator to test.

### Hypothesis assessment

**INCONCLUSIVE** for dynamic_buffer. Neither arm produced any code, so no
comparison of quality or correctness is possible. The problem appears to exceed
the current timeout configuration for both single and two-agent workflows.

### Recommendations

- Consider increasing per-checkpoint and global timeouts for complex problems
  like dynamic_buffer
- The problem may benefit from a more generous cost limit (currently $3.00
  for implementer, $2.00 for reviewer)
- 37 other problem/mode combinations have been successfully evaluated for
  sc-hypotheses.286, so this is an isolated failure rather than a systemic issue

## Cost Analysis

| Arm | Total Cost |
|-----|-----------|
| Baseline | $0.00 |
| Two-agent | ~$0.05 |

Minimal cost was incurred since both arms timed out early.

## Conclusion

**INCONCLUSIVE**. The dynamic_buffer problem exceeded timeout limits for both
experimental arms. No usable data was produced for hypothesis evaluation.
This problem is an outlier in terms of complexity and may need different
timeout/budget parameters.
