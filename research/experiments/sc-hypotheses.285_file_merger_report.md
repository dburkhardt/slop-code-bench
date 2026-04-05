# Experiment Report: sc-hypotheses.285 file_merger

## Hypothesis

**H-low-baseline**: Two-agent 60/40 split benefits problems with low single-agent baseline (<50% pass rate). file_merger has an expected baseline around 15%.

## Setup

- **Problem**: file_merger (4 checkpoints)
- **Model**: local-sonnet-4.6
- **Budget**: $5.00
- **Budget split**: 60/40 (implementer/reviewer)
- **Implementer prompt**: configs/prompts/default_implementer.jinja
- **Reviewer prompt**: configs/prompts/default_reviewer.jinja
- **Hypothesis ID**: sc-hypotheses.285
- **Date**: 2026-04-05

## Results

### Baseline (single-agent)

| Metric | Checkpoint 1 |
|--------|-------------|
| Pass rate | 7/46 (15.2%) |
| Elapsed | 788s |
| Status | **TIMED OUT** |
| Cost | $0.00 (tracking broken) |

The baseline agent timed out on checkpoint 1. It produced a snapshot but the entry file (`merge_files.py`) was not found, resulting in 0/18 core tests passing and only 7/46 total (all 7 from the Error group, which checks error handling).

### Two-agent (60/40)

| Metric | Checkpoint 1 |
|--------|-------------|
| Pass rate | 40/46 (87.0%) |
| Elapsed | 488s |
| Status | Completed CP1, then **pipeline timed out at 3600s** |
| Cost | $1.29 (CP1 implementer pass only) |

The two-agent arm completed checkpoint 1 with 87% pass rate (40/46 tests). Quality metrics: 0 AST-grep violations, max CC=16, 29 functions. The pipeline then timed out at the 3600s limit before the two-agent runner could finish checkpoints 2-4.

### Comparison (checkpoint 1 only)

| Metric | Baseline | Two-agent | Delta |
|--------|----------|-----------|-------|
| Pass rate | 15.2% | 87.0% | +71.7% |
| Elapsed | 788s | 488s | -300s |
| Completed | Error | OK | -- |

## Analysis

The two-agent arm dramatically outperformed the baseline on checkpoint 1 of file_merger, achieving 87% pass rate vs 15.2%. This is consistent with the H-low-baseline hypothesis that two-agent benefits low-baseline problems.

However, this result is **INCONCLUSIVE** for three reasons:

1. **Both arms failed to complete all 4 checkpoints.** The baseline timed out on CP1, and the two-agent arm timed out at the pipeline level (3600s) during subsequent checkpoints. We cannot compute total pass rates across all checkpoints.

2. **Baseline cost tracking returned $0.00**, making cost comparison impossible.

3. **Single run per arm.** Without replication, the CP1 delta could reflect variance rather than a real effect.

The partial CP1 data is suggestive but insufficient to confirm or refute the hypothesis.

## Cost Analysis

- Budget allocated: $5.00
- Two-agent CP1 cost: $1.29
- Baseline cost: unknown ($0.00 reported, likely a tracking bug)
- Budget remaining after run: not updated (pipeline skipped Dolt inserts)

## Conclusion

**INCONCLUSIVE.** Both arms failed to complete all checkpoints (baseline error on CP1, pipeline timeout at 3600s). Partial CP1 data shows +71.7% pass rate delta favoring two-agent (87% vs 15.2%), but without full checkpoint completion, this is not sufficient evidence to support or refute the hypothesis. The file_merger problem may require a higher timeout or budget allocation for complete runs.
