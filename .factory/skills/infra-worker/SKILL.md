---
name: infra-worker
description: Sets up Gas Town, Dolt, beads, and infrastructure for the SCBench research lab
---

# Infrastructure Worker

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Features involving:
- Creating Dolt tables (experiments, budget)
- Creating Gas Town beads (role beads, epics, research log)
- Creating/installing Gas Town formulas (TOML files)
- Setting up cron jobs or sync scripts
- Configuring Gas Town roles (CLAUDE.md, settings for polecats)
- Gas Town crew workspace setup

## Required Skills

None.

## Work Procedure

1. **Read the feature description carefully.** Understand preconditions, expectedBehavior, and verificationSteps.

2. **Set up environment:**
   ```bash
   export PATH=$PATH:/home/ubuntu/gopath/bin:/home/ubuntu/go/bin
   export GOROOT=/home/ubuntu/go
   export GOPATH=/home/ubuntu/gopath
   cd /home/ubuntu/git-repos/slop-code-bench
   ```

3. **Investigate existing state.** Before making changes:
   - Check Gas Town status: `gt status`, `gt rig list`
   - Check existing beads: `bd list` (with appropriate --db flag for scbench)
   - Check Dolt tables: `cd ~/gt/.dolt-data/scbench && dolt sql -q "SHOW TABLES;"`
   - Read `research/spec.md` for the exact schema definitions and role descriptions
   - Read `.factory/library/architecture.md` for system overview

4. **Write setup scripts when appropriate.** For repeatable infrastructure:
   - Create SQL scripts for Dolt table creation
   - Create shell scripts for bead creation sequences
   - Make scripts idempotent (check before create)

5. **Implement infrastructure changes:**
   - For Dolt tables: Use `cd ~/gt/.dolt-data/scbench && dolt sql -q "CREATE TABLE IF NOT EXISTS ..."`
   - For beads: Use `bd create`, `bd update`, `bd link` commands with `BEADS_DIR=~/gt/scbench/.beads`
   - For formulas: Create TOML file in `research/formulas/`, then copy/install to formula search path
   - For cron: Use `crontab -e` or create script in research/

6. **Verify each change immediately:**
   - Dolt: `dolt sql -q "DESCRIBE <table>;"` to verify schema
   - Beads: `bd show <bead-id>` to verify creation
   - Formulas: `gt formula show <name>` to verify registration
   - Gas Town: `gt status` to verify state

7. **Test the full workflow.** After creating infrastructure, test it end-to-end:
   - Insert and query test data in Dolt tables
   - Create and manipulate test beads
   - Pour a test formula molecule
   - Verify dependencies and blocking work

## Example Handoff

```json
{
  "salientSummary": "Created experiments and budget Dolt tables with full spec schema (27 columns + 5 columns). Budget initialized at $500. Created 3 role beads (idea-factory, review-board, red-team), 2 epic beads (research-kb, hypotheses), and mayor research log. All verified via DESCRIBE, bd show, and test INSERT/SELECT.",
  "whatWasImplemented": "Dolt tables: experiments (27 cols with JSON, ENUM, DECIMAL types) and budget (5 cols with generated remaining column) in ~/gt/.dolt-data/scbench. Budget initialized to $500. Gas Town beads: sc-idea-factory-role, sc-review-board-role, sc-red-team-role (role beads with descriptions), sc-research-kb and sc-hypotheses (epic beads), sc-research-log (mayor's research log). Setup script at research/scripts/setup_infrastructure.sh.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {"command": "cd ~/gt/.dolt-data/scbench && dolt sql -q 'DESCRIBE experiments;'", "exitCode": 0, "observation": "All 27 columns present with correct types"},
      {"command": "cd ~/gt/.dolt-data/scbench && dolt sql -q 'SELECT * FROM budget;'", "exitCode": 0, "observation": "1 row: total_budget=500.00, spent=0.00, remaining=500.00"},
      {"command": "BEADS_DIR=~/gt/scbench/.beads bd show sc-idea-factory-role", "exitCode": 0, "observation": "Bead exists with role description"},
      {"command": "BEADS_DIR=~/gt/scbench/.beads bd show sc-research-kb", "exitCode": 0, "observation": "Epic bead exists, status open"},
      {"command": "cd ~/gt/.dolt-data/scbench && dolt sql -q \"INSERT INTO experiments (problem_id, model, mode) VALUES ('test', 'test', 'single'); SELECT * FROM experiments;\"", "exitCode": 0, "observation": "Test row inserted and retrieved successfully"}
    ],
    "interactiveChecks": [
      {"action": "Tested budget auto-compute by updating spent", "observed": "UPDATE budget SET spent=50 WHERE id=1; SELECT remaining returns 450.00 as expected"}
    ]
  },
  "tests": {
    "added": []
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- Gas Town workspace is corrupted or gt commands fail systematically
- Dolt server is not running and cannot be started
- Need to create crew workspace but user credentials unknown
- Formula registration path is unclear or gt formula commands don't work as expected
- Beads database is locked or corrupted
