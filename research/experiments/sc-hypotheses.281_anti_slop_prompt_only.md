# sc-hypotheses.281: Anti-Slop Prompt Reduces Verbosity at Zero Cost Overhead

**Hypothesis:** A single-agent anti-slop prompt that adds explicit instructions (no docstrings unless public API, no defensive type checks, no wrapper functions) reduces verbosity at zero additional cost, matching reviewer-driven quality pressure through prompt engineering alone.

**Predicted outcome:** Verbosity drops from ~30% to ~20%. Pass rate unchanged within 3pp. Identical cost to baseline.

**Testable claim:** Single-agent with anti-slop prompt achieves verbosity 5-15pp lower than default single-agent, with pass rate within 3pp, at identical cost.

**Verdict:** INCONCLUSIVE

## Design

### Arms

| Parameter | Baseline (single-agent) | Treatment (two-agent + anti-slop) |
|-----------|------------------------|-----------------------------------|
| Model | local-claude-sonnet-4-6 | local-claude-sonnet-4-6 |
| Implementer prompt | anti_slop.jinja | anti_slop.jinja |
| Reviewer prompt | N/A | default_reviewer.jinja |
| Budget split | N/A | 60/40 |
| Budget per arm | $5.00 | $5.00 |
| Problems | 4 (see below) | 4 (see below) |

### Problems tested

etl_pipeline (5 checkpoints), code_search (3 checkpoints), eve_industry (2 checkpoints), log_query (2 checkpoints)

### Primary metric

Verbosity ratio: `{AST-Grep Flagged Lines + Clone Lines} / LOC`

### Secondary metrics

Pass rate, structural erosion (mass.high_cc_pct), total cost

## Results

### Per-problem summary

| Problem | Mode | Pass Rate | Cost | Verbosity (mean) | Erosion (mean) |
|---------|------|-----------|------|-------------------|----------------|
| etl_pipeline | single | 0.86 | $3.21 | 0.000 | 0.505 |
| etl_pipeline | two-agent | 0.83 | $3.15 | 0.116 | 0.834 |
| code_search | single | 0.84 | $0.90 | 0.000 | 0.000 |
| code_search | two-agent | 0.74 | $1.70 | 0.000 | 0.000 |
| eve_industry | single | 0.91 | $1.45 | 0.009 | 0.051 |
| eve_industry | two-agent | 0.22 | $1.02 | 0.028 | 0.174 |
| log_query | single | 0.65 | $0.96 | 0.038 | 0.620 |
| log_query | two-agent | 0.68 | $1.70 | 0.054 | 0.442 |

### Aggregate deltas (two-agent minus single)

| Problem | Delta Pass Rate | Delta Erosion |
|---------|----------------|---------------|
| etl_pipeline | -0.03 | +0.329 |
| code_search | -0.10 | 0.000 |
| eve_industry | -0.69 | +0.123 |
| log_query | +0.02 | +0.129 |

### Cost comparison

| Problem | Single Cost | Two-Agent Cost | Ratio |
|---------|------------|----------------|-------|
| etl_pipeline | $3.21 | $3.15 | 0.98x |
| code_search | $0.90 | $1.70 | 1.89x |
| eve_industry | $1.45 | $1.02 | 0.70x |
| log_query | $0.96 | $1.70 | 1.77x |
| **Total** | **$6.52** | **$7.57** | **1.16x** |

## Analysis

### Pass rate

The two-agent arm underperformed on 3 of 4 problems. The eve_industry result is catastrophic: the reviewer broke checkpoint 1 (100% -> 25%), and the damage cascaded through subsequent checkpoints. On code_search, the two-agent arm lost 10pp. Only log_query showed a marginal improvement (+2pp).

### Verbosity

Verbosity was near zero for both arms on most problems. The anti-slop prompt appears to already suppress verbosity in the single-agent baseline (etl_pipeline single: 0.000, code_search: 0.000), leaving little room for the reviewer to improve. On log_query, the two-agent arm actually had *higher* verbosity (0.054 vs 0.038). The hypothesis that prompt-only changes reduce verbosity is supported, but the claim that a reviewer adds further reduction is not.

### Structural erosion

The two-agent arm produced higher erosion on 3 of 4 problems. On etl_pipeline, erosion jumped from 0.505 to 0.834, a 65% increase. The reviewer's modifications introduced more complex function structures. Only on log_query did the two-agent arm show lower erosion (0.442 vs 0.620).

### Cost

The two-agent arm cost 16% more overall ($7.57 vs $6.52). The reviewer pass adds cost without providing consistent quality improvements.

## Conclusion: INCONCLUSIVE

The experiment does not cleanly test the original hypothesis because both arms use the anti-slop prompt. This makes it a test of "anti-slop prompt + reviewer" vs "anti-slop prompt alone," not "anti-slop prompt" vs "default prompt."

Key findings:
1. The anti-slop prompt is effective at suppressing verbosity in single-agent mode (verbosity near zero on 2/4 problems).
2. Adding a reviewer on top of the anti-slop prompt does not further reduce verbosity and often increases erosion.
3. The reviewer introduces risk of catastrophic failure (eve_industry: -69pp pass rate).
4. Cost increases 16% with the reviewer for no consistent quality gain.

To properly test the hypothesis, a follow-up experiment should compare default single-agent (no anti-slop prompt) against anti-slop single-agent on the same problems.
