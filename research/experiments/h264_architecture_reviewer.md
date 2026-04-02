# H264: Architecture Reviewer vs Baseline on circuit_eval + execution_server

**Hypothesis:** The architecture-focused reviewer prompt reduces structural erosion (high_cc_pct) compared to the default reviewer on long-sequence problems (circuit_eval, execution_server), because it specifically targets complexity distribution and module organization.

**Predicted outcome:** Erosion slope (high_cc_pct growth per checkpoint) reduced by 20-40% vs default reviewer. Pass rate may drop 0-10pp due to reviewer overhead spent on refactoring rather than bug fixes.

**Testable claim:** Architecture reviewer produces lower high_cc_pct than default reviewer on circuit_eval and execution_server, while maintaining pass rate within 10pp.

**Verdict:** PENDING

## Design

### Arms

| Parameter | Baseline (single-agent) | Treatment (two-agent + architecture reviewer) |
|-----------|------------------------|-----------------------------------------------|
| Run config | `configs/runs/h264_*_baseline.yaml` | `configs/runs/h264_*_arch_reviewer.yaml` |
| Agent type | claude_code | reviewer_coder |
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Implementer prompt | just-solve | just-solve |
| Reviewer prompt | N/A | `research/prompts/architecture-reviewer.jinja` |
| Budget split | N/A | 70/30 |
| Review cycles | N/A | 3 |
| Coder turns/batch | N/A | 10 |
| Problems | circuit_eval, execution_server | circuit_eval, execution_server |

### Primary metric

**Structural erosion** (mass.high_cc_pct) across checkpoints. This measures the concentration of cyclomatic complexity in high-CC functions. A higher value means complexity is concentrated in fewer, more complex functions.

The slope captures how quickly erosion compounds through iterative specification refinement. The architecture reviewer targets complexity distribution directly, so it should produce a flatter slope.

### Secondary metrics

- **Pass rate** (to confirm reviewer does not harm correctness by more than 10pp)
- **Verbosity** (AST-Grep Flagged Lines + Clone Lines / LOC)
- **Cost** (total and per-checkpoint)
- **LOC** (to detect whether the reviewer simply produces shorter code)

### Why these problems

circuit_eval (8 checkpoints) and execution_server (6 checkpoints) are the longest-sequence problems in the benchmark. Structural erosion compounds over checkpoints, so long sequences give the architecture reviewer the most opportunity to show an effect. The hypothesis predicts complexity concentration in a few functions over successive checkpoints, which these problems are most likely to exhibit.

### Controls

Both arms use the same model (local-claude-sonnet-4-6), thinking mode (none), pass policy (any), and budget ($5.00 per arm). The only difference is the agent type and reviewer prompt.

## Execution

### Via experiment pipeline (runs both arms)

```bash
python research/runner/experiment_pipeline.py \
  --problem circuit_eval \
  --model local-claude-sonnet-4-6 \
  --budget 5.0 \
  --budget-split 70 \
  --reviewer-prompt research/prompts/architecture-reviewer.jinja \
  --hypothesis-id sc-hypotheses.264

python research/runner/experiment_pipeline.py \
  --problem execution_server \
  --model local-claude-sonnet-4-6 \
  --budget 5.0 \
  --budget-split 70 \
  --reviewer-prompt research/prompts/architecture-reviewer.jinja \
  --hypothesis-id sc-hypotheses.264
```

### Via individual run configs

```bash
# Baseline
slop-code run --config configs/runs/h264_circuit_eval_baseline.yaml
slop-code run --config configs/runs/h264_execution_server_baseline.yaml

# Treatment
slop-code run --config configs/runs/h264_circuit_eval_arch_reviewer.yaml
slop-code run --config configs/runs/h264_execution_server_arch_reviewer.yaml
```

## Analysis plan

1. Compute per-checkpoint structural erosion (mass.high_cc_pct) for both arms on both problems.
2. Fit a linear slope to erosion across checkpoints for each arm.
3. Compare slopes: the treatment should show a flatter (lower) erosion slope.
4. Check that pass rates are comparable (within 10pp).
5. Report cost overhead of the two-agent configuration.
6. Secondary: check whether verbosity also decreases (the architecture reviewer does not target verbosity directly, but cleaner structure may reduce it as a side effect).

### Success criteria

The hypothesis is **supported** if:
- Erosion slope is at least 20% lower in the treatment arm across both problems
- Pass rate does not degrade by more than 10pp compared to baseline

## KB provenance

- sc-research-kb.90: MACOG shows 17-point reviewer uplift; architecture-specific review should target erosion metrics directly
- sc-research-kb.211: Multi-agent failure modes warn refactoring-heavy reviewer may introduce coordination overhead

## Results

*To be filled after execution.*
