#!/usr/bin/env python3
"""Parse checkpoint_results.jsonl and print a summary for autoresearch agents.

Usage:
    python3 autoresearch/parse_results.py <output_dir>
    python3 autoresearch/parse_results.py <output_dir> --json  # machine-readable
"""

import json
import os
import sys


def parse_results(outdir: str) -> list[dict]:
    """Parse checkpoint results and return structured records."""
    records = []
    path = os.path.join(outdir, "checkpoint_results.jsonl")
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            total = d.get("total_tests", 0)
            passed = d.get("passed_tests", 0)
            records.append({
                "problem": d["problem"],
                "checkpoint": d["checkpoint"],
                "pass_rate": passed / total if total else 0,
                "core_pass_rate": d.get("core_pass_rate") or 0,
                "erosion": d.get("erosion") or 0,
                "verbosity": d.get("verbosity") or 0,
                "loc": d.get("loc", 0),
                "steps": d.get("steps", 0),
                "step_utilization": d.get("step_utilization") or 0,
                "cost": d.get("cost", 0),
                "regression_passed": d.get("regression_passed", 0),
                "regression_total": d.get("regression_total", 0),
                "churn": d.get("delta.churn_ratio") or 0,
                "lines_added": d.get("lines_added", 0),
                "lines_removed": d.get("lines_removed", 0),
                "import_errors": d.get("import_errors", 0),
                "assertion_errors": d.get("assertion_errors", 0),
                "timeout_errors": d.get("timeout_errors", 0),
                "other_errors": d.get("other_errors", 0),
                "phase_count": d.get("phase_count"),
                "reviewer_cost_fraction": d.get("reviewer_cost_fraction"),
                "reviewer_num_cycles": d.get("reviewer_num_cycles"),
                "reviewer_suggestion_chars": d.get("reviewer_suggestion_chars"),
                "mid_phase_pass_rate_first": d.get("mid_phase_pass_rate_first"),
                "mid_phase_pass_rate_last": d.get("mid_phase_pass_rate_last"),
                "mid_phase_pass_rate_delta": d.get("mid_phase_pass_rate_delta"),
            })
    return records


def compute_summary(records: list[dict]) -> dict:
    """Compute aggregate scores across checkpoints."""
    if not records:
        return {}
    n = len(records)
    return {
        "pass_rate": sum(r["pass_rate"] for r in records) / n,
        "erosion": sum(r["erosion"] for r in records) / n,
        "verbosity": sum(r["verbosity"] for r in records) / n,
        "cost": sum(r["cost"] for r in records),
        "step_utilization_mean": sum(r["step_utilization"] for r in records) / n,
        "mid_phase_pass_rate_delta_mean": sum(
            r["mid_phase_pass_rate_delta"] or 0 for r in records
        ) / n,
        "problems": sorted(set(r["problem"] for r in records)),
    }


def print_human(records: list[dict]) -> None:
    """Print human-readable summary."""
    for r in records:
        pr, cpr = r["pass_rate"], r["core_pass_rate"]
        er, vb = r["erosion"], r["verbosity"]
        print(
            f"{r['problem']}/{r['checkpoint']}: "
            f"pass={pr:.3f} core={cpr:.3f} erosion={er:.3f} verb={vb:.3f} "
            f"loc={r['loc']} steps={r['steps']} util={r['step_utilization']:.2f} "
            f"cost=${r['cost']:.2f}"
        )
        ie, ae = r["import_errors"], r["assertion_errors"]
        te, oe = r["timeout_errors"], r["other_errors"]
        if ie or ae or te or oe:
            print(f"  failures: import={ie} assert={ae} timeout={te} other={oe}")
        if r["regression_total"]:
            print(
                f"  regression: {r['regression_passed']}/{r['regression_total']} "
                f"churn={r['churn']:.3f} +{r['lines_added']}/-{r['lines_removed']}"
            )
        if r["phase_count"] is not None:
            print(
                f"  phases={r['phase_count']} rev_frac={r['reviewer_cost_fraction']} "
                f"rev_cycles={r['reviewer_num_cycles']} "
                f"rev_chars={r['reviewer_suggestion_chars']}"
            )
        if r["mid_phase_pass_rate_first"] is not None:
            print(
                f"  mid_phase: first={r['mid_phase_pass_rate_first']} "
                f"last={r['mid_phase_pass_rate_last']} "
                f"delta={r['mid_phase_pass_rate_delta']}"
            )

    s = compute_summary(records)
    composite = s["pass_rate"] - 0.3 * s["erosion"] - 0.3 * s["verbosity"]
    print(f"\nSUMMARY: composite={composite:.3f} pass={s['pass_rate']:.3f} "
          f"erosion={s['erosion']:.3f} verb={s['verbosity']:.3f} "
          f"cost=${s['cost']:.2f}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 autoresearch/parse_results.py <output_dir> [--json]")
        sys.exit(1)

    outdir = sys.argv[1]
    records = parse_results(outdir)

    if "--json" in sys.argv:
        s = compute_summary(records)
        s["composite"] = s["pass_rate"] - 0.3 * s["erosion"] - 0.3 * s["verbosity"]
        s["checkpoints"] = records
        print(json.dumps(s, indent=2))
    else:
        print_human(records)


if __name__ == "__main__":
    main()
