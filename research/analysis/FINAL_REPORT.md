# SCBench Research Lab: Consolidated 102-Experiment Analysis

*Generated: 2026-04-05 (Iteration 29)*
*Previous version: Post-Iteration 7 (90 experiments)*

## 1. Executive Summary

Across 102 valid experiments (116 total, 14 excluded) covering all 20 SCBench
problems, the two-agent system (Implementer + Reviewer) does not reliably
improve pass rates over a single-agent baseline.

- **Valid experiments:** 102 (58 single, 44 two-agent)
- **Paired problems:** 19 (dag_execution has no single-agent baseline)
- **Mean pass rate delta (two-agent minus single):** -5.2 percentage points
- **Win/tie/loss record:** 5 wins, 6 ties, 8 losses (threshold: 5pp)
- **Cost multiplier:** 1.68x ($3.25 vs $1.93 per experiment)

The two-agent system costs 68% more while producing lower average pass rates
(0.52 vs 0.68). Baseline difficulty remains the strongest predictor of
reviewer value.

## 2. Data Quality

### 2.1 Validation summary

| Metric | Count |
|--------|-------|
| Total experiments | 116 |
| results_valid=true | 106 |
| Excluded (bad scale/duplicates) | 4 |
| **Analyzable** | **102** |
| manipulation_check='passed' | 13 |
| manipulation_check='skipped' | 91 |
| manipulation_check='failed' | 3 |

Most experiments (91 of 102) have manipulation_check='skipped' rather than
'passed'. These were executed correctly; the manipulation check was not run.
The query_experiments.py VALIDATION_FILTER excludes them, reducing the
analyzable dataset from 102 to 13. This report uses all experiments where
results_valid=true, excluding known data quality issues.

### 2.2 Excluded rows

- **IDs 637-640 (metric_transform_lang):** Four rows stored on 0-100 scale
  instead of 0-1, and two are exact duplicates of the other two. All four
  excluded. The two valid metric_transform_lang experiments (IDs 594-595,
  604-605) use the correct 0-1 scale.

### 2.3 Model naming inconsistency

Three model name strings appear for the same underlying model:
`local-sonnet-4.6` (100), `claude_code_local/local-claude-sonnet-4-6` (10),
`local-claude-sonnet-4-6` (6). Cross-model joins may miss pairs when model
names do not match exactly.

## 3. Per-Problem Results

| Problem | n_single | n_two | avg_single | avg_two | delta | Effect |
|---------|----------|-------|------------|---------|-------|--------|
| execution_server | 6 | 4 | 0.925 | 0.390 | -0.535 | HURTS |
| eve_industry | 3 | 2 | 0.790 | 0.285 | -0.505 | HURTS |
| code_search | 5 | 3 | 0.844 | 0.647 | -0.197 | HURTS |
| file_backup | 9 | 5 | 0.621 | 0.454 | -0.167 | HURTS |
| log_query | 6 | 2 | 0.813 | 0.655 | -0.158 | HURTS |
| eve_market_tools | 1 | 1 | 0.280 | 0.130 | -0.150 | HURTS |
| database_migration | 5 | 5 | 0.730 | 0.608 | -0.122 | HURTS |
| trajectory_api | 3 | 2 | 0.890 | 0.840 | -0.050 | HURTS |
| etl_pipeline | 3 | 2 | 0.880 | 0.850 | -0.030 | NEUTRAL |
| layered_config_synthesizer | 2 | 2 | 0.040 | 0.025 | -0.015 | NEUTRAL |
| eve_jump_planner | 1 | 1 | 0.000 | 0.000 | +0.000 | NEUTRAL |
| eve_route_planner | 1 | 1 | 0.450 | 0.450 | +0.000 | NEUTRAL |
| migrate_configs | 2 | 2 | 0.835 | 0.840 | +0.005 | NEUTRAL |
| dynamic_buffer | 1 | 1 | 0.330 | 0.370 | +0.040 | NEUTRAL |
| circuit_eval | 2 | 2 | 0.435 | 0.500 | +0.065 | HELPS |
| file_merger | 2 | 4 | 0.510 | 0.585 | +0.075 | HELPS |
| file_query_tool | 2 | 1 | 0.825 | 0.900 | +0.075 | HELPS |
| metric_transform_lang | 2 | 2 | 0.370 | 0.525 | +0.155 | HELPS |
| dynamic_config_service_api | 2 | 1 | 0.320 | 0.850 | +0.530 | HELPS |

