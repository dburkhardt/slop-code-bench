# Research Iteration 3: Anti-Slop Replication Analysis

**Date:** 2026-04-05
**Bead:** sc-research-log.13
**Hypothesis:** sc-hypotheses.281 (anti-slop prompt reduces verbosity at zero cost)
**Budget spent this iteration:** $0 (analysis only, no new experiments run)
**Budget remaining:** $626.95

## Orient

### Data Inventory

After batches 7-10 and scattered replication attempts, the Dolt ledger contains
13 valid anti-slop single-agent experiments across 7 problems, plus 16 valid
default-prompt single-agent experiments for comparison. "Valid" means total cost
above $0.50 (excluding timeout/initialization failures that produced no useful
output).

| Problem | N (anti-slop) | N (default) |
|---------|:---:|:---:|
| code_search | 3 | 1 |
| database_migration | 1 | 4 |
| etl_pipeline | 1 | 2 |
| eve_industry | 1 | 2 |
| execution_server | 2 | 2 |
| file_backup | 3 | 3 |
| log_query | 2 | 2 |

Three additional problems have anti-slop data but no default comparison:
dynamic_config_service_api (timeout, $0 cost), file_query_tool (1 checkpoint
only, wrong-scale entry in Dolt), and database_migration (one valid anti-slop
run). Several problems tested in Batch 5 (trajectory_api, eve_market_tools,
eve_route_planner, metric_transform_lang, layered_config_synthesizer,
migrate_configs) have default-prompt data only with no anti-slop runs.

### Prior Claims Under Review

Iteration 5 concluded:
1. "Anti-slop prompt achieves verbosity = 0.0 across ALL checkpoints, ALL
   problems"
2. "Mean pass rate delta: +4.9pp (2/6 strongly positive, 3/6 neutral, 1/6
   negative)"
3. "The anti-slop prompt is more effective than the two-agent reviewer"

These were all based on N=1 per problem. Replication data now exists for 3
problems (code_search, file_backup, execution_server) with N=2-3 each.

## Analysis

### Pass Rate Effect

| Problem | Anti-slop mean | Default mean | Delta | N(AS)/N(Df) |
|---------|:-:|:-:|:-:|:-:|
| eve_industry | 0.910 | 0.730 | +18.0pp | 1/2 |
| file_backup | 0.800 | 0.560 | +24.0pp | 3/3 |
| log_query | 0.810 | 0.735 | +7.5pp | 2/2 |
| database_migration | 0.890 | 0.690 | +20.0pp | 1/4 |
| code_search | 0.843 | 0.840 | +0.3pp | 3/1 |
| execution_server | 0.915 | 0.920 | -0.5pp | 2/2 |
| etl_pipeline | 0.860 | 0.890 | -3.0pp | 1/2 |

**Headline: +9.5pp mean delta, 4/7 positive, 2/7 neutral, 1/7 negative.**

However, this number is misleading. The large positive deltas are inflated by
default-prompt failures that did not occur in anti-slop runs:

- **database_migration**: Default mean is 0.69 because one run (id=499,
  just-solve prompt) scored 0.00. Excluding that outlier, default mean rises to
  0.92, and the delta flips to -3pp.
- **file_backup**: Default mean is 0.56 because one run (id=495, only completed
  checkpoint 1) scored 0.13. Excluding it, default mean = 0.775, delta = +2.5pp.
- **eve_industry**: N=1 anti-slop, N=2 default. The anti-slop run scored 0.91
  where both defaults scored 0.73, but a single run can easily be an outlier
  (checkpoint 2 pass rates vary from 0.45 to 0.82 across runs).

Excluding the three low-quality default runs and treating eve_industry as
inconclusive (N=1), the remaining problems show:

| Problem | Delta | Confidence |
|---------|:---:|:-:|
| file_backup | +2.5pp | Moderate (N=3 vs N=2) |
| log_query | +7.5pp | Low (N=2, variance 0.23 std) |
| code_search | +0.3pp | High (N=3, std=0.006) |
| execution_server | -0.5pp | Moderate (N=2 each) |
| etl_pipeline | -3.0pp | Low (N=1 anti-slop) |

**Revised conclusion: The anti-slop prompt has no reliable effect on pass rate.**
The +9.5pp headline is driven by default-prompt failures and small samples.
On the two problems with the most data (code_search N=3, file_backup N=3), the
effect is 0pp and +2.5pp respectively. Run-to-run variance dominates any prompt
effect. Log_query shows the problem starkly: anti-slop results of 0.65 and 0.97
(range = 0.32) from the same prompt, same model, same problem.

### Verbosity Effect

