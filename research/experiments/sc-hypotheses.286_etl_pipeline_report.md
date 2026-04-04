# Experiment Report: etl_pipeline Two-Agent at 60/40

**Hypothesis ID:** sc-hypotheses.286  
**Bead ID:** sc-hypotheses.286.8  
**Problem:** etl_pipeline (5 checkpoints)  
**Model:** claude_code_local/local-claude-sonnet-4-6  
**Budget:** $5/arm  
**Budget split:** 60/40 (implementer/reviewer)  
**Date:** 2026-04-04  

## Summary

The two-agent arm (60/40 split) showed minimal pass rate improvement (+0.4 pp) over the single-agent baseline while reducing total cost by 14%. Structural erosion was consistently lower in the two-agent arm, but verbosity was higher. Core pass rates were identical across both arms.

## Results

### Per-Checkpoint Comparison

| CP | BL Pass | TA Pass | BL Cost | TA Cost | BL Erosion | TA Erosion | BL Verb | TA Verb | BL LOC | TA LOC |
|----|---------|---------|---------|---------|------------|------------|---------|---------|--------|--------|
| 1  | 0.854   | 0.854   | $0.36   | $0.32   | 0.536      | 0.604      | 0.000   | 0.053   | 235    | 266    |
| 2  | 0.904   | 0.904   | $0.86   | $0.82   | 0.622      | 0.360      | 0.099   | 0.156   | 705    | 582    |
| 3  | 0.923   | 0.932   | $0.54   | $0.39   | 0.698      | 0.523      | 0.093   | 0.136   | 835    | 699    |
| 4  | 0.821   | 0.828   | $0.98   | $0.87   | 0.680      | 0.547      | 0.085   | 0.119   | 960    | 801    |
| 5  | 0.841   | 0.848   | $0.78   | $0.61   | 0.706      | 0.596      | 0.072   | 0.108   | 1137   | 947    |

### Aggregates

| Metric | Baseline | Two-Agent | Delta |
|--------|----------|-----------|-------|
| Avg pass rate | 0.869 | 0.873 | +0.004 |
| Total cost | $3.51 | $3.02 | -$0.49 (14% reduction) |
| Erosion slope | 0.0399 | 0.0172 | -0.0227 |
| Verbosity slope | ... | ... | ... |
| Final LOC (CP5) | 1137 | 947 | -190 (17% reduction) |

### Core Pass Rates

Both arms had identical core pass rates: 1.0 on CP1, CP2, CP4, CP5, and 0.75 on CP3 (3/4 core tests passed). The CP3 core failure was the same test in both arms.

### Step Utilization

| CP | BL Steps | TA Steps |
|----|----------|----------|
| 1  | 8 (8%)   | 10 (10%) |
| 2  | 17 (17%) | 16 (16%) |
| 3  | 16 (16%) | 18 (18%) |
| 4  | 20 (20%) | 24 (24%) |
| 5  | 24 (24%) | 14 (14%) |

## Observations

1. **Pass rates nearly identical.** The two-agent arm matched or slightly exceeded the baseline at every checkpoint. The +0.4 pp average improvement is within noise for a single run.

2. **Lower erosion in two-agent arm.** The two-agent erosion slope (0.017) was less than half the baseline slope (0.040). The two-agent arm maintained lower high_cc_pct across CP2-CP5, suggesting the reviewer pass helped contain structural complexity growth.

3. **Higher verbosity in two-agent arm.** The two-agent arm had higher verbosity at every checkpoint. The reviewer pass may introduce additional comments or defensive patterns while reducing structural complexity.

4. **Smaller codebase.** The two-agent arm produced 17% less code at the final checkpoint (947 vs 1137 LOC), consistent with the lower erosion scores. The reviewer pass appears to consolidate code rather than expand it.

5. **Lower cost.** The two-agent arm cost $3.02 vs $3.51 for baseline (14% reduction). This is consistent with the 60/40 split constraining the implementer budget, and the reviewer pass being efficient (fewer steps needed).

## Classification

**Result: INCONCLUSIVE (small positive signal)**

Pass rate improvement is negligible (+0.4 pp). Erosion reduction is the main signal, but a single run cannot establish statistical confidence. The cost reduction is a positive secondary finding.

## Output Directories

- Baseline: `outputs/baseline_claude_code_local/local-claude-sonnet-4-6_etl_pipeline_20260404_152058/`
- Two-agent (implementer): `outputs/local-claude-sonnet-4-6/claude_code-2.0.51_default_implementer_none_20260404T1556/`
- Two-agent (reviewer): `outputs/local-claude-sonnet-4-6/claude_code-2.0.51_default_reviewer_none_20260404T1623/`
- Two-agent (final): `outputs/two_agent_local-claude-sonnet-4-6_etl_pipeline_20260404_155619_e4ff07f365ad/`

## Dolt Records

- Baseline: experiments.id = 587
- Two-agent: experiments.id = 588
