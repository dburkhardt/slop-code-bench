# Exp B9.2: file_backup anti-slop replication

**Hypothesis:** sc-hypotheses.281 (H-prompt-only: Single-agent anti-slop prompt reduces verbosity at zero cost overhead)

**Problem:** file_backup
**Model:** claude_code_local/local-claude-sonnet-4-6
**Prompt:** configs/prompts/anti_slop.jinja
**Mode:** single-only (baseline arm only)
**Budget:** $5.00 (actual spend: $0.16)

## Results

| Checkpoint | State | Pass Rate | Cost | LOC | Verbosity | Erosion | Steps |
|------------|-------|-----------|------|-----|-----------|---------|-------|
| 1 | error | 12.5% | $0.16 | 203 | 0.000 | 0.000 | 5 |
| 2 | skipped | - | - | - | - | - | - |
| 3 | skipped | - | - | - | - | - | - |
| 4 | skipped | - | - | - | - | - | - |

**Aggregate:** total_pass_rate=0.125, total_cost=$0.16

## Observations

1. **Agent timed out on checkpoint 1.** The Claude Code process timed out after
   601s with only 5 steps completed (5% of the 100-step limit). The agent
   produced code (203 LOC across 2 files, 8 functions, 3 classes) but the
   implementation was largely incorrect: 4 of 32 tests passed (all 4 were
   error-handling tests). Zero core tests and zero functionality tests passed.

2. **Verbosity = 0.0.** The anti-slop prompt produced zero AST-Grep flagged
   lines and zero clone lines. Despite the low pass rate, the code was clean.

3. **Erosion = 0.0.** No high-complexity functions (CC > 10) were generated.
   Maximum cyclomatic complexity was 10, mean was 3.875.

4. **All 8 functions were single-use.** This suggests the agent created a
   reasonable module structure but did not complete the implementation before
   the timeout.

5. **Checkpoints 2 through 4 were skipped** because checkpoint 1 errored out.
   The $5 budget was barely touched ($0.16 spent).

6. **Comparison with prior run (d85a076):** A previous file_backup anti-slop
   experiment also reported INCONCLUSIVE results, suggesting file_backup
   may be a harder problem for the single-agent anti-slop configuration.

## Dolt Verification

Row inserted: experiments.id = 623
- problem_id: file_backup
- hypothesis_id: sc-hypotheses.281
- mode: single
- total_pass_rate: 0.125
- total_cost: 0.16

## Output Directory

`outputs/baseline_claude_code_local/local-claude-sonnet-4-6_file_backup_20260405_012937/`
