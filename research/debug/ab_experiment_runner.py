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
import subprocess
import sys
import time

RESULTS_DIR = os.path.join(
    os.path.dirname(__file__), "results"
)
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
    key = os.environ.get("NVIDIA_INFERENCE_KEY", "")
    if not key:
        print("ERROR: NVIDIA_INFERENCE_KEY not set")
        sys.exit(1)
    return key


def start_container() -> str:
    """Start a fresh Docker container and return its ID."""
    result = subprocess.run(
        ["docker", "run", "-d", IMAGE, "sleep", "infinity"],
        capture_output=True, text=True, check=True,
    )
    cid = result.stdout.strip()
    print(f"  Container: {cid[:12]}")
    return cid


def stop_container(cid: str) -> None:
    """Stop and remove a Docker container."""
    subprocess.run(
        ["docker", "rm", "-f", cid],
        capture_output=True, text=True,
    )
    print(f"  Container {cid[:12]} removed")


def run_claude_experiment(
    cid: str,
    env_vars: dict[str, str],
    label: str,
) -> dict:
    """Run Claude CLI inside container and parse step timing."""
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

    steps = []
    start = time.monotonic()
    last_event_time = start
    raw_lines = []

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        # Use timeout
        import threading

        def kill_after_timeout():
            time.sleep(TIMEOUT_SECS)
            if proc.poll() is None:
                proc.kill()

        timer = threading.Thread(
            target=kill_after_timeout, daemon=True,
        )
        timer.start()

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
                    if block.get("type") == "tool_use":
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
                    elif block.get("type") == "text":
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

    except Exception as e:
        total_time = time.monotonic() - start
        timed_out = False
        steps.append({
            "elapsed_s": round(total_time, 1),
            "gap_s": 0,
            "event": f"ERROR: {e}",
            "has_3min_gap": False,
        })

    # Count 3-minute gaps
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

    # Save raw output
    raw_path = os.path.join(
        RESULTS_DIR, f"{label}_raw.jsonl"
    )
    with open(raw_path, "w") as f:
        for rl in raw_lines:
            f.write(rl + "\n")

    return result


