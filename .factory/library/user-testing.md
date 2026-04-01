# User Testing

Testing surface, required testing skills/tools, and resource cost classification.

## Validation Surface

This is a CLI/infrastructure project with no web UI. All testing is done via shell commands.

### Surfaces:
1. **Shell CLI** - slop-code CLI, two_agent_runner.py, gt/bd commands, dolt SQL
2. **Dolt SQL** - Direct SQL queries against experiment and budget tables
3. **Gas Town** - gt and bd command outputs, bead state, convoy status

### Tools:
- Shell commands (bash)
- `curl` for NVIDIA API verification
- `dolt sql -q` for Dolt queries
- `gt` / `bd` for Gas Town operations
- `slop-code` CLI for harness operations

### Testing Approach:
- Run commands, check exit codes and output
- Query Dolt tables to verify data integrity
- Check bead state for Gas Town operations
- Verify file existence and structure for outputs

## Validation Concurrency

### Shell surface:
- Machine: 4 CPUs, 15GB RAM
- Each validator runs shell commands sequentially
- Shell commands are lightweight (~50MB per process)
- Docker experiments are heavier but run one at a time within a validator
- **Max concurrent validators: 3** (conservatively, to leave headroom for Docker and Dolt)

### Rationale:
- Docker containers for slop-code experiments can use 2-4GB RAM each
- Dolt server uses ~200MB
- Gas Town processes are lightweight
- With 15GB total and ~2GB baseline usage, 3 concurrent validators each potentially running Docker = ~8-10GB, within 70% of available headroom

## Flow Validator Guidance: shell

- Scope each subagent to only its assigned assertion IDs.
- Run commands from `/home/ubuntu/git-repos/slop-code-bench`.
- Use a unique temp workspace per flow at `/tmp/scbench-user-testing/<group-id>/`
  for any transient files.
- Write exactly one flow report to
  `.factory/validation/<milestone>/user-testing/flows/<group-id>.json`.
- Save command evidence under
  `/home/ubuntu/.factory/missions/87f1dbde-093a-4612-97da-91c8bec9fe63/evidence/<milestone>/<group-id>/`.
- Do not restart Docker or Dolt. Treat port `3307` as managed infrastructure.
- Do not modify implementation code as part of flow validation.

## Known Validation Frictions and Blockers

- Use `uv run python`, not system `python3`, when importing mission runner modules.
  The runner imports `datetime.UTC`, which is unavailable in Python 3.10.
- `research/runner/two_agent_runner.py` can report successful phase progression
  while internal subprocess invocation (`python -m slop_code run`) fails in this
  environment with `No module named slop_code.__main__`. When this happens,
  metrics remain at zero and eval-compatible run artifacts are not produced.
- Canary failure diagnostics are asymmetric. Docker failures are component-tagged,
  while invalid API-key scenarios can surface as a generic implementer-stage
  failure without explicit auth wording.
- `--budget-split 100` is rejected by argument validation (`range 1-99`), which
  conflicts with assertions expecting implementer-only boundary behavior.
- Foundation pipeline validation remains blocked until Dolt research tables
  `experiments` and `budget` are present in the `scbench` database.
- Run `gt` and `bd` validation commands from `/home/ubuntu/gt/scbench`.
  Running from `/home/ubuntu/gt` targets the HQ dataset and can miss rig beads.
- Analytical-roles validation can remain blocked when no loop execution artifacts
  exist. Missing artifacts include batch beads, Review Board conclusions, and
  Red Team post-mortem beads in the `scbench` rig.
