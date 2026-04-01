# A/B Test Results: Claude CLI Latency Investigation

**Date:** 2026-04-01 22:11:15
**Image:** slop-code:claude_code-2.0.51-python3.12
**Model:** aws/anthropic/bedrock-claude-sonnet-4-6
**Max turns:** 8
**Timeout per test:** 900s (15 min)

## Task

> Create hello.py that prints hello world, create a venv, run it, then modify it to also print the current date, run again.

## Comparison Table

| Test | Auth Method | Bg Tasks | Total Time | Steps | Gaps >2min | Notes |
|------|-----------|----------|------------|-------|------------|-------|
| TEST A | AUTH_TOKEN | Yes | 58s | 4 | 0 | Only 4 steps; agent stopped early |
| TEST B | API_KEY | No | 442s | 8 | 2 | 219s gap after first Bash, 184s gap at end |
| TEST C | AUTH_TOKEN | No | 400s | 8 | 2 | 200s gap after first Bash, 179s gap at end |
| TEST D | AUTH_TOKEN | Yes | 455s | 8 | 2 | 190s + 227s gaps; pcap captured |

## Important Note on Test A

Test A completed with only 4 steps (the agent chose to stop early). Because it
never reached the point where the ~3-minute gaps typically appear (which is AFTER
the first Bash tool execution), Test A cannot be used as a valid baseline
comparison. Tests B, C, and D all reached 8 turns and all showed the same gap
pattern.

## TEST A — Baseline (AUTH_TOKEN + bg tasks)

**Environment Variables:**

- `ANTHROPIC_AUTH_TOKEN=***`
- `ANTHROPIC_BASE_URL=https://inference-api.nvidia.com`
- `DISABLE_AUTOUPDATER=1`
- `DISABLE_NON_ESSENTIAL_MODEL_CALLS=1`
- `FORCE_AUTO_BACKGROUND_TASKS=1`
- `ENABLE_BACKGROUND_TASKS=1`

**Total time:** 58.2s | **Steps:** 4 | **Gaps >2min:** 0

| Elapsed | Gap | Event |
|---------|-----|-------|
| 5.5s | 5.5s | TOOL: TodoWrite |
| 8.6s | 3.1s | TOOL: Write |
| 15.2s | 6.6s | TOOL: TodoWrite |
| 18.8s | 3.6s | TOOL: Bash |

**Verdict:** Invalid for comparison — too few steps to trigger the gap.

## TEST B — API_KEY (no AUTH_TOKEN, no bg tasks)

**Environment Variables:**

- `ANTHROPIC_API_KEY=***`
- `ANTHROPIC_BASE_URL=https://inference-api.nvidia.com`
- `DISABLE_AUTOUPDATER=1`
- `DISABLE_NON_ESSENTIAL_MODEL_CALLS=1`

**Total time:** 441.5s | **Steps:** 8 | **Gaps >2min:** 2

| Elapsed | Gap | Event |
|---------|-----|-------|
| 6.3s | 6.3s | TOOL: TodoWrite |
| 17.6s | 11.3s | TOOL: TodoWrite |
| 21.0s | 3.3s | TOOL: Write |
| 23.8s | 2.8s | TOOL: TodoWrite |
| 26.7s | 2.9s | TOOL: Bash |
| 245.8s | 219.1s **⚠️** | TOOL: TodoWrite |
| 257.8s | 12.0s | TOOL: Bash |
| 441.5s | 183.6s **⚠️** | RESULT: turns=8 cost=$0.0473 |

**Verdict:** Same gap pattern as AUTH_TOKEN tests. API_KEY does NOT eliminate the delay.

## TEST C — AUTH_TOKEN (no bg tasks)

**Environment Variables:**

- `ANTHROPIC_AUTH_TOKEN=***`
- `ANTHROPIC_BASE_URL=https://inference-api.nvidia.com`
- `DISABLE_AUTOUPDATER=1`
- `DISABLE_NON_ESSENTIAL_MODEL_CALLS=1`

**Total time:** 400.0s | **Steps:** 8 | **Gaps >2min:** 2

| Elapsed | Gap | Event |
|---------|-----|-------|
| 5.6s | 5.6s | TOOL: TodoWrite |
| 9.4s | 3.8s | TOOL: Write |
| 13.3s | 3.9s | TOOL: TodoWrite |
| 16.7s | 3.4s | TOOL: Bash |
| 217.1s | 200.4s **⚠️** | TOOL: TodoWrite |
| 220.7s | 3.5s | TOOL: Bash |
| 399.9s | 179.2s **⚠️** | TOOL: TodoWrite |
| 399.9s | 0.0s | RESULT: turns=8 cost=$0.0554 |

**Verdict:** Gaps present without FORCE_AUTO_BACKGROUND_TASKS/ENABLE_BACKGROUND_TASKS. Background task env vars are not the cause.

## TEST D — Baseline + tcpdump

**Environment Variables:**

