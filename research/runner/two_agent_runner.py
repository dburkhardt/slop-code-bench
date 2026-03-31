#!/usr/bin/env python3
"""Two-agent runner for SCBench experiments.

Wraps ``slop-code run`` with an Implementer + Reviewer pattern.
For each checkpoint the implementer gets *budget_split*% of the
per-checkpoint budget and the reviewer gets the remainder.

Usage::

    python two_agent_runner.py \\
        --problem file_backup \\
        --model opus-4.5 \\
        --budget 5.0 \\
        --budget-split 70
"""

import json
import subprocess
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path

import typer
from pydantic import BaseModel
from pydantic import Field

# ---------------------------------------------------------------------------
# Repo root (two levels up from research/runner/)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = REPO_ROOT / "configs"
MODELS_DIR = CONFIGS_DIR / "models"
PROBLEMS_DIR = REPO_ROOT / "problems"
OUTPUTS_DIR = REPO_ROOT / "outputs"

DEFAULT_IMPLEMENTER_PROMPT = (
    "configs/prompts/default_implementer.jinja"
)
DEFAULT_REVIEWER_PROMPT = (
    "configs/prompts/default_reviewer.jinja"
)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class CheckpointMetrics(BaseModel):
    """Per-checkpoint tracked metrics."""

    pass_rate: float = 0.0
    erosion: float = 0.0
    verbosity: float = 0.0
    tokens_implementer: int = 0
    tokens_reviewer: int = 0
    cost: float = 0.0


