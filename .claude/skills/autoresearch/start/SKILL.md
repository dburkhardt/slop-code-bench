---
name: autoresearch:start
description: >-
  Initialize and run an autonomous autoresearch optimization loop on the
  reviewer-coder agent. Reads program.md for full instructions, sets up
  isolation, runs baseline, then enters the infinite experiment loop.
  Invoke with /autoresearch:start <problem_name>.
argument-hint: "<problem_name> e.g. dag_execution"
---

# Start AutoResearch Run

You are launching an autonomous autoresearch optimization loop.

**Problem:** $ARGUMENTS

## Step 1: Read the full instructions

Read `autoresearch/program.md` completely. It contains everything you need:
- Setup procedure (run ID, worktree, manifest)
- What you're optimizing (composite score formula)
- What you can and cannot modify
- Baseline policy
- The 12-step experiment loop
- Signal interpretation guide
- Artifact structure and templates
- Multi-agent coordination rules
- Revert procedure
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

Follow the Setup section in `program.md` to initialize your run, then enter the experiment loop. The problem to optimize on is `$ARGUMENTS`.

Do NOT ask for confirmation. The human launched you with `/autoresearch:start` — that is the go signal. Begin immediately.
