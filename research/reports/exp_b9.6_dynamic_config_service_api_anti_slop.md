# Exp B9.6: dynamic_config_service_api anti-slop replication

**Hypothesis:** sc-hypotheses.281
**Problem:** dynamic_config_service_api (4 checkpoints)
**Model:** claude_code_local/local-claude-sonnet-4-6
**Prompt:** configs/prompts/anti_slop.jinja
**Mode:** single-agent baseline only
**Budget:** $5.00
**Actual cost:** $0.00

## Results

| Checkpoint | Pass Rate | Verbosity | Erosion | Cost ($) |
|------------|-----------|-----------|---------|----------|
| 1          | 0.000     | 0.0       | 0.0     | 0.00     |
| 2          | (skipped) | -         | -       | -        |
| 3          | (skipped) | -         | -       | -        |
| 4          | (skipped) | -         | -       | -        |

**Mean pass rate (1 checkpoint):** 0.0000
**Total cost:** $0.00

## Observations

1. The Claude Code agent timed out on checkpoint 1 after 652 seconds,
   producing no code. All 47 tests (13 core, 19 functionality, 15 error)
   errored because the entry file `config_server.py` was never created.

2. The agent logged zero steps, zero tokens, and zero cost, indicating
   the Claude Code subprocess likely stalled during initialization or
   early prompt processing rather than running out of time mid-implementation.

3. Checkpoints 2-4 were skipped because checkpoint 1 failed with an error
   state. The pipeline does not proceed past a fatal checkpoint.

4. This is a negative data point for the hypothesis. The anti-slop prompt
   did not cause the timeout (the problem itself may be complex enough to
   trigger initialization stalls in the local Claude Code runner), but the
   result contributes no signal about verbosity or structural erosion.

## Dolt verification

1 row exists for hypothesis sc-hypotheses.281 + problem dynamic_config_service_api
(ID 622, mode=single, pass_rate=0.0, cost=$0.00).

## Pipeline fix

Removed duplicate `single_only` parameter definition in
`research/runner/experiment_pipeline.py` (lines 1150-1157) that caused a
SyntaxError preventing the pipeline from starting.
