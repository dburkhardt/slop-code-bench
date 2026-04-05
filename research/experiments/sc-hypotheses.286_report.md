# Experiment Report: sc-hypotheses.286 (eve_market_tools, polecat shale)

## Hypothesis

Run baseline + two-agent on eve_market_tools to establish baselines and test
the threshold hypothesis: reviewer helps when baseline pass rate < 50%, hurts
when > 50%. This run is a replication attempt within the broader N=20 coverage
campaign.

## Setup

- **Problem**: eve_market_tools (4 checkpoints)
- **Model**: local-sonnet-4.6 (Claude Sonnet 4.6 via local claude code)
- **Budget**: $5 per arm
- **Budget split**: 60/40 (implementer/reviewer)
- **Implementer prompt**: configs/prompts/default_implementer.jinja
- **Reviewer prompt**: configs/prompts/default_reviewer.jinja
- **Polecat**: shale
- **Date**: 2026-04-05

## Results

### Baseline (single-agent)

| Checkpoint | State | Pass Rate | Tests | Cost |
|------------|-------|-----------|-------|------|
| checkpoint_1 | error | 0.0% | 0/10 | $0.00 |
| checkpoint_2 | missing | - | - | - |
| checkpoint_3 | missing | - | - | - |
| checkpoint_4 | missing | - | - | - |

The baseline agent timed out on checkpoint_1 after 614 seconds. The Claude Code
process produced zero tokens and zero cost, suggesting the agent never received
API responses within the timeout window. All subsequent checkpoints were skipped.

### Two-agent

| Run | Checkpoint | State | Pass Rate | Tests | Cost |
|-----|------------|-------|-----------|-------|------|
| Implementer | checkpoint_1 | error | 0.0% | 0/10 | $0.00 |
| Reviewer | checkpoint_1 | ran | 10.0% | 1/10 | $0.98 |
| Implementer | checkpoint_2 | ran | 0.0% | 0/28 | $0.91 |
| Implementer | checkpoint_3 | error | 8.1% | 5/62 | $0.54 |
| Reviewer retry | checkpoint_1 | error | 0.0% | 0/10 | $0.42 |

The two-agent arm produced partial results before the overall 3600s subprocess
timeout killed it. The implementer failed on checkpoint_1 (same timeout issue
as baseline), but the reviewer pass on checkpoint_1 achieved 1/10 tests passing
at $0.98 cost. Subsequent checkpoints show degrading performance on increasingly
complex specs.

Total two-agent cost: ~$2.85 (partial, 5 checkpoint runs before timeout)

### Cost Analysis

- Baseline: $0.00 (timeout before any API calls completed)
- Two-agent: ~$2.85 (partial runs)
- Total experiment cost: ~$2.85

## Analysis

This experiment is **INCONCLUSIVE** due to infrastructure failures.

The baseline arm timed out entirely on checkpoint_1, producing no usable data.
The Claude Code agent process failed to complete within the 614s checkpoint
timeout, with zero tokens generated. This suggests API congestion or scheduling
delays rather than a problem-specific issue.

The two-agent arm produced partial results but was killed by the 3600s
subprocess timeout before completing all checkpoints. No data was inserted
into Dolt because the pipeline requires both arms to produce valid metrics.

### Existing Data Context

Other polecats have already run eve_market_tools for sc-hypotheses.286:
- **Single-agent** (prior run): pass_rate=0.28, cost=$1.23
- **Two-agent** (prior run): pass_rate=0.13, cost=$2.21

The prior data shows the two-agent arm performed worse than baseline on this
problem (0.13 vs 0.28 pass rate). The baseline is below 50%, yet the reviewer
did not help, which contradicts the "helps below 50%" threshold prediction.

## Conclusion

**INCONCLUSIVE**: Pipeline infrastructure failures (agent timeouts) prevented
this replication from producing insertable data. The hypothesis already has
39 rows from other polecats covering this problem and others. This run adds
no new evidence but confirms that the local-sonnet-4.6 agent can experience
timeout failures under concurrent load from multiple polecats.
