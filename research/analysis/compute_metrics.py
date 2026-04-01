"""Statistical computations for SCBench experiments.

Computes pass rate delta, erosion/verbosity slope
comparisons, and budget efficiency from validated
experiment data. All functions accept pre-queried data
(from ``query_experiments``) and return structured
results.

Every function reports sample sizes and flags low-N
results as preliminary (N < 5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from dataclasses import field

from research.analysis.query_experiments import LOW_N_THRESHOLD
from research.analysis.query_experiments import BudgetEfficiency
from research.analysis.query_experiments import ExclusionCounts
from research.analysis.query_experiments import ModeComparison
from research.analysis.query_experiments import PassRateDelta
from research.analysis.query_experiments import PerProblemRow

logger = logging.getLogger(__name__)


# ── Aggregate result containers ──────────────────────


@dataclass
class AggregatePassRateDelta:
    """Aggregate pass rate delta across problems."""

    per_problem: list[PassRateDelta] = field(
        default_factory=list,
    )
    mean_delta: float = 0.0
    n_pairs: int = 0
    is_preliminary: bool = False


@dataclass
class SlopeComparison:
    """Side-by-side slope comparison for two modes."""

    metric_name: str = ""
    single: ModeComparison | None = None
    two_agent: ModeComparison | None = None
    difference: float = 0.0
    any_preliminary: bool = False


@dataclass
class BudgetComparison:
    """Side-by-side budget efficiency comparison."""

    single: BudgetEfficiency | None = None
    two_agent: BudgetEfficiency | None = None
    any_preliminary: bool = False


@dataclass
class AnalysisSummary:
    """Complete analysis summary for report generation."""

    exclusion_counts: ExclusionCounts = field(
        default_factory=ExclusionCounts,
    )
    pass_rate_delta: AggregatePassRateDelta = field(
        default_factory=AggregatePassRateDelta,
    )
    erosion_comparison: SlopeComparison = field(
        default_factory=SlopeComparison,
    )
    verbosity_comparison: SlopeComparison = field(
        default_factory=SlopeComparison,
    )
    budget_comparison: BudgetComparison = field(
        default_factory=BudgetComparison,
    )
    per_problem: list[PerProblemRow] = field(
        default_factory=list,
    )
    has_data: bool = False
    any_preliminary: bool = False


# ── Computation functions ────────────────────────────


def compute_aggregate_pass_rate_delta(
    deltas: list[PassRateDelta],
) -> AggregatePassRateDelta:
    """Aggregate pass rate deltas across problems.

    Returns mean delta, count of matched pairs, and
    a preliminary flag when N < LOW_N_THRESHOLD.
    """
    if not deltas:
        return AggregatePassRateDelta(
            is_preliminary=True,
        )
    mean = sum(d.delta for d in deltas) / len(deltas)
    n = len(deltas)
    return AggregatePassRateDelta(
        per_problem=deltas,
        mean_delta=round(mean, 4),
        n_pairs=n,
        is_preliminary=n < LOW_N_THRESHOLD,
    )


def compute_slope_comparison(
    mode_stats: list[ModeComparison],
    metric_name: str,
) -> SlopeComparison:
    """Build a side-by-side slope comparison.

    Expects up to two ModeComparison entries (one per
    mode). Computes the difference (two-agent - single).
    """
    single = None
    two_agent = None
    for mc in mode_stats:
        if mc.mode == "single":
            single = mc
        elif mc.mode == "two-agent":
            two_agent = mc

    diff = 0.0
    if single is not None and two_agent is not None:
        diff = round(two_agent.mean - single.mean, 4)

    any_prelim = any(
        mc.is_preliminary for mc in mode_stats
    )
    return SlopeComparison(
        metric_name=metric_name,
        single=single,
        two_agent=two_agent,
        difference=diff,
        any_preliminary=any_prelim,
    )


def compute_budget_comparison(
    efficiency: list[BudgetEfficiency],
) -> BudgetComparison:
    """Build a side-by-side budget efficiency comparison."""
    single = None
    two_agent = None
    for be in efficiency:
        if be.mode == "single":
            single = be
        elif be.mode == "two-agent":
            two_agent = be
    any_prelim = any(
        be.is_preliminary for be in efficiency
    )
    return BudgetComparison(
        single=single,
        two_agent=two_agent,
        any_preliminary=any_prelim,
    )


def compute_full_analysis(
    exclusions: ExclusionCounts,
    deltas: list[PassRateDelta],
    erosion_stats: list[ModeComparison],
    verbosity_stats: list[ModeComparison],
    budget_stats: list[BudgetEfficiency],
    per_problem: list[PerProblemRow],
) -> AnalysisSummary:
    """Run the full analysis pipeline.

    Aggregates all metrics and flags whether any results
    are preliminary.
    """
    prd = compute_aggregate_pass_rate_delta(deltas)
    erosion = compute_slope_comparison(
        erosion_stats, "erosion",
    )
    verbosity = compute_slope_comparison(
        verbosity_stats, "verbosity",
    )
    budget = compute_budget_comparison(budget_stats)

    has_data = exclusions.valid > 0
    any_prelim = any([
        prd.is_preliminary,
        erosion.any_preliminary,
        verbosity.any_preliminary,
        budget.any_preliminary,
    ])

    return AnalysisSummary(
        exclusion_counts=exclusions,
        pass_rate_delta=prd,
        erosion_comparison=erosion,
        verbosity_comparison=verbosity,
        budget_comparison=budget,
        per_problem=per_problem,
        has_data=has_data,
        any_preliminary=any_prelim,
    )


def identify_sweet_spots(
    per_problem: list[PerProblemRow],
    deltas: list[PassRateDelta],
) -> list[str]:
    """Identify problems where two-agent outperforms.

    Returns a list of summary strings describing the
    sweet spots (problems with positive delta).
    """
    spots: list[str] = []
    for d in deltas:
        if d.delta > 0:
            spots.append(
                f"{d.problem_id}: two-agent "
                f"outperforms by {d.delta:+.2f}pp "
                f"(baseline={d.baseline_pass_rate:.2f}, "
                f"two-agent="
                f"{d.two_agent_pass_rate:.2f})"
            )
    if not spots:
        spots.append(
            "No problems showed two-agent improvement "
            "over baseline in the current data."
        )
    return spots
