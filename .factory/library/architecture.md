# Architecture — Latency Investigation

## System Under Investigation

SCBench runs coding agent experiments. The execution chain:

```
two_agent_runner.py (host, Python)
  → subprocess.run: slop-code run (host, Python CLI)
    → DockerStreamingRuntime: docker exec claude CLI (inside persistent container)
      → Anthropic API (console auth) → Claude Sonnet 4.6
```

### Key Components

**`research/runner/two_agent_runner.py`** — Top-level orchestrator. Runs `slop-code run` as a subprocess with `capture_output=True` (no streaming visibility). Manages budget, checkpoint iteration, implementer/reviewer phases.

**`src/slop_code/agent_runner/agents/cli_utils.py`** — The narrowest instrumentation chokepoint. `stream_cli_command()` receives individual parsed lines from Claude CLI's `stream-json` output. Each `yield parser(line)` corresponds to one step. Adding timestamps between consecutive yields directly measures API time vs tool execution time.

**`src/slop_code/agent_runner/agents/claude_code/agent.py`** — `ClaudeCodeAgent._run()` consumes the generator from `stream_cli_command()`. Each iteration is one step. Tracks cost, tokens, steps.

**`src/slop_code/execution/docker_runtime/streaming.py`** — `DockerStreamingRuntime.stream()` runs `docker exec` via `subprocess.Popen` and pipes stdout through threaded pump → event queue → `process_stream()` → `RuntimeEvent` objects.

**`src/slop_code/execution/stream_processor.py`** — `process_stream()` handles threading, timeout, and event routing. Events flow: pump thread → queue → handle_event → yield RuntimeEvent.

### The Latency Problem

~3-minute gaps occur between some steps. Already determined:
- The gap is NOT API inference time (measured at 5-17s between steps)
- The gap is NOT Bash subprocess execution (no child process spawned during gaps)
- Claude CLI is blocked in `epoll_wait()` on a socket during gaps
- API responds in 3-14s even at 49k tokens

**Leading hypothesis:** Claude CLI makes hidden API calls (background tasks, compaction, telemetry) between visible inference calls, and these hidden calls are slow or rate-limited.

### Instrumentation Points

| Layer | File | What to measure |
|-------|------|-----------------|
| Step timing | `cli_utils.py:stream_cli_command()` | Wall-clock between consecutive `yield parser(line)` calls |
| Network traffic | tcpdump inside container | ALL HTTPS requests, timing, endpoints |
| Process tracing | strace on host | What syscalls Claude makes during gaps |

### Output Structure

Experiment outputs go to `outputs/<model>/<agent>_<config>_<timestamp>/<problem>/`. Key files: `infer.log` (step log), `checkpoint_N/agent/stdout.jsonl` (Claude CLI stream-json output).
