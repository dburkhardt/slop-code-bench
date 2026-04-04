# Experiment Report: sc-hypotheses.281 (execution_server)

## Hypothesis

Single-agent anti-slop prompt reduces verbosity at zero cost overhead compared to
two-agent (anti-slop implementer + default reviewer) on execution_server.

**Testable claim**: A single-agent with anti-slop prompt instructions achieves
verbosity ratio 5-15pp lower than default single-agent, with pass rate within 3pp,
at identical cost.

## Setup

- **Problem**: execution_server (6 checkpoints)
- **Model**: local-claude-sonnet-4-6 (Claude Code 2.0.51)
- **Budget**: $5/arm, split 60/40 (implementer/reviewer) for two-agent
- **Baseline prompt**: anti_slop
- **Two-agent prompts**: anti_slop (implementer) + default_reviewer (reviewer)

## Results

### Per-Checkpoint Pass Rates

| Checkpoint | Baseline (single) | Two-Agent | Delta |
|:----------:|:-----------------:|:---------:|:-----:|
| 1          | 0.9556            | 0.9556    | 0.0000 |
| 2          | 0.9655            | 0.9655    | 0.0000 |
| 3          | 0.9612            | 0.9126    | -0.0486 |
| 4          | 0.9735            | 0.9404    | -0.0331 |
| 5          | 0.9786            | 0.9465    | -0.0321 |
| 6          | 0.5571            | 0.2857    | -0.2714 |

### Per-Checkpoint Erosion

| Checkpoint | Baseline | Two-Agent | Delta |
|:----------:|:--------:|:---------:|:-----:|
| 1          | 0.6785   | 0.6155    | -0.0631 |
| 2          | 0.6547   | 0.5938    | -0.0610 |
| 3          | 0.4926   | 0.5471    | +0.0546 |
| 4          | 0.7064   | 0.6645    | -0.0419 |
| 5          | 0.6802   | 0.6904    | +0.0102 |
| 6          | 0.6176   | 0.5889    | -0.0287 |

### Per-Checkpoint Verbosity

| Checkpoint | Baseline | Two-Agent | Delta |
|:----------:|:--------:|:---------:|:-----:|
| 1          | 0.0000   | 0.0000    | 0.0000 |
| 2          | 0.0000   | 0.0000    | 0.0000 |
| 3          | 0.0000   | 0.0000    | 0.0000 |
| 4          | 0.0000   | 0.0278    | +0.0278 |
| 5          | 0.0000   | 0.0358    | +0.0358 |
| 6          | 0.0127   | 0.0217    | +0.0090 |

### Aggregates

| Metric           | Baseline (single) | Two-Agent | Delta   |
|:----------------:|:-----------------:|:---------:|:-------:|
| Avg pass rate    | 0.8986            | 0.8344    | -0.0642 |
| Avg erosion      | 0.6383            | 0.6167    | -0.0216 |
| Avg verbosity    | 0.0021            | 0.0142    | +0.0121 |
| Total cost       | $2.93             | $2.43     | -$0.50  |
| LOC (final)      | 942               | 828       | -114    |

## Analysis

1. **Pass rate**: The single-agent baseline outperformed the two-agent arm by 6.4pp
   on average. Both arms collapsed at checkpoint 6 (pass rates of 55.7% and 28.6%),
   but the baseline maintained higher pass rates across all checkpoints from cp3 onward.
   The two-agent arm performed worse, not better.

2. **Verbosity**: The anti-slop prompt effectively suppressed verbosity in both arms.
   The baseline achieved near-zero verbosity (0.21% avg), while the two-agent arm
   showed slightly higher verbosity (1.42% avg). The reviewer did not reduce
   verbosity; it introduced it.

3. **Erosion**: Both arms show comparable structural erosion (0.638 vs 0.617). The
   two-agent arm has marginally lower erosion on average, but the difference is small
   and not consistent across checkpoints.

4. **Cost**: The baseline cost $2.93 and the two-agent arm cost $2.43. The two-agent
   arm was cheaper, but this is because the reviewer budget was unused for most
   checkpoints (the 60/40 split means the implementer only gets 60% of budget).

5. **LOC**: The two-agent arm produced 114 fewer lines of code (828 vs 942), but this
   did not translate to better pass rates.

## Conclusion: INCONCLUSIVE

The anti-slop prompt effectively suppresses verbosity in both configurations. The
single-agent baseline actually outperforms the two-agent arm on pass rate, suggesting
the reviewer adds negative value on this problem. However, this experiment compares
anti-slop single-agent vs anti-slop+reviewer two-agent. To properly test sc-hypotheses.281,
we need a comparison against the default (non-anti-slop) single-agent prompt to measure
the anti-slop prompt's standalone effect on verbosity.

The hypothesis that "prompt-only changes can achieve similar verbosity reduction" cannot
be confirmed or refuted without a default-prompt baseline comparison.
