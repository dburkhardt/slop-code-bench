# H281: Two-Agent (60/40) with Anti-Slop Prompt on eve_industry

**Hypothesis:** Two-agent at 60/40 split with anti-slop implementer prompt improves pass rate and reduces verbosity compared to single-agent baseline on eve_industry (6 checkpoints).

**Bead:** sc-hypotheses.281

**Verdict:** REFUTED. The two-agent arm performed drastically worse than the baseline, achieving only 22% average pass rate vs 91% for single-agent. The reviewer loop degraded checkpoint 1 from near-functional to broken, and downstream checkpoints never recovered.

## Setup

| Parameter | Single-Agent (Baseline) | Two-Agent (60/40) |
|-----------|------------------------|-------------------|
| Agent type | claude_code | reviewer_coder |
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Implementer prompt | anti_slop | anti_slop |
| Reviewer prompt | N/A | default_reviewer |
| Cost limit | $5.00 total | $5.00 total (60% impl, 40% review) |
| Budget split | N/A | 60/40 |
| Environment | local-py | local-py |

## Results

### Baseline (single-agent)

| Checkpoint | Pass Rate | Tests | Cost | LOC | CC sum | Verbosity |
|------------|-----------|-------|------|-----|--------|-----------|
| cp1 | 100.0% (12/12) | 12 | $0.87 | 253 | 51 | 0.000 |
| cp2 | 81.8% (27/33) | 33 | $0.58 | 573 | 118 | 0.017 |
| cp3-cp6 | not reached (budget) | - | - | - | - | - |
| **Total** | **90.9%** | - | **$1.45** | - | - | - |

The baseline completed checkpoint 1 perfectly and achieved a solid 82% on checkpoint 2 before the agent timed out on the second checkpoint's implementation (600s). Total spend was $1.45 of the $5 budget. Checkpoint 2 had 6 test failures, all in the invention functionality category (Tech III ships and advanced invention mechanics).

### Two-Agent (60/40)

| Checkpoint | Pass Rate | Tests | Cost | Error |
|------------|-----------|-------|------|-------|
| cp1 | 25.0% (3/12) | 12 | $0.48 | No |
| cp2 | 18.2% (6/33) | 33 | $0.40 | Yes (timeout) |
| cp3 | 22.0% (11/50) | 50 | $0.15 | No |
| **Total** | **21.7%** | - | **$1.02** | - |

The two-agent arm completed 3 checkpoints but with severe quality degradation. Checkpoint 1 passed only error-handling tests (3/12); all core and functionality tests failed. The reviewer phase apparently broke the working implementation rather than improving it. Checkpoint 2 timed out at 900s. Checkpoint 3 continued to accumulate failures with only 11/50 tests passing.

The two-agent pipeline itself timed out at 3600s, preventing further checkpoints.

### Comparison

| Metric | Baseline | Two-Agent (60/40) | Delta |
|--------|----------|-------------------|-------|
| cp1 pass rate | 100.0% | 25.0% | -75.0pp |
| cp2 pass rate | 81.8% | 18.2% | -63.6pp |
| Mean pass rate | 90.9% | 21.7% | -69.2pp |
| Total cost | $1.45 | $1.02 | -$0.43 |
| Checkpoints completed | 2/6 | 3/6 | +1 |

## Cost Analysis

| Metric | Baseline | Two-Agent |
|--------|----------|-----------|
| Total spend | $1.45 | $1.02 |
| Cost per checkpoint | $0.73 | $0.34 |
| Pass-rate-weighted cost | $1.60/pass | $4.64/pass |

The two-agent arm spent less overall ($1.02 vs $1.45) but achieved far worse results. On a cost-per-passing-test basis, the two-agent approach was roughly 3x more expensive.

## Analysis

The results are unambiguous: the two-agent 60/40 configuration with anti-slop prompting severely degraded performance on eve_industry.

The core failure pattern matches what prior experiments (H286.9) observed on this problem. The reviewer loop introduces modifications that break previously working code at checkpoint 1, and this damage propagates to all subsequent checkpoints. With only 25% pass rate at cp1, the two-agent arm was doomed from the start.

eve_industry's checkpoint 1 involves parsing complex YAML game data (EVE Online SDE files) and computing manufacturing recipes. This domain-specific task appears poorly suited to a review-then-revise workflow, where the reviewer may not understand the domain constraints well enough to suggest improvements without breaking correctness.

The anti-slop implementer prompt did not improve the situation. The baseline's anti-slop output was already clean (0 AST-grep violations at cp1, 10 flagged lines at cp2), leaving little room for a reviewer to reduce verbosity.

## Conclusion

**REFUTED.** Two-agent with anti-slop prompting produces catastrophically worse results than single-agent on eve_industry. The 69pp pass-rate drop and 3x worse cost efficiency confirm that the reviewer loop is harmful for this problem type. This is consistent with the pattern that domain-specific data processing problems do not benefit from code review, as the reviewer lacks the domain knowledge to avoid breaking correctness.
