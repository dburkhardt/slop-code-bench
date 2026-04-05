# Exp B8.6: log_query anti-slop replication (single-only)

**Bead:** sc-hypotheses.281.6
**Parent hypothesis:** sc-hypotheses.281 (H-prompt-only: single-agent anti-slop prompt reduces verbosity at zero cost overhead)

## Configuration

| Parameter | Value |
|-----------|-------|
| Problem | log_query |
| Model | claude_code_local/local-claude-sonnet-4-6 |
| Mode | single-agent only |
| Prompt | configs/prompts/anti_slop.jinja |
| Budget | $5.00 |
| Budget split | 60 (unused in single-only) |

## Results

### Per-checkpoint metrics

| Checkpoint | Pass Rate | Cost | Verbosity | Erosion | LOC | State |
|------------|-----------|------|-----------|---------|-----|-------|
| checkpoint_1 | 0.9776 | $0.66 | 0.0341 | 0.3922 | 528 | ran |
| checkpoint_2 | 0.9614 | $0.31 | 0.0282 | 0.5031 | 852 | error |

**Checkpoints completed:** 2 of 5. The agent timed out during checkpoint 3.

### Aggregates

| Metric | Value |
|--------|-------|
| Mean pass rate | 0.9695 |
| Total cost | $0.97 |
| Mean verbosity | 0.0311 |
| Mean erosion | 0.4477 |

### Comparison with prior run (from parent experiment)

The prior log_query single-agent run (Dolt row id=612) reported a mean pass rate of 0.65 with $0.96 cost. This replication achieved a substantially higher mean pass rate of 0.97 for the same cost. Both runs completed only 2 of 5 checkpoints (agent timeout), but this run passed far more tests per checkpoint.

| Run | Mean Pass Rate | Cost | Verbosity | Erosion |
|-----|---------------|------|-----------|---------|
| Prior (id=612) | 0.65 | $0.96 | 0.038 | 0.620 |
| This run (id=619) | 0.97 | $0.97 | 0.031 | 0.448 |

## Observations

1. **Verbosity is low.** The anti-slop prompt keeps verbosity around 3%, consistent with the parent hypothesis that prompt-only intervention suppresses verbosity effectively.

2. **Erosion increases across checkpoints.** Erosion rose from 0.39 to 0.50 between checkpoints 1 and 2, driven by high-complexity functions accumulating as the codebase grows (LOC went from 528 to 852).

3. **Pass rate is high but decreasing.** Checkpoint 1 achieved 97.8%, checkpoint 2 dropped to 96.1%. The 8 failing tests in checkpoint 2 were all assertion errors (no import or timeout failures).

4. **Timeout at checkpoint 3.** The agent timed out, terminating the run early. This is consistent with the prior run and suggests log_query checkpoint 3 is expensive for this model.

5. **Replication variance is high.** The same configuration produced 0.65 and 0.97 mean pass rates across two runs, a 32pp spread. This reinforces the paper's finding that initial design decisions create high variance across runs.

## Dolt verification

Row inserted into experiments table: id=619, hypothesis_id=sc-hypotheses.281, problem_id=log_query, total_pass_rate=0.97, total_cost=$0.97.

## Pipeline notes

Added `--single-only` flag to `experiment_pipeline.py` to support running only the single-agent baseline arm without the two-agent comparison. This was required by the bead instructions but did not exist in the codebase.
