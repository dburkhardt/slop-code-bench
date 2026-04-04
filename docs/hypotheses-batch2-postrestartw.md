# Batch 2: Post-Restart Hypotheses

Generated 2026-04-04 from 13 valid experiments across 5 problems.

## Context

Key findings from prior experiments:
- Two-agent (70/30) shows dramatic wins on circuit_eval and file_backup but costs 5-19x more
- 90/10 budget split reversed gains on file_backup
- Single-agent wins decisively on high-baseline problems (eve_industry, execution_server)
- Budget starvation is the dominant confound across all experiments

## Hypotheses Filed

| Bead | Title | Priority | Source |
|------|-------|----------|--------|
| sc-hypotheses.276 | Re-solving vs revision decomposition | HIGH | arxiv:2604.01029 |
| sc-hypotheses.277 | Difficulty-dependent strategy selection | MEDIUM | test-time compute scaling |
| sc-hypotheses.278 | Explicit constraint reviewer | MEDIUM | arxiv:2603.08520 |
| sc-hypotheses.279 | Budget-equalized comparison | HIGHEST | cost confound in all experiments |
| sc-hypotheses.280 | Multi-file problem interaction | LOW | arxiv:2512.18470 |
| sc-hypotheses.281 | Prompt-only anti-slop | HIGH | arxiv:2604.01029 |
| sc-hypotheses.282 | Checkpoint-conditional review | MEDIUM | test-time compute research |

## Recommended Experiment Order

1. **H-budget-eq** (sc-hypotheses.279): The cost confound invalidates all current comparisons. Run single-agent with $15 budget to match two-agent actual spend. If single-agent matches two-agent at equal cost, the architecture question is settled.

2. **H-prompt-only** (sc-hypotheses.281): Free intervention. Add anti-slop instructions to the single-agent prompt. If verbosity drops 5-15pp with no pass-rate loss, this becomes the new default baseline.

3. **H-resolving** (sc-hypotheses.276): Run dual-solver (two independent attempts, pick best) vs. implementer-reviewer. If dual-solver matches, the reviewer's value is in providing a second attempt, not in reviewing.

4. **H-conditional** (sc-hypotheses.282): If two-agent is worth keeping, conditional review (review only on test failure) should cut costs 40-60% while preserving gains.

## Papers Cited

1. "Revision or Re-Solving? Decomposing Second-Pass Gains in Multi-LLM Pipelines" (arxiv:2604.01029, April 2026)
2. "SCAFFOLD-CEGIS: Preventing Latent Security Degradation in LLM-Driven Iterative Code Refinement" (arxiv:2603.08520, March 2026)
3. "Thinking Longer, Not Larger: Enhancing Software Engineering Agents via Scaling Test-Time Compute" (arxiv:2503.23803)
4. "SWE-EVO: Benchmarking Coding Agents in Long-Horizon Software Evolution Scenarios" (arxiv:2512.18470)
5. "Scaling LLM Test-Time Compute Optimally" (OpenReview:4FWAwZtd2n)
