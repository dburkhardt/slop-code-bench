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
- `research/runner/two_agent_runner.py` currently fails checkpoint discovery for
  problems laid out as `checkpoint_*.md` files, with `Error: no checkpoints found`.
  This blocks multiple runner and pipeline assertions that require checkpoint
  execution.
- Foundation milestone validation can encounter missing Dolt research tables
  (`experiments`, `budget`). Those tables are created by later setup work.
- Canary preflight path checks `ANTHROPIC_API_KEY`; if missing, canary fails in
  preflight before checkpoint execution.