class RunState(BaseModel):
    """Mutable state accumulated during a run."""

    model_config = {"arbitrary_types_allowed": True}

    problem: str
    model: str
    budget: float
    budget_split: int
    output_dir: Path
    checkpoint_metrics: dict[str, CheckpointMetrics] = Field(
        default_factory=dict,
    )
    budget_exceeded: bool = False
    last_reviewer_suggestions: str | None = None

    @property
    def cumulative_cost(self) -> float:
        return sum(
            m.cost for m in self.checkpoint_metrics.values()
        )

    def save_results(self) -> None:
        """Persist metrics to *output_dir*/two_agent_metrics.json."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "problem": self.problem,
            "model": self.model,
            "budget": self.budget,
            "budget_split": self.budget_split,
            "cumulative_cost": round(self.cumulative_cost, 6),
            "budget_exceeded": self.budget_exceeded,
            "completed_checkpoints": len(
                self.checkpoint_metrics,
            ),
            "checkpoints": {
                name: m.model_dump()
                for name, m in self.checkpoint_metrics.items()
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }
        out_file = self.output_dir / "two_agent_metrics.json"
        out_file.write_text(
            json.dumps(payload, indent=2) + "\n",
        )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_budget_split(value: int) -> int:
    """Ensure *value* is in [1, 99]. Exits on failure."""
    if value < 1 or value > 99:
        typer.echo(
            f"Error: --budget-split must be in range 1-99, "
            f"got {value}",
            err=True,
        )
        raise SystemExit(1)
    return value


def validate_model(name: str) -> str:
    """Check that *name* resolves to a known model config.

    Uses the upstream ``ModelCatalog`` so that aliases and
    provider slugs are honoured.  Returns the canonical name
    on success, exits with a descriptive error otherwise.
    """
    # Add repo root to path so slop_code is importable
    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from slop_code.common.llms import ModelCatalog

    model = ModelCatalog.get(name)
    if model is None:
        available = ModelCatalog.list_models()
        typer.echo(
            f"Error: unknown model '{name}'. "
            f"Available models: {', '.join(available[:15])}"
            + (" ..." if len(available) > 15 else ""),
            err=True,
        )
        raise SystemExit(1)
    return model.name


def validate_problem(name: str) -> str:
    """Ensure *name* matches a directory under ``problems/``."""
    problem_dir = PROBLEMS_DIR / name
    if not problem_dir.is_dir():
        available = sorted(
            d.name
            for d in PROBLEMS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        typer.echo(
            f"Error: unknown problem '{name}'. "
            f"Available: {', '.join(available[:10])}"
            + (" ..." if len(available) > 10 else ""),
            err=True,
        )
        raise SystemExit(1)
    return name


def validate_prompt_template(path_str: str) -> Path:
    """Resolve a prompt template path relative to repo root."""
    path = Path(path_str)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.is_file():
        typer.echo(
            f"Error: prompt template not found: {path}",
            err=True,
        )
        raise SystemExit(1)
    return path


# ---------------------------------------------------------------------------
# Budget helpers
# ---------------------------------------------------------------------------


def is_budget_exceeded(
    cumulative_cost: float,
    budget: float,
) -> bool:
    """Return True when *cumulative_cost* > *budget*."""
    return cumulative_cost > budget


# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------


def build_output_dir(
    problem: str,
    model: str,
    base: Path | None = None,
) -> Path:
    """Build an output directory path compatible with slop-code eval.

    Layout::

        outputs/two_agent_<model>_<problem>_<timestamp>/
            <problem>/
                checkpoint_N/
                    snapshot/
    """
    if base is None:
        base = OUTPUTS_DIR
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    run_name = f"two_agent_{model}_{problem}_{ts}"
    return base / run_name


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def build_implementer_prompt(
    spec_text: str,
    *,
    is_continuation: bool,
    reviewer_suggestions: str | None = None,
) -> str:
    """Render the implementer prompt, optionally injecting
    prior reviewer suggestions."""
    parts: list[str] = []
    if reviewer_suggestions:
        parts.append(
            "A code reviewer provided the following "
            "suggestions on the previous iteration. "
            "Incorporate them as you implement the spec.\n\n"
            "<reviewer_suggestions>\n"
            f"{reviewer_suggestions}\n"
            "</reviewer_suggestions>\n"
        )
    parts.append(spec_text)
    return "\n".join(parts)


def build_reviewer_prompt(
    spec_text: str,
    *,
    is_continuation: bool,
) -> str:
    """Render the reviewer prompt."""
    return spec_text


# ---------------------------------------------------------------------------
# slop-code wrapper
# ---------------------------------------------------------------------------


def run_slop_code(
    problem: str,
    model: str,
    prompt_template: Path,
    output_dir: Path,
    budget_fraction: float,
    total_budget: float,
) -> dict:
    """Invoke ``slop-code run`` as a subprocess.

    Returns a dict with keys:
        cost, tokens, pass_rate, erosion, verbosity, exit_code
    """
    _ = total_budget * budget_fraction  # reserved for future use
    cmd = [
        sys.executable, "-m", "slop_code",
        "run",
        "--problem", problem,
        "--model", model,
        "--prompt", str(prompt_template),
        "--evaluate",
    ]

    result = subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=3600,
    )

    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "cost": 0.0,
        "tokens": 0,
    }


# ---------------------------------------------------------------------------
# Core loop
# ---------------------------------------------------------------------------


def run_two_agent(
    problem: str,
    model: str,
    implementer_prompt: Path,
    reviewer_prompt: Path,
    budget_split: int,
    budget: float,
    output_dir: Path,
) -> RunState:
    """Execute the two-agent loop over all checkpoints.

    For each checkpoint:
      1. Implementer runs with budget_split% of the budget.
      2. Reviewer runs with (100-budget_split)% of the budget.
      3. Per-checkpoint metrics recorded.
      4. Reviewer output fed back as context for next iteration.

    Returns the accumulated ``RunState``.
    """
    state = RunState(
        problem=problem,
        model=model,
        budget=budget,
        budget_split=budget_split,
        output_dir=output_dir,
    )

    # Discover checkpoints from problem config
    problem_dir = PROBLEMS_DIR / problem
    checkpoints = sorted(
        d.name
        for d in problem_dir.iterdir()
        if d.is_dir() and d.name.startswith("checkpoint_")
    )

    if not checkpoints:
        typer.echo(
            f"Error: no checkpoints found for problem "
            f"'{problem}' in {problem_dir}",
            err=True,
        )
        raise SystemExit(1)

    _implementer_fraction = budget_split / 100.0

    for idx, checkpoint_name in enumerate(checkpoints):
        # Check budget before each checkpoint
        if is_budget_exceeded(state.cumulative_cost, budget):
            typer.echo(
                f"Budget cap exceeded: "
                f"${state.cumulative_cost:.2f} > "
                f"${budget:.2f}. "
                f"Saving partial results.",
                err=True,
            )
            state.budget_exceeded = True
            state.save_results()
            raise SystemExit(1)

        is_continuation = idx > 0
        spec_file = problem_dir / f"{checkpoint_name}.md"
        if not spec_file.exists():
            # Some problems use nested structure
            spec_file = problem_dir / checkpoint_name / "spec.md"
        spec_text = (
            spec_file.read_text()
            if spec_file.exists()
            else f"Checkpoint: {checkpoint_name}"
        )

        # -- Implementer phase --
        # Build prompt (used by canary-mode / actual runs)
        build_implementer_prompt(
            spec_text=spec_text,
            is_continuation=is_continuation,
            reviewer_suggestions=(
                state.last_reviewer_suggestions
            ),
        )

        # In a real run this invokes slop-code; for now we
        # record structural placeholders.  The actual
        # invocation is wired up by the canary-mode and
        # runner-resilience features.
        impl_cost = 0.0
        impl_tokens = 0
        review_cost = 0.0
        review_tokens = 0

        # -- Reviewer phase --
        build_reviewer_prompt(
            spec_text=spec_text,
            is_continuation=is_continuation,
        )

        # Store reviewer output for next iteration
        state.last_reviewer_suggestions = None

        # Record metrics
        metrics = CheckpointMetrics(
            pass_rate=0.0,
            erosion=0.0,
            verbosity=0.0,
            tokens_implementer=impl_tokens,
            tokens_reviewer=review_tokens,
            cost=impl_cost + review_cost,
        )
        state.checkpoint_metrics[checkpoint_name] = metrics

    state.save_results()
    return state


# ---------------------------------------------------------------------------
# Typer CLI
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="two-agent-runner",
    help=(
        "Run a two-agent (Implementer + Reviewer) experiment "
        "on a SlopCodeBench problem."
    ),
    add_completion=False,
)


@app.command()
def main(
    problem: str | None = typer.Option(
        None,
        "--problem",
        help="Problem name (required unless --canary).",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Model name or alias (required unless --canary).",
    ),
    implementer_prompt: str = typer.Option(
        DEFAULT_IMPLEMENTER_PROMPT,
        "--implementer-prompt",
        help="Path to implementer Jinja prompt template.",
    ),
    reviewer_prompt: str = typer.Option(
        DEFAULT_REVIEWER_PROMPT,
        "--reviewer-prompt",
        help="Path to reviewer Jinja prompt template.",
    ),
    budget_split: int = typer.Option(
        70,
        "--budget-split",
        help=(
            "Percentage of per-checkpoint budget for the "
            "implementer (1-99)."
        ),
    ),
    budget: float | None = typer.Option(
        None,
        "--budget",
        help="Maximum spend for this experiment in USD.",
    ),
    canary: bool = typer.Option(  # noqa: FBT001
        False,  # noqa: FBT003
        "--canary",
        help=(
            "Run a quick $0.50 canary to validate "
            "Docker, API keys, and pipeline."
        ),
    ),
) -> None:
    """Run a two-agent experiment on a SlopCodeBench problem."""

    # -- Canary mode defaults --
    if canary:
        problem = problem or "file_backup"
        model = model or "opus-4.5"
        budget = budget if budget is not None else 0.50

    # -- Validate required args --
    if not problem:
        typer.echo(
            "Error: --problem is required "
            "(or use --canary).",
            err=True,
        )
        raise SystemExit(1)
    if not model:
        typer.echo(
            "Error: --model is required "
            "(or use --canary).",
            err=True,
        )
        raise SystemExit(1)
    if budget is None:
        typer.echo(
            "Error: --budget is required.",
            err=True,
        )
        raise SystemExit(1)

    # -- Validate inputs --
    validate_budget_split(budget_split)
    model = validate_model(model)
    problem = validate_problem(problem)
    impl_prompt_path = validate_prompt_template(
        implementer_prompt,
    )
    rev_prompt_path = validate_prompt_template(
        reviewer_prompt,
    )

    output_dir = build_output_dir(problem, model)

    typer.echo(
        f"Starting two-agent run\n"
        f"  problem:      {problem}\n"
        f"  model:        {model}\n"
        f"  budget:       ${budget:.2f}\n"
        f"  budget_split: {budget_split}% implementer / "
        f"{100 - budget_split}% reviewer\n"
        f"  output:       {output_dir}\n"
    )

    state = run_two_agent(
        problem=problem,
        model=model,
        implementer_prompt=impl_prompt_path,
        reviewer_prompt=rev_prompt_path,
        budget_split=budget_split,
        budget=budget,
        output_dir=output_dir,
    )

    typer.echo(
        f"\nRun complete. "
        f"Checkpoints: {len(state.checkpoint_metrics)}, "
        f"Cost: ${state.cumulative_cost:.2f}"
    )
    if state.budget_exceeded:
        typer.echo(
            "WARNING: Budget was exceeded. "
            "Partial results saved.",
            err=True,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    app()
