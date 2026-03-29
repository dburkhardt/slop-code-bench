"""Reviewer-Coder multi-agent: Claude Code with periodic code review.

Runs Claude Code for a batch of turns, then invokes a reviewer pass
(also via the claude CLI) that reads the workspace and suggests
quality improvements.  The reviewer's suggestions are prepended to
the next coding invocation so the coder can act on them.
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
import typing as tp
from pathlib import Path

from pydantic import ConfigDict

from slop_code.agent_runner.agent import Agent
from slop_code.agent_runner.agent import AgentConfigBase
from slop_code.agent_runner.agents.claude_code.agent import ClaudeCodeAgent
from slop_code.agent_runner.agents.claude_code.agent import ClaudeCodeConfig
from slop_code.agent_runner.agents.cli_utils import stream_cli_command
from slop_code.agent_runner.credentials import ProviderCredential
from slop_code.agent_runner.models import AgentCostLimits
from slop_code.agent_runner.models import AgentError
from slop_code.agent_runner.registry import register_agent
from slop_code.common.llms import APIPricing
from slop_code.common.llms import ModelDefinition
from slop_code.common.llms import ThinkingPreset
from slop_code.execution.runtime import RuntimeResult

# ---------------------------------------------------------------------------
# Reviewer prompt
# ---------------------------------------------------------------------------

REVIEWER_SYSTEM_PROMPT = """\
You are a senior code quality reviewer. First, run the test suite to \
understand which tests pass and fail. Then read the source files and \
provide specific, actionable suggestions.

Focus on:
1. CODE THAT CAUSES TEST FAILURES: prioritize fixes that help failing \
tests pass without breaking passing tests.
2. DUPLICATION: repeated code blocks that should be shared functions.
3. COMPLEXITY: functions with cyclomatic complexity >10 should be split.
4. DEAD CODE: unused imports, unreachable code, unused variables.

