# Experiment Report: H-prompt-only file_backup (sc-hypotheses.281)

## Overview

| Field | Value |
|-------|-------|
| Problem | file_backup |
| Model | claude_code_local/local-claude-sonnet-4-6 |
| Budget | $5/arm |
| Budget Split | 60/40 (implementer/reviewer) |
| Hypothesis | sc-hypotheses.281 (anti-slop prompt reduces verbosity at zero cost overhead) |
| Date | 2026-04-04 |

## Baseline (Single-Agent with Anti-Slop Prompt)

| Checkpoint | Pass Rate | Cost | Steps | Elapsed |
|------------|-----------|------|-------|---------|
| 1 | 87.5% (28/32) | $0.61 | 10 | 372s |
| 2 | 82.0% (41/50) | $0.67 | 18 | 317s |
| 3 | 77.9% (53/68) | $0.72 | 27 | 373s |
| 4 | 75.3% (67/89) | $0.22 | 15 | 651s |

**Totals:** Mean pass rate = 80.7%, Total cost = $2.23

**Quality metrics (per checkpoint):**

| Checkpoint | LOC | AST Violations | Verbosity | CC Max | CC Sum | Functions |
|------------|-----|----------------|-----------|--------|--------|-----------|
| 1 | 152 | 0 | 0.000 | 8 | 41 | 15 |
| 2 | 252 | 0 | 0.000 | 8 | 63 | 25 |
| 3 | 324 | 0 | 0.000 | 10 | 80 | 29 |
| 4 | 324 | 0 | 0.000 | 10 | 80 | 29 |

### Observations

Checkpoint 4 timed out (Claude Code process timeout). The snapshot and quality metrics are identical to checkpoint 3, indicating no code changes were made. The agent spent 651s on checkpoint 4 with only 92 output tokens and 15 steps before timing out, suggesting it struggled with the incremental backup extension.

Pass rate declined monotonically from 87.5% to 75.3% across checkpoints as test count grew from 32 to 89. The anti-slop prompt was highly effective: zero AST-grep violations and zero verbosity flags across all checkpoints. No structural erosion was detected (high_cc_pct = 0.0 throughout, cc_max never exceeded 10).

## Two-Agent (60/40 Split)

The two-agent arm exceeded the $5 budget after a single checkpoint. The implementer consumed $2.54 and the reviewer consumed $2.89, totaling $5.42 for checkpoint 1 alone.

| Checkpoint | Pass Rate | Cost | Tokens (Impl) | Tokens (Rev) |
|------------|-----------|------|---------------|--------------|
| 1 | 87.5% (28/32) | $5.42 | 4,529,929 | 3,477,614 |
| 2-4 | -- (budget exceeded) | -- | -- | -- |

**Totals:** Mean pass rate = 87.5% (1 checkpoint), Total cost = $5.42

**Quality (checkpoint 1 only):** LOC = 186, AST violations = 0, CC max = 8, CC sum = 46, functions = 15.

### Observations

The two-agent arm produced 22% more code (186 vs 152 LOC) for identical pass rate (87.5%) on checkpoint 1. The reviewer consumed 3.5M tokens reviewing the implementer's work, without improving pass rate. The combined cost ($5.42) exceeded the entire $5 budget on a single checkpoint, leaving no budget for checkpoints 2-4.

## Comparison

| Metric | Baseline | Two-Agent |
|--------|----------|-----------|
| Checkpoints completed | 4 (cp4 timed out) | 1 (budget exceeded) |
| cp1 pass rate | 87.5% | 87.5% |
| Mean pass rate | 80.7% | 87.5% |
| Total cost | $2.23 | $5.42 |
| Cost per checkpoint | $0.56 | $5.42 |
| LOC (cp1) | 152 | 186 |
| Verbosity | 0.000 | 0.000 |
| Erosion (high_cc_pct) | 0.000 | 0.000 |

## Analysis

The hypothesis predicts that a single-agent anti-slop prompt can achieve verbosity reduction at zero additional cost. The baseline results support this: verbosity was 0.000 across all checkpoints with zero AST-grep violations. The anti-slop prompt completely suppressed verbose patterns.

The two-agent arm failed to add value: it produced the same pass rate on checkpoint 1 (87.5%) at 8.8x the cost ($5.42 vs $0.61). The reviewer spent 3.5M tokens without changing the outcome. Budget exhaustion after one checkpoint meant the two-agent approach could not attempt checkpoints 2-4, losing the iterative signal entirely.

The baseline's pass rate decline (87.5% to 75.3%) across checkpoints is consistent with the benchmark's iterative difficulty scaling. Checkpoint 4's timeout suggests the incremental backup specification was beyond the agent's capacity within wall-clock limits, regardless of prompt.

## Cost Analysis

| Arm | Total | Per Checkpoint | Budget Utilization |
|-----|-------|----------------|-------------------|
| Baseline | $2.23 | $0.56 | 45% |
| Two-Agent | $5.42 | $5.42 | 108% (exceeded) |

The two-agent arm's per-checkpoint cost was 9.7x higher than baseline. With a $5 budget, the baseline could run all 4 checkpoints with headroom, while the two-agent arm exhausted the budget on checkpoint 1.

## Conclusion: INCONCLUSIVE

The anti-slop prompt eliminated all measured verbosity in the single-agent baseline, supporting the hypothesis that prompt-only changes can reduce verbosity. However, a proper test requires comparison against the default prompt (without anti-slop instructions) on the same problem, which was not part of this experiment. The two-agent comparison shows the reviewer adds no value on this problem at enormous cost, but does not directly test whether anti-slop prompt changes improve on the default prompt.
