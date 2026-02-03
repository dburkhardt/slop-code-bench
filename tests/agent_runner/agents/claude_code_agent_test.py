"""Unit tests for the Claude Code agent configuration."""

from __future__ import annotations

import pytest

from slop_code.agent_runner.agents.claude_code import ClaudeCodeConfig
from slop_code.agent_runner.models import AgentCostLimits


@pytest.fixture
def mock_cost_limits():
    """Standard cost limits for tests."""
    return AgentCostLimits(
        step_limit=10,
        cost_limit=100.0,
        net_cost_limit=200.0,
    )


class TestClaudeCodeConfig:
    """Tests for ClaudeCodeConfig."""

    def test_version_is_required(self, mock_cost_limits):
        """Version field is required for docker template."""
        with pytest.raises(Exception):  # Pydantic validation error
            ClaudeCodeConfig(
                type="claude_code",
                cost_limits=mock_cost_limits,
                # Missing version
            )

    def test_config_with_version(self, mock_cost_limits):
        """Config can be created with version."""
        config = ClaudeCodeConfig(
            type="claude_code",
            version="2.0.51",
            cost_limits=mock_cost_limits,
        )
        assert config.version == "2.0.51"
        assert config.binary == "claude"

    def test_get_docker_file_renders_version(self, mock_cost_limits):
        """get_docker_file renders version into template."""
        config = ClaudeCodeConfig(
            type="claude_code",
            version="2.0.51",
            cost_limits=mock_cost_limits,
        )
        dockerfile = config.get_docker_file("base-image:latest")
        assert dockerfile is not None
        assert "base-image:latest" in dockerfile
        assert "@anthropic-ai/claude-code@2.0.51" in dockerfile
