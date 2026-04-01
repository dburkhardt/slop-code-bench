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
