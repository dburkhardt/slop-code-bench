"""Tests for research.analysis.compute_metrics."""

from __future__ import annotations

import pytest

from research.analysis.compute_metrics import AnalysisSummary
from research.analysis.compute_metrics import compute_aggregate_pass_rate_delta
from research.analysis.compute_metrics import compute_budget_comparison
from research.analysis.compute_metrics import compute_full_analysis
from research.analysis.compute_metrics import compute_slope_comparison
from research.analysis.compute_metrics import identify_sweet_spots
from research.analysis.query_experiments import BudgetEfficiency
from research.analysis.query_experiments import ExclusionCounts
from research.analysis.query_experiments import ModeComparison
from research.analysis.query_experiments import PassRateDelta
from research.analysis.query_experiments import PerProblemRow

# ── compute_aggregate_pass_rate_delta ────────────────


def test_aggregate_delta_empty():
    """Empty deltas return preliminary flag."""
    result = compute_aggregate_pass_rate_delta([])
    assert result.n_pairs == 0
    assert result.is_preliminary is True
    assert result.mean_delta == 0.0


def test_aggregate_delta_single():
    """Single delta returns correct mean."""
    deltas = [
        PassRateDelta(
            problem_id="p1", delta=5.0,
        ),
    ]
    result = compute_aggregate_pass_rate_delta(deltas)
    assert result.mean_delta == 5.0
    assert result.n_pairs == 1
    assert result.is_preliminary is True


def test_aggregate_delta_multiple():
    """Multiple deltas are averaged correctly."""
    deltas = [
        PassRateDelta(
            problem_id="p1", delta=10.0,
        ),
        PassRateDelta(
            problem_id="p2", delta=-4.0,
        ),
        PassRateDelta(
            problem_id="p3", delta=6.0,
        ),
        PassRateDelta(
            problem_id="p4", delta=0.0,
        ),
        PassRateDelta(
            problem_id="p5", delta=8.0,
        ),
    ]
    result = compute_aggregate_pass_rate_delta(deltas)
    assert result.mean_delta == pytest.approx(4.0)
    assert result.n_pairs == 5
    assert result.is_preliminary is False


# ── compute_slope_comparison ─────────────────────────


def test_slope_comparison_both_modes():
    """Comparison computes difference correctly."""
    stats = [
        ModeComparison(
            mode="single", n=10, mean=0.05,
        ),
        ModeComparison(
            mode="two-agent", n=10, mean=0.03,
        ),
    ]
    result = compute_slope_comparison(stats, "erosion")
    assert result.metric_name == "erosion"
    assert result.single is not None
    assert result.two_agent is not None
    assert result.difference == pytest.approx(-0.02)
    assert result.any_preliminary is False


def test_slope_comparison_single_mode():
    """Missing mode returns None."""
    stats = [
        ModeComparison(
            mode="single", n=10, mean=0.05,
        ),
    ]
    result = compute_slope_comparison(
        stats, "verbosity",
    )
    assert result.single is not None
    assert result.two_agent is None
    assert result.difference == 0.0


def test_slope_comparison_preliminary():
    """Preliminary flag propagated from any mode."""
    stats = [
        ModeComparison(
            mode="single", n=3, mean=0.05,
            is_preliminary=True,
        ),
        ModeComparison(
            mode="two-agent", n=10, mean=0.03,
            is_preliminary=False,
        ),
    ]
    result = compute_slope_comparison(stats, "erosion")
    assert result.any_preliminary is True


# ── compute_budget_comparison ────────────────────────


def test_budget_comparison_both_modes():
    """Budget comparison assigns modes correctly."""
    efficiency = [
        BudgetEfficiency(
            mode="single", n=5,
            mean_cost=8.0, mean_pass_rate=80.0,
            cost_per_pct_point=0.1,
        ),
        BudgetEfficiency(
            mode="two-agent", n=5,
            mean_cost=12.0, mean_pass_rate=85.0,
            cost_per_pct_point=0.1412,
        ),
    ]
    result = compute_budget_comparison(efficiency)
    assert result.single is not None
    assert result.two_agent is not None
    assert result.any_preliminary is False


def test_budget_comparison_preliminary():
    """Preliminary flag from low-N."""
    efficiency = [
        BudgetEfficiency(
            mode="single", n=2,
            is_preliminary=True,
        ),
    ]
    result = compute_budget_comparison(efficiency)
    assert result.any_preliminary is True


# ── compute_full_analysis ────────────────────────────


def test_full_analysis_with_data():
    """Full analysis produces correct summary."""
    exclusions = ExclusionCounts(
        total=10, valid=8, excluded=2,
        excluded_manipulation=1, excluded_invalid=1,
    )
    deltas = [
        PassRateDelta(
            problem_id="p1", delta=5.0,
        ),
        PassRateDelta(
            problem_id="p2", delta=-3.0,
        ),
    ]
    erosion = [
        ModeComparison(
            mode="single", n=4, mean=0.05,
            is_preliminary=True,
        ),
        ModeComparison(
            mode="two-agent", n=4, mean=0.03,
            is_preliminary=True,
        ),
    ]
    verbosity = [
        ModeComparison(
            mode="single", n=4, mean=0.08,
            is_preliminary=True,
        ),
    ]
    budget = [
        BudgetEfficiency(
            mode="single", n=4,
            is_preliminary=True,
        ),
    ]
    per_problem = [
        PerProblemRow(
            problem_id="p1", mode="single", n=2,
        ),
    ]

    result = compute_full_analysis(
        exclusions, deltas, erosion, verbosity,
        budget, per_problem,
    )

    assert isinstance(result, AnalysisSummary)
    assert result.has_data is True
    assert result.any_preliminary is True
    assert result.pass_rate_delta.mean_delta == (
        pytest.approx(1.0)
    )


def test_full_analysis_no_data():
    """Summary with zero valid experiments."""
    exclusions = ExclusionCounts(
        total=0, valid=0,
    )
    result = compute_full_analysis(
        exclusions, [], [], [], [], [],
    )
    assert result.has_data is False


# ── identify_sweet_spots ─────────────────────────────


def test_sweet_spots_finds_improvements():
    """Problems with positive delta are identified."""
    deltas = [
        PassRateDelta(
            problem_id="p1", delta=5.0,
            baseline_pass_rate=80.0,
            two_agent_pass_rate=85.0,
        ),
        PassRateDelta(
            problem_id="p2", delta=-3.0,
        ),
        PassRateDelta(
            problem_id="p3", delta=2.0,
            baseline_pass_rate=70.0,
            two_agent_pass_rate=72.0,
        ),
    ]
    spots = identify_sweet_spots([], deltas)
    assert len(spots) == 2
    assert "p1" in spots[0]
    assert "p3" in spots[1]


def test_sweet_spots_no_improvements():
    """No positive deltas returns default message."""
    deltas = [
        PassRateDelta(
            problem_id="p1", delta=-1.0,
        ),
    ]
    spots = identify_sweet_spots([], deltas)
    assert len(spots) == 1
    assert "No problems" in spots[0]


def test_sweet_spots_empty():
    """Empty deltas returns default message."""
    spots = identify_sweet_spots([], [])
    assert len(spots) == 1
    assert "No problems" in spots[0]
