---
name: autoresearch:summarize
description: >-
  Generate a cross-run comparison of all autoresearch runs. Reads manifests,
  results, and summaries to produce a ranked table and identify the best
  configuration. Use to review progress across multiple research agents.
---

# AutoResearch Cross-Run Summary

## All Run Manifests

!`for d in autoresearch/runs/*/manifest.yaml; do [ -f "$d" ] && echo "### $(basename $(dirname $d))" && cat "$d" && echo; done 2>/dev/null || echo "(no runs found)"`

## Latest Results Per Run

!`for d in autoresearch/runs/*/; do latest=$(ls -td "$d"iter_* 2>/dev/null | head -1); if [ -n "$latest" ] && [ -f "$latest/results.json" ]; then echo "### $(basename $d) — $(basename $latest)"; cat "$latest/results.json"; echo; fi; done 2>/dev/null || echo "(no results found)"`

## Run Summaries

!`for d in autoresearch/runs/*/summary.md; do [ -f "$d" ] && echo "### $(basename $(dirname $d))" && cat "$d" && echo "---"; done 2>/dev/null || echo "(no summaries found)"`

## Your Task

Using the data above, produce:

1. **Leaderboard** — table of all runs ranked by best composite score:

   | Rank | Run ID | Researcher | Focus | Best Composite | Best Iter | Iters | Cost | Status |
   |------|--------|------------|-------|----------------|-----------|-------|------|--------|

2. **Best config** — identify the run and iteration with the highest composite. Show the path to its `agent.py` and `config.yaml` snapshots so the human can inspect or adopt them.

3. **Researcher grading** — group runs by researcher model/harness. For each researcher, report: number of runs, mean best composite, total cost, mean iterations before best. Which researcher found improvements most efficiently?

4. **Search space coverage** — what dimensions have been explored (prompts, flow, concurrency, budget allocation, etc.) and what remains untried? Cross-reference the "Promising directions" from each run's summary.md.

5. **Key findings** — the 3-5 most important insights across all runs. What works, what doesn't, and what's surprising?
