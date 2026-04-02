"""CLI utilities for agent execution."""

from __future__ import annotations

import time
from collections.abc import Callable
from collections.abc import Generator
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import structlog

from slop_code.common.llms import TokenUsage
from slop_code.execution.protocols import StreamingRuntime
from slop_code.execution.runtime import RuntimeResult

logger = structlog.get_logger(__name__)

__all__ = [
    "AgentCommandResult",
    "stream_cli_command",
]


@dataclass(slots=True)
class AgentCommandResult:
    """Result of running an agent CLI command."""

    result: RuntimeResult | None
    steps: list[Any]  # Vestigial - always empty
    usage_totals: dict[str, int]
    stdout: str | None
    stderr: str | None
    had_error: bool = False
    error_message: str | None = None


def _extract_tool_type(
    parsed: tuple[Any, ...] | None,
) -> str:
    """Extract tool type from a parsed step payload."""
    if not isinstance(parsed, tuple) or len(parsed) < 3:
        return "unknown"
    payload = parsed[2]
    if not isinstance(payload, dict):
        return "unknown"
    # Claude Code payloads carry tool info in several places
    tool = payload.get("tool", "")
    if tool:
        return str(tool)
    content = payload.get("message", {})
    if isinstance(content, dict):
        msg_type = content.get("type", "")
        if msg_type:
            return str(msg_type)
    return payload.get("type", "unknown")


_TOOL_USE_NAMES = {"Bash", "Edit", "Read", "Write"}


def _has_tool_use(
    parsed: tuple[Any, ...] | None,
) -> bool:
    """Return True if parsed payload is a tool_use step.

    A tool_use step is an assistant message whose content
    contains at least one ``tool_use`` block (Bash, Edit,
    Read, or Write).  The time elapsed *after* such a step
    represents tool execution, not API inference.
    """
    if not isinstance(parsed, tuple) or len(parsed) < 3:
        return False
    payload = parsed[2]
    if not isinstance(payload, dict):
        return False
    # Direct tool field (some payload shapes)
    tool = payload.get("tool", "")
    if tool in _TOOL_USE_NAMES:
        return True
    # Standard Claude stream-json: assistant message with
    # content blocks of type "tool_use"
    message = payload.get("message", {})
    if not isinstance(message, dict):
        return False
    for block in message.get("content", []):
        if (
            isinstance(block, dict)
            and block.get("type") == "tool_use"
        ):
            return True
    return False


