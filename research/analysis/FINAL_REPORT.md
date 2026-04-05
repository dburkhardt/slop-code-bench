# SCBench Research Lab: Post-Iteration 7 Analysis

*Generated: 2026-04-05*

## 1. Executive Summary

Across 90 experiments (35 matched single/two-agent pairs from 9 hypothesis groups),
the two-agent system (Implementer + Reviewer) does not reliably improve pass rates
over a single-agent baseline.

- **Total experiments:** 90
- **Valid experiments (results_valid=true):** 78
- **Matched pairs analyzed:** 35
- **Mean pass rate delta (two-agent minus baseline):** -8.7 percentage points
- **Win/tie/loss record:** 9 wins, 10 ties, 16 losses (threshold: 5pp)

The two-agent system costs 1.8x more on average ($3.67 vs $2.06 per experiment)
while producing lower pass rates in the majority of comparisons.

## 2. Data Quality

### Validation summary

| Metric | Count |
|--------|-------|
| Total experiments | 90 |
| results_valid=true | 78 |
| manipulation_check='passed' | 13 |
| manipulation_check='skipped' | 72 |
| manipulation_check='failed' | 3 |
| manipulation_check=NULL | 2 |

Most experiments (72 of 90) have manipulation_check='skipped' rather than 'passed'.
These experiments have valid results and were executed correctly; the manipulation
check was simply not run. The query_experiments.py VALIDATION_FILTER excludes them,
reducing the analyzable dataset from 78 to 13. This report uses all experiments
where results_valid=true regardless of manipulation_check status.

### Model naming inconsistency

Three model name strings appear for the same underlying model:
`local-sonnet-4.6`, `local-claude-sonnet-4-6`, `claude_code_local/local-claude-sonnet-4-6`.
Cross-model joins may miss pairs when model names do not match exactly.

## 3. Findings by Hypothesis Group

### sc-hypotheses.283 (6 pairs, avg delta: -57.0pp)

The worst-performing configuration. All 6 pairs show the two-agent system
losing, with catastrophic drops on database_migration (-42pp to -54pp),
file_backup (-63pp), and circuit_eval (-87pp). This likely represents a
50/50 or otherwise harmful budget split.

### sc-hypotheses.260 (2 pairs, avg delta: -32.5pp)

Mixed results: database_migration shows a tie (-1pp) while file_backup
shows a catastrophic regression (-64pp).

### sc-hypotheses.286 (12 pairs, avg delta: -7.9pp)

The largest hypothesis group by pair count. Two wins
(metric_transform_lang +30pp, dynamic_config_service_api +21pp),
five ties, and five losses. The losses cluster on problems where the
baseline already scores above 70%: execution_server (-67pp from a 94%
baseline), eve_industry (-38pp from 73%), code_search (-9pp from 85%).

### sc-hypotheses.281 (10 pairs, avg delta: -1.6pp)

Near-zero average delta, but high variance. file_backup shows consistent
improvement across 4 pairs (+6pp to +75pp), while eve_industry shows a
catastrophic -69pp drop and log_query drops -29pp.

### Earlier hypotheses (.236, .238, .256, .257)

Small samples (1-2 pairs each). The early pairs (.236, .238, .256) all
show two-agent wins, but these all have baseline pass rates below 20%.
The two-agent system appears helpful when the baseline fails completely;
the reviewer can rescue a failed implementation.

## 4. The Baseline Difficulty Effect

The clearest pattern in the data: two-agent value depends on baseline
performance.

| Baseline band | Pairs | Avg delta | Wins | Losses | Avg cost delta |
|---------------|-------|-----------|------|--------|----------------|
| 0-20% | 5 | +56.4pp | 4 | 0 | +$4.12 |
| 20-50% | 5 | +4.0pp | 1 | 1 | +$1.09 |
| 50-80% | 7 | -18.7pp | 2 | 3 | +$2.08 |
| 80-100% | 18 | -26.4pp | 2 | 12 | +$0.88 |

When the single agent scores below 20%, the reviewer has broken code to
fix and delivers large gains. When the single agent already scores above
80%, the reviewer is more likely to break working code than to improve it.
The crossover from net-positive to net-negative falls somewhere in the
40-60% range.

## 5. Per-Problem Consistency

