# User Testing — Latency Investigation

## Validation Surface

This mission's output is CLI scripts and a markdown investigation report. No web UI or API server.

**Surface:** File system + CLI output
**Tool:** Shell commands (bash, grep, find, cat, git diff)
**No browser testing needed.**

## Validation Concurrency

Max concurrent validators: **3** (4 vCPUs, 15GB RAM, ~10GB used baseline). All validation is lightweight CLI commands, no heavy processes. The main constraint is that experiment execution (Phase 2) must run serially to get clean timing measurements.

## Testing Approach

1. **Instrumentation validation:** Run existing pytest suite (`tests/runner/`) + ruff lint
2. **Script validation:** Syntax checks (bash -n, python ast.parse)
3. **Experiment validation:** Check output files exist with expected content
4. **Analysis validation:** Check investigation document for new sections, hypothesis verdicts, data references

For `VAL-INST-003`, use the mission-scoped command that excludes known
pre-existing failures not related to this milestone:
`uv run pytest tests/runner/ -x -q -k 'not test_provenance_chain_documented and not test_formula_pour_creates_molecule and not canary'`.

## Flow Validator Guidance: cli-file-surface

- Stay inside `/home/ubuntu/git-repos/slop-code-bench` and
  `/home/ubuntu/.factory/missions/ba94244c-8343-4186-8ee5-9d59460ef8a8`.
- Treat all mission artifacts as read-only, except writing each flow report to
  `.factory/validation/investigation/user-testing/flows/<group-id>.json` and
  optional evidence files under
  `/home/ubuntu/.factory/missions/ba94244c-8343-4186-8ee5-9d59460ef8a8/evidence/investigation/<group-id>/`.
- Do not run destructive cleanup commands, container operations, or long-running
  experiments during validation.
- Assertions are validated by file/content checks and lightweight test/lint
  commands only.
