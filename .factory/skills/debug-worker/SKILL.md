---
name: debug-worker
description: Worker for latency investigation — builds instrumentation, runs experiments, analyzes results
---

# Debug Worker

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Use for all features in the latency investigation mission: building instrumentation code, creating debug scripts, running experiments, capturing network/strace data, and analyzing results to update the investigation document.

## Required Skills

None — all work is done via file editing and shell commands.

## Work Procedure

### For instrumentation features (modifying cli_utils.py or agent.py):

1. **Read the current source** — Understand `stream_cli_command()` in `cli_utils.py` and `_run()` in `claude_code/agent.py`. Read the architecture doc at `.factory/library/architecture.md`.
2. **Read the investigation document** — `research/debug/latency-investigation.md` for full context on what timing data is needed and why.
3. **Write tests first** if modifying source code that has existing tests. Check `tests/runner/` for relevant test files. Make the test fail first.
4. **Implement the instrumentation** — Add per-step timing with `time.monotonic()`. The key measurement: time between consecutive `yield parser(line)` calls in `stream_cli_command()`. Emit structured data (JSON or tagged log lines).
5. **Run tests:** `cd /home/ubuntu/git-repos/slop-code-bench && uv run pytest tests/runner/ -x -q`
6. **Run lint:** `cd /home/ubuntu/git-repos/slop-code-bench && uv run ruff check src/slop_code/agent_runner/agents/cli_utils.py src/slop_code/agent_runner/agents/claude_code/agent.py`
7. **Commit** with a descriptive message.

### For debug script features (creating scripts in research/debug/):

1. **Read the investigation document** for the exact script requirements (command templates are provided in the "How to validate" and "Recommended Debugging Plan" sections).
2. **Create the script** in `research/debug/`. Include a docstring/comment header explaining purpose and usage.
3. **Syntax check:** `bash -n script.sh` or `python3 -c "import ast; ast.parse(open('script.py').read())"`
4. **Run lint if Python:** `cd /home/ubuntu/git-repos/slop-code-bench && uv run ruff check research/debug/script.py`
5. **Commit** with a descriptive message.

### For experiment execution features:

1. **Read the investigation document** for the exact experiment procedure.
2. **Clean up first** if the feature requires it — kill processes, stop containers. Log what was cleaned.
3. **Run the experiment** with appropriate timeout (use `timeout 1800` for 30-minute cap).
4. **Capture output** — save experiment logs, timing data, pcap files to `research/debug/results/`.
5. **If experiment times out or fails**, capture whatever partial data was produced. This is still valuable.
6. **Document what happened** — add a note to the investigation doc or a results file.
7. **Commit** results and updated investigation doc.

### For analysis features:

1. **Read all collected data** — experiment logs, timing data, pcap analysis, strace output.
2. **Correlate data sources** — match timestamps across infer.log, step timing, network capture, strace.
3. **Address each hypothesis** — for H1-H7 plus "hidden API calls", determine: confirmed, refuted, or inconclusive with evidence.
4. **Identify root cause** — or narrow to ≤2 candidates with a clear next step.
5. **Update `research/debug/latency-investigation.md`** with a new findings section containing data-backed conclusions.
6. **Commit** the updated document.

## Example Handoff

```json
{
  "salientSummary": "Added per-step timing instrumentation to cli_utils.py. Each step now emits a STEP_TIMING log line with api_ms, tool_ms, and tool_type. Ran pytest tests/runner/ (12 passing) and ruff check (0 errors). Timing data format: JSON with step, timestamp, api_ms, tool_ms, tool_type fields.",
  "whatWasImplemented": "Per-step wall-clock timing in stream_cli_command() using time.monotonic() between consecutive yield calls. Emits structured log lines via structlog with step number, API inference duration, tool execution duration, and tool type (Bash/Edit/Read/Write). Data written to stderr alongside existing output.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {
        "command": "cd /home/ubuntu/git-repos/slop-code-bench && uv run pytest tests/runner/ -x -q",
        "exitCode": 0,
        "observation": "12 tests passed, no failures"
      },
      {
        "command": "cd /home/ubuntu/git-repos/slop-code-bench && uv run ruff check src/slop_code/agent_runner/agents/cli_utils.py",
        "exitCode": 0,
        "observation": "No lint errors"
      }
    ],
    "interactiveChecks": []
  },
  "tests": {
    "added": []
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- Cannot install tcpdump (Docker container lacks root access or apt-get fails)
- strace not available on host and cannot be installed
- NVIDIA API key is expired or invalid
- Experiment produces no output after 30 minutes (infrastructure issue)
- Rate limiting prevents any API calls
- Existing tests fail BEFORE any changes were made (pre-existing issue)