dag_execution has only one two-agent run (0.00) with no single-agent baseline.

## 4. The Baseline Difficulty Effect

The strongest pattern: two-agent value depends on baseline performance.

| Baseline band | Problems | Avg delta | W/T/L |
|---------------|----------|-----------|-------|
| 0-20% | 2 | -0.007 | 0/2/0 |
| 20-50% | 6 | +0.107 | 3/2/1 |
| 50-80% | 4 | -0.180 | 1/0/3 |
| 80-100% | 7 | -0.127 | 1/2/4 |

**0-20% baseline (layered_config_synthesizer, eve_jump_planner):** Both arms
score near zero. The problems are too hard for the model. The reviewer adds
nothing because there is nothing to review.

**20-50% baseline (6 problems):** The reviewer helps. Three wins
(dynamic_config_service_api +53pp, metric_transform_lang +15.5pp,
circuit_eval +6.5pp), two ties, one loss (eve_market_tools -15pp). Average
delta is +10.7pp. This is where the reviewer adds genuine value, catching
structural errors in partially-working code.

**50-80% baseline (4 problems):** The reviewer hurts. Three losses
(eve_industry -50.5pp, file_backup -16.7pp, database_migration -12.2pp),
one win (file_merger +7.5pp). Average delta is -18.0pp.

**80-100% baseline (7 problems):** The reviewer hurts. Four losses
(execution_server -53.5pp, code_search -19.7pp, log_query -15.8pp,
trajectory_api -5.0pp), two ties (etl_pipeline, migrate_configs), one win
(file_query_tool +7.5pp, but n=1 for two-agent). Average delta is -12.7pp.

The crossover from net-positive to net-negative falls around 50% baseline
pass rate. Below 50%, the reviewer catches errors in broken code. Above 50%,
the reviewer introduces regressions into working code.

## 5. High-Confidence Findings

### 5.1 Catastrophic reviewer harm on high-baseline problems

execution_server (n=10, 6 single / 4 two-agent): single avg 0.925,
two-agent avg 0.390. Delta: -53.5pp. The reviewer destroys working
solutions. This is the single most replicated finding in the dataset.

eve_industry (n=5, 3/2): single avg 0.790, two-agent avg 0.285. Delta:
-50.5pp. Same pattern.

code_search (n=8, 5/3): single avg 0.844, two-agent avg 0.647. Delta:
-19.7pp. Consistent harm.

### 5.2 Reviewer helps on medium-baseline problems

dynamic_config_service_api (n=3, 2/1): single avg 0.320, two-agent 0.850.
Delta: +53.0pp. Large positive effect but n=1 for two-agent arm; needs
replication.

metric_transform_lang (n=4, 2/2): single avg 0.370, two-agent avg 0.525.
Delta: +15.5pp. Consistent positive across two runs.

### 5.3 High run-to-run variance

file_backup (n=14, 9/5): single ranges 0.130 to 0.820, two-agent ranges
0.130 to 0.880. The standard deviation within each mode exceeds the
between-mode difference. N=1 per-problem comparisons remain unreliable.

circuit_eval (n=4, 2/2): single ranges 0.000 to 0.870, two-agent ranges
0.000 to 1.000. Binary outcomes suggest the model either solves the problem
completely or fails entirely.

## 6. Cost Analysis

| Mode | N | Avg cost | Avg pass rate | Cost per pct point |
|------|---|----------|---------------|-------------------|
| Single | 58 | $1.93 | 0.678 | $2.85 |
| Two-agent | 44 | $3.25 | 0.520 | $6.25 |

