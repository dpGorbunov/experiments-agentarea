"""Tests for stateful agent."""

import pytest

from agentarea_agents_sdk.agents.stateful_agent import StatefulAgent
from agentarea_agents_sdk.middleware import Middleware


class LoggingMiddleware:
    """Test middleware that logs calls."""

    def __init__(self):
        self.log = []

    async def before_llm_call(self, state):
        self.log.append(("before_llm", state.get("iteration", 0)))

    async def after_llm_call(self, state, response):
        self.log.append(("after_llm", state.get("iteration", 0)))

    async def before_tool_call(self, tool_call, state):
        self.log.append(("before_tool", tool_call.get("name")))
        return tool_call

    async def after_tool_call(self, tool_call, result, state):
        self.log.append(("after_tool", tool_call.get("name")))
        return result


@pytest.mark.unit
def test_stateful_agent_initialization():
    agent = StatefulAgent(
        name="Test",
        instruction="Test agent",
        model_provider="ollama_chat",
        model_name="qwen2.5",
    )

    assert agent.name == "Test"
    assert agent.state.get("initialized") is None


@pytest.mark.unit
def test_stateful_agent_with_middleware():
    mw = LoggingMiddleware()

    agent = StatefulAgent(
        name="Test",
        instruction="Test agent",
        model_provider="ollama_chat",
        model_name="qwen2.5",
        middlewares=[mw],
    )

    assert len(agent.middlewares.middlewares) == 1


@pytest.mark.integration
async def test_stateful_agent_run(skip_if_no_llm):
    skip_if_no_llm()

    mw = LoggingMiddleware()

    agent = StatefulAgent(
        name="TestAgent",
        instruction="You are a test agent",
        model_provider="ollama_chat",
        model_name="qwen2.5",
        middlewares=[mw],
        max_iterations=3,
    )

    result = await agent.run("What is 2+2?")

    assert result is not None
    assert agent.state.get("initialized") is True
    assert len(agent.state.get("messages", [])) > 0
    assert len(mw.log) > 0