def stream_cli_command(
    runtime: StreamingRuntime,
    command: str,
    parser: Callable[
        [str],
        tuple[float | None, TokenUsage | None, dict],
    ],
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
    *,
    parse_stderr: bool = False,
) -> Generator[
    tuple[float | None, TokenUsage | None, dict]
    | RuntimeResult
    | None,
    None,
    None,
]:
    """Stream CLI command output and parse lines.

    Parses each line through *parser* and yields the result.
    Emits per-step wall-clock timing via structlog so that
    API-inference time and tool-execution time can be measured
    in post-hoc analysis.

    Args:
        runtime: The streaming runtime to execute the command
        command: The command to execute
        parser: Callable that parses a line and returns
            ``(cost, tokens, payload)``
        env: Environment variables for the command
        timeout: Optional timeout in seconds
        parse_stderr: If True, also parse stderr lines
            through the parser
    """
    env = dict(env or {})
    stdout_buffer = ""
    stderr_buffer = ""
    stdout = stderr = ""
    start = time.monotonic()
    result: RuntimeResult | None = None

    # -- timing state --
    step_n = 0
    prev_yield_done: float = start
    prev_was_tool_use: bool = False

    for event in runtime.stream(
        command=command, env=env, timeout=timeout
    ):
        if event.kind == "stdout":
            stdout += event.text or ""
            stdout_buffer += event.text or ""
            while "\n" in stdout_buffer:
                line, stdout_buffer = stdout_buffer.split(
                    "\n", 1
                )
                line = line.strip()
                if not line:
                    continue
                now = time.monotonic()
                parsed = parser(line)
                elapsed = (now - prev_yield_done) * 1000.0
                tool_type = _extract_tool_type(parsed)
                if prev_was_tool_use:
                    api_ms = 0.0
                    tool_ms = round(elapsed, 2)
                else:
                    api_ms = round(elapsed, 2)
                    tool_ms = 0.0
                logger.info(
                    "step_timing",
                    step=step_n,
                    api_ms=api_ms,
                    tool_ms=tool_ms,
                    tool_type=tool_type,
                    timestamp=now,
                )
                prev_was_tool_use = _has_tool_use(
                    parsed
                )
                step_n += 1
                yield parsed
                prev_yield_done = time.monotonic()
        elif event.kind == "stderr":
            stderr += event.text or ""
            if parse_stderr:
                stderr_buffer += event.text or ""
                while "\n" in stderr_buffer:
                    line, stderr_buffer = (
                        stderr_buffer.split("\n", 1)
                    )
                    line = line.strip()
                    if not line:
                        continue
                    now = time.monotonic()
                    parsed = parser(line)
                    elapsed = (
                        (now - prev_yield_done) * 1000.0
                    )
                    tool_type = _extract_tool_type(parsed)
                    if prev_was_tool_use:
                        api_ms = 0.0
                        tool_ms = round(elapsed, 2)
                    else:
                        api_ms = round(elapsed, 2)
                        tool_ms = 0.0
                    logger.info(
                        "step_timing",
                        step=step_n,
                        api_ms=api_ms,
                        tool_ms=tool_ms,
                        tool_type=tool_type,
                        timestamp=now,
                    )
                    prev_was_tool_use = _has_tool_use(
                        parsed
                    )
                    step_n += 1
                    yield parsed
                    prev_yield_done = time.monotonic()
        elif event.kind == "finished":
            result = event.result
            break

    # Flush remaining stdout buffer
    for line in stdout_buffer.split("\n"):
        line = line.strip()
        if not line:
            continue
        now = time.monotonic()
        parsed = parser(line)
        elapsed = (now - prev_yield_done) * 1000.0
        tool_type = _extract_tool_type(parsed)
        if prev_was_tool_use:
            api_ms = 0.0
            tool_ms = round(elapsed, 2)
        else:
            api_ms = round(elapsed, 2)
            tool_ms = 0.0
        logger.info(
            "step_timing",
            step=step_n,
            api_ms=api_ms,
            tool_ms=tool_ms,
            tool_type=tool_type,
            timestamp=now,
        )
        prev_was_tool_use = _has_tool_use(parsed)
        step_n += 1
        yield parsed
        prev_yield_done = time.monotonic()

    # Flush remaining stderr buffer if parsing stderr
    if parse_stderr:
        for line in stderr_buffer.split("\n"):
            line = line.strip()
            if not line:
                continue
            now = time.monotonic()
            parsed = parser(line)
            elapsed = (now - prev_yield_done) * 1000.0
            tool_type = _extract_tool_type(parsed)
            if prev_was_tool_use:
                api_ms = 0.0
                tool_ms = round(elapsed, 2)
            else:
                api_ms = round(elapsed, 2)
                tool_ms = 0.0
            logger.info(
                "step_timing",
                step=step_n,
                api_ms=api_ms,
                tool_ms=tool_ms,
                tool_type=tool_type,
                timestamp=now,
            )
            prev_was_tool_use = _has_tool_use(parsed)
            step_n += 1
            yield parsed
            prev_yield_done = time.monotonic()

    if result is None:
        result = RuntimeResult(
            exit_code=0,
            stdout=stdout,
            stderr=stderr,
            setup_stdout="",
            setup_stderr="",
            elapsed=time.monotonic() - start,
            timed_out=False,
        )
    yield result
