# Lessons Learned: SCBench Autonomous Research (April 2026)

Three systems were used to run experiments on this machine over ~5 days:

1. **optimization_log** (manual iteration, ~$160 spent) — a human-in-the-loop
   loop where a single Claude Code session ran experiments one at a time and
   logged results to a markdown file.

2. **scbench-mission** (simple Python loop, ~$215 spent, 43 experiments) — a
   single autonomous Claude Code session that ran `experiment_pipeline.py` in
   a loop, tracked budget in a JSON file, wrote iteration analysis reports.

3. **Gas Town rig** (multi-agent orchestration, ~$382 spent, 90 experiments) —
   a full Gas Town deployment with Mayor, Deacon, Witness, Staff Scientist,
   Idea Factory, Red Team, Review Board, polecats, formulas, beads, convoys,
   hooks, cron jobs, and a Dolt database.

---

## Research Findings

All three systems investigated the same question: can a two-agent
(implementer + reviewer) system beat a single agent on SlopCodeBench?

The answer, across 130+ experiments, is **no, not reliably**. Specific findings:

1. **60/40 budget split is the least harmful.** +2.5pp mean delta pass rate with
   zero regressions (n=6), but 2.5pp is within run-to-run variance (5-15pp).

2. **50/50 is catastrophic.** -16.3pp mean delta. The reviewer eats half the
   budget and produces worse code than no review at all.

3. **The sweet spot for reviewer value is narrow.** 5-6 checkpoints, baseline
   pass rate 70-90%. Below 70%, the single agent can't solve the problem and
   the reviewer has nothing useful to review. Above 90%, there's no room to
   improve.

4. **Anti-slop prompts have no reliable effect on pass rate.** The +9.5pp
   headline from raw means is an artifact of default-prompt failures in the
   comparison group. After controlling for outliers, the effect is ~0pp.

5. **Anti-slop prompts reduce verbosity modestly on some problems** (etl_pipeline
   -7pp, file_backup -1.6pp) but not universally. The "verbosity = 0.0
   everywhere" claim from N=1 data does not replicate.

6. **Run-to-run variance dominates everything.** log_query ranges from 0.65 to
   0.97 pass rate under the same prompt, same model, same problem. N=1
   per-problem comparisons are unreliable. Minimum N=5 per condition needed to
   detect a 5pp effect.

7. **The paper-relevant finding is the two-agent negative result.** Across 50+
   experiments, two-agent mode at any budget split is harmful or neutral on
   competent baselines. That is a strong, well-replicated negative result.

---

## System Lessons

### What scbench-mission got right

The simple system produced every actionable finding. It worked because:

- **Single context, single loop.** One Claude session ran experiments, analyzed
  results, decided what to do next. No message passing, no coordination.

- **Budget tracked in a JSON file.** Simple, atomic, no database needed.

- **Parallel via `&` + `wait`.** 6-8 experiments ran concurrently with no
  orchestration framework.

- **Analysis happened inline.** The same session that ran experiments also
  analyzed them. No separate "analyst" role needed.

### What Gas Town added (and didn't)

Gas Town added 47 more experiments at the cost of:

- 14 formula files, 6 hook configs, 3 cron jobs, 5 infrastructure agents
- 600+ lines of issue documentation (RIG_ISSUES.md)
- Days of manual intervention to fix orchestration failures
- $382 in API costs (vs $215 for the same findings from scbench-mission)

The 47 additional experiments mostly confirmed what was already known. No new
findings emerged that weren't present in the first 43 experiments.

### The LLM compliance problem

The single most important lesson: **LLM agents do not reliably follow
multi-step orchestration instructions.** Every "Category F" failure in
RIG_ISSUES.md traces to this:

- **F1**: Staff scientist called `experiment_pipeline.py` directly instead of
  using Gas Town dispatch. The agent rationally chose the simpler path.

- **F6**: Agent used `gt sling` in a for-loop (one call per bead) instead of a
  single batch call. The instruction distinction was subtle.

- **F7**: Witness ran 13 patrol cycles without ever reading `state.json`, despite
  explicit instructions to check it on every patrol.

- **F8**: Mayor recognized it had reached the handoff threshold but did not
  execute `gt handoff`.

- **O6**: Research iteration polecat skipped `chain-next-iteration.sh` despite
  the formula saying "YOU MUST RUN THIS SCRIPT. DO NOT SKIP IT."

The pattern: agents follow simple, visible instructions. They skip complex,
multi-step procedures, especially when a simpler path exists. They do not
reliably read files they are told to read. They do not reliably execute
commands at specific lifecycle points.

