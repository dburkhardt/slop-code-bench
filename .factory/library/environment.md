# Environment

Environment variables, external dependencies, and setup notes.

**What belongs here:** Required env vars, external API keys/services, dependency quirks, platform-specific notes.
**What does NOT belong here:** Service ports/commands (use `.factory/services.yaml`).

---

## Required Environment Variables

- Claude Code uses console billing (no separate API key needed)

## Tool Paths

- Go: `/home/ubuntu/go/bin/go` (GOROOT=/home/ubuntu/go)
- Go binaries: `/home/ubuntu/gopath/bin/` (gt, bd)
- Dolt: `/usr/local/bin/dolt`
- Claude Code: `/home/ubuntu/.local/bin/claude`
- uv: `/home/ubuntu/.local/bin/uv`

Workers must set: `export PATH=$PATH:/home/ubuntu/gopath/bin:/home/ubuntu/go/bin`

## Gas Town Workspace

- Town root: `~/gt`
- Rig: `~/gt/scbench`
- Dolt data: `~/gt/.dolt-data/hq` (town), `~/gt/.dolt-data/scbench` (rig)
- Rig config: `~/gt/scbench/config.json`

## Python

- Python 3.12.13 managed by uv
- Virtual env at `/home/ubuntu/git-repos/slop-code-bench/.venv/`
- Dependencies synced via `uv sync`
- Use `uv run python` for mission scripts under `research/runner/`. System `python3` is 3.10 on this host and can fail on `datetime.UTC` imports used by the runner.

## Docker

- Docker 29.3.1 available
- Required for slop-code experiment execution
- Agent Docker images build automatically on first run

## Environment Quirks

- Gas Town escalation config expects `smtp_port` as a string value in `~/gt/settings/escalation.json` in this environment.
- Dolt auto-commit validation must run through the SQL server path on port `3307`; local `dolt sql` CLI mode does not exercise the same commit-log behavior.
- For role `settings.json` hooks, use a PATH that includes `/home/ubuntu/gopath/bin` and `/home/ubuntu/go/bin` so `gt` and `bd` resolve consistently.
- For machine-readable bead creation/output parsing, prefer `bd ... --json`; `-q` is not guaranteed to emit only a raw bead ID.
- Some role polecat safety-net scripts may run `git stash` in the shared repository when reactivated. This can interfere with active worker edits during integration tests. Stop idle polecats before mutation-heavy local test runs, or isolate test execution in a dedicated worktree.
