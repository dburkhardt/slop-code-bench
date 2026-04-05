# Exp B6.5: file_merger replication run 2

**Hypothesis:** sc-hypotheses.287 (H-replication-positive: Confirm two-agent benefit replicates)
**Problem:** file_merger (4 checkpoints)
**Model:** claude_code_local/local-claude-sonnet-4-6
**Prompt:** configs/prompts/default_implementer.jinja / default_reviewer.jinja
**Mode:** two-agent (60/40 budget split)
**Budget:** $5.00/arm
**Actual cost:** ~$0.40 (two-agent partial), $0.00 (baseline timeout)

## Status: FAILED

Both arms failed to produce usable data.

## Baseline (single-agent)

The Claude Code process timed out on checkpoint_1 after ~745s. No solution was
produced (snapshot empty, cost $0.00). The agent appears to have hung during
initialization or early execution. Only error-category tests passed (7/46),
which are tests that validate error handling on an empty/missing solution.

## Two-agent

The two-agent subprocess timed out at the 3600s limit. Partial results:

| Phase | Checkpoint | State | Strict Pass | Core Pass | Cost ($) | Duration (s) |
|-------|-----------|-------|-------------|-----------|----------|--------------|
| First implementer | 1 | error | 15.2% | 0.0% | 0.00 | 745 |
| Reviewer | 1 | ran | 15.2% | 0.0% | 0.08 | 10 |
| Reviewer | 2 | ran | 15.1% | 0.0% | 0.05 | 12 |
| Reviewer | 3 | error | 16.3% | 0.0% | 0.27 | 748 |
| Second implementer | 1 | error | 15.2% | 0.0% | 0.00 | 985 |

The first-pass implementer timed out producing an empty solution. The reviewer
then ran on this empty solution (no code to review), explaining the 0% core
pass rate. The second-pass implementer also timed out.

All "passing" tests (15%) are error-category tests that pass on empty solutions.

## Dolt

No rows inserted. The baseline insertion failed with a lost Dolt connection
(error 2013). The two-agent arm was skipped due to no metrics.

## Diagnosis

The Claude Code local agent appears unable to complete file_merger checkpoint_1
within the default timeout. This problem may require a longer timeout or
investigation of the local agent configuration. The agent cost reporting shows
$0.00 for timed-out runs, suggesting the local agent wrapper does not track
partial costs.

## Output directories

- Baseline: `outputs/baseline_claude_code_local/local-claude-sonnet-4-6_file_merger_20260405_041752/`
- Two-agent: `outputs/two_agent_local-claude-sonnet-4-6_file_merger_20260405_043035_97caec531452/`
