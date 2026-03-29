---
description: >-
  Initialize and run an autonomous autoresearch optimization loop on the
  reviewer-coder agent. Reads program.md for full instructions, sets up
  isolation, runs baseline, then enters the infinite experiment loop.
  Invoke with /autoresearch:start or /autoresearch:start <problem_name>.
  Defaults to dag_execution if no problem specified.
argument-hint: "[problem_name]"
---

# Start AutoResearch Run

You are launching an autonomous autoresearch optimization loop.

**Primary problem:** $ARGUMENTS
If no problem was specified, use `file_backup` as the primary problem and `dag_execution` as the cross-validation problem.
If a problem was specified, choose a different problem for cross-validation (every 3-4 iterations).

**Default problems:**
- Primary (4 checkpoints, reliable tests, known baseline 0.606): `file_backup`
- Cross-validation (3 checkpoints, harder, baseline 0.447): `dag_execution`
- Other options if you want variety: `dynamic_buffer`, `file_merger`, `layered_config_synthesizer` (all 4 checkpoints, untested with reviewer_coder)

## Step 1: Read the full instructions

Read `autoresearch/program.md` completely. It contains everything you need:
- Setup procedure (run ID, worktree, manifest)
- What you're optimizing (composite score formula)
- What you can and cannot modify
- Baseline policy (run once in iteration 0)
- The 12-step experiment loop
- Signal interpretation guide
- Artifact structure and templates
- Multi-agent coordination rules
- Revert procedure and provisional keeps
- Budget ($750)

## Step 2: Check current environment

Before setup, understand what's already running:

**Active runs:**
!`for d in autoresearch/runs/*/manifest.yaml; do [ -f "$d" ] && echo "- $(basename $(dirname $d)): $(grep 'status:' "$d" | head -1)" 2>/dev/null; done 2>/dev/null || echo "- (none)"`

**Running slop-code processes:**
!`ps aux | grep 'slop-code run' | grep -v grep | awk '{print "- PID " $2 ": " $NF}' 2>/dev/null || echo "- (none)"`

**Git worktrees:**
!`git worktree list 2>/dev/null`

## Step 3: Execute

Follow the Setup section in `program.md` to initialize your run, then enter the experiment loop.

Do NOT ask for confirmation. The human launched you with `/autoresearch:start` — that is the go signal. Begin immediately.
