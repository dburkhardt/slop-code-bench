# H203: Structured Anti-Slop Reviewer vs Baseline on file_backup + todo_app

**Hypothesis:** Structured reviewer prompts that explicitly target verbosity reduce the verbosity slope compared to baseline.

**Predicted outcome:** Two-agent with the anti-slop reviewer prompt yields lower verbosity slope than baseline across 3+ problems.

**Testable claim:** Structured reviewer prompts reduce verbosity slope by at least 15%.

**Verdict:** PENDING

## Design

### Arms

| Parameter | Baseline (single-agent) | Treatment (two-agent + anti-slop) |
|-----------|------------------------|-----------------------------------|
| Run config | `configs/runs/h203_anti_slop_baseline.yaml` | `configs/runs/h203_anti_slop_two_agent.yaml` |
| Agent type | claude_code | reviewer_coder |
| Model | opus-4.5 | opus-4.5 |
| Implementer prompt | just-solve | just-solve |
| Reviewer prompt | N/A | `research/prompts/anti-slop-reviewer.jinja` |
| Budget split | N/A | 70/30 |
| Review cycles | N/A | 3 |
| Coder turns/batch | N/A | 10 |
| Problems | file_backup, todo_app | file_backup, todo_app |

### Primary metric

**Verbosity slope** across checkpoints. Verbosity is defined as `{AST-Grep Flagged Lines + Clone Lines} / LOC`.

The slope captures how quickly verbosity compounds through iterative specification refinement. A steeper slope means slop accumulates faster across checkpoints.

### Secondary metrics

- **Pass rate** (to confirm reviewer does not harm correctness)
- **Structural erosion** (mass.high_cc_pct)
- **Cost** (total and per-checkpoint)
- **LOC** (to detect whether the reviewer simply produces shorter code rather than less verbose code)

### Why these problems

The bead metadata specifies file_backup and todo_app. Both are multi-checkpoint problems where verbosity can compound across iterations, making them suitable for measuring verbosity slope.

### Controls

Both arms use the same model (opus-4.5), thinking mode (none), pass policy (any), and environment (docker-python3.12-uv). The only difference is the agent type and reviewer prompt.

## Execution

### Via experiment pipeline (runs both arms)

```bash
python research/runner/experiment_pipeline.py run \
  --problem file_backup \
  --model opus-4.5 \
  --budget 5.0 \
  --budget-split 70 \
  --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
  --hypothesis-id sc-hypotheses.203

python research/runner/experiment_pipeline.py run \
  --problem todo_app \
  --model opus-4.5 \
  --budget 5.0 \
  --budget-split 70 \
  --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
  --hypothesis-id sc-hypotheses.203
```

### Via individual run configs

```bash
# Baseline
slop-code run --config configs/runs/h203_anti_slop_baseline.yaml

# Treatment
slop-code run --config configs/runs/h203_anti_slop_two_agent.yaml
```

## Analysis plan

1. Compute per-checkpoint verbosity for both arms on both problems.
2. Fit a linear slope to verbosity across checkpoints for each arm.
3. Compare slopes: the treatment should show a flatter (lower) verbosity slope.
4. Check that pass rates are comparable (the reviewer should not harm correctness).
5. Report cost overhead of the two-agent configuration.

### Success criteria

The hypothesis is **supported** if:
- Verbosity slope is at least 15% lower in the treatment arm across both problems
- Pass rate does not degrade by more than 5% compared to baseline

## H2 lessons incorporated

H2 (sc-hypotheses.237) found that the reviewer_coder agent's reviewer output extraction was broken (zero suggestions extracted). This experiment uses the same reviewer_coder agent, so the same extraction issue may apply. If reviewer suggestions are again not extracted, the treatment arm's verbosity reduction (if any) would be attributable to the CODER_APPEND_PROMPT rather than the anti-slop reviewer prompt itself.

To distinguish the reviewer prompt effect from the coder append prompt effect, results should be compared against H2's two-agent quality metrics (which used the default reviewer prompt).

## Results

*To be filled after execution.*
