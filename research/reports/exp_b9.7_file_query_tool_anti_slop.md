# Exp B9.7: file_query_tool anti-slop replication

**Hypothesis:** sc-hypotheses.281
**Problem:** file_query_tool (5 checkpoints)
**Model:** claude_code_local/local-claude-sonnet-4-6
**Prompt:** configs/prompts/anti_slop.jinja
**Mode:** single-agent baseline only
**Budget:** $5.00
**Actual cost:** $0.30

## Results

| Checkpoint | Pass Rate | Verbosity | Erosion | Cost ($) |
|------------|-----------|-----------|---------|----------|
| 1          | 75.0%     | 0.0       | 0.0     | 0.30     |
| 2          | (skipped) | -         | -       | -        |
| 3          | (skipped) | -         | -       | -        |
| 4          | (skipped) | -         | -       | -        |
| 5          | (skipped) | -         | -       | -        |

**Mean pass rate (1 checkpoint):** 75.0%
**Total cost:** $0.30

## Observations

1. The agent completed checkpoint 1 with 15 of 20 tests passing (2/4 core,
   13/16 functionality) before timing out after 674 seconds. The implementation
   produced 4 source files (131 LOC) with clean structure: no AST-grep
   violations, no code clones, and no functions exceeding CC 10.

2. Failed core tests were JOIN-related (basic join and sorted join), while
   3 of 16 functionality tests failed on join-with-aggregate, NOT operator,
   and NULL handling. The agent built a working SQL-on-CSV query tool but
   did not fully implement join semantics.

3. The anti-slop prompt produced notably clean code: zero verbosity
   (no flagged lines, no clones), zero structural erosion (max CC of 8,
   no high-complexity functions). This is the cleanest checkpoint-1 output
   observed so far in the B9 batch.

4. Checkpoints 2-5 were skipped because the agent timed out on checkpoint 1.
   The pipeline does not proceed past a fatal checkpoint.

5. Cost was $0.30 (10 agent steps, ~379k cached tokens read), well under the
   $5.00 budget. The timeout was a wall-clock limit, not a budget exhaustion.

## Dolt verification

1 row exists for hypothesis sc-hypotheses.281 + problem file_query_tool
(ID 629, mode=single, pass_rate=75.0%, cost=$0.30).

## Pipeline fix

Added missing `--single-only` CLI flag to the typer `main()` function in
`research/runner/experiment_pipeline.py`. The `run_pipeline()` function already
accepted `single_only` as a parameter, but the CLI entrypoint did not expose it,
causing a NameError at runtime. Previous polecat commits added the flag but the
changes were lost in a merge.
