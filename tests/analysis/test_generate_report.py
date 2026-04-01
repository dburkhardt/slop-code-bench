"""Tests for research.analysis.generate_report."""

from __future__ import annotations

from research.analysis.compute_metrics import AggregatePassRateDelta
from research.analysis.compute_metrics import AnalysisSummary
from research.analysis.compute_metrics import BudgetComparison
from research.analysis.compute_metrics import SlopeComparison
from research.analysis.generate_report import build_section_aggregate
from research.analysis.generate_report import build_section_budget
from research.analysis.generate_report import build_section_data_quality
from research.analysis.generate_report import build_section_erosion_verbosity
from research.analysis.generate_report import build_section_executive_summary
from research.analysis.generate_report import build_section_limitations
from research.analysis.generate_report import build_section_methodology
from research.analysis.generate_report import build_section_per_problem
from research.analysis.generate_report import build_section_recommendations
from research.analysis.generate_report import build_section_sweet_spots
from research.analysis.generate_report import generate_report
from research.analysis.query_experiments import BudgetEfficiency
from research.analysis.query_experiments import ExclusionCounts
from research.analysis.query_experiments import ModeComparison
from research.analysis.query_experiments import PassRateDelta
from research.analysis.query_experiments import PerProblemRow

# ── Fixtures ─────────────────────────────────────────

REQUIRED_SECTIONS = [
    "Executive Summary",
    "Methodology",
    "Per-Problem Results",
    "Aggregate Results",
    "Erosion and Verbosity Analysis",
    "Budget Analysis",
    "Sweet Spots",
    "Limitations",
    "Recommendations",
]


def _make_summary(
    *,
    has_data: bool = True,  # noqa: FBT001, FBT002
    any_preliminary: bool = False,  # noqa: FBT001, FBT002
    n_pairs: int = 5,
) -> AnalysisSummary:
    """Build a minimal AnalysisSummary for testing."""
    ec = ExclusionCounts(
        total=10, valid=8, excluded=2,
        excluded_manipulation=1,
        excluded_invalid=1,
    )
    deltas = [
        PassRateDelta(
            problem_id="file_backup",
            model="opus-4.5",
            hypothesis_id="h1",
            baseline_pass_rate=80.0,
            two_agent_pass_rate=85.0,
            delta=5.0,
        ),
    ]
    prd = AggregatePassRateDelta(
        per_problem=deltas,
        mean_delta=5.0,
        n_pairs=n_pairs,
        is_preliminary=n_pairs < 5,
    )
    erosion = SlopeComparison(
        metric_name="erosion",
        single=ModeComparison(
            mode="single", n=8, mean=0.03,
            min_val=0.01, max_val=0.05,
        ),
        two_agent=ModeComparison(
            mode="two-agent", n=8, mean=0.02,
            min_val=0.005, max_val=0.04,
        ),
        difference=-0.01,
    )
    verbosity = SlopeComparison(
        metric_name="verbosity",
        single=ModeComparison(
            mode="single", n=8, mean=0.08,
            min_val=0.02, max_val=0.15,
        ),
        two_agent=ModeComparison(
            mode="two-agent", n=8, mean=0.05,
            min_val=0.01, max_val=0.10,
        ),
        difference=-0.03,
    )
    budget = BudgetComparison(
        single=BudgetEfficiency(
            mode="single", n=8,
            mean_cost=8.0, mean_pass_rate=80.0,
            cost_per_pct_point=0.1,
        ),
        two_agent=BudgetEfficiency(
            mode="two-agent", n=8,
            mean_cost=12.0, mean_pass_rate=85.0,
            cost_per_pct_point=0.1412,
        ),
    )
    per_problem = [
        PerProblemRow(
            problem_id="file_backup",
            mode="single", n=4,
            mean_pass_rate=80.0,
            mean_erosion_slope=0.03,
            mean_verbosity_slope=0.08,
            mean_cost=8.0,
        ),
        PerProblemRow(
            problem_id="file_backup",
            mode="two-agent", n=4,
            mean_pass_rate=85.0,
            mean_erosion_slope=0.02,
            mean_verbosity_slope=0.05,
            mean_cost=12.0,
        ),
    ]
    return AnalysisSummary(
        exclusion_counts=ec,
        pass_rate_delta=prd,
        erosion_comparison=erosion,
        verbosity_comparison=verbosity,
        budget_comparison=budget,
        per_problem=per_problem,
        has_data=has_data,
        any_preliminary=any_preliminary,
    )


# ── generate_report: all 9 sections ─────────────────


def test_report_has_all_nine_sections():
    """FINAL_REPORT.md contains all 9 required sections."""
    summary = _make_summary()
    report = generate_report(summary)

    for section in REQUIRED_SECTIONS:
        assert section in report, (
            f"Missing section: {section}"
        )


def test_report_has_data_quality_appendix():
    """Report includes data quality appendix."""
    summary = _make_summary()
    report = generate_report(summary)
    assert "Data Quality" in report
    assert "Validation Summary" in report


def test_report_references_validated_data():
    """Report references validation criteria."""
    summary = _make_summary()
    report = generate_report(summary)
    assert "manipulation_check" in report
    assert "results_valid" in report


# ── Executive summary ────────────────────────────────


def test_executive_summary_has_counts():
    """Summary includes experiment counts."""
    summary = _make_summary()
    text = build_section_executive_summary(summary)
    assert "10" in text  # total
    assert "8" in text   # valid
    assert "2" in text   # excluded


def test_executive_summary_no_data():
    """No-data warning when has_data is False."""
    summary = _make_summary(has_data=False)
    text = build_section_executive_summary(summary)
    assert "No validated experiment data" in text


