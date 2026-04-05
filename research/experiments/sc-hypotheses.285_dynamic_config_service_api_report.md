# Experiment Report: sc-hypotheses.285 — dynamic_config_service_api

## Hypothesis

**H-low-baseline**: Two-agent (60/40 split) benefits problems with low single-agent baseline (<50% pass rate). Testing on `dynamic_config_service_api` (untested, likely low baseline).

## Setup

- **Problem**: dynamic_config_service_api (1 checkpoint in problem, multi-checkpoint evaluation)
- **Model**: local-sonnet-4.6
- **Budget**: $5.00, 60/40 implementer/reviewer split
- **Implementer prompt**: configs/prompts/default_implementer.jinja
- **Reviewer prompt**: configs/prompts/default_reviewer.jinja
- **Date**: 2026-04-05

## Results

### Baseline (Single-Agent)

| Checkpoint | State | Pass Rate | Core Pass | Cost | Steps | Duration |
|------------|-------|-----------|-----------|------|-------|----------|
| checkpoint_1 | error (timeout) | 0.0% (0/47) | 0.0% (0/13) | $0.00 | 0 | 827s |

The baseline agent timed out without producing any code (0 steps, 0 tokens). The Claude Code process timed out after ~827 seconds.

### Two-Agent

| Phase | Checkpoint | State | Pass Rate | Core Pass | Cost | Steps | Duration |
|-------|------------|-------|-----------|-----------|------|-------|----------|
| Implementer | cp1 | error (timeout) | 0.0% (0/47) | 0.0% (0/13) | $0.00 | 0 | 827s |
| Reviewer | cp1 | ran | 83.0% (39/47) | 84.6% (11/13) | $0.31 | 15 | 450s |
| Reviewer | cp2 | error | 51.6% (48/93) | 26.3% (5/19) | $0.047 | 2 | 750s |
| Re-impl | cp1 | error (timeout) | 0.0% (0/47) | 0.0% (0/13) | $0.061 | 3 | 610s |

**Total two-agent cost**: $0.356

The implementer phase timed out identically to the baseline. However, the reviewer agent, starting from the empty/failed implementer output, independently built a working solution achieving 83% pass rate on checkpoint 1 (11/13 core tests). This is a notable result: the reviewer effectively acted as a fresh implementer rather than a code reviewer.

Checkpoint 2 regressed to 51.6% strict pass rate (only 5/19 core tests) with just 2 steps, suggesting the reviewer could not adapt the solution to new requirements.

A re-implementation attempt (likely the pipeline's fallback) also timed out.

### Quality Metrics (Two-Agent, Checkpoint 1)

| Metric | Value |
|--------|-------|
| LOC | 486 |
| SLOC | 402 |
| Verbosity | 17.5% |
| Erosion (high_cc_pct) | 51.2% |
| CC max | 27 |
| CC mean | 5.33 |
| Clone lines | 85 |
| Lint errors | 29 |
| Trivial wrappers | 3 |
| Unused variables | 5 |

High erosion (51.2%) and moderate verbosity (17.5%). The code has two high-complexity functions driving the erosion metric. Significant code duplication (85 clone lines).

## Analysis

**Baseline confirmed as low**: 0% pass rate (timeout), validating this as a "low baseline" problem for the hypothesis test. However, 0% is anomalous; it suggests an infrastructure issue (agent process timeout) rather than a genuinely difficult problem.

**Two-agent result is ambiguous**: The reviewer achieved 83% pass rate on checkpoint 1, but the implementer produced nothing. The reviewer essentially did the implementer's job rather than reviewing existing code. This does not test the intended two-agent dynamic (implementer produces code, reviewer refines it).

**Timeout pattern**: Both baseline and two-agent implementer timed out identically (827s, 0 steps, 0 cost). This suggests a systemic issue with how Claude Code processes launch for this problem, not a model capability limitation.

**No Dolt insertion**: The pipeline did not insert results because it classified both arms as failed. Partial metrics exist only in local output files.

## Cost Analysis

- Baseline: $0.00 (timed out before any API calls)
- Two-agent: $0.356 total ($0.31 reviewer cp1, $0.047 reviewer cp2, $0.061 re-impl attempt)
- Budget remaining: $607.70 (from $607.70 pre-experiment; the $0.356 was deducted)

## Conclusion: INCONCLUSIVE

Both arms experienced identical timeout failures in the implementer/baseline phase. The two-agent reviewer achieved strong results (83% pass) by building from scratch, but this does not test the hypothesis as intended. The timeout pattern suggests an infrastructure issue with this specific problem rather than a model capability boundary.

**Recommendation**: Retry with a longer timeout or investigate why Claude Code times out on dynamic_config_service_api. The problem itself appears solvable (reviewer proved 83% achievable).
