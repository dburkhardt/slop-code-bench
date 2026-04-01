#!/usr/bin/env python3
"""Generate FINAL_REPORT.md from analysis results.

Queries the Dolt experiments table, computes all metrics,
and writes a structured report with all 9 required sections.
All data comes from validated experiments only
(manipulation_check='passed' AND results_valid=true).

Usage::

    python -m research.analysis.generate_report
    # or
    python research/analysis/generate_report.py \\
        --output research/analysis/FINAL_REPORT.md
"""

from __future__ import annotations

import logging
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import typer

from research.analysis.compute_metrics import AnalysisSummary
from research.analysis.compute_metrics import BudgetEfficiency
from research.analysis.compute_metrics import ModeComparison
from research.analysis.compute_metrics import compute_full_analysis
from research.analysis.compute_metrics import identify_sweet_spots
from research.analysis.query_experiments import LOW_N_THRESHOLD
from research.analysis.query_experiments import ExclusionCounts
from research.analysis.query_experiments import PerProblemRow
from research.analysis.query_experiments import get_connection
from research.analysis.query_experiments import query_budget_efficiency
from research.analysis.query_experiments import query_erosion_comparison
from research.analysis.query_experiments import query_exclusion_counts
from research.analysis.query_experiments import query_pass_rate_delta
from research.analysis.query_experiments import query_per_problem_breakdown
from research.analysis.query_experiments import query_verbosity_comparison

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO_ROOT / "research" / "analysis" / "FINAL_REPORT.md"
)

DOLT_HOST = "127.0.0.1"
DOLT_PORT = 3307


# ── Report section builders ─────────────────────────


def _prelim_badge(*, is_preliminary: bool) -> str:
    """Return a preliminary warning badge if needed."""
    if is_preliminary:
        return (
            " ⚠️ **PRELIMINARY** "
            f"(N < {LOW_N_THRESHOLD})"
        )
    return ""


def _mode_stat_row(mc: ModeComparison | None) -> str:
    """Format a mode comparison as a table row."""
    if mc is None:
        return "| — | — | — | — | — |"
    prelim = " ⚠️" if mc.is_preliminary else ""
    return (
        f"| {mc.mode} | {mc.mean:.4f} | "
        f"{mc.min_val:.4f} | {mc.max_val:.4f} | "
        f"{mc.n}{prelim} |"
    )


def _budget_row(be: BudgetEfficiency | None) -> str:
    """Format a budget efficiency as a table row."""
    if be is None:
        return "| — | — | — | — | — |"
    cpp = (
        f"${be.cost_per_pct_point:.4f}"
        if be.cost_per_pct_point is not None
        else "N/A (N < 3)"
    )
    prelim = " ⚠️" if be.is_preliminary else ""
    return (
        f"| {be.mode} | ${be.mean_cost:.4f} | "
        f"{be.mean_pass_rate:.2f}% | "
        f"{cpp} | {be.n}{prelim} |"
    )


def build_section_executive_summary(
    summary: AnalysisSummary,
) -> str:
    """Section 1: Executive Summary."""
    ec = summary.exclusion_counts
    prd = summary.pass_rate_delta

    prelim_note = ""
    if summary.any_preliminary:
        prelim_note = (
            "\n\n> **Note:** Some results are "
            "flagged as preliminary due to "
            "small sample sizes "
            f"(N < {LOW_N_THRESHOLD}). "
            "Interpret with caution."
        )

    no_data = ""
    if not summary.has_data:
        no_data = (
            "\n\n> **No validated experiment data "
            "available.** All sections below show "
            "placeholder values. Run experiments and "
            "ensure manipulation_check='passed' and "
            "results_valid=true before generating "
            "the final report."
        )

    return f"""## 1. Executive Summary

This report summarizes findings from the SCBench Research
Lab comparing single-agent and two-agent (Implementer +
Reviewer) systems on SlopCodeBench problems.

- **Total experiments conducted:** {ec.total}
- **Validated experiments:** {ec.valid}
- **Excluded experiments:** {ec.excluded}
- **Mean pass rate delta (two-agent - baseline):** \
{prd.mean_delta:+.4f}pp (N={prd.n_pairs} pairs)\
{_prelim_badge(is_preliminary=prd.is_preliminary)}
- **Any preliminary results:** \
{"Yes" if summary.any_preliminary else "No"}{prelim_note}\
{no_data}
"""