def test_executive_summary_preliminary():
    """Preliminary note when flagged."""
    summary = _make_summary(any_preliminary=True)
    text = build_section_executive_summary(summary)
    assert "preliminary" in text.lower()


# ── Methodology ──────────────────────────────────────


def test_methodology_describes_filters():
    """Methodology section describes validation filters."""
    summary = _make_summary()
    text = build_section_methodology(summary)
    assert "manipulation_check" in text
    assert "results_valid" in text


def test_methodology_describes_metrics():
    """Methodology describes all four metrics."""
    summary = _make_summary()
    text = build_section_methodology(summary)
    assert "Pass rate delta" in text
    assert "Erosion slope" in text
    assert "Verbosity slope" in text
    assert "Budget efficiency" in text


def test_methodology_describes_sample_size_policy():
    """Methodology describes sample size handling."""
    summary = _make_summary()
    text = build_section_methodology(summary)
    assert "sample size" in text.lower()
    assert "PRELIMINARY" in text


# ── Per-problem results ──────────────────────────────


def test_per_problem_has_table():
    """Per-problem section includes results table."""
    summary = _make_summary()
    text = build_section_per_problem(
        summary.per_problem, summary,
    )
    assert "file_backup" in text
    assert "80.00%" in text
    assert "85.00%" in text


def test_per_problem_empty():
    """No data shows placeholder."""
    summary = _make_summary()
    summary.pass_rate_delta.per_problem = []
    text = build_section_per_problem([], summary)
    assert "no matched pairs" in text.lower()


# ── Aggregate results ────────────────────────────────


def test_aggregate_shows_delta():
    """Aggregate section reports mean delta."""
    summary = _make_summary()
    text = build_section_aggregate(summary)
    assert "+5.0000pp" in text


def test_aggregate_positive_interpretation():
    """Positive delta shows improvement text."""
    summary = _make_summary()
    text = build_section_aggregate(summary)
    assert "improvement" in text.lower()


def test_aggregate_no_pairs():
    """Zero pairs shows no-comparison message."""
    summary = _make_summary(n_pairs=0)
    summary.pass_rate_delta.n_pairs = 0
    summary.pass_rate_delta.mean_delta = 0.0
    text = build_section_aggregate(summary)
    assert "No matched" in text


# ── Erosion and verbosity ────────────────────────────


def test_erosion_verbosity_has_tables():
    """Both slope tables are present."""
    summary = _make_summary()
    text = build_section_erosion_verbosity(summary)
    assert "Erosion Slope Comparison" in text
    assert "Verbosity Slope Comparison" in text
    assert "single" in text
    assert "two-agent" in text


def test_erosion_verbosity_shows_difference():
    """Difference between modes is reported."""
    summary = _make_summary()
    text = build_section_erosion_verbosity(summary)
    assert "Difference" in text


# ── Budget analysis ──────────────────────────────────


def test_budget_has_table():
    """Budget section includes efficiency table."""
    summary = _make_summary()
    text = build_section_budget(summary)
    assert "Cost per Percentage" in text
    assert "single" in text


def test_budget_comparison_note():
    """Comparison note describes which is better."""
    summary = _make_summary()
    text = build_section_budget(summary)
    # Single has lower cost_per_pct (0.1 vs 0.1412)
    assert "better budget efficiency" in text.lower()


# ── Sweet spots ──────────────────────────────────────


def test_sweet_spots_lists_problems():
    """Sweet spots identifies improvement problems."""
    summary = _make_summary()
    text = build_section_sweet_spots(summary)
    assert "file_backup" in text
    assert "outperforms" in text


# ── Limitations ──────────────────────────────────────


def test_limitations_present():
    """Limitations section lists key limitations."""
    summary = _make_summary()
    text = build_section_limitations(summary)
    assert "Fixed compute budget" in text
    assert "Problem coverage" in text


def test_limitations_excluded_warning():
    """Excluded experiments noted in limitations."""
    summary = _make_summary()
    text = build_section_limitations(summary)
    assert "Excluded" in text
    assert "2" in text


def test_limitations_preliminary_warning():
    """Preliminary flag noted in limitations."""
    summary = _make_summary(any_preliminary=True)
    text = build_section_limitations(summary)
    assert "Small sample sizes" in text


# ── Recommendations ──────────────────────────────────


def test_recommendations_with_improvement():
    """Positive delta recommends scaling."""
    summary = _make_summary()
    text = build_section_recommendations(summary)
    assert "promise" in text.lower()


def test_recommendations_no_data():
    """No-data recommends running experiments."""
    summary = _make_summary(has_data=False)
    text = build_section_recommendations(summary)
    assert "Run validated" in text


def test_recommendations_preliminary():
    """Preliminary recommends increasing N."""
    summary = _make_summary(
        any_preliminary=True, n_pairs=3,
    )
    summary.pass_rate_delta.is_preliminary = True
    text = build_section_recommendations(summary)
    assert "Increase sample size" in text


# ── Data quality appendix ────────────────────────────


def test_data_quality_has_counts():
    """Data quality shows validation counts."""
    ec = ExclusionCounts(
        total=15, valid=12, excluded=3,
        excluded_manipulation=2,
        excluded_invalid=1,
    )
    text = build_section_data_quality(ec)
    assert "15" in text
    assert "12" in text
    assert "3" in text
    assert "2" in text
    assert "1" in text


def test_data_quality_states_criteria():
    """Data quality states the filter criteria."""
    ec = ExclusionCounts()
    text = build_section_data_quality(ec)
    assert "manipulation_check = 'passed'" in text
    assert "results_valid = true" in text