- `ANTHROPIC_AUTH_TOKEN=***`
- `ANTHROPIC_BASE_URL=https://inference-api.nvidia.com`
- `DISABLE_AUTOUPDATER=1`
- `DISABLE_NON_ESSENTIAL_MODEL_CALLS=1`
- `FORCE_AUTO_BACKGROUND_TASKS=1`
- `ENABLE_BACKGROUND_TASKS=1`

**Total time:** 455.1s | **Steps:** 8 | **Gaps >2min:** 2
**Pcap packets:** 3883

| Elapsed | Gap | Event |
|---------|-----|-------|
| 6.5s | 6.5s | TOOL: TodoWrite |
| 8.7s | 2.3s | TOOL: Write |
| 15.7s | 6.9s | TOOL: TodoWrite |
| 35.6s | 20.0s | TOOL: Bash |
| 225.3s | 189.6s **⚠️** | TOOL: TodoWrite |
| 227.6s | 2.3s | TOOL: Bash |
| 455.0s | 227.4s **⚠️** | TOOL: TodoWrite |
| 455.0s | 0.0s | RESULT: turns=8 cost=$0.0552 |

### Network Analysis (from pcap)

**Remote endpoints contacted:**

| IP | Location | Packets | Role |
|----|----------|---------|------|
| 34.36.57.103 | GCP (Google) | 1115 | NVIDIA inference gateway |
| 16.146.192.132 | AWS us-west-2 | 316 | Bedrock backend |
| 52.39.201.119 | AWS us-west-2 | 226 | Bedrock streaming |
| 35.165.251.166 | AWS us-west-2 | 70 | Bedrock streaming |
| 3.233.158.* (5 IPs) | AWS us-east-1 | 75 | Anthropic auth/telemetry |

**Traffic during Gap 1 (22:04:14 to 22:07:24, 190s):**
- 1695 packets total — network is NOT idle during the gap
- Steady 30-65 packets per 10-second window to NVIDIA and AWS
- Occasional small exchanges with Anthropic us-east-1 (3.233.158.*)
- Gap ends with large burst (321+438 packets) when inference response arrives

**Traffic during Gap 2 (22:07:26 to 22:11:12, 227s):**
- 847 packets total — similar pattern of periodic low-volume exchanges
- 20-50 packets per 10-second window
- Gap ends with 253+94 packet burst

## Analysis

### Hypothesis: AUTH_TOKEN vs API_KEY causes the delay

**REFUTED.** Test B (API_KEY, no AUTH_TOKEN) shows the same ~200s gaps as Tests C
and D (AUTH_TOKEN). The gap appeared after the first Bash tool use in all three
tests that completed 8 turns. The auth method has no measurable effect on the
delay.

| | Test B (API_KEY) | Test C (AUTH_TOKEN) | Test D (AUTH_TOKEN) |
|---|---|---|---|
| Gap 1 | 219.1s | 200.4s | 189.6s |
| Gap 2 | 183.6s | 179.2s | 227.4s |

### Hypothesis: Background task env vars cause the delay

**REFUTED.** Test C (without FORCE_AUTO_BACKGROUND_TASKS and
ENABLE_BACKGROUND_TASKS) shows the same gaps as Test D (with both enabled).
The gap sizes are comparable (200s vs 190s for gap 1, 179s vs 227s for gap 2).

### Hypothesis: Claude CLI makes hidden API calls during gaps

**PARTIALLY REFUTED.** The pcap data shows the CLI does contact Anthropic
infrastructure (3.233.158.* in us-east-1) sporadically, but these are small
exchanges (12-26 packets per IP total). The dominant traffic during gaps is
with NVIDIA's GCP gateway (34.36.57.103) and AWS Bedrock endpoints, indicating
the CLI is waiting for an inference response, not making hidden calls.

### Root cause: Server-side queuing at NVIDIA/Bedrock

The network data strongly suggests the delay is server-side:

1. Network traffic continues during gaps (not blocked/idle)
2. Traffic flows to the same NVIDIA gateway used for inference
3. Gaps end with large response bursts (consistent with queued inference completing)
4. Gap duration is consistent (~190-220s) regardless of client-side config
5. All client-side variable changes (auth method, background tasks) had no effect

The ~3-minute delay is consistent with NVIDIA's inference proxy queuing requests
when the backend (AWS Bedrock) is under load. The request sits in queue for
~180-220s before the Bedrock instance processes it and streams the response back.

## Conclusion

The 3-minute gaps are caused by **server-side queuing at the NVIDIA inference
proxy or AWS Bedrock layer**, not by the Claude CLI's local behavior. Neither
the auth method (ANTHROPIC_AUTH_TOKEN vs ANTHROPIC_API_KEY) nor the background
task configuration has any effect on the delay. The network capture confirms
that during gaps, the CLI maintains an active HTTPS connection to NVIDIA's
gateway and is simply waiting for a response. The fix must be server-side
(higher throughput, dedicated capacity) or by switching to a direct Anthropic
API endpoint that avoids the NVIDIA proxy.
