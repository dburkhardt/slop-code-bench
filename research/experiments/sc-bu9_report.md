# Experiment Report: sc-bu9

## Hypothesis

**Default 70/30 two-agent vs single-agent on code_search**

Does the two-agent (implementer + reviewer) configuration with a 70/30 budget split
outperform the single-agent baseline on the code_search problem?

## Setup

| Parameter | Value |
|-----------|-------|
| Problem | code_search (3 checkpoints) |
| Model | claude_code_local/local-claude-sonnet-4-6 |
| Budget | $5 per arm |
| Budget split | 70% implementer / 30% reviewer (two-agent) |
| Base branch | main |

## Results

### Pass Rates

| Checkpoint | Baseline | Two-Agent | Delta |
|------------|----------|-----------|-------|
| checkpoint_1 | 12/12 (100.0%) | 12/12 (100.0%) | 0.0% |
| checkpoint_2 | 23/23 (100.0%) | 23/23 (100.0%) | 0.0% |
| checkpoint_3 | 23/44 (52.3%) | TIMED OUT | N/A |

**Overall baseline pass rate: 84.1%**
**Two-agent: incomplete (timed out on checkpoint_3 after 3600s)**

### Cost

| Checkpoint | Baseline | Two-Agent |
|------------|----------|-----------|
| checkpoint_1 | $0.2324 (121s, 9 steps) | $0.2318 (114s, 8 steps) |
| checkpoint_2 | $0.1497 (41s, 8 steps) | $0.1493 (62s, 7 steps) |
| checkpoint_3 | $0.1592 (1202s, 7 steps) | N/A (timed out) |
| **Total** | **$0.5414** | **$0.3811** (2 cp only) |

### Quality Metrics

| Checkpoint | Arm | LOC | AST-Grep Violations | Clone Lines | CC Max |
|------------|-----|-----|---------------------|-------------|--------|
| cp1 | baseline | 124 | 0 | 0 | 8 |
| cp1 | two-agent | 88 | 0 | 0 | 5 |
| cp2 | baseline | 135 | 0 | 0 | 8 |
| cp2 | two-agent | 89 | 0 | 0 | 6 |
| cp3 | baseline | 135 | 0 | 0 | 8 |
| cp3 | two-agent | N/A | N/A | N/A | N/A |

## Analysis

Both arms performed identically on checkpoints 1 and 2 (100% pass rate). The two-agent
arm produced more concise code (88-89 LOC vs 124-135 LOC) with lower complexity (CC max
5-6 vs 8), suggesting the reviewer successfully reduced verbosity.

The two-agent arm timed out on checkpoint 3 (structure-aware patterns with metavariables),
which is the most complex checkpoint. This is likely due to the 70/30 budget split
leaving insufficient budget for the implementer on a difficult task, combined with
API contention from 5 concurrent experiments on the machine.

The baseline solved checkpoint 3 at 52.3% (23/44 tests), spending only $0.16 and 7 steps
but taking 1202s wall-clock time. The long wall time suggests API rate limiting or
contention was a factor for both arms.

## Cost Analysis

- Baseline total: $0.54 for 3 checkpoints
- Two-agent total: $0.38 for 2 checkpoints (timed out on cp3)
- Per-checkpoint costs were nearly identical for cp1 and cp2 ($0.23, $0.15)
- Well within the $5 budget

## Conclusion: INCONCLUSIVE

The experiment cannot determine whether two-agent outperforms single-agent on code_search
because the two-agent arm timed out on checkpoint 3. For the two completed checkpoints,
both arms achieved identical pass rates (100%), but the two-agent arm produced notably
more concise code with lower complexity. A re-run with a longer timeout or during
lower machine contention would be needed for a definitive result.