def build_section_methodology(
    summary: AnalysisSummary,
) -> str:
    """Section 2: Methodology."""
    return """## 2. Methodology

### Experiment Design

Each experiment runs both a single-agent baseline and a
two-agent (Implementer + Reviewer) system on the same
SlopCodeBench problem using the same model and budget.

- **Baseline (single-agent):** Standard `slop-code run`
  with the implementer prompt only.
- **Two-agent:** Implementer produces code, Reviewer
  refactors/improves, output feeds back into subsequent
  checkpoints.

### Validation Filters

All analysis uses exclusively validated experiments:
- `manipulation_check = 'passed'`
- `results_valid = true`

Experiments failing either condition are excluded and
counted in the Data Quality section.

### Metrics

1. **Pass rate delta:** `two_agent_pass_rate -
   baseline_pass_rate` per matched problem/model pair.
2. **Erosion slope:** Least-squares slope of erosion
   scores across checkpoints. Compared between modes.
3. **Verbosity slope:** Least-squares slope of verbosity
   scores across checkpoints. Compared between modes.
4. **Budget efficiency:** `mean_cost / mean_pass_rate`
   per mode (cost per percentage point of pass rate).

### Sample Size Policy

- All statistics report N (sample size).
- Results with N < 5 are flagged as **PRELIMINARY**.
- Derived statistics are not computed for N < 3.
"""


def build_section_per_problem(
    per_problem: list[PerProblemRow],
    summary: AnalysisSummary,
) -> str:
    """Section 3: Per-Problem Results."""
    prd = summary.pass_rate_delta

    lines = [
        "## 3. Per-Problem Results",
        "",
        "### Pass Rate Delta by Problem",
        "",
        "| Problem | Model | Baseline | Two-Agent "
        "| Delta | N |",
        "|---------|-------|----------|-----------|"
        "-------|---|",
    ]
    if prd.per_problem:
        for d in prd.per_problem:
            lines.append(
                f"| {d.problem_id} | {d.model} | "
                f"{d.baseline_pass_rate:.2f}% | "
                f"{d.two_agent_pass_rate:.2f}% | "
                f"{d.delta:+.2f}pp | "
                f"{d.sample_size} |"
            )
    else:
        lines.append(
            "| (no matched pairs) | — | — | — | — | — |"
        )

    lines.extend([
        "",
        "### Per-Problem Breakdown by Mode",
        "",
        "| Problem | Mode | N | Pass Rate | "
        "Erosion Slope | Verbosity Slope | Cost |",
        "|---------|------|---|-----------|"
        "--------------|-----------------|------|",
    ])
    if per_problem:
        for row in per_problem:
            prelim = " ⚠️" if row.is_preliminary else ""
            lines.append(
                f"| {row.problem_id} | {row.mode} | "
                f"{row.n}{prelim} | "
                f"{row.mean_pass_rate:.2f}% | "
                f"{row.mean_erosion_slope:.4f} | "
                f"{row.mean_verbosity_slope:.4f} | "
                f"${row.mean_cost:.2f} |"
            )
    else:
        lines.append(
            "| (no data) | — | — | — | — | — | — |"
        )
    lines.append("")
    return "\n".join(lines)


def build_section_aggregate(
    summary: AnalysisSummary,
) -> str:
    """Section 4: Aggregate Results."""
    prd = summary.pass_rate_delta
    return f"""## 4. Aggregate Results

### Overall Pass Rate Delta

- **Mean delta (two-agent - baseline):** \
{prd.mean_delta:+.4f}pp
- **Number of matched pairs:** {prd.n_pairs}\
{_prelim_badge(is_preliminary=prd.is_preliminary)}

### Interpretation

{"The two-agent system shows a mean improvement of "
 f"{prd.mean_delta:+.4f} percentage points over the "
 "single-agent baseline across all matched pairs."
 if prd.mean_delta > 0
 else "The two-agent system does not show consistent "
      "improvement over the single-agent baseline in "
      "the current data."
 if prd.n_pairs > 0
 else "No matched experiment pairs available for "
      "comparison."}
"""