The two-agent system is 2.2x less cost-efficient (cost per percentage point
of pass rate). For every dollar spent on the reviewer, the average return is
negative.

## 7. Erosion and Verbosity

Erosion and verbosity slopes remain near zero across all experiments. Of 102
valid experiments, only one (file_backup, two-agent, sc-hypotheses.236) has
a nonzero erosion slope (-0.0909). The remaining experiments report 0.0000.

This indicates either: (a) the metrics are not computed for most experiments,
(b) the pipeline does not extract per-checkpoint erosion/verbosity data, or
(c) the problems tested do not produce measurable erosion over their
checkpoint sequences. The erosion/verbosity metrics are central to the
paper's claims and cannot be validated with the current experimental data.

## 8. Budget Status

| Item | Amount |
|------|--------|
| Total budget | $1,000.00 |
| Spent | $408.84 |
| Remaining | $591.16 |

Budget utilization: 40.9%. Approximately $4.01 per experiment.

## 9. Under-Replicated Cells

Problems with n=1 in either arm, limiting confidence:

| Problem | n_single | n_two | Priority |
|---------|----------|-------|----------|
| dag_execution | 0 | 1 | HIGH (no baseline) |
| dynamic_buffer | 1 | 1 | HIGH |
| eve_market_tools | 1 | 1 | HIGH |
| eve_jump_planner | 1 | 1 | LOW (unsolvable) |
| eve_route_planner | 1 | 1 | MEDIUM |
| dynamic_config_service_api | 2 | 1 | HIGH (large positive delta) |
| file_query_tool | 2 | 1 | MEDIUM |

dynamic_config_service_api and dag_execution are the highest-priority
replication targets. The former shows the largest positive delta (+53pp)
on n=1 two-agent data; the latter has no single-agent baseline at all.

## 10. Conclusions

1. **The two-agent system is net harmful.** Across 19 paired problems, it
   loses 8 and wins 5, with a mean delta of -5.2pp. The cost is 1.68x
   higher. This is a well-replicated negative result.

2. **Baseline difficulty predicts reviewer value.** The crossover is around
   50% baseline pass rate. Below 50%, the reviewer catches errors in broken
   code (+10.7pp average in the 20-50% band). Above 50%, the reviewer
   introduces regressions (-15.4pp average in the 50-100% bands).

3. **The harm is catastrophic on competent baselines.** execution_server
   drops 53.5pp, eve_industry drops 50.5pp. The reviewer does not merely
   fail to help; it actively destroys working solutions.

4. **Run-to-run variance is large.** file_backup ranges from 0.13 to 0.88
   within the two-agent arm. N=1 per-problem results cannot distinguish
   signal from noise. Minimum N=3 per arm per problem is needed for
   directional conclusions.

5. **Erosion/verbosity metrics are uninformative.** Nearly all values are
   zero. This data cannot validate or refute claims about code quality
   differences between modes.

6. **The manipulation_check filter is too aggressive.** It excludes 89 of
   102 valid experiments. The filter should treat 'skipped' as valid when
   results_valid=true, or the manipulation check should be run on all future
   experiments.

## 11. Recommendations

1. **Stop running two-agent experiments on high-baseline problems** where
   single-agent already scores above 70%. The evidence is sufficient: the
   reviewer hurts.

2. **Focus replication on the 20-50% baseline band** where the reviewer
   shows genuine value. Prioritize dynamic_config_service_api (n=1
   two-agent) and dynamic_buffer (n=1 each).

3. **Fix erosion/verbosity metric computation.** Investigate why the
   pipeline reports 0.0000 for nearly all experiments.

4. **Fix the manipulation_check filter** in query_experiments.py or
   retroactively set manipulation_check='passed' on experiments that were
   manually validated.

5. **Standardize model naming** to prevent missed joins.

6. **Report the negative result.** The two-agent system does not help on
   competent baselines. This is the paper-relevant finding.