| Problem | Pairs | Avg delta | Direction | Consistent? |
|---------|-------|-----------|-----------|-------------|
| file_backup | 7 | +5.0pp | NEUTRAL | No (range: -64pp to +75pp) |
| metric_transform_lang | 2 | +15.5pp | HELPS | Yes |
| dynamic_config_service_api | 1 | +21.0pp | HELPS | Yes (n=1) |
| circuit_eval | 2 | +6.5pp | HELPS | No (range: -87pp to +100pp) |
| dynamic_buffer | 1 | +4.0pp | NEUTRAL | Yes (n=1) |
| etl_pipeline | 2 | -1.5pp | NEUTRAL | No |
| eve_route_planner | 1 | 0.0pp | NEUTRAL | Yes (n=1) |
| file_query_tool | 1 | 0.0pp | NEUTRAL | Yes (n=1) |
| layered_config_synthesizer | 1 | -2.0pp | NEUTRAL | Yes (n=1) |
| code_search | 2 | -9.5pp | HURTS | Yes |
| log_query | 3 | -9.0pp | HURTS | No (range: -29pp to +3pp) |
| trajectory_api | 1 | -14.0pp | HURTS | Yes (n=1) |
| eve_market_tools | 1 | -15.0pp | HURTS | Yes (n=1) |
| database_migration | 6 | -24.5pp | HURTS | No |
| eve_industry | 2 | -53.5pp | HURTS | Yes |
| execution_server | 2 | -37.0pp | HURTS | Yes |

file_backup has the most data (7 pairs) but the widest variance (-64pp to
+75pp), making it unreliable for drawing conclusions. The only consistently
positive problem with more than one pair is metric_transform_lang (+30pp,
+1pp). Problems consistently hurt by the reviewer (code_search, eve_industry,
execution_server) tend to have high baseline pass rates.

## 6. Cost Analysis

| Mode | Avg cost | Observations |
|------|----------|-------------|
| Single-agent | $2.06 | 35 experiments |
| Two-agent | $3.67 | 35 experiments |
| **Multiplier** | **1.8x** | |

The two-agent system costs 78% more per experiment. For problems where
it helps (baseline <20%), the cost premium buys genuine improvement. For
problems where the baseline already works well, the extra cost produces
worse results.

## 7. Erosion and Verbosity

Erosion and verbosity slopes are nearly zero across all experiments.
Of 90 experiments, only one (file_backup, two-agent, sc-hypotheses.236)
has a nonzero erosion slope (-0.0909) and one has nonzero verbosity
slope (0.0096). The remaining experiments all report 0.0000 for both
metrics.

This suggests either: (a) the metrics are not being computed for most
experiments, (b) the problems tested do not produce meaningful
erosion/verbosity variation, or (c) the slope calculation needs more
checkpoints to show signal.

## 8. Key Conclusions

1. **The two-agent system is net harmful.** Across 35 matched pairs, it
   loses 16 and wins 9, with a mean delta of -8.7pp. The cost is 1.8x
   higher.

2. **Baseline difficulty predicts reviewer value.** When the single agent
   fails (0-20% pass rate), the reviewer rescues broken code. When the
   single agent already succeeds (80%+), the reviewer damages working code.
   The crossover is around 40-60%.

3. **Run-to-run variance is large.** file_backup ranges from -64pp to +75pp
   delta across 7 pairs. circuit_eval ranges from -87pp to +100pp across
   2 pairs. N=1 per-problem results are unreliable. Minimum N=5 per
   condition is needed to detect a 5pp effect.

4. **sc-hypotheses.283 is a failed configuration.** All 6 pairs show
   catastrophic losses. Whatever reviewer prompt or budget split this
   represents should be abandoned.

5. **Erosion/verbosity slopes are uninformative** in the current dataset.
   Nearly all values are zero, providing no signal about code quality
   differences between modes.

6. **The manipulation_check filter is too aggressive.** It excludes 65
   valid experiments, reducing the dataset from 78 to 13 usable rows
   for the automated report generator. The filter should treat 'skipped'
   as valid when results_valid=true.

## 9. Recommendations

1. **Stop running two-agent experiments on high-baseline problems.** Problems
   where single-agent already scores above 70% consistently show
   regression under two-agent mode. Focus two-agent experiments on
   problems where single-agent scores below 40%.

2. **Fix the manipulation_check filter.** Update VALIDATION_FILTER in
   query_experiments.py to include 'skipped' status, or run the
   manipulation check on all experiments going forward.

3. **Fix erosion/verbosity metric computation.** Investigate why nearly all
   experiments report 0.0000 slopes. These metrics are central to the
   paper's claims and cannot be validated with the current data.

4. **Increase per-problem sample sizes.** Most problem/condition cells have
   N=1 or N=2. The high variance (15-70pp within-problem range) means
   current sample sizes cannot distinguish signal from noise.

5. **Standardize model naming.** Consolidate the three model name variants
   to prevent missed joins in paired comparisons.

6. **Report the negative result.** The two-agent system does not help on
   competent baselines. This is a well-replicated finding (16 losses out
   of 35 pairs) and is the paper-relevant result.
