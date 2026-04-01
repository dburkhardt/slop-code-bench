# ruff: noqa: S607
#!/usr/bin/env python3
"""A/B experiment runner for Claude CLI latency investigation.

Runs 4 targeted experiments to isolate the root cause of ~3-minute
delays between Bash tool-use steps. Each experiment uses a different
environment variable configuration.

Usage:
    python3 research/debug/ab_experiment_runner.py

Results are saved to research/debug/results/.
"""
from __future__ import annotations

import json
import os
import subprocess  # noqa: S404
import sys
import time
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
IMAGE = "slop-code:claude_code-2.0.51-python3.12"
MODEL = "aws/anthropic/bedrock-claude-sonnet-4-6"
BASE_URL = "https://inference-api.nvidia.com"
TASK = (
    "Create hello.py that prints hello world, create a venv, "
    "run it, then modify it to also print the current date, "
    "run again."
)
MAX_TURNS = 8
TIMEOUT_SECS = 900  # 15 minutes per test


def get_nvidia_key() -> str:
    """Read and validate NVIDIA_INFERENCE_KEY."""
    key = os.environ.get("NVIDIA_INFERENCE_KEY", "")
    if not key:
        print("ERROR: NVIDIA_INFERENCE_KEY not set")
        sys.exit(1)
    return key


def start_container() -> str:
    """Start a fresh Docker container and return its ID."""
    result = subprocess.run(  # noqa: S603, S607
        ["docker", "run", "-d", IMAGE, "sleep", "infinity"],
        capture_output=True, text=True, check=True,
    )
    cid = result.stdout.strip()
    print(f"  Container: {cid[:12]}")
    return cid


def stop_container(cid: str) -> None:
    """Stop and remove a Docker container."""
    subprocess.run(  # noqa: S603, S607
        ["docker", "rm", "-f", cid],
        capture_output=True, text=True,
    )
    print(f"  Container {cid[:12]} removed")


