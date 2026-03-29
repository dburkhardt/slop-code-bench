"""Tests for ReviewerCoderAgent._extract_review_text.

Validates that review text extraction handles the key scenarios
from Claude Code's stream-json output format, where each content
block (text, tool_use, thinking) is emitted as a separate event.
"""

import pytest

from slop_code.agent_runner.agents.reviewer_coder.agent import (
    ReviewerCoderAgent,
)


def _make_result_payload(result_text: str, stop_reason: str = "end_turn"):
    return {
        "type": "result",
        "result": result_text,
        "stop_reason": stop_reason,
        "total_cost_usd": 0.01,
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
        },
    }


def _make_assistant_text(text: str):
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        },
    }


def _make_assistant_tool_use(name: str = "Bash"):
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "toolu_123", "name": name, "input": {}}
            ],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        },
    }


class TestExtractReviewText:
    """Test _extract_review_text with simulated step payloads."""

    @pytest.fixture
    def agent(self):
        """Create a minimal agent for testing extraction."""
        # We only need the steps list and the method; use object.__new__
        # to skip __init__ which requires many dependencies.
        agent = object.__new__(ReviewerCoderAgent)
        agent.steps = []
        return agent

    def test_result_payload_with_text(self, agent):
        """Normal case: result payload has the full review text."""
        review = "1. Extract duplicated code\n2. Reduce complexity in process()"
        agent.steps = [
            _make_assistant_text(review),
            _make_result_payload(review),
        ]
        assert agent._extract_review_text(None) == review

    def test_empty_result_falls_back_to_longest_text(self, agent):
        """When result is empty (stop_reason=tool_use), pick the longest text."""
        preamble = "I'll analyze the code."
        review = "1. Extract duplicated code into shared helper\n2. Split complex function"
        agent.steps = [
            _make_assistant_text(preamble),
            _make_assistant_tool_use("Read"),
            _make_result_payload("", stop_reason="tool_use"),
        ]
        # Only preamble available, so it should return that
        assert agent._extract_review_text(None) == preamble

    def test_empty_result_prefers_longer_text(self, agent):
        """With multiple text events and empty result, pick the longest."""
        preamble = "Let me review."
        review = "1. Extract duplicated code into shared helper\n2. Split the process function"
        agent.steps = [
            _make_assistant_text(preamble),
            _make_assistant_tool_use("Bash"),
            _make_assistant_text(review),
            _make_result_payload("", stop_reason="tool_use"),
        ]
        assert agent._extract_review_text(None) == review

    def test_review_start_idx_skips_coder_output(self, agent):
        """review_start_idx should skip coder batch payloads."""
        coder_text = "I've implemented the feature as requested."
        review = "1. The calculate function has CC>10, split it"
        agent.steps = [
            _make_assistant_text(coder_text),  # index 0: coder
            _make_result_payload(coder_text),  # index 1: coder result
            _make_assistant_text(review),  # index 2: reviewer
            _make_result_payload(review),  # index 3: reviewer result
        ]
        assert agent._extract_review_text(None, review_start_idx=2) == review

    def test_no_text_returns_none(self, agent):
        """When there's no text at all, return None."""
        agent.steps = [
            _make_assistant_tool_use("Read"),
            _make_result_payload("", stop_reason="tool_use"),
        ]
        assert agent._extract_review_text(None) is None

    def test_short_text_ignored(self, agent):
        """Text shorter than 10 chars is ignored."""
        agent.steps = [
            _make_assistant_text("OK"),
            _make_result_payload(""),
        ]
        assert agent._extract_review_text(None) is None

    def test_text_truncated_at_6000(self, agent):
        """Long review text is truncated to 6000 chars."""
        long_review = "x" * 10000
        agent.steps = [
            _make_assistant_text(long_review),
            _make_result_payload(long_review),
        ]
        result = agent._extract_review_text(None)
        assert len(result) == 6000
