# Experiment Report: sc-hypotheses.283 — database_migration

## Hypothesis

60/40 budget split produces consistent positive pass-rate delta on database_migration.
Success criterion: >70% positive rate with mean delta >1pp.

## Setup

- **Problem**: database_migration (5 checkpoints)
- **Model**: local-sonnet-4.6
- **Budget**: $5.00 (split 60/40 implementer/reviewer)
- **Prompt**: default_implementer.jinja
- **Date**: 2026-04-05

## Results

### Baseline (single-agent)

| Checkpoint | Pass Rate | Cost   | Erosion | Verbosity | State |
|-----------|-----------|--------|---------|-----------|-------|
| 1         | 100.0%    | $0.509 | 0.339   | 0.014     | ran   |
| 2         |  95.1%    | $0.283 | 0.242   | 0.024     | ran   |
| 3         |  81.2%    | $0.424 | 0.328   | 0.096     | error |
| 4         | skipped   | —      | —       | —         | skipped |
| 5         | skipped   | —      | —       | —         | skipped |

**Total cost**: $1.22. **Mean pass rate (cp1-3)**: 92.1%.
Timed out at checkpoint 3 (AgentError: Claude Code process timed out).

### Two-Agent (merged)

| Checkpoint | Pass Rate | Cost   | Erosion | Verbosity | State |
|-----------|-----------|--------|---------|-----------|-------|
| 1         | 30.8%     | $0.159 | 0.000   | 0.000     | ran   |
| 2         | 34.4%     | $0.183 | 0.000   | 0.000     | ran   |
| 3         | 38.8%     | $0.136 | 0.000   | 0.000     | ran   |
| 4         | 31.1%     | $0.131 | 0.000   | 0.000     | ran   |
| 5         | 33.1%     | $0.129 | 0.000   | 0.000     | ran   |

**Total cost**: $1.31 (reviewer $0.57 + merger $0.74). **Mean pass rate (cp1-3)**: 34.7%.

The reviewer arm also timed out at checkpoint 3 (same error as baseline).
Zero erosion and verbosity across all merged checkpoints suggests the merge phase
produced minimal or structurally trivial code.

### Reviewer Arm (pre-merge)

| Checkpoint | Pass Rate | Cost   | State |
|-----------|-----------|--------|-------|
| 1         | 100.0%    | $0.200 | ran   |
| 2         |  90.2%    | $0.269 | ran   |
| 3         |  77.6%    | $0.103 | error |

## Analysis

**Pass-rate delta (cp1-3)**: -57.4pp (two-agent much worse than baseline).

The two-agent workflow failed on this problem for two reasons:

1. Both the implementer and reviewer arms timed out at checkpoint 3 of 5,
   meaning the merge phase received incomplete inputs.
2. The merged output achieved only 31-39% pass rates across all checkpoints,
   compared to 81-100% for the baseline on cp1-3. The zero erosion/verbosity
   in the merged output suggests the merger produced minimal code.

The cost ratio was 1.08x (two-agent $1.31 vs baseline $1.22), so the two-agent
approach was slightly more expensive while delivering much worse results.

## Cost Analysis

| Arm         | Cost   |
|-------------|--------|
| Baseline    | $1.22  |
| Reviewer    | $0.57  |
| Merger      | $0.74  |
| Two-agent total | $1.31 |
| **Combined spend** | **$2.53** |

## Conclusion

**INCONCLUSIVE** — Both arms timed out at checkpoint 3. The database_migration
problem appears to be too complex for the per-checkpoint timeout limit, causing
both single-agent and two-agent workflows to error. The two-agent merged results
are unreliable because they were built from incomplete (timed-out) inputs. This
run cannot be used to evaluate the 60/40 split hypothesis.
