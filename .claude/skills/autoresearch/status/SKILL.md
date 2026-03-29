---
name: autoresearch:status
description: >-
  Check the status of all autoresearch runs. Shows active processes,
  current iterations, budget remaining, and what each agent is working on.
---

# AutoResearch Status

## Running Processes

!`ps aux | grep 'slop-code run' | grep -v grep | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print "  (PID "$2")"}' 2>/dev/null || echo "(no slop-code processes running)"`

## Git Worktrees

!`git worktree list 2>/dev/null`

## Run Manifests

!`for d in autoresearch/runs/*/manifest.yaml; do [ -f "$d" ] && echo "### $(basename $(dirname $d))" && cat "$d" && echo; done 2>/dev/null || echo "(no runs found)"`

## Latest Iteration Per Run

!`for d in autoresearch/runs/*/; do latest=$(ls -td "$d"iter_* 2>/dev/null | head -1); if [ -n "$latest" ] && [ -f "$latest/report.md" ]; then echo "### $(basename $d) — $(basename $latest)"; head -3 "$latest/report.md"; echo; if [ -f "$latest/results.json" ]; then echo '```'; cat "$latest/results.json"; echo '```'; fi; echo "---"; fi; done 2>/dev/null || echo "(no iteration reports found)"`

## Your Task

Summarize the above into a concise status dashboard:
1. Which runs are active vs completed
2. What each active run is currently exploring (from manifest focus + latest report)
3. Budget remaining per run (from manifest budget vs latest results.json cumulative cost)
4. Flag any stalled runs (manifest says running but no slop-code process found)
5. Quick leaderboard: best composite per run