| Problem | Anti-slop mean verb. | Default mean verb. | Delta |
|---------|:-:|:-:|:-:|
| etl_pipeline | 0.000 | 0.070 | -7.00pp |
| file_backup | 0.006 | 0.022 | -1.61pp |
| log_query | 0.034 | 0.049 | -1.44pp |
| code_search | 0.000 | N/A | N/A |
| eve_industry | 0.009 | 0.000 | +0.87pp |
| execution_server | 0.012 | 0.002 | +0.97pp |
| database_migration | 0.089 | 0.078 | +1.11pp |

**Mean verbosity delta: -1.18pp (reduced on 3/6, increased on 3/6).**

The initial claim of "verbosity = 0.0 across ALL problems" is refuted.
Replication shows:

1. **etl_pipeline** is the one clear success: verbosity dropped from 7% to 0%.
   This is consistent across all 5 checkpoints (all zero). But N=1 for
   anti-slop.

2. **file_backup** shows modest reduction from 2.2% to 0.6%. The first
   anti-slop run had 0.0% but replications showed 0-3.3%. The prompt
   suppresses verbosity somewhat but not perfectly.

3. **log_query** shows modest reduction from 4.9% to 3.4%. Both prompts
   produce similar (low) verbosity.

4. **Three problems show anti-slop INCREASING verbosity**, though by small
   amounts (<1.1pp). This is within noise for N=1-2.

5. **code_search** had zero verbosity under both prompts. The metric detects
   nothing to suppress.

The verbosity effect is real but problem-dependent and modest. It is not the
"universal zero" claimed from N=1 data. The strongest effect (etl_pipeline,
-7pp) needs replication.

### Structural Erosion

Neither prompt consistently affects structural erosion. Anti-slop erosion scores
range from 0.0 to 0.71 across problems, similar to default-prompt ranges. The
anti-slop prompt targets surface-level code style (comments, wrappers, defensive
checks), not architectural complexity.

### Cost

Anti-slop and default prompt costs are comparable within each problem. No cost
overhead from the prompt change, as expected (same model, same single-agent
mode).

## Key Findings

1. **The anti-slop prompt has no reliable effect on pass rate.** The +9.5pp
   headline from raw means is an artifact of default-prompt failures in the
   comparison group. After controlling for outliers, the effect is approximately
   zero (range: -3pp to +2.5pp on well-sampled problems).

2. **The anti-slop prompt reduces verbosity on some problems (etl_pipeline,
   file_backup) but not universally.** The "verbosity = 0.0 everywhere" claim
   from N=1 data does not replicate. Mean reduction is about 1pp.

3. **Run-to-run variance dominates prompt effects.** Log_query ranges from 0.65
   to 0.97 under the same prompt. File_backup defaults range from 0.13 to 0.78.
   With this level of variance, N=1 per-problem comparisons are unreliable.
   Minimum N=5 per condition would be needed to detect a 5pp effect.

4. **Two-agent mode remains conclusively harmful.** No new data changes the
   Iteration 3 conclusion (0/11 positive at 60/40 split). The anti-slop prompt
   does not rescue two-agent mode.

## Recommendations for Next Iteration

1. **Stop running new experiments until the variance problem is addressed.**
   With run-to-run standard deviations of 0.03 to 0.37, adding one more
   experiment per condition adds no statistical power. Either (a) run N=5+
   replications on 2-3 focal problems, or (b) accept that the current data
   cannot distinguish prompt effects from noise and write up what we know.

2. **The paper-relevant finding is the two-agent result, not the prompt
   result.** Across 50+ experiments, two-agent mode at any budget split is
   harmful or neutral on competent baselines. That is a strong, well-replicated
   negative result. The anti-slop prompt story is suggestive but underpowered.

3. **If running more experiments, focus narrowly.** Pick 2 problems
   (etl_pipeline for verbosity, file_backup for pass rate), run N=5 anti-slop
   and N=5 default on each. Total cost: ~$50. This would produce a publishable
   comparison.

4. **Data quality issues to address:**
   - file_query_tool (id=629) has total_pass_rate=75.00 (wrong scale, should be
     0.75)
   - Several runs with NULL verbosity_scores need backfilling from output dirs
   - Dolt experiment rows from early batches (id < 500) have inconsistent
     prompt column names

## Decision

**LOOP to next iteration for focused replication study.**

Priority: Run N=5 anti-slop + N=5 default on etl_pipeline and file_backup.
Estimated cost: ~$50. Remaining budget: $626.95.

Alternative: If the witness/mayor determines the budget should be preserved for
other priorities, the current data supports writing up two-agent negative results
now and treating anti-slop as "suggestive, needs replication" in the discussion.