def build_section_erosion_verbosity(
    summary: AnalysisSummary,
) -> str:
    """Section 5: Erosion and Verbosity Analysis."""
    ec = summary.erosion_comparison
    vc = summary.verbosity_comparison

    lines = [
        "## 5. Erosion and Verbosity Analysis",
        "",
        "### Erosion Slope Comparison",
        _prelim_badge(is_preliminary=ec.any_preliminary),
        "",
        "| Mode | Mean Slope | Min | Max | N |",
        "|------|-----------|-----|-----|---|",
        _mode_stat_row(ec.single),
        _mode_stat_row(ec.two_agent),
        "",
        f"**Difference (two-agent - single):** "
        f"{ec.difference:+.4f}",
        "",
        "### Verbosity Slope Comparison",
        _prelim_badge(is_preliminary=vc.any_preliminary),
        "",
        "| Mode | Mean Slope | Min | Max | N |",
        "|------|-----------|-----|-----|---|",
        _mode_stat_row(vc.single),
        _mode_stat_row(vc.two_agent),
        "",
        f"**Difference (two-agent - single):** "
        f"{vc.difference:+.4f}",
        "",
    ]
    return "\n".join(lines)


def build_section_budget(
    summary: AnalysisSummary,
) -> str:
    """Section 6: Budget Analysis."""
    bc = summary.budget_comparison
    lines = [
        "## 6. Budget Analysis",
        "",
        "### Budget Efficiency (Cost per Percentage "
        "Point of Pass Rate)",
        "",
        "| Mode | Mean Cost | Mean Pass Rate | "
        "Cost/pct-point | N |",
        "|------|-----------|---------------|"
        "----------------|---|",
        _budget_row(bc.single),
        _budget_row(bc.two_agent),
        "",
    ]

    # Comparative note
    if (
        bc.single is not None
        and bc.two_agent is not None
        and bc.single.cost_per_pct_point is not None
        and bc.two_agent.cost_per_pct_point is not None
    ):
        if (
            bc.two_agent.cost_per_pct_point
            < bc.single.cost_per_pct_point
        ):
            lines.append(
                "The two-agent system achieves better "
                "budget efficiency (lower cost per "
                "percentage point) than the baseline."
            )
        else:
            lines.append(
                "The single-agent baseline achieves "
                "better budget efficiency (lower cost "
                "per percentage point) than the "
                "two-agent system."
            )
    else:
        lines.append(
            "Budget efficiency comparison unavailable "
            "(insufficient data or zero pass rate)."
        )

    lines.append("")
    return "\n".join(lines)


def build_section_sweet_spots(
    summary: AnalysisSummary,
) -> str:
    """Section 7: Sweet Spots."""
    spots = identify_sweet_spots(
        summary.per_problem,
        summary.pass_rate_delta.per_problem,
    )
    lines = [
        "## 7. Sweet Spots",
        "",
        "Problems where the two-agent system "
        "outperforms the baseline:",
        "",
    ]
    for s in spots:
        lines.append(f"- {s}")
    lines.append("")
    return "\n".join(lines)


def build_section_limitations(
    summary: AnalysisSummary,
) -> str:
    """Section 8: Limitations."""
    ec = summary.exclusion_counts
    lines = [
        "## 8. Limitations",
        "",
    ]

    if summary.any_preliminary:
        lines.append(
            "- **Small sample sizes.** Some results "
            f"are based on fewer than "
            f"{LOW_N_THRESHOLD} experiments and are "
            "flagged as preliminary."
        )

    if ec.excluded > 0:
        lines.append(
            f"- **Excluded experiments.** {ec.excluded} "
            f"of {ec.total} experiments were excluded "
            "due to validation failures. This may "
            "introduce selection bias."
        )

    lines.extend([
        "- **Fixed compute budget.** Results depend "
        "on the total budget allocated. Different "
        "budgets may change the relative performance "
        "of the two approaches.",
        "- **Problem coverage.** Findings apply to "
        "the SlopCodeBench problems tested and may "
        "not generalize to all coding tasks.",
        "- **Single model family.** Experiments used "
        "specific model configurations. Results may "
        "differ across model families.",
        "- **Reviewer prompt sensitivity.** The "
        "two-agent system's performance depends on "
        "the reviewer prompt template, which was not "
        "exhaustively optimized.",
        "",
    ])
    return "\n".join(lines)