**Implication for system design**: any behavior that must happen reliably
cannot depend on LLM compliance. It must be either (a) a deterministic script,
(b) a hook/guard that fires automatically, or (c) unnecessary.

### The workaround escalation pattern

Every compliance failure led to the same fix pattern:

1. Add a hook or cron job to do mechanically what the agent was supposed to do.
2. Add a guard to block the agent from taking the wrong path.
3. Add a fallback cron that recovers if both the agent and the hook fail.

The result was layer upon layer of mechanical workarounds for behavior that a
simple bash script would have done in the first place. The cron job that checks
for stalled dispatch every 3 minutes and sends the Mayor the exact command to
run is the reductio ad absurdum of this approach: if you have to cron-automate
the thing the agent was supposed to do, the agent is not adding value.

### Infrastructure failures vs. research failures

Every failure documented in RIG_ISSUES.md is an orchestration failure. Zero are
research failures. The experiment pipeline itself works. The Dolt database
works. The problems are all in the layer between "decide what to run" and "run
it."

Specific infrastructure failures that have no analog in a simpler system:

- **Deacon stuck** for 3 days, daemon detected it 1,132 times without restarting
- **Witness went down**, nobody noticed for hours
- **max_polecats=10 on a 15GB machine** caused OOM cascades
- **93 garbage polecats** created from duplicate hypothesis beads
- **22-hour Mayor blackout** because it finished a thought and returned to prompt
- **Stale polecat count** in deferred scheduler blocked all dispatch
- **One-bead-per-convoy** broke auto-feed, polecats went idle
- **Hook overrides wiped on agent restart** (race condition)
- **state.json files persisted from dead sessions** with stale flags

### The PLAN_REVIEW paradox

A review document (PLAN_REVIEW.md) argued against rebuilding Gas Town on the
grounds that "the system was designed well, it just wasn't running." The
infrastructure diagnosis was correct. But the conclusion missed the point: if a
well-designed system fails because the agents don't follow it, the design is
not the bottleneck. The agents are. And you cannot fix agents with more design.

### Latency and cost

The NVIDIA inference endpoint adds ~3 minutes of server-side queuing per step
after the first Bash tool use. This is 10x slower than the direct Anthropic API.
The latency is server-side (confirmed via pcap), unaffected by auth method or
client config. Using `local-sonnet-4.6` with direct console auth eliminates this.

Cost per experiment: $5-15 for a two-agent pair (baseline + two-agent). The
budget-split parameter matters more for research outcomes than for cost.

### Data quality

Six data quality issues accumulated during Gas Town's run:

- **D1**: total_pass_rate stored on two different scales (0-1 and 0-100)
- **D2**: pass_rates JSON uses two formats (array vs. object)
- **D3**: Three different model name strings for the same model
- **D4**: Budget tracking $22 discrepancy from non-atomic insert/update
- **D5**: Four invalid experiment results from silent pipeline degradation
- **D6**: Zero-cost rows from early-INSERT-before-run race condition

All of these are avoidable with validation at the pipeline boundary. The
experiment pipeline should enforce schema constraints before writing, not rely
on downstream consumers to handle inconsistencies.

---

## Design Principles for the Next System

Based on the above, the next research automation system should follow these:

1. **No persistent agent sessions.** Fresh context per LLM call. One-shot
   planning, one-shot analysis. No accumulated context pollution, no stale
   state, no lifecycle management.

2. **No LLM compliance for critical paths.** Budget gates, dispatch, iteration
   chaining, crash recovery — all deterministic. The LLM decides *what* to run,
   not *whether* to run it.

3. **No agent coordination.** If two things need to happen, a script calls them
   both. No message passing, no mail, no nudges, no blocking dependencies.

4. **Parallelism via processes, not agents.** `xargs -P` or `&` + `wait`.
   Each experiment is an independent process. If one fails, the others continue.

5. **State in the database, not in sessions.** Dolt (or even flat files) stores
   experiment results. The planning call reads current state from Dolt every
   time. No session has to remember anything.

6. **Validate at the boundary.** The experiment pipeline enforces schema, cost,
   and completeness constraints before writing to the database. Downstream
   consumers trust the data.

7. **Match infrastructure to the problem.** This project needs to run
   `experiment_pipeline.py` in a loop with a budget gate and some LLM reasoning
   about what to run next. That is a bash script with two `claude --print` calls,
   not a multi-agent town with 5 roles and 14 formulas.