def run_test_a(key: str) -> dict:
    """Test A: Baseline (current config)."""
    print("\n=== TEST A: Baseline (AUTH_TOKEN + bg tasks) ===")
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
        "\n=== TEST B: API_KEY (no AUTH_TOKEN, no bg) ==="
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
    print(
        "\n=== TEST D: Baseline + tcpdump ==="
    )
    cid = start_container()
    env = {
        "ANTHROPIC_AUTH_TOKEN": key,
        "ANTHROPIC_BASE_URL": BASE_URL,
        "DISABLE_AUTOUPDATER": "1",
        "DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1",
        "FORCE_AUTO_BACKGROUND_TASKS": "1",
        "ENABLE_BACKGROUND_TASKS": "1",
    }

    # Install tcpdump
    print("  Installing tcpdump...")
    subprocess.run(
        [
            "docker", "exec", "-u", "root", cid,
            "bash", "-c",
            "apt-get update -qq && "
            "apt-get install -y -qq tcpdump >/dev/null 2>&1",
        ],
        capture_output=True, text=True, timeout=120,
    )

    # Start tcpdump capture in background
    print("  Starting tcpdump capture...")
    tcpdump_proc = subprocess.Popen(
        [
            "docker", "exec", "-u", "root", cid,
            "tcpdump", "-i", "any", "-w",
            "/tmp/capture.pcap", "port", "443",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)  # Let tcpdump start

    try:
        result = run_claude_experiment(cid, env, "test_d")

        # Stop tcpdump
        print("  Stopping tcpdump...")
        subprocess.run(
            [
                "docker", "exec", "-u", "root", cid,
                "pkill", "tcpdump",
            ],
            capture_output=True, text=True,
        )
        time.sleep(2)
        tcpdump_proc.terminate()

        # Extract pcap file
        pcap_path = os.path.join(
            RESULTS_DIR, "capture.pcap"
        )
        print(f"  Extracting pcap to {pcap_path}...")
        subprocess.run(
            [
                "docker", "cp",
                f"{cid}:/tmp/capture.pcap",
                pcap_path,
            ],
            capture_output=True, text=True,
        )

        # Analyze pcap with tcpdump
        analysis_path = os.path.join(
            RESULTS_DIR, "network_analysis.txt"
        )
        print("  Analyzing pcap...")
        analysis = subprocess.run(
            [
                "docker", "exec", "-u", "root", cid,
                "tcpdump", "-r", "/tmp/capture.pcap",
                "-n", "-q",
            ],
            capture_output=True, text=True, timeout=30,
        )
        with open(analysis_path, "w") as f:
            f.write(
                "# Network Analysis - tcpdump output\n"
                f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"# Container: {cid[:12]}\n\n"
            )
            lines = analysis.stdout.strip().split("\n")
            f.write(f"Total packets captured: {len(lines)}\n\n")
            f.write("First 100 packets:\n")
            for pline in lines[:100]:
                f.write(pline + "\n")
            if len(lines) > 100:
                f.write(f"\n... ({len(lines) - 100} more packets)\n")

            # Summary stats
            f.write("\n\n# Connection Summary\n")
            # Count unique destination IPs
            ips = set()
            for pline in lines:
                parts = pline.split()
                for part in parts:
                    if "." in part and part.count(".") >= 3:
                        # Might be an IP
                        ip_candidate = part.split(":")[0].rstrip(".")
                        if all(
                            c.isdigit() or c == "."
                            for c in ip_candidate
                        ):
                            ips.add(ip_candidate)
            f.write(f"Unique IPs seen: {len(ips)}\n")
            for ip in sorted(ips):
                f.write(f"  {ip}\n")

        print(
            f"  Network analysis saved to "
            f"{analysis_path}"
        )
        result["pcap_packets"] = len(lines)
        result["unique_ips"] = len(ips)

        return result
    finally:
        stop_container(cid)


def generate_report(results: list[dict]) -> str:
    """Generate markdown comparison report."""
    report = []
    report.append(
        "# A/B Test Results: Claude CLI Latency Investigation"
    )
    report.append("")
    report.append(
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    report.append(
        f"**Image:** {IMAGE}"
    )
    report.append(f"**Model:** {MODEL}")
    report.append(f"**Max turns:** {MAX_TURNS}")
    report.append(
        f"**Timeout per test:** {TIMEOUT_SECS}s "
        f"(15 min)"
    )
    report.append("")
    report.append("## Task")
    report.append("")
    report.append(f"> {TASK}")
    report.append("")

    # Comparison table
    report.append("## Comparison Table")
    report.append("")
    report.append(
        "| Test | Auth Method | Bg Tasks | "
        "Total Time | Steps | 3min Gaps | Timed Out |"
    )
    report.append(
        "|------|-----------|----------|"
        "------------|-------|-----------|-----------|"
    )

    for r in results:
        label = r["label"].upper().replace("_", " ")
        env = r["env_vars"]

        if "ANTHROPIC_API_KEY" in env:
            auth = "API_KEY"
        else:
            auth = "AUTH_TOKEN"

        bg = "Yes" if (
            "FORCE_AUTO_BACKGROUND_TASKS" in env
        ) else "No"

        total = f"{r['total_time_s']:.0f}s"
        steps = str(r["num_steps"])
        gaps = str(r["gaps_over_2min"])
        timeout = "Yes" if r["timed_out"] else "No"

        report.append(
            f"| {label} | {auth} | {bg} | "
            f"{total} | {steps} | {gaps} | {timeout} |"
        )

    report.append("")

    # Detailed results for each test
    for r in results:
        label = r["label"].upper().replace("_", " ")
        report.append(f"## {label}")
        report.append("")
        report.append("**Environment Variables:**")
        report.append("")
        for k, v in r["env_vars"].items():
            report.append(f"- `{k}={v}`")
        report.append("")
        report.append(
            f"**Total time:** {r['total_time_s']:.1f}s"
        )
        report.append(f"**Steps:** {r['num_steps']}")
        report.append(
            f"**Gaps >2min:** {r['gaps_over_2min']}"
        )
        report.append(
            f"**Timed out:** "
            f"{'Yes' if r['timed_out'] else 'No'}"
        )

        if r.get("pcap_packets"):
            report.append(
                f"**Pcap packets:** {r['pcap_packets']}"
            )
        if r.get("unique_ips"):
            report.append(
                f"**Unique IPs:** {r['unique_ips']}"
            )

        report.append("")
        report.append("**Step-by-step timing:**")
        report.append("")
        report.append(
            "| Elapsed | Gap | Event |"
        )
        report.append(
            "|---------|-----|-------|"
        )
        for step in r["steps"]:
            elapsed = f"{step['elapsed_s']:.1f}s"
            gap = f"{step['gap_s']:.1f}s"
            event = step["event"][:80]
            flag = " **⚠️**" if step["has_3min_gap"] else ""
            report.append(
                f"| {elapsed} | {gap}{flag} | {event} |"
            )
        report.append("")

    # Analysis section
    report.append("## Analysis")
    report.append("")

    # Check if we have enough data to draw conclusions
    completed = [
        r for r in results if not r["timed_out"]
    ]
    if len(completed) < 2:
        report.append(
            "Insufficient data for comparison "
            "(too many tests timed out)."
        )
    else:
        # Compare Test A vs Test B
        # (AUTH_TOKEN vs API_KEY)
        a_results = [
            r for r in results
            if r["label"] == "test_a"
        ]
        b_results = [
            r for r in results
            if r["label"] == "test_b"
        ]
        c_results = [
            r for r in results
            if r["label"] == "test_c"
        ]

        if a_results and b_results:
            a = a_results[0]
            b = b_results[0]
            report.append(
                "### AUTH_TOKEN vs API_KEY "
                "(Test A vs Test B)"
            )
            report.append("")
            if a["gaps_over_2min"] > 0 and b["gaps_over_2min"] == 0:
                report.append(
                    "**Finding:** AUTH_TOKEN shows "
                    f"{a['gaps_over_2min']} gaps >2min "
                    "while API_KEY shows none. "
                    "This confirms the AUTH_TOKEN code "
                    "path triggers the delay."
                )
            elif (
                a["gaps_over_2min"] > 0
                and b["gaps_over_2min"] > 0
            ):
                report.append(
                    "**Finding:** Both AUTH_TOKEN and "
                    "API_KEY show gaps >2min "
                    f"({a['gaps_over_2min']} vs "
                    f"{b['gaps_over_2min']}). "
                    "The auth method alone does not "
                    "explain the delay."
                )
            elif (
                a["gaps_over_2min"] == 0
                and b["gaps_over_2min"] == 0
            ):
                report.append(
                    "**Finding:** Neither test showed "
                    "gaps >2min. Compare total times: "
                    f"A={a['total_time_s']:.0f}s vs "
                    f"B={b['total_time_s']:.0f}s."
                )
            else:
                report.append(
                    f"**Finding:** A gaps="
                    f"{a['gaps_over_2min']}, "
                    f"B gaps={b['gaps_over_2min']}. "
                    f"A time={a['total_time_s']:.0f}s, "
                    f"B time={b['total_time_s']:.0f}s."
                )
            report.append("")

        if a_results and c_results:
            a = a_results[0]
            c = c_results[0]
            report.append(
                "### Background Tasks Effect "
                "(Test A vs Test C)"
            )
            report.append("")
            if (
                a["gaps_over_2min"] > 0
                and c["gaps_over_2min"] == 0
            ):
                report.append(
                    "**Finding:** Enabling "
                    "FORCE_AUTO_BACKGROUND_TASKS/"
                    "ENABLE_BACKGROUND_TASKS causes "
                    f"{a['gaps_over_2min']} gaps >2min. "
                    "Disabling them eliminates gaps. "
                    "Background tasks are the root cause."
                )
            elif (
                a["gaps_over_2min"] > 0
                and c["gaps_over_2min"] > 0
            ):
                report.append(
                    "**Finding:** Both configs show "
                    "gaps >2min. Background task env "
                    "vars do not explain the delay."
                )
            else:
                report.append(
                    f"**Finding:** A gaps="
                    f"{a['gaps_over_2min']}, "
                    f"C gaps={c['gaps_over_2min']}. "
                    f"A time={a['total_time_s']:.0f}s, "
                    f"C time={c['total_time_s']:.0f}s."
                )
            report.append("")

    report.append("## Conclusion")
    report.append("")
    report.append(
        "See the comparison table and per-test "
        "timing above for detailed results. "
        "The combination of AUTH_TOKEN vs API_KEY "
        "and background task configuration isolates "
        "which factor causes the 3-minute delays."
    )
    report.append("")

    return "\n".join(report)


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    key = get_nvidia_key()
    results = []

    print(
        f"Starting A/B experiments at "
        f"{time.strftime('%H:%M:%S')}"
    )
    print(f"Results dir: {RESULTS_DIR}")
    print(f"Timeout per test: {TIMEOUT_SECS}s")

    # Test A: Baseline
    try:
        results.append(run_test_a(key))
    except Exception as e:
        print(f"  TEST A FAILED: {e}")
        results.append({
            "label": "test_a",
            "env_vars": {"error": str(e)},
            "total_time_s": 0,
            "timed_out": False,
            "num_steps": 0,
            "gaps_over_2min": 0,
            "steps": [{"elapsed_s": 0, "gap_s": 0, "event": f"ERROR: {e}", "has_3min_gap": False}],
        })

    # Test B: API_KEY
    try:
        results.append(run_test_b(key))
    except Exception as e:
        print(f"  TEST B FAILED: {e}")
        results.append({
            "label": "test_b",
            "env_vars": {"error": str(e)},
            "total_time_s": 0,
            "timed_out": False,
            "num_steps": 0,
            "gaps_over_2min": 0,
            "steps": [{"elapsed_s": 0, "gap_s": 0, "event": f"ERROR: {e}", "has_3min_gap": False}],
        })

    # Test C: No bg tasks
    try:
        results.append(run_test_c(key))
    except Exception as e:
        print(f"  TEST C FAILED: {e}")
        results.append({
            "label": "test_c",
            "env_vars": {"error": str(e)},
            "total_time_s": 0,
            "timed_out": False,
            "num_steps": 0,
            "gaps_over_2min": 0,
            "steps": [{"elapsed_s": 0, "gap_s": 0, "event": f"ERROR: {e}", "has_3min_gap": False}],
        })

    # Test D: Baseline + tcpdump
    try:
        results.append(run_test_d(key))
    except Exception as e:
        print(f"  TEST D FAILED: {e}")
        results.append({
            "label": "test_d",
            "env_vars": {"error": str(e)},
            "total_time_s": 0,
            "timed_out": False,
            "num_steps": 0,
            "gaps_over_2min": 0,
            "steps": [{"elapsed_s": 0, "gap_s": 0, "event": f"ERROR: {e}", "has_3min_gap": False}],
        })

    # Generate and save report
    report = generate_report(results)
    report_path = os.path.join(
        RESULTS_DIR, "ab_test_results.md"
    )
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport saved to {report_path}")

    # Save raw JSON results
    json_path = os.path.join(
        RESULTS_DIR, "ab_test_results.json"
    )
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"JSON results saved to {json_path}")

    print("\n=== All experiments complete ===")


if __name__ == "__main__":
    main()