Rules:
- Reference exact function names and file paths.
- For each suggestion, show the exact code to change and the replacement.
- Limit to 3-5 highest-impact suggestions.
- Do NOT suggest adding error handling, logging, types, or docs.
- Do NOT suggest changes that would alter external behaviour.
- Be concise. Each suggestion: 2-3 sentences max."""

CODER_APPEND_PROMPT = """\
Write clean, minimal code. Rules: \
(1) Modify existing functions in-place instead of creating wrappers. \
(2) Never create single-use helper functions. \
(3) Keep cyclomatic complexity per function under 10. \
(4) Extract genuinely shared logic into helpers, but only if used 3+ times. \
(5) If a reviewer provides suggestions, implement them before continuing."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class ReviewerCoderConfig(ClaudeCodeConfig, agent_type="reviewer_coder"):
    """Configuration for the ReviewerCoder multi-agent."""

    model_config = ConfigDict(extra="allow")
    type: tp.Literal["reviewer_coder"] = "reviewer_coder"
    docker_template: Path = (
        Path(__file__).parent.parent / "claude_code" / "docker.j2"
    )

    # Reviewer settings
    coder_turns_per_batch: int = 10
    num_review_cycles: int = 3


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class ReviewerCoderAgent(ClaudeCodeAgent):
    """Multi-agent that alternates Claude Code coding batches with
    reviewer passes, all via the ``claude`` CLI binary.

    Within a single ``run()`` call for one checkpoint:

    1.  Run ``claude --print --max-turns <coder_turns_per_batch>``
        with the task prompt  ->  coder writes code.
    2.  Run ``claude --print`` with the reviewer system prompt
        ->  reviewer reads workspace and returns suggestions.
    3.  Run ``claude --print --max-turns <coder_turns_per_batch>``
        with the suggestions + "continue with the spec"
        ->  coder refactors and continues.
    4.  Repeat for ``num_review_cycles``.
    5.  Final coding batch without a turns cap to finish.

    All invocations share the same Docker workspace, so file
    changes persist across calls.
    """

    def __init__(
        self,
        problem_name: str,
        image: str,
        verbose: bool,
        cost_limits: AgentCostLimits,
        pricing: APIPricing,
        credential: ProviderCredential,
        # Claude Code config
        binary: str,
        model: str,
        timeout: int | None,
        settings: dict,
        env: dict[str, str],
        extra_args: list[str],
        allowed_tools: list[str],
        disallowed_tools: list[str],
        permission_mode: str | None,
        base_url: str | None,
        thinking: ThinkingPreset | None,
        max_thinking_tokens: int | None,
        max_output_tokens: int | None,
        # Reviewer config
        coder_turns_per_batch: int,
        num_review_cycles: int,
        *,
        append_system_prompt: str | None = None,
    ) -> None:
        super().__init__(
            problem_name=problem_name,
            image=image,
            verbose=verbose,
            cost_limits=cost_limits,
            pricing=pricing,
            credential=credential,
            binary=binary,
            model=model,
            timeout=timeout,
            settings=settings,
            env=env,
            extra_args=extra_args,
            append_system_prompt=append_system_prompt,
            allowed_tools=allowed_tools,
            disallowed_tools=disallowed_tools,
            permission_mode=permission_mode,
            base_url=base_url,
            thinking=thinking,
            max_thinking_tokens=max_thinking_tokens,
            max_output_tokens=max_output_tokens,
            agent_name="reviewer_coder",
        )
        self.coder_turns_per_batch = coder_turns_per_batch
        self.num_review_cycles = num_review_cycles
        self._cost_before_invocation: float = 0.0
        self._review_suggestions: list[tuple[int, str]] = []
        self._mid_phase_enabled: bool = False
        self._mid_phase_entrypoint: str = "python main.py"
        self._mid_phase_checkpoint: str = "checkpoint_1"

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def _from_config(
        cls,
        config: AgentConfigBase,
        model: ModelDefinition,
        credential: ProviderCredential,
        problem_name: str,
        verbose: bool,
        image: str | None,
        thinking_preset: ThinkingPreset | None = None,
        thinking_max_tokens: int | None = None,
    ) -> Agent:
        if not isinstance(config, ReviewerCoderConfig):
            raise TypeError(
                f"Expected ReviewerCoderConfig, "
                f"got {type(config).__name__}"
            )
        if image is None:
            raise ValueError("ReviewerCoderAgent requires an image")
        if model.pricing is None:
            raise AgentError(
                "ReviewerCoderAgent requires pricing configuration"
            )

        params = cls._resolve_config_params(
            config,
            model,
            credential,
            agent_settings_keys=("reviewer_coder", "claude_code"),
            thinking_preset=thinking_preset,
            thinking_max_tokens=thinking_max_tokens,
        )

        return cls(
            problem_name=problem_name,
            image=image,
            verbose=verbose,
            cost_limits=config.cost_limits,
            pricing=model.pricing,
            credential=credential,
            binary=config.binary,
            model=params.model_slug,
            timeout=config.timeout,
            settings=config.settings,
            env=params.env,
            extra_args=config.extra_args,
            allowed_tools=config.allowed_tools,
            disallowed_tools=config.disallowed_tools,
            permission_mode=config.permission_mode,
            base_url=params.base_url,
            thinking=params.thinking,
            max_thinking_tokens=params.max_thinking_tokens,
            max_output_tokens=config.max_output_tokens,
            coder_turns_per_batch=config.coder_turns_per_batch,
            num_review_cycles=config.num_review_cycles,
        )

    # ------------------------------------------------------------------
    # CLI helpers
    # ------------------------------------------------------------------

    def _build_reviewer_args(self) -> list[str]:
        """Build ``claude`` CLI args for a reviewer invocation."""
        args = [
            self.binary,
            "--output-format", "stream-json",
            "--verbose",
            "--model", shlex.quote(self.model),
            "--max-turns", "1",
            "--append-system-prompt",
            shlex.quote(REVIEWER_SYSTEM_PROMPT),
        ]
        if self.permission_mode:
            args.extend([
                "--permission-mode",
                shlex.quote(self.permission_mode),
            ])
        args.append("--print")
        args.append("--")
        return args

    # ------------------------------------------------------------------
    # Phase tracking
    # ------------------------------------------------------------------

    def _record_phase(self, label: str, role: str, cycle: int) -> None:
        """Record cost/step data for a completed phase."""
        prev_cost = self.telemetry.get("_last_cost", 0.0)
        phase_cost = self.usage.cost - prev_cost
        self.telemetry.setdefault("phases", []).append({
            "label": label,
            "role": role,
            "cycle": cycle,
            "phase_cost": round(phase_cost, 6),
            "cumulative_cost": round(self.usage.cost, 6),
            "cumulative_steps": self.usage.steps,
        })
        self.telemetry["_last_cost"] = self.usage.cost

    # ------------------------------------------------------------------
    # Mid-phase evaluation
    # ------------------------------------------------------------------

    def setup_mid_phase_eval(self, problem, checkpoint) -> None:
        """Copy test files into workspace for mid-phase evaluation."""
        try:
            problem_tests = problem.path / "tests"
            if not problem_tests.exists():
                self.log.debug("reviewer_coder.mid_phase.no_tests", path=str(problem_tests))
                return

            workspace_tests = self.workspace / ".evaluation_tests"
            workspace_tests.mkdir(parents=True, exist_ok=True)

            # Copy test files for current and prior checkpoints
            for item in problem_tests.iterdir():
                if item.is_file() and item.suffix == ".py":
                    shutil.copy2(item, workspace_tests / item.name)
                elif item.is_dir():
                    shutil.copytree(item, workspace_tests / item.name, dirs_exist_ok=True)

            # Store entrypoint and checkpoint for pytest args
            self._mid_phase_entrypoint = f"python {problem.entry_file}"
            self._mid_phase_checkpoint = checkpoint.name

            self._mid_phase_enabled = True
            self.log.info("reviewer_coder.mid_phase.setup", test_dir=str(workspace_tests))
        except Exception as e:
            self.log.warning("reviewer_coder.mid_phase.setup_failed", error=str(e))
            self._mid_phase_enabled = False

    def _run_mid_phase_pytest(self, label: str) -> dict | None:
        """Run a quick pytest inside the workspace for progress tracking."""
        if not self._mid_phase_enabled:
            return None

        try:
            proc = subprocess.run(
                ["uvx", "--from", "pytest", "pytest",
                 ".evaluation_tests/",
                 f"--entrypoint={self._mid_phase_entrypoint}",
                 f"--checkpoint={self._mid_phase_checkpoint}",
                 "--tb=no", "--no-header", "-q"],
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = proc.stdout + proc.stderr

            passed = 0
            failed = 0
            match = re.search(r"(\d+) passed", output)
            if match:
                passed = int(match.group(1))
            match = re.search(r"(\d+) failed", output)
            if match:
                failed = int(match.group(1))
            match = re.search(r"(\d+) error", output)
            if match:
                failed += int(match.group(1))
            total = passed + failed
            pass_rate = passed / total if total > 0 else 0.0

            mid_result = {
                "label": label,
                "passed": passed,
                "total": total,
                "pass_rate": round(pass_rate, 4),
            }

            self.log.info(
                "reviewer_coder.mid_phase_eval",
                label=label,
                pass_rate=pass_rate,
                passed=passed,
                total=total,
            )
            return mid_result
        except Exception as e:
            self.log.warning("reviewer_coder.mid_phase_eval.failed", error=str(e))
            return None

    # ------------------------------------------------------------------
    # Running a single claude invocation
    # ------------------------------------------------------------------

    def _invoke_claude(
        self,
        cli_args: list[str],
        prompt: str,
        env_overrides: dict[str, str],
        label: str = "claude",
    ) -> RuntimeResult | None:
        """Run one ``claude --print`` invocation and accumulate
        usage onto ``self.usage``.
        """
        command = " ".join(cli_args) + " " + shlex.quote(prompt)

        # Save cost before this invocation so we can accumulate
        self._cost_before_invocation = self.usage.cost

        self.log.info(
            f"reviewer_coder.invoke.{label}.start",
            prompt_chars=len(prompt),
        )

        gen = stream_cli_command(
            runtime=self.runtime,
            command=command,
            parser=self.parse_line,
            env=env_overrides,
            timeout=(
                float(self.timeout) if self.timeout is not None
                else None
            ),
        )

        added_msg_ids: set[str] = set()
        result: RuntimeResult | None = None

        for step in gen:
            if not isinstance(step, tuple):
                result = step
                break
            cost, tokens, payload = step
            if payload is None:
                continue

            # Track error state
            self._process_payload_for_error(payload)

            msg_id = (
                payload.get("message", {}).get("id")
            )

            if cost is not None:
                # "result" payload: total_cost_usd for THIS
                # invocation.  Add to prior-invocation total.
                self.usage.cost = (
                    self._cost_before_invocation + cost
                )
                if tokens is not None:
                    self.usage.net_tokens += tokens
                    self.usage.current_tokens = tokens
            elif (
                tokens is not None
                and msg_id not in added_msg_ids
            ):
                step_cost = self.pricing.get_cost(tokens)
                self.usage.cost += step_cost
                self.usage.steps += 1
                self.usage.current_tokens = tokens
                self.usage.net_tokens += tokens
                if msg_id:
                    added_msg_ids.add(msg_id)

            self.steps.append(payload)

        self.log.info(
            f"reviewer_coder.invoke.{label}.done",
            cost=self.usage.cost,
            steps=self.usage.steps,
        )
        return result

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self, task: str) -> None:
        self.log.info(
            "reviewer_coder.run.start",
            coder_turns=self.coder_turns_per_batch,
            review_cycles=self.num_review_cycles,
        )

        env_overrides = self._build_env_overrides()
        last_suggestions: str | None = None

        for cycle in range(self.num_review_cycles):
            # --- Coding batch ---
            if last_suggestions:
                coder_prompt = (
                    f"A code reviewer has suggested improvements. "
                    f"Implement them, then continue with the spec.\n\n"
                    f"<reviewer_suggestions>\n"
                    f"{last_suggestions}\n"
                    f"</reviewer_suggestions>\n\n"
                    f"The original specification:\n{task}"
                )
            else:
                coder_prompt = task

            coder_args = self._build_cli_args(
                max_turns=self.coder_turns_per_batch,
                append_system_prompt=CODER_APPEND_PROMPT,
            )
            result = self._invoke_claude(
                coder_args, coder_prompt, env_overrides,
                label=f"coder_batch_{cycle}",
            )
            self._record_phase(f"coder_batch_{cycle}", "coder", cycle)

            # Mid-phase eval after coder batch
            if self._mid_phase_enabled:
                mid_result = self._run_mid_phase_pytest(f"after_coder_batch_{cycle}")
                if mid_result:
                    self.telemetry.setdefault("mid_phase_evals", []).append(mid_result)

            if result is not None and result.timed_out:
                self.log.error("Coder timed out")
                self.final_result = result
                return

            # Check cost limits
            if self.cost_limits.is_above_limits(
                self.usage, prior_cost=self.prior_cost
            ):
                self.log.info("Hit cost limits, stopping")
                self.final_result = result
                return

            # --- Review pass ---
            reviewer_args = self._build_reviewer_args()
            reviewer_prompt = (
                "Read all source files in the current working "
                "directory and provide your code quality review. "
                "Focus on reducing duplication and complexity."
            )

            review_start = len(self.steps)
            review_result = self._invoke_claude(
                reviewer_args, reviewer_prompt, env_overrides,
                label=f"reviewer_{cycle}",
            )
            self._record_phase(f"reviewer_{cycle}", "reviewer", cycle)

            # Extract suggestions from reviewer steps only
            last_suggestions = self._extract_review_text(
                review_result, review_start
            )

            if last_suggestions:
                self._review_suggestions.append((cycle, last_suggestions))
                self.log.info("reviewer_coder.review.captured", cycle=cycle, chars=len(last_suggestions))

            if self.cost_limits.is_above_limits(
                self.usage, prior_cost=self.prior_cost
            ):
                self.log.info(
                    "Hit cost limits after review, stopping"
                )
                self.final_result = review_result
                return

        # --- Final coding batch ---
        if last_suggestions:
            final_prompt = (
                f"A code reviewer has suggested improvements. "
                f"Implement them, then finish the specification.\n\n"
                f"<reviewer_suggestions>\n"
                f"{last_suggestions}\n"
                f"</reviewer_suggestions>\n\n"
                f"The specification:\n{task}"
            )
        else:
            final_prompt = task

        # Calculate remaining turns from budget instead of using
        # step_limit directly (which is the overall budget, not a
        # per-invocation cap).
        remaining_turns: int | None = None
        if self.cost_limits.step_limit > 0:
            remaining_turns = max(
                1, self.cost_limits.step_limit - self.usage.steps
            )

        final_args = self._build_cli_args(
            max_turns=remaining_turns,
            append_system_prompt=CODER_APPEND_PROMPT,
        )
        result = self._invoke_claude(
            final_args, final_prompt, env_overrides,
            label="coder_final",
        )
        self._record_phase("coder_final", "coder", self.num_review_cycles)

        # Mid-phase eval after final coder batch
        if self._mid_phase_enabled:
            mid_result = self._run_mid_phase_pytest("after_coder_final")
            if mid_result:
                self.telemetry.setdefault("mid_phase_evals", []).append(mid_result)

        self.final_result = result
        self._finalize_telemetry()

        self.log.info(
            "reviewer_coder.run.done",
            total_cost=self.usage.cost,
            total_steps=self.usage.steps,
        )

    def _finalize_telemetry(self) -> None:
        """Compute summary telemetry and clean up workspace artifacts."""
        phases = self.telemetry.get("phases", [])
        reviewer_phases = [p for p in phases if p["role"] == "reviewer"]
        self.telemetry["phase_count"] = len(phases)
        self.telemetry["reviewer_cost"] = round(
            sum(p["phase_cost"] for p in reviewer_phases), 6
        )
        self.telemetry["reviewer_cost_fraction"] = round(
            self.telemetry["reviewer_cost"] / self.usage.cost
            if self.usage.cost > 0 else 0.0, 4
        )
        self.telemetry.pop("_last_cost", None)

        self.telemetry["reviewer_num_cycles"] = len(self._review_suggestions)
        self.telemetry["reviewer_suggestion_chars"] = sum(
            len(s) for _, s in self._review_suggestions
        )

        evals = self.telemetry.get("mid_phase_evals", [])
        if evals:
            self.telemetry["mid_phase_pass_rate_first"] = evals[0]["pass_rate"]
            self.telemetry["mid_phase_pass_rate_last"] = evals[-1]["pass_rate"]
            self.telemetry["mid_phase_pass_rate_delta"] = round(
                evals[-1]["pass_rate"] - evals[0]["pass_rate"], 4
            )

        test_dir = self.workspace / ".evaluation_tests"
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
        pytest_ini = self.workspace / "pytest.ini"
        if pytest_ini.exists():
            pytest_ini.unlink(missing_ok=True)

    def _extract_review_text(
        self,
        result: RuntimeResult | None,
        review_start_idx: int = 0,
    ) -> str | None:
        """Pull the reviewer's text output from the accumulated steps.

        Only searches steps from ``review_start_idx`` onwards to avoid
        returning coder output from a previous batch.
        """
        for payload in reversed(self.steps[review_start_idx:]):
            if payload.get("type") == "result":
                text = payload.get("result", "")
                if text and len(text) > 10:
                    return text[:6000]
        return None

    # ------------------------------------------------------------------
    # Artifacts
    # ------------------------------------------------------------------

    def save_artifacts(self, path: Path) -> None:
        super().save_artifacts(path)
        for cycle, text in self._review_suggestions:
            (path / f"reviewer_cycle_{cycle}.md").write_text(text)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        super().reset()
        self._cost_before_invocation = 0.0
        self._review_suggestions = []
        self._mid_phase_enabled = False
        self._mid_phase_entrypoint = "python main.py"
        self._mid_phase_checkpoint = "checkpoint_1"


register_agent("reviewer_coder", ReviewerCoderAgent)
