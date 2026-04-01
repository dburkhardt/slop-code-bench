---
name: python-worker
description: Builds Python code, configs, and prompt templates for the SCBench research lab
---

# Python Worker

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Features involving:
- Building/modifying the two-agent runner script (research/runner/two_agent_runner.py)
- Creating/modifying prompt templates (Jinja2 files in configs/prompts/ or research/prompts/)
- Creating/modifying model and provider configs (YAML files in configs/)
- Building analysis scripts (research/analysis/)
- Writing Python tests for any of the above

## Required Skills

None.

## Work Procedure

1. **Read the feature description carefully.** Understand preconditions, expectedBehavior, and verificationSteps.

2. **Set up environment:**
   ```bash
   export PATH=$PATH:/home/ubuntu/gopath/bin:/home/ubuntu/go/bin
   cd /home/ubuntu/git-repos/slop-code-bench
   ```

3. **Investigate existing code.** Before writing anything:
   - Read the spec at `research/spec.md` for architectural context
   - Read existing related code (e.g., `src/slop_code/agent_runner/agents/reviewer_coder/` for the existing two-agent pattern)
   - Read `configs/` examples for YAML format patterns
   - Read `.factory/library/architecture.md` for system overview

4. **Write tests first (TDD).** For Python code:
   - Create test files under `tests/` mirroring source structure
   - Write failing tests that verify the feature's expectedBehavior
   - Run tests to confirm they fail: `uv run pytest tests/path/to/test_file.py -v`

5. **Implement.** Write the code to make tests pass:
   - Follow existing coding conventions (ruff, isort, type annotations)
   - Use structlog for logging
   - Use pathlib.Path for file operations
   - Use Pydantic for config models

6. **Verify:**
   - Run targeted tests: `uv run pytest tests/path/to/test_file.py -v`
   - Run full test suite: `uv run pytest -q`
   - Run lint: `uv run ruff check .`
   - For CLI scripts, run `--help` and verify all flags work
   - For Jinja templates, test rendering with sample variables
   - For configs, verify YAML is parseable and fields are correct

7. **Manual verification.** Run the actual command/script with real inputs to verify it works beyond unit tests. For the runner, try a dry-run or canary mode. For configs, verify slop-code CLI accepts them.

8. **Commit and push (MANDATORY).** After all verification passes:
   ```bash
   cd /home/ubuntu/git-repos/slop-code-bench
   git add -A research/ tests/runner/ tests/analysis/ configs/ .factory/
   git commit -m "<feature-id>: <short description>"
   git push origin main
   ```
   This preserves work in case the VM crashes. Do NOT skip the push.

## Example Handoff

```json
{
  "salientSummary": "Built two_agent_runner.py with CLI args (--problem, --model, --budget-split, --budget, --canary), budget split enforcement per checkpoint, and cost cap with partial result saving. Tests pass (8 cases), ruff clean, canary mode verified with $0.50 cap on file_backup problem.",
  "whatWasImplemented": "research/runner/two_agent_runner.py: CLI entry point using typer, per-checkpoint implementer->reviewer loop with configurable budget split, cumulative cost tracking with abort on overrun, partial result serialization, canary mode with defaults. Output directory structure matches slop-code eval expectations.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {"command": "uv run pytest tests/runner/test_two_agent_runner.py -v", "exitCode": 0, "observation": "8 tests passed: CLI args, budget split, cost cap, canary mode, metrics tracking, output structure, resume detection, model validation"},
      {"command": "uv run ruff check research/runner/", "exitCode": 0, "observation": "No lint errors"},
      {"command": "uv run python research/runner/two_agent_runner.py --help", "exitCode": 0, "observation": "All 7 flags listed with descriptions"},
      {"command": "uv run python research/runner/two_agent_runner.py --canary", "exitCode": 0, "observation": "Canary completed in 45s, cost $0.32, output at outputs/canary_20260331/"}
    ],
    "interactiveChecks": [
      {"action": "Ran canary mode and checked output directory structure", "observed": "Output contains checkpoint_1/ with solution files, eval-compatible layout, metrics.json with all 6 per-checkpoint metrics"}
    ]
  },
  "tests": {
    "added": [
      {"file": "tests/runner/test_two_agent_runner.py", "cases": [
        {"name": "test_cli_accepts_required_args", "verifies": "All 7 CLI flags are present and validated"},
        {"name": "test_budget_split_enforcement", "verifies": "Implementer gets X%, reviewer gets (100-X)% within tolerance"},
        {"name": "test_cost_cap_aborts", "verifies": "Runner aborts when cumulative cost exceeds --budget"},
        {"name": "test_canary_mode_defaults", "verifies": "Canary runs with sensible defaults and $0.50 cap"},
        {"name": "test_metrics_tracking", "verifies": "All 6 metrics recorded per checkpoint"},
        {"name": "test_output_structure", "verifies": "Output directory matches slop-code eval expectations"},
        {"name": "test_resume_detection", "verifies": "Runner detects existing output and resumes from next checkpoint"},
        {"name": "test_invalid_model_rejected", "verifies": "Non-existent model name produces clear error"}
      ]}
    ]
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- The feature requires modifying upstream harness code in `src/slop_code/`
- Docker is not running and the feature requires Docker execution
- API credentials are missing or invalid
- The feature depends on Gas Town infrastructure not yet set up (Dolt tables, beads)
