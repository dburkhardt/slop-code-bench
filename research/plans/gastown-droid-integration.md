# Plan: Integrate Factory Droid as Gas Town Agent Provider

**Status:** Ready to implement  
**Risk:** Low (per-role config, existing sessions unaffected, easy rollback)  
**Effort:** ~30 minutes

## Background

Gas Town supports any CLI agent via a JSON preset system (Tier 1 integration). No code changes to Gas Town needed. The preset tells Gas Town how to launch, detect, resume, and communicate with the agent.

Reference: https://github.com/steveyegge/gastown/blob/main/docs/agent-provider-integration.md

## Prerequisites

- `droid` binary at `/home/ubuntu/.local/bin/droid` (already installed)
- `gt`, `bd`, `dolt` at `/home/ubuntu/gopath/bin/` (already installed)
- Gas Town workspace at `~/gt/` with `scbench` rig (already configured)

## Step 1: Create Agent Preset

Create `~/gt/settings/agents.json`:

```json
{
  "version": 1,
  "agents": {
    "droid": {
      "name": "droid",
      "command": "droid",
      "args": [],
      "env": {
        "PATH": "/home/ubuntu/gopath/bin:/home/ubuntu/go/bin:/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin"
      },
      "process_names": ["droid"],
      "resume_flag": "--resume",
      "resume_style": "flag",
      "prompt_mode": "arg",
      "ready_prompt_prefix": "> ",
      "ready_delay_ms": 8000,
      "instructions_file": "AGENTS.md",
      "hooks_informational": true
    }
  }
}
```

**Key details:**
- `env.PATH` includes `~/gopath/bin` so `gt`, `bd`, `dolt` are found in droid sessions
- `process_names: ["droid"]` — droid is a native ELF binary, appears as `droid` in `ps`
- `resume_flag: "--resume"` — droid supports `droid --resume [sessionId]` or `droid -r [sessionId]`
- `ready_prompt_prefix: "> "` — droid's interactive prompt; `ready_delay_ms` is fallback
- `hooks_informational: true` — droid doesn't have Claude-compatible lifecycle hooks, so Gas Town uses tmux nudge-based fallback (same tier as Codex/AMP/Auggie)

## Step 2: Create Droid Settings for Autonomous Mode

Droid's `--settings <path>` flag accepts a JSON file. Gas Town needs autonomy mode set to high for unattended operation.

Create a settings file that Gas Town roles can reference. The exact location depends on how Gas Town resolves the `--settings` flag for the droid preset — it may need to go in the role's working directory as `.factory/settings.json` or be passed via the preset's `args` field.

**Option A: Add to preset args** (simplest):
```json
"args": ["--settings", "/home/ubuntu/gt/settings/droid-autonomous.json"]
```

**Option B: Per-role settings file** in each role's `.factory/` directory.

Create `/home/ubuntu/gt/settings/droid-autonomous.json`:
```json
{
  "autonomyMode": "auto-high",
  "completionSound": "off",
  "awaitingInputSound": "off",
  "cloudSessionSync": false
}
```

- `autonomyMode: "auto-high"` — equivalent of Claude's `--dangerously-skip-permissions`
- Sounds off (headless tmux)
- Cloud sync off (Gas Town manages its own session state)

## Step 3: Configure Per-Role Agent Assignment

Create `~/gt/settings/config.json`:
```json
{
  "type": "town-settings",
  "version": 1,
  "default_agent": "claude",
  "role_agents": {
    "mayor": "droid"
  }
}
```

This means:
- **Mayor** → Droid
- **Everything else** (deacon, witness, refinery, polecats) → Claude (unchanged)

To switch more roles later, add them to `role_agents`:
```json
"role_agents": {
  "mayor": "droid",
  "polecat": "droid",
  "witness": "claude"
}
```

## Step 4: Test with a Disposable Crew Member

Before touching the Mayor, test with a throwaway crew session:

```bash
gt crew start test-droid --agent droid
```

Verify:
1. Session starts in tmux (check `gt status`)
2. `gt prime` content is delivered (look for Gas Town role context in the session)
3. Agent can receive nudges: `gt nudge scbench/crew/test-droid "hello"`
4. Agent responds and can execute commands
5. Process detection works: `tmux -L gt-ae82a2 display-message -t sc-test-droid -p '#{pane_current_command}'` should show `droid`

Clean up: `gt crew stop test-droid`

## Step 5: Switch Mayor to Droid

```bash
gt mayor restart
```

Verify:
1. `gt status` shows mayor running with `droid` process
2. `gt mayor attach scbench` connects to the droid session
3. Mayor receives research loop instructions via `gt prime`
4. Mayor can execute `gt`, `bd`, `dolt` commands

## Rollback

If anything breaks:
1. Delete `~/gt/settings/agents.json`
2. Delete or edit `~/gt/settings/config.json` to remove `role_agents`
3. Kill the droid tmux session: `tmux -L gt-ae82a2 kill-session -t hq-mayor`
4. Gas Town automatically falls back to built-in `claude` preset
5. `gt mayor restart` creates a fresh Claude session

**Existing Claude sessions are NOT affected by config changes.** Config only applies when new sessions are created.

## Limitations (Tier 1 / Informational Hooks)

- **No automatic hooks**: Gas Town's `SessionStart`, `PreCompact`, `UserPromptSubmit` hooks don't fire automatically. Gas Town compensates with tmux nudge-based fallback.
- **No tool guards**: `PreToolUse` guards (like PR workflow protection) don't apply. Droid's own auto-run risk classification provides similar protection.
- **No cost recording hook**: The `Stop` hook that runs `gt costs record` won't fire. Cost tracking relies on droid's own usage tracking.
- **Mail delivery**: Gas Town starts a nudge-poller background process for non-hook agents to deliver mail periodically.

## Future: Tier 2 Integration (Hooks)

Droid supports hooks via `~/.factory/hooks/` or `.factory/hooks/` (see https://docs.factory.ai/cli/configuration/hooks-guide.md). A future integration could:

1. Create Gas Town hook scripts that call `gt prime`, `gt mail check --inject`
2. Register them as droid hooks for `SessionStart`, `PreCompact` events
3. This would bring droid to full Tier 2 parity with Claude

## References

- Gas Town agent provider docs: https://github.com/steveyegge/gastown/blob/main/docs/agent-provider-integration.md
- Droid CLI reference: https://docs.factory.ai/reference/cli-reference.md
- Droid auto-run docs: https://docs.factory.ai/cli/user-guides/auto-run.md
- Droid settings: https://docs.factory.ai/cli/configuration/settings.md
- Droid hooks: https://docs.factory.ai/cli/configuration/hooks-guide.md
