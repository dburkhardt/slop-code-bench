# Exp B8.10: code_search anti-slop replication

**Hypothesis:** sc-hypotheses.281 (H-prompt-only: Single-agent anti-slop prompt reduces verbosity at zero cost overhead)

**Problem:** code_search
**Model:** claude_code_local/local-claude-sonnet-4-6
**Prompt:** configs/prompts/anti_slop.jinja
**Mode:** single-only (baseline arm only)
**Budget:** $5.00 (actual spend: $0.52)

## Results

| Checkpoint | State | Pass Rate | Cost | LOC | Verbosity | Erosion | Steps |
|------------|-------|-----------|------|-----|-----------|---------|-------|
| 1 | ran | 100.0% | $0.17 | 127 | 0.000 | 0.000 | 7 |
| 2 | ran | 100.0% | $0.18 | 144 | 0.000 | 0.000 | 9 |
| 3 | error | 54.5% | $0.17 | 144 | 0.000 | 0.000 | 12 |
| 4 | skipped | - | - | - | - | - | - |
| 5 | skipped | - | - | - | - | - | - |

**Aggregate:** total_pass_rate=0.8485, total_cost=$0.52

## Observations

1. **Verbosity = 0.0 across all checkpoints.** The anti-slop prompt produced zero
   AST-Grep flagged lines and zero clone lines in all three completed checkpoints.

2. **Erosion = 0.0 across all checkpoints.** No high-complexity functions
   (CC > 10) were generated. Maximum cyclomatic complexity was 7 (checkpoint 1)
   and 6 (checkpoints 2-3).

3. **Checkpoint 3 timed out** during agent execution (Claude Code process timed
   out after 725s). The snapshot was identical to checkpoint 2 (zero lines
   added/removed), so the agent made no code changes before timing out. This
   caused checkpoints 4 and 5 to be skipped.

4. **Cost was low:** $0.52 total across 3 checkpoints, well under the $5 budget.
   Step utilization was 7-12% of the 100-step limit.

5. **Code stayed compact:** 127 LOC at checkpoint 1, growing to 144 LOC at
   checkpoint 2 with no further growth at checkpoint 3.

## Dolt Verification

Row inserted: experiments.id = 618
- problem_id: code_search
- hypothesis_id: sc-hypotheses.281
- mode: single
- total_pass_rate: 0.8485
- total_cost: 0.52

## Output Directory

`outputs/baseline_claude_code_local/local-claude-sonnet-4-6_code_search_20260405_001813/`