def run_claude_experiment(
    cid: str,
    env_vars: dict[str, str],
    label: str,
) -> dict:
    """Run Claude CLI inside container and parse timing."""
    cmd = ["docker", "exec"]
    for k, v in env_vars.items():
        cmd.extend(["--env", f"{k}={v}"])
    cmd.extend([
        cid,
        "claude",
        "--output-format", "stream-json",
        "--verbose",
        "--model", MODEL,
        "--max-turns", str(MAX_TURNS),
        "--permission-mode", "bypassPermissions",
        "--print", "--",
        TASK,
    ])

    steps: list[dict] = []
    start = time.monotonic()
    last_event_time = start
    raw_lines: list[str] = []

    try:
        proc = subprocess.Popen(  # noqa: S603
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        import threading

        def kill_after_timeout() -> None:
            time.sleep(TIMEOUT_SECS)
            if proc.poll() is None:
                proc.kill()

        timer = threading.Thread(
            target=kill_after_timeout, daemon=True,
        )
        timer.start()

        assert proc.stdout is not None  # noqa: S101
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            now = time.monotonic()
            elapsed = now - start
            gap = now - last_event_time

            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue

            raw_lines.append(line)
            evt_type = d.get("type", "")

            if evt_type == "assistant":
                msg = d.get("message", {})
                for block in msg.get("content", []):
                    btype = block.get("type")
                    if btype == "tool_use":
                        tool_name = block.get("name", "?")
                        step_info = {
                            "elapsed_s": round(elapsed, 1),
                            "gap_s": round(gap, 1),
                            "event": f"TOOL: {tool_name}",
                            "has_3min_gap": gap > 120,
                        }
                        steps.append(step_info)
                        print(
                            f"  [{elapsed:7.1f}s] "
                            f"(gap={gap:6.1f}s) "
                            f"TOOL: {tool_name}"
                        )
                        last_event_time = now
                    elif btype == "text":
                        text = block.get("text", "")[:60]
                        step_info = {
                            "elapsed_s": round(elapsed, 1),
                            "gap_s": round(gap, 1),
                            "event": f"TEXT: {text}",
                            "has_3min_gap": gap > 120,
                        }
                        steps.append(step_info)
                        print(
                            f"  [{elapsed:7.1f}s] "
                            f"(gap={gap:6.1f}s) "
                            f"TEXT: {text}"
                        )
                        last_event_time = now
            elif evt_type == "result":
                cost = d.get("total_cost_usd", 0)
                turns = d.get("num_turns", 0)
                step_info = {
                    "elapsed_s": round(elapsed, 1),
                    "gap_s": round(gap, 1),
                    "event": (
                        f"RESULT: turns={turns} "
                        f"cost=${cost:.4f}"
                    ),
                    "has_3min_gap": gap > 120,
                }
                steps.append(step_info)
                print(
                    f"  [{elapsed:7.1f}s] "
                    f"RESULT: turns={turns} "
                    f"cost=${cost:.4f}"
                )
                last_event_time = now

        proc.wait()
        total_time = time.monotonic() - start
        timed_out = proc.returncode == -9

    except (OSError, ValueError, subprocess.SubprocessError) as e:
        total_time = time.monotonic() - start
        timed_out = False
        steps.append({
            "elapsed_s": round(total_time, 1),
            "gap_s": 0,
            "event": f"ERROR: {e}",
            "has_3min_gap": False,
        })

    gaps_over_2min = sum(
        1 for s in steps if s.get("has_3min_gap")
    )

    result = {
        "label": label,
        "env_vars": {
            k: ("***" if "KEY" in k or "TOKEN" in k else v)
            for k, v in env_vars.items()
        },
        "total_time_s": round(total_time, 1),
        "timed_out": timed_out,
        "num_steps": len(steps),
        "gaps_over_2min": gaps_over_2min,
        "steps": steps,
    }

    raw_path = RESULTS_DIR / f"{label}_raw.jsonl"
    raw_path.write_text(
        "\n".join(raw_lines) + "\n"
    )

    return result


def run_test_a(key: str) -> dict:
    """Test A: Baseline (current config)."""
    print("\n=== TEST A: Baseline (AUTH_TOKEN + bg) ===")
    cid = start_container()
    env = {
        "ANTHROPIC_AUTH_TOKEN": key,
        "ANTHROPIC_BASE_URL": BASE_URL,
        "DISABLE_AUTOUPDATER": "1",
        "DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1",
        "FORCE_AUTO_BACKGROUND_TASKS": "1",
        "ENABLE_BACKGROUND_TASKS": "1",
    }
    try:
        return run_claude_experiment(cid, env, "test_a")
    finally:
        stop_container(cid)


def run_test_b(key: str) -> dict:
    """Test B: API_KEY instead of AUTH_TOKEN."""
    print(
        "\n=== TEST B: API_KEY (no AUTH_TOKEN) ==="
    )
    cid = start_container()
    env = {
        "ANTHROPIC_API_KEY": key,
        "ANTHROPIC_BASE_URL": BASE_URL,
        "DISABLE_AUTOUPDATER": "1",
        "DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1",
    }
    try:
        return run_claude_experiment(cid, env, "test_b")
    finally:
        stop_container(cid)


def run_test_c(key: str) -> dict:
    """Test C: AUTH_TOKEN but no background tasks."""
    print(
        "\n=== TEST C: AUTH_TOKEN (no bg tasks) ==="
    )
    cid = start_container()
    env = {
        "ANTHROPIC_AUTH_TOKEN": key,
        "ANTHROPIC_BASE_URL": BASE_URL,
        "DISABLE_AUTOUPDATER": "1",
        "DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1",
    }
    try:
        return run_claude_experiment(cid, env, "test_c")
    finally:
        stop_container(cid)


def run_test_d(key: str) -> dict:
    """Test D: Baseline + tcpdump capture."""
    print("\n=== TEST D: Baseline + tcpdump ===")
    cid = start_container()
    env = {
        "ANTHROPIC_AUTH_TOKEN": key,
        "ANTHROPIC_BASE_URL": BASE_URL,
        "DISABLE_AUTOUPDATER": "1",
        "DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1",
        "FORCE_AUTO_BACKGROUND_TASKS": "1",
        "ENABLE_BACKGROUND_TASKS": "1",
    }

    print("  Installing tcpdump...")
    subprocess.run(  # noqa: S603, S607
        [
            "docker", "exec", "-u", "root", cid,
            "bash", "-c",
            "apt-get update -qq && "
            "apt-get install -y -qq tcpdump "
            ">/dev/null 2>&1",
        ],
        capture_output=True, text=True, timeout=120,
    )

    print("  Starting tcpdump capture...")
    pcap_container = "/tmp/capture.pcap"  # noqa: S108
    tcpdump_proc = subprocess.Popen(  # noqa: S603, S607
        [
            "docker", "exec", "-u", "root", cid,
            "tcpdump", "-i", "any", "-w",
            pcap_container, "port", "443",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)

    try:
        result = run_claude_experiment(
            cid, env, "test_d"
        )

        print("  Stopping tcpdump...")
        subprocess.run(  # noqa: S603, S607
            [
                "docker", "exec", "-u", "root", cid,
                "pkill", "tcpdump",
            ],
            capture_output=True, text=True,
        )
        time.sleep(2)
        tcpdump_proc.terminate()

        pcap_path = RESULTS_DIR / "capture.pcap"
        print(f"  Extracting pcap to {pcap_path}...")
        subprocess.run(  # noqa: S603, S607
            [
                "docker", "cp",
                f"{cid}:{pcap_container}",
                str(pcap_path),
            ],
            capture_output=True, text=True,
        )

        analysis_path = (
            RESULTS_DIR / "network_analysis.txt"
        )
        print("  Analyzing pcap...")
        analysis = subprocess.run(  # noqa: S603, S607
            [
                "docker", "exec", "-u", "root", cid,
                "tcpdump", "-r", pcap_container,
                "-n", "-q",
            ],
            capture_output=True, text=True, timeout=30,
        )
        lines = analysis.stdout.strip().split("\n")
        ips: set[str] = set()
        for pline in lines:
            parts = pline.split()
            for part in parts:
                if (
                    "." in part
                    and part.count(".") >= 3
                ):
                    ip_candidate = (
                        part.split(":")[0].rstrip(".")
                    )
                    if all(
                        c.isdigit() or c == "."
                        for c in ip_candidate
                    ):
                        ips.add(ip_candidate)

        out_lines = [
            "# Network Analysis - tcpdump output",
            f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Container: {cid[:12]}",
            "",
            f"Total packets captured: {len(lines)}",
            "",
            "First 100 packets:",
        ]
        out_lines.extend(lines[:100])
        if len(lines) > 100:
            extra = len(lines) - 100
            out_lines.append(f"\n... ({extra} more)")
        out_lines.append("\n\n# Connection Summary")
        out_lines.append(f"Unique IPs seen: {len(ips)}")
        for ip in sorted(ips):
            out_lines.append(f"  {ip}")

        analysis_path.write_text(
            "\n".join(out_lines) + "\n"
        )
        print(
            f"  Network analysis saved: {analysis_path}"
        )
        result["pcap_packets"] = len(lines)
        result["unique_ips"] = len(ips)

        return result
    finally:
        stop_container(cid)


def generate_report(results: list[dict]) -> str:
    """Generate markdown comparison report."""
    r = []
    r.append(
        "# A/B Test Results: "
        "Claude CLI Latency Investigation"
    )
    r.append("")
    r.append(
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    r.append(f"**Image:** {IMAGE}")
    r.append(f"**Model:** {MODEL}")
    r.append(f"**Max turns:** {MAX_TURNS}")
    r.append(f"**Timeout per test:** {TIMEOUT_SECS}s")
    r.append("")
    r.append("## Task")
    r.append("")
    r.append(f"> {TASK}")
    r.append("")
    r.append("## Comparison Table")
    r.append("")
    r.append(
        "| Test | Auth Method | Bg Tasks | "
        "Total Time | Steps | 3min Gaps | Timed Out |"
    )
    r.append(
        "|------|-----------|----------|"
        "------------|-------|-----------|-----------|"
    )

    for res in results:
        label = res["label"].upper().replace("_", " ")
        env = res["env_vars"]
        auth = (
            "API_KEY"
            if "ANTHROPIC_API_KEY" in env
            else "AUTH_TOKEN"
        )
        bg = (
            "Yes"
            if "FORCE_AUTO_BACKGROUND_TASKS" in env
            else "No"
        )
        total = f"{res['total_time_s']:.0f}s"
        steps = str(res["num_steps"])
        gaps = str(res["gaps_over_2min"])
        to = "Yes" if res["timed_out"] else "No"
        r.append(
            f"| {label} | {auth} | {bg} | "
            f"{total} | {steps} | {gaps} | {to} |"
        )

    r.append("")

    for res in results:
        label = res["label"].upper().replace("_", " ")
        r.append(f"## {label}")
        r.append("")
        r.append("**Environment Variables:**")
        r.append("")
        for k, v in res["env_vars"].items():
            r.append(f"- `{k}={v}`")
        r.append("")
        r.append(
            f"**Total time:** {res['total_time_s']:.1f}s"
        )
        r.append(f"**Steps:** {res['num_steps']}")
        r.append(
            f"**Gaps >2min:** {res['gaps_over_2min']}"
        )
        timed = "Yes" if res["timed_out"] else "No"
        r.append(f"**Timed out:** {timed}")

        if res.get("pcap_packets"):
            r.append(
                f"**Pcap packets:** "
                f"{res['pcap_packets']}"
            )

        r.append("")
        r.append("**Step-by-step timing:**")
        r.append("")
        r.append("| Elapsed | Gap | Event |")
        r.append("|---------|-----|-------|")
        for step in res["steps"]:
            elapsed = f"{step['elapsed_s']:.1f}s"
            gap = f"{step['gap_s']:.1f}s"
            event = step["event"][:80]
            flag = (
                " **warn**"
                if step["has_3min_gap"]
                else ""
            )
            r.append(
                f"| {elapsed} | {gap}{flag} | "
                f"{event} |"
            )
        r.append("")

    r.append("## Conclusion")
    r.append("")
    r.append(
        "See the comparison table and per-test "
        "timing above for detailed results."
    )
    r.append("")

    return "\n".join(r)


def _make_error_result(
    label: str, error: str,
) -> dict:
    return {
        "label": label,
        "env_vars": {"error": error},
        "total_time_s": 0,
        "timed_out": False,
        "num_steps": 0,
        "gaps_over_2min": 0,
        "steps": [{
            "elapsed_s": 0,
            "gap_s": 0,
            "event": f"ERROR: {error}",
            "has_3min_gap": False,
        }],
    }


def main() -> None:
    """Run all A/B experiments."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    key = get_nvidia_key()
    results: list[dict] = []

    print(
        f"Starting A/B experiments at "
        f"{time.strftime('%H:%M:%S')}"
    )
    print(f"Results dir: {RESULTS_DIR}")
    print(f"Timeout per test: {TIMEOUT_SECS}s")

    for test_fn, label in [
        (run_test_a, "test_a"),
        (run_test_b, "test_b"),
        (run_test_c, "test_c"),
        (run_test_d, "test_d"),
    ]:
        try:
            results.append(test_fn(key))
        except (
            OSError, ValueError,
            subprocess.SubprocessError,
        ) as e:
            print(f"  {label.upper()} FAILED: {e}")
            results.append(
                _make_error_result(label, str(e))
            )

    report = generate_report(results)
    report_path = RESULTS_DIR / "ab_test_results.md"
    report_path.write_text(report)
    print(f"\nReport saved to {report_path}")

    json_path = RESULTS_DIR / "ab_test_results.json"
    json_path.write_text(
        json.dumps(results, indent=2) + "\n"
    )
    print(f"JSON results saved to {json_path}")
    print("\n=== All experiments complete ===")


if __name__ == "__main__":
    main()