def build_section_recommendations(
    summary: AnalysisSummary,
) -> str:
    """Section 9: Recommendations."""
    prd = summary.pass_rate_delta
    lines = [
        "## 9. Recommendations",
        "",
    ]

    if not summary.has_data:
        lines.append(
            "- Run validated experiments before "
            "drawing conclusions."
        )
    elif prd.n_pairs == 0:
        lines.append(
            "- Run matched baseline/two-agent pairs "
            "to enable comparison."
        )
    else:
        if prd.is_preliminary:
            lines.append(
                "- **Increase sample size.** Current "
                "results are preliminary. Run "
                "additional experiments to reach "
                f"N >= {LOW_N_THRESHOLD} per group "
                "before drawing firm conclusions."
            )

        if prd.mean_delta > 0:
            lines.append(
                "- **Two-agent shows promise.** "
                "Consider scaling experiments on "
                "problems where the delta is largest."
            )
        else:
            lines.append(
                "- **Re-evaluate reviewer strategy.** "
                "The current two-agent configuration "
                "does not consistently outperform "
                "the baseline. Consider alternative "
                "reviewer prompts or budget splits."
            )

        lines.extend([
            "- **Investigate erosion patterns.** "
            "Compare erosion trajectories between "
            "modes at the per-checkpoint level.",
            "- **Test budget split sensitivity.** "
            "Vary the implementer/reviewer budget "
            "split to find optimal allocation.",
            "- **Expand problem coverage.** Run on "
            "additional SlopCodeBench problems to "
            "test generalization.",
        ])

    lines.append("")
    return "\n".join(lines)


def build_section_data_quality(
    ec: ExclusionCounts,
) -> str:
    """Data quality appendix (referenced by report)."""
    return f"""## Appendix: Data Quality

### Validation Summary

| Metric | Count |
|--------|-------|
| Total experiments | {ec.total} |
| Validated (passed + valid) | {ec.valid} |
| Excluded total | {ec.excluded} |
| Excluded: failed manipulation check | \
{ec.excluded_manipulation} |
| Excluded: invalid results | {ec.excluded_invalid} |

### Validation Criteria

All analysis in this report uses exclusively experiments
where:
- `manipulation_check = 'passed'`
- `results_valid = true`

Experiments failing either criterion are counted above
but excluded from all statistical computations.
"""


# ── Full report assembly ─────────────────────────────


def generate_report(
    summary: AnalysisSummary,
) -> str:
    """Assemble the full FINAL_REPORT.md content."""
    timestamp = datetime.now(UTC).strftime(
        "%Y-%m-%d %H:%M UTC",
    )
    sections = [
        "# SCBench Research Lab — Final Report",
        "",
        f"*Generated: {timestamp}*",
        "",
        build_section_executive_summary(summary),
        build_section_methodology(summary),
        build_section_per_problem(
            summary.per_problem, summary,
        ),
        build_section_aggregate(summary),
        build_section_erosion_verbosity(summary),
        build_section_budget(summary),
        build_section_sweet_spots(summary),
        build_section_limitations(summary),
        build_section_recommendations(summary),
        build_section_data_quality(
            summary.exclusion_counts,
        ),
    ]
    return "\n".join(sections)


def run_analysis_and_generate(
    conn: Any,
) -> AnalysisSummary:
    """Query Dolt and compute full analysis.

    Returns the AnalysisSummary used for report
    generation.
    """
    exclusions = query_exclusion_counts(conn)
    deltas = query_pass_rate_delta(conn)
    erosion = query_erosion_comparison(conn)
    verbosity = query_verbosity_comparison(conn)
    budget = query_budget_efficiency(conn)
    per_problem = query_per_problem_breakdown(conn)

    return compute_full_analysis(
        exclusions=exclusions,
        deltas=deltas,
        erosion_stats=erosion,
        verbosity_stats=verbosity,
        budget_stats=budget,
        per_problem=per_problem,
    )


# ── CLI ──────────────────────────────────────────────

app = typer.Typer(
    name="generate-report",
    help=(
        "Generate FINAL_REPORT.md from Dolt "
        "experiment data."
    ),
    add_completion=False,
)


@app.command()
def main(
    output: Path = typer.Option(
        DEFAULT_OUTPUT,
        "--output", "-o",
        help="Output path for the report.",
    ),
    dolt_host: str = typer.Option(
        DOLT_HOST,
        "--dolt-host",
        help="Dolt server host.",
    ),
    dolt_port: int = typer.Option(
        DOLT_PORT,
        "--dolt-port",
        help="Dolt server port.",
    ),
) -> None:
    """Generate FINAL_REPORT.md from experiment data."""
    typer.echo("Connecting to Dolt ...")
    conn = get_connection(
        host=dolt_host, port=dolt_port,
    )

    try:
        typer.echo("Running analysis queries ...")
        summary = run_analysis_and_generate(conn)

        typer.echo("Generating report ...")
        report = generate_report(summary)

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report)
        typer.echo(f"Report written to {output}")
    finally:
        conn.close()


if __name__ == "__main__":
    app()
