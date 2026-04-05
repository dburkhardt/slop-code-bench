# Exp B9.3: file_backup anti-slop replication

**Hypothesis:** sc-hypotheses.281 (H-prompt-only: Single-agent anti-slop prompt reduces verbosity at zero cost overhead)

**Problem:** file_backup
**Model:** claude_code_local/local-claude-sonnet-4-6
**Prompt:** configs/prompts/anti_slop.jinja
**Mode:** single-only (baseline arm only)
**Budget:** $5.00 (actual spend: $3.36)

## Results

| Checkpoint | State | Pass Rate | Core Pass | Cost | LOC | Verbosity | Erosion | Steps |
|------------|-------|-----------|-----------|------|-----|-----------|---------|-------|
| 1 | ran | 87.5% | 100.0% | $0.87 | 321 | 0.000 | 0.000 | 16 |
| 2 | ran | 82.0% | 66.7% | $0.60 | 489 | 0.016 | 0.000 | 21 |
| 3 | ran | 77.9% | 66.7% | $0.72 | 583 | 0.000 | 0.238 | 23 |
| 4 | ran | 80.9% | 100.0% | $1.18 | 718 | 0.000 | 0.225 | 28 |

**Aggregate:** total_pass_rate=0.82, total_cost=$3.36

## Observations

1. **All four checkpoints completed successfully.** The agent solved all checkpoints
   within the 100-step limit (16-28 steps per checkpoint, 16-28% utilization).

2. **Verbosity was near zero.** Only checkpoint 2 had any verbosity (0.016, from 8
   clone lines). Checkpoints 1, 3, and 4 had zero AST-Grep violations and zero clone
   lines. Mean verbosity across checkpoints: 0.004.

3. **Structural erosion appeared at checkpoint 3.** A function with CC=13 emerged at
   checkpoint 3 (erosion=0.238), persisting into checkpoint 4 with CC=15 (erosion=0.225).
   This is consistent with the paper's finding that high-complexity symbols grow across
   checkpoints even when pass rates are stable.

4. **Core pass rate dipped at checkpoints 2-3** (66.7%) before recovering to 100% at
   checkpoint 4. Overall strict pass rate declined from 87.5% to 80.9%, with
   functionality tests accounting for most failures (18/22 passed at CP1, 15/17 at CP4).

5. **LOC grew steadily:** 321 to 718 lines across four checkpoints, roughly doubling.
   The churn ratio averaged 0.38 per checkpoint, indicating substantial code modification
   at each step.

6. **Cost was moderate:** $3.36 total, within the $5 budget. Per-checkpoint costs ranged
   from $0.60 to $1.18, with later checkpoints costing more as the codebase grew.

## Dolt Verification

Row inserted: experiments.id = 626
- problem_id: file_backup
- hypothesis_id: sc-hypotheses.281
- mode: single
- total_pass_rate: 0.82
- total_cost: 3.36

## Output Directory

`outputs/baseline_claude_code_local/local-claude-sonnet-4-6_file_backup_20260405_012739/`
