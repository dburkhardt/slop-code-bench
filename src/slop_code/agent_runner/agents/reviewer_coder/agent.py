"""Reviewer-Coder multi-agent: Claude Code with periodic code review.

Runs Claude Code for a batch of turns, then invokes a reviewer pass
(also via the claude CLI) that reads the workspace and suggests
quality improvements.  The reviewer's suggestions are prepended to
the next coding invocation so the coder can act on them.
"""

from __future__ import annotations

import shlex
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
You are a senior code quality reviewer. Read all the source files in \
the current working directory, then provide specific, actionable \
suggestions to improve code quality.

Focus on:
1. DUPLICATION: repeated code blocks that should be shared functions.
2. COMPLEXITY: deeply nested or many-branch functions to simplify/split.
3. DEAD CODE: unused imports, unreachable code, unused variables.
4. STRUCTURE: better file/function organization.

Rules:
- Reference exact function names and file paths.
- Say exactly what to change and how.
- Limit to 3-5 highest-impact suggestions.
- Do NOT suggest adding error handling, logging, types, or docs.
- Do NOT suggest changes that would alter external behaviour.
- Be concise. Each suggestion: 2-3 sentences max."""

CODER_APPEND_PROMPT = """\
Keep your code clean and well-structured. Avoid duplication: extract \
shared logic into helper functions. Keep functions short and focused. \
If a reviewer provides improvement suggestions, implement them."""


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
            "--max-turns", "3",
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

            # Extract suggestions from reviewer steps only
            last_suggestions = self._extract_review_text(
                review_result, review_start
            )

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
        self.final_result = result

        self.log.info(
            "reviewer_coder.run.done",
            total_cost=self.usage.cost,
            total_steps=self.usage.steps,
        )

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
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        super().reset()
        self._cost_before_invocation = 0.0


register_agent("reviewer_coder", ReviewerCoderAgent)
