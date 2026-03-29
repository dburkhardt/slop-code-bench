"""Reviewer-Coder trajectory parser.

Reuses the Claude Code parser since both agents produce the same
stream-json output format from the ``claude`` CLI.
"""

from slop_code.agent_runner.agents.claude_code.parser import ClaudeCodeParser


class ReviewerCoderParser(ClaudeCodeParser):
    """Parser for Reviewer-Coder trajectory format.

    The output format is identical to Claude Code, so this subclass
    only overrides the agent_type label in parsed trajectories.
    """
