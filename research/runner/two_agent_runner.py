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
import logging
import os
import shutil
import subprocess
import sys
import uuid
from datetime import UTC
from datetime import datetime
from pathlib import Path

import typer
from pydantic import BaseModel
from pydantic import Field

logger = logging.getLogger(__name__)

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

# Canary defaults
CANARY_PROBLEM = "file_backup"
CANARY_BUDGET = 0.50
CANARY_BUDGET_SPLIT = 70
CANARY_DEFAULT_MODEL = "opus-4.5"


# ---------------------------------------------------------------------------
# Canary error
# ---------------------------------------------------------------------------


class CanaryError(Exception):
    """Raised when a canary preflight or pipeline step fails.

    Attributes:
        component: Which component failed (e.g. "Docker",
            "API", "Claude CLI", "Implementer", "Reviewer",
            "Evaluation").
        detail: Human-readable detail about the failure.
    """

    def __init__(
        self, component: str, detail: str,
    ) -> None:
        self.component = component
        self.detail = detail
        super().__init__(
            f"Canary failed [{component}]: {detail}",
        )


# ---------------------------------------------------------------------------
# Preflight checks (used by canary mode)
# ---------------------------------------------------------------------------


def check_docker() -> None:
    """Verify the Docker daemon is reachable.

    Raises ``CanaryError`` with component="Docker" on failure.
    """
    try:
        result = subprocess.run(  # noqa: S603
            ["docker", "info"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            raise CanaryError(
                "Docker",
                "Docker daemon is not running or not "
                "accessible. 'docker info' exited with "
                f"code {result.returncode}.\n"
                f"stderr: {result.stderr.strip()[:200]}",
            )
    except FileNotFoundError:
        raise CanaryError(
            "Docker",
            "Docker CLI not found on PATH. "
            "Is Docker installed?",
        )
    except subprocess.TimeoutExpired:
        raise CanaryError(
            "Docker",
            "'docker info' timed out after 15 s. "
            "The Docker daemon may be unresponsive.",
        )


def check_api_key(model_name: str) -> None:
    """Verify that an API key is available for *model_name*.

    Raises ``CanaryError`` with component="API" on failure.
    """
    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from slop_code.agent_runner.credentials import API_KEY_STORE
    from slop_code.agent_runner.credentials import CredentialNotFoundError
    from slop_code.common.llms import ModelCatalog

    model_def = ModelCatalog.get(model_name)
    if model_def is None:
        raise CanaryError(
            "API",
            f"Model '{model_name}' not found in catalog.",
        )

    try:
        API_KEY_STORE.resolve(model_def.provider)
    except (CredentialNotFoundError, ValueError) as exc:
        raise CanaryError(
            "API",
            f"Cannot resolve API key for provider "
            f"'{model_def.provider}': {exc}",
        ) from exc


def check_claude_cli() -> None:
    """Verify that the Claude Code CLI is reachable.

    Raises ``CanaryError`` with component="Claude CLI"
    on failure.
    """
    try:
        result = subprocess.run(  # noqa: S603
            ["claude", "--version"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            raise CanaryError(
                "Claude CLI",
                "'claude --version' exited with code "
                f"{result.returncode}.\n"
                f"stderr: {result.stderr.strip()[:200]}",
            )
    except FileNotFoundError:
        raise CanaryError(
            "Claude CLI",
            "Claude Code CLI ('claude') not found "
            "on PATH.",
        )
    except subprocess.TimeoutExpired:
        raise CanaryError(
            "Claude CLI",
            "'claude --version' timed out after 15 s.",
        )


def run_preflight_checks(model_name: str) -> None:
    """Run all canary preflight checks in order.

    Checks: Docker -> API key -> Claude CLI.
    Stops on the first failure with a descriptive
    ``CanaryError``.
    """
    check_docker()
    check_api_key(model_name)
    check_claude_cli()


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

    run_id: str = Field(
        default_factory=lambda: uuid.uuid4().hex[:12],
    )
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

    @property
    def container_name_prefix(self) -> str:
        """Unique Docker container name prefix for this run."""
        return f"scbench-{self.run_id}"

    def save_results(self) -> None:
        """Persist metrics to *output_dir*/two_agent_metrics.json."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_id": self.run_id,
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
    run_id: str | None = None,
) -> Path:
    """Build an output directory path compatible with slop-code eval.

    A short *run_id* suffix is appended so that parallel runs
    never collide even when started in the same second.

    Layout::

        outputs/two_agent_<model>_<problem>_<ts>_<run_id>/
            <problem>/
                checkpoint_N/
                    snapshot/
    """
    if base is None:
        base = OUTPUTS_DIR
    if run_id is None:
        run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    run_name = (
        f"two_agent_{model}_{problem}_{ts}_{run_id}"
    )
    return base / run_name


# ---------------------------------------------------------------------------
# Resume helpers
# ---------------------------------------------------------------------------


def detect_completed_checkpoints(
    output_dir: Path,
) -> dict[str, CheckpointMetrics]:
    """Detect already-completed checkpoints in *output_dir*.

    Reads ``two_agent_metrics.json`` if it exists and returns
    a dict mapping checkpoint names to their saved metrics.
    Returns an empty dict when no prior state is found.
    """
    metrics_file = output_dir / "two_agent_metrics.json"
    if not metrics_file.is_file():
        return {}
    try:
        data = json.loads(metrics_file.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    checkpoints: dict[str, CheckpointMetrics] = {}
    for name, raw in data.get("checkpoints", {}).items():
        try:
            checkpoints[name] = CheckpointMetrics(**raw)
        except Exception:  # noqa: BLE001, S112
            continue
    return checkpoints


def load_resume_state(
    output_dir: Path,
) -> dict | None:
    """Load the full metrics payload from a prior run.

    Returns the parsed JSON dict, or ``None`` when no
    resumable state exists.
    """
    metrics_file = output_dir / "two_agent_metrics.json"
    if not metrics_file.is_file():
        return None
    try:
        return json.loads(metrics_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None


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
    run_id: str | None = None,
    phase: str = "implementer",
) -> dict:
    """Invoke ``slop-code run`` as a subprocess.

    When *run_id* is provided it is passed via the
    ``SCBENCH_RUN_ID`` environment variable so that
    downstream Docker containers receive a unique name
    prefix, preventing collisions between parallel runs.

    The *budget_fraction* of *total_budget* is passed as
    the per-phase cost limit so that budget split is
    enforced at the harness level.

    Returns a dict with keys:
        cost, tokens, pass_rate, erosion, verbosity,
        exit_code, output_dir
    """
    cost_limit = round(
        total_budget * budget_fraction, 4,
    )
    cmd = [
        sys.executable, "-m", "slop_code",
        "run",
        "--problem", problem,
        "--model", model,
        "--prompt", str(prompt_template),
        "--evaluate",
        f"agent.cost_limits.cost_limit={cost_limit}",
    ]

    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }
    if run_id:
        env["SCBENCH_RUN_ID"] = (
            f"{run_id}-{phase}"
        )

    result = subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=3600,
        env=env,
    )

    # Parse cost and metrics from the output directory
    parsed = _parse_slop_code_output(
        problem, result.stdout,
    )

    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "cost": parsed.get("cost", 0.0),
        "tokens": parsed.get("tokens", 0),
        "pass_rate": parsed.get("pass_rate", 0.0),
        "erosion": parsed.get("erosion", 0.0),
        "verbosity": parsed.get("verbosity", 0.0),
        "output_dir": parsed.get("output_dir"),
    }


def _parse_slop_code_output(
    problem: str,
    stdout: str,
) -> dict:
    """Parse metrics from the latest slop-code output dir.

    Reads ``checkpoint_results.jsonl`` from the most recent
    output directory matching the problem name.

    Returns a dict with cost, tokens, pass_rate, erosion,
    verbosity, and output_dir.
    """
    result: dict = {
        "cost": 0.0,
        "tokens": 0,
        "pass_rate": 0.0,
        "erosion": 0.0,
        "verbosity": 0.0,
        "output_dir": None,
    }

    run_dir = _find_latest_run_dir(problem)
    if run_dir is None:
        return result

    run_dir_path, _ = run_dir
    result["output_dir"] = str(run_dir_path)

    # Parse checkpoint_results.jsonl
    results_file = run_dir_path / "checkpoint_results.jsonl"
    if results_file.exists():
        try:
            for line in results_file.read_text().splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                # Use flattened metric keys if available
                if "strict_pass_rate" in data:
                    result["pass_rate"] = float(
                        data["strict_pass_rate"],
                    )
                elif "total_counts" in data:
                    total = data.get("total_counts", 0)
                    passed = data.get("pass_counts", 0)
                    if total > 0:
                        result["pass_rate"] = round(
                            passed / total, 4,
                        )
                if "erosion" in data:
                    result["erosion"] = float(
                        data["erosion"],
                    )
                if "verbosity" in data:
                    result["verbosity"] = float(
                        data["verbosity"],
                    )
                if "cost" in data:
                    result["cost"] = float(data["cost"])
                break  # Use first checkpoint line
        except (json.JSONDecodeError, OSError):
            pass

    return result


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
    run_id: str | None = None,
    max_checkpoints: int | None = None,
) -> RunState:
    """Execute the two-agent loop over all checkpoints.

    If *output_dir* already contains results from a prior
    (crashed) run, completed checkpoints are preserved and
    execution resumes from the next incomplete checkpoint.

    Each run is identified by *run_id* (auto-generated when
    ``None``).  The id is embedded in Docker container names
    so that parallel runs never collide.

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
        **({"run_id": run_id} if run_id else {}),
    )

    # -- Resume: detect previously completed checkpoints --
    completed = detect_completed_checkpoints(output_dir)
    if completed:
        state.checkpoint_metrics.update(completed)
        logger.info(
            "Resuming run: %d completed checkpoint(s) "
            "found in %s",
            len(completed),
            output_dir,
        )
        typer.echo(
            f"Resuming: {len(completed)} completed "
            f"checkpoint(s) found, skipping them.",
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

    # Optionally constrain the number of checkpoints
    # (used by canary to limit to checkpoint_1 only).
    if max_checkpoints is not None:
        checkpoints = checkpoints[:max_checkpoints]

    _implementer_fraction = budget_split / 100.0
    _reviewer_fraction = 1.0 - _implementer_fraction

    for idx, checkpoint_name in enumerate(checkpoints):
        # Skip already-completed checkpoints (resume)
        if checkpoint_name in completed:
            logger.info(
                "Skipping completed checkpoint: %s",
                checkpoint_name,
            )
            continue

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
            spec_file = (
                problem_dir / checkpoint_name / "spec.md"
            )
        spec_text = (
            spec_file.read_text()
            if spec_file.exists()
            else f"Checkpoint: {checkpoint_name}"
        )

        # -- Implementer phase --
        build_implementer_prompt(
            spec_text=spec_text,
            is_continuation=is_continuation,
            reviewer_suggestions=(
                state.last_reviewer_suggestions
            ),
        )

        typer.echo(
            f"  [{checkpoint_name}] Implementer phase "
            f"(budget: ${budget * _implementer_fraction:.2f})"
            " ...",
        )

        impl_result = run_slop_code(
            problem=problem,
            model=model,
            prompt_template=implementer_prompt,
            output_dir=output_dir,
            budget_fraction=_implementer_fraction,
            total_budget=budget,
            run_id=state.run_id,
            phase="implementer",
        )
        impl_cost = impl_result.get("cost", 0.0)
        impl_tokens = impl_result.get("tokens", 0)

        # Copy implementer artifacts into eval-compatible
        # directory layout under output_dir.
        _copy_checkpoint_artifacts(
            problem=problem,
            checkpoint_name=checkpoint_name,
            source_output=impl_result.get("output_dir"),
            target_dir=output_dir,
        )

        # -- Reviewer phase --
        build_reviewer_prompt(
            spec_text=spec_text,
            is_continuation=is_continuation,
        )

        typer.echo(
            f"  [{checkpoint_name}] Reviewer phase "
            f"(budget: ${budget * _reviewer_fraction:.2f})"
            " ...",
        )

        review_result = run_slop_code(
            problem=problem,
            model=model,
            prompt_template=reviewer_prompt,
            output_dir=output_dir,
            budget_fraction=_reviewer_fraction,
            total_budget=budget,
            run_id=state.run_id,
            phase="reviewer",
        )
        review_cost = review_result.get("cost", 0.0)
        review_tokens = review_result.get("tokens", 0)

        # Parse reviewer suggestions from output and
        # propagate to next implementer iteration.
        state.last_reviewer_suggestions = (
            _extract_reviewer_suggestions(
                review_result,
            )
        )

        # Copy reviewer artifacts (may overwrite
        # implementer snapshot with improved code)
        _copy_checkpoint_artifacts(
            problem=problem,
            checkpoint_name=checkpoint_name,
            source_output=review_result.get("output_dir"),
            target_dir=output_dir,
        )

        # Use the best available pass_rate (prefer
        # reviewer if it ran successfully, else
        # implementer)
        pass_rate = (
            review_result.get("pass_rate", 0.0)
            or impl_result.get("pass_rate", 0.0)
        )
        erosion = (
            review_result.get("erosion", 0.0)
            or impl_result.get("erosion", 0.0)
        )
        verbosity = (
            review_result.get("verbosity", 0.0)
            or impl_result.get("verbosity", 0.0)
        )

        # Record metrics
        metrics = CheckpointMetrics(
            pass_rate=pass_rate,
            erosion=erosion,
            verbosity=verbosity,
            tokens_implementer=impl_tokens,
            tokens_reviewer=review_tokens,
            cost=impl_cost + review_cost,
        )
        state.checkpoint_metrics[checkpoint_name] = metrics

        # Persist checkpoint completion state to disk
        # immediately for crash-safe resume.
        state.save_results()
        typer.echo(
            f"  [{checkpoint_name}] Complete. "
            f"Cost: ${impl_cost + review_cost:.4f}, "
            f"Pass rate: {pass_rate:.4f}",
        )

    state.save_results()
    return state


# ---------------------------------------------------------------------------
# Artifact helpers
# ---------------------------------------------------------------------------


def _copy_checkpoint_artifacts(
    problem: str,
    checkpoint_name: str,
    source_output: str | None,
    target_dir: Path,
) -> None:
    """Copy checkpoint artifacts from slop-code output into
    the eval-compatible directory layout under *target_dir*.

    Layout::

        target_dir/
            <problem>/
                <checkpoint_name>/
                    snapshot/
                        ...solution files...
            checkpoint_results.jsonl  (appended)
    """
    if source_output is None:
        return

    src = Path(source_output)
    if not src.is_dir():
        return

    # Copy problem/<checkpoint>/snapshot/ if it exists
    src_problem = src / problem
    if not src_problem.is_dir():
        return

    src_cp = src_problem / checkpoint_name
    if src_cp.is_dir():
        dst_cp = target_dir / problem / checkpoint_name
        if dst_cp.exists():
            shutil.rmtree(dst_cp)
        shutil.copytree(src_cp, dst_cp)

    # Append checkpoint results to target JSONL
    src_results = src / "checkpoint_results.jsonl"
    if src_results.is_file():
        dst_results = target_dir / "checkpoint_results.jsonl"
        with dst_results.open("a") as f:
            for line in src_results.read_text().splitlines():
                if line.strip():
                    f.write(line + "\n")

    # Copy config.yaml and environment.yaml if present
    for cfg_name in ("config.yaml", "environment.yaml"):
        cfg_src = src / cfg_name
        cfg_dst = target_dir / cfg_name
        if cfg_src.is_file() and not cfg_dst.is_file():
            shutil.copy2(cfg_src, cfg_dst)


def _extract_reviewer_suggestions(
    review_result: dict,
) -> str | None:
    """Extract reviewer suggestions from slop-code output.

    Looks for the reviewer's code diff or stderr output
    that contains actionable suggestions. Returns ``None``
    when no suggestions are found.
    """
    # Try to extract from stderr (reviewer output notes)
    stderr = review_result.get("stderr", "")

    # If the reviewer produced output, use it as suggestions
    suggestions_parts: list[str] = []

    # Look for output directory to find reviewer's solution
    output_dir = review_result.get("output_dir")
    if output_dir is not None:
        out_path = Path(output_dir)
        # Find any .py files in the snapshot directory
        for snapshot in out_path.rglob("snapshot"):
            if snapshot.is_dir():
                for py_file in snapshot.glob("*.py"):
                    try:
                        content = py_file.read_text()
                        if content.strip():
                            suggestions_parts.append(
                                f"Reviewer's refactored "
                                f"{py_file.name}:\n"
                                f"{content[:2000]}",
                            )
                    except OSError:
                        pass

    if suggestions_parts:
        return "\n\n".join(suggestions_parts)

    # Fall back to stderr for any review notes
    if stderr and len(stderr.strip()) > 20:
        return stderr[:2000]

    return None


# ---------------------------------------------------------------------------
# Canary pipeline
# ---------------------------------------------------------------------------


def run_canary(
    problem: str = CANARY_PROBLEM,
    model: str = CANARY_DEFAULT_MODEL,
    budget: float = CANARY_BUDGET,
    budget_split: int = CANARY_BUDGET_SPLIT,
    implementer_prompt: Path | None = None,
    reviewer_prompt: Path | None = None,
) -> RunState:
    """Execute a canary run exercising the full pipeline.

    Steps:
      1. Preflight checks (Docker, API key, Claude CLI).
      2. Invoke ``slop-code run`` for *checkpoint_1* only
         (implementer phase) to exercise Docker container
         launch, API auth, and agent execution.
      3. Invoke a reviewer pass on the implementer output.
      4. Run ``slop-code eval`` on the output to verify
         eval compatibility.
      5. Save two-agent metrics.

    On any component failure a ``CanaryError`` is raised
    whose ``component`` field names the failing stage.

    Returns the ``RunState`` on success.
    """
    impl_prompt = implementer_prompt or validate_prompt_template(
        DEFAULT_IMPLEMENTER_PROMPT,
    )
    rev_prompt = reviewer_prompt or validate_prompt_template(
        DEFAULT_REVIEWER_PROMPT,
    )

    # Resolve canonical model name
    model = validate_model(model)

    # ── Step 1: Preflight ──────────────────────────────
    typer.echo("Canary: running preflight checks ...")
    run_preflight_checks(model)
    typer.echo("Canary: preflight OK (Docker, API, CLI)")

    # ── Prepare output directory ───────────────────────
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUTS_DIR / f"canary_{ts}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 2-4: Run two-agent loop (checkpoint_1 only)
    typer.echo(
        "Canary: running two-agent loop "
        f"(problem={problem}, checkpoint_1 only) ...",
    )

    try:
        state = run_two_agent(
            problem=problem,
            model=model,
            implementer_prompt=impl_prompt,
            reviewer_prompt=rev_prompt,
            budget_split=budget_split,
            budget=budget,
            output_dir=output_dir,
            max_checkpoints=1,
        )
    except SystemExit as exc:
        raise CanaryError(
            "Pipeline",
            f"Two-agent loop exited with code "
            f"{exc.code}.",
        ) from exc

    typer.echo("Canary: two-agent loop complete.")

    # ── Step 5: Evaluation ─────────────────────────────
    typer.echo("Canary: running evaluation ...")
    slop_run_env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }
    eval_cmd = [
        sys.executable, "-m", "slop_code",
        "eval",
        str(output_dir),
    ]

    try:
        eval_result = subprocess.run(  # noqa: S603
            eval_cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=120,
            env=slop_run_env,
        )
    except subprocess.TimeoutExpired:
        raise CanaryError(
            "Evaluation",
            "slop-code eval timed out after 120 s.",
        )

    if eval_result.returncode != 0:
        raise CanaryError(
            "Evaluation",
            "slop-code eval exited with code "
            f"{eval_result.returncode}.\n"
            f"stderr (last 500 chars): "
            f"{eval_result.stderr[-500:]}",
        )

    typer.echo("Canary: evaluation complete.")

    # ── Step 6: Update metrics from eval ───────────────
    results_file = output_dir / "checkpoint_results.jsonl"
    if results_file.exists():
        cp_metrics = state.checkpoint_metrics.get(
            "checkpoint_1",
        )
        if cp_metrics is not None:
            _update_metrics_from_results(
                cp_metrics, results_file,
            )

    # Enforce budget cap
    if state.cumulative_cost > budget:
        state.budget_exceeded = True

    state.save_results()
    return state


def _find_latest_run_dir(
    problem: str,
) -> tuple[Path, Path] | None:
    """Find the most recent slop-code output containing *problem*.

    Returns ``(run_dir, problem_dir)`` or ``None``.
    """
    if not OUTPUTS_DIR.exists():
        return None
    candidates: list[tuple[float, Path]] = []
    for d in OUTPUTS_DIR.iterdir():
        if not d.is_dir():
            continue
        problem_dir = d / problem
        if problem_dir.is_dir():
            candidates.append((d.stat().st_mtime, d))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    best = candidates[0][1]
    return best, best / problem


def _update_metrics_from_results(
    metrics: CheckpointMetrics,
    results_file: Path,
) -> None:
    """Parse *checkpoint_results.jsonl* and update *metrics*.

    Reads the first matching line and extracts pass_rate
    using the flattened metric schema (``strict_pass_rate``,
    ``total_tests``, ``passed_tests``).  Falls back to
    ``pass_counts``/``total_counts`` for legacy data.
    """
    try:
        for line in results_file.read_text().splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            # Prefer flattened metric keys
            if "strict_pass_rate" in data:
                metrics.pass_rate = float(
                    data["strict_pass_rate"],
                )
            else:
                total = data.get("total_tests", 0)
                passed = data.get("passed_tests", 0)
                if total > 0:
                    metrics.pass_rate = round(
                        passed / total, 4,
                    )
            if "cost" in data:
                metrics.cost = float(data["cost"])
            break
    except (json.JSONDecodeError, OSError):
        pass


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
    output_dir: str | None = typer.Option(
        None,
        "--output-dir",
        help=(
            "Resume a prior run by pointing to its "
            "output directory. Completed checkpoints "
            "are preserved."
        ),
    ),
) -> None:
    """Run a two-agent experiment on a SlopCodeBench problem."""

    # -- Canary mode --
    if canary:
        canary_problem = problem or CANARY_PROBLEM
        canary_model = model or CANARY_DEFAULT_MODEL
        canary_budget_val = (
            budget if budget is not None else CANARY_BUDGET
        )
        typer.echo(
            f"Canary mode: problem={canary_problem}, "
            f"model={canary_model}, "
            f"budget=${canary_budget_val:.2f}, "
            f"budget_split={budget_split}"
        )
        try:
            state = run_canary(
                problem=canary_problem,
                model=canary_model,
                budget=canary_budget_val,
                budget_split=budget_split,
            )
        except CanaryError as exc:
            typer.echo(
                f"CANARY FAILED [{exc.component}]: "
                f"{exc.detail}",
                err=True,
            )
            raise SystemExit(1) from exc

        typer.echo(
            f"\nCanary complete. "
            f"Cost: ${state.cumulative_cost:.2f}, "
            f"Output: {state.output_dir}"
        )
        if state.budget_exceeded:
            typer.echo(
                "WARNING: canary budget exceeded.",
                err=True,
            )
            raise SystemExit(1)
        return

    # -- Validate required args for normal mode --
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

    # Generate a unique run_id for concurrent isolation
    rid = uuid.uuid4().hex[:12]

    # Use explicit --output-dir for resume, otherwise create
    # a fresh directory with the run_id embedded.
    if output_dir is not None:
        resolved_output = Path(output_dir)
        if not resolved_output.is_absolute():
            resolved_output = REPO_ROOT / resolved_output
    else:
        resolved_output = build_output_dir(
            problem, model, run_id=rid,
        )

    typer.echo(
        f"Starting two-agent run  (run_id={rid})\n"
        f"  problem:      {problem}\n"
        f"  model:        {model}\n"
        f"  budget:       ${budget:.2f}\n"
        f"  budget_split: {budget_split}% implementer / "
        f"{100 - budget_split}% reviewer\n"
        f"  output:       {resolved_output}\n"
    )

    state = run_two_agent(
        problem=problem,
        model=model,
        implementer_prompt=impl_prompt_path,
        reviewer_prompt=rev_prompt_path,
        budget_split=budget_split,
        budget=budget,
        output_dir=resolved_output,
        run_id=rid,
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
