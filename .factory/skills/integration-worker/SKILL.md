---
name: integration-worker
description: Wires up end-to-end flows, Gas Town roles, research loop, and analysis for SCBench
---

# Integration Worker

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Features involving:
- Wiring up Gas Town analytical roles (Review Board, Red Team, Idea Factory) with CLAUDE.md and settings
- Setting up the research loop (Mayor patrol phases)
- Connecting the experiment pipeline end-to-end (formula -> convoy -> polecat -> Dolt -> analysis)
- Building analysis scripts that query Dolt and produce reports
- Setting up escalation routing and monitoring
- Creating the final report

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

3. **Investigate existing state thoroughly:**
   - Gas Town: `gt status`, `gt rig list`, `bd list`
   - Dolt data: `cd ~/gt/.dolt-data/scbench && dolt sql -q "SELECT COUNT(*) FROM experiments;"`
   - Existing infrastructure: verify all preconditions are met
   - Read `research/spec.md` for role descriptions, loop phases, and analysis requirements
   - Read `.factory/library/architecture.md` for system overview

4. **For Gas Town roles (CLAUDE.md/settings):**
   - Create role-specific CLAUDE.md files that instruct the polecat on its behavior
   - Include explicit bead query commands for context reconstruction (roles are stateless)
   - Include the validation filter for Review Board (`manipulation_check='passed' AND results_valid=true`)
   - Include adversarial stance for Red Team (no rubber-stamping)
   - Install in the appropriate Gas Town location for the rig

5. **For research loop wiring:**
   - Create Mayor CLAUDE.md with the full patrol loop (Phases 0-5)
   - Include budget check SQL, batch planning, Red Team gate flow
   - Include shutdown sequence steps
   - Test each phase individually before testing the full loop

6. **For analysis scripts:**
   - Write Python scripts that query Dolt with validation filters
   - Compute required metrics (pass rate delta, erosion slope, budget efficiency)
   - Include sample size reporting
   - Generate markdown output for conclusions and final report

7. **Verify end-to-end:**
   - Test bead creation, dependency linking, and bd ready behavior
   - Test formula pouring and molecule step execution
   - Test convoy creation and status tracking
   - Test escalation firing and listing
   - Verify data flows from experiment -> Dolt -> analysis -> conclusion bead

8. **Commit and push (MANDATORY).** After all verification passes:
   ```bash
   cd /home/ubuntu/git-repos/slop-code-bench
   git add -A research/ .factory/ configs/
   git commit -m "<feature-id>: <short description>"
   git push origin main
   ```
   This preserves work in case the VM crashes. Do NOT skip the push.

9. **Run validators:**
   - `uv run pytest -q` (should not break existing tests)
   - `uv run ruff check .` for any Python scripts
   - `gt status` to verify Gas Town is healthy
   - Verify Dolt data integrity after operations

## Example Handoff

```json
{
  "salientSummary": "Set up Review Board role with CLAUDE.md containing Dolt query instructions (validation filters enforced), conclusion bead filing procedure. Tested by creating a test conclusion bead with mock data. Red Team role configured with adversarial review instructions and blocks dependency creation flow. Verified blocking gate: batch absent from bd ready while review open, present after close.",
  "whatWasImplemented": "Review Board CLAUDE.md at ~/gt/scbench/polecats/review-board/.claude/CLAUDE.md with Dolt query templates, validation filters, conclusion bead schema, and exclusion count reporting. Red Team CLAUDE.md at ~/gt/scbench/polecats/red-team/.claude/CLAUDE.md with adversarial review checklist, blocking dependency creation procedure, and post-mortem (advisory) procedure. Both roles include bd commands for context reconstruction from beads.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {"command": "bd show sc-review-board-role", "exitCode": 0, "observation": "Role bead contains Review Board instructions"},
      {"command": "bd create 'Test Batch' && bd create 'Test Review' && bd link batch review --type blocks && bd ready | grep batch", "exitCode": 1, "observation": "Batch correctly absent from bd ready while blocked"},
      {"command": "bd close review && bd ready | grep batch", "exitCode": 0, "observation": "Batch appears in bd ready after review closed"},
      {"command": "gt escalate --severity medium --reason 'Test escalation' && gt escalate list | grep 'Test'", "exitCode": 0, "observation": "Escalation created and visible in list"}
    ],
    "interactiveChecks": [
      {"action": "Verified Review Board CLAUDE.md contains validation filter", "observed": "CLAUDE.md includes WHERE manipulation_check = 'passed' AND results_valid = true in all query templates"}
    ]
  },
  "tests": {
    "added": []
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- Gas Town roles require permissions or configurations not available
- Dolt tables don't exist yet (precondition not met)
- Two-agent runner doesn't exist yet (precondition for pipeline integration)
- Formula pouring fails due to Gas Town bugs or version incompatibilities
- Convoy dispatch doesn't work as expected
