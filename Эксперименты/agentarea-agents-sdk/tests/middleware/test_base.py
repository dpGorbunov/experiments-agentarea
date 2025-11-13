"""Tests for middleware base components."""

import pytest

from agentarea_agents_sdk.middleware import Middleware, MiddlewareStack


class MockMiddleware:
    """Mock middleware for testing."""

    def __init__(self):
        self.before_llm_called = False
        self.after_llm_called = False
        self.before_tool_called = False
        self.after_tool_called = False

    async def before_llm_call(self, state):
        self.before_llm_called = True
        state["test"] = "value"

    async def after_llm_call(self, state, response):
        self.after_llm_called = True

    async def before_tool_call(self, tool_call, state):
        self.before_tool_called = True
        return tool_call

    async def after_tool_call(self, tool_call, result, state):
        self.after_tool_called = True
        return result


@pytest.mark.unit
async def test_middleware_stack_before_llm():
    mw1 = MockMiddleware()
    mw2 = MockMiddleware()
    stack = MiddlewareStack([mw1, mw2])

    state = {}
    await stack.run_before_llm(state)

    assert mw1.before_llm_called
    assert mw2.before_llm_called
    assert state["test"] == "value"


@pytest.mark.unit
async def test_middleware_stack_after_llm():
    mw = MockMiddleware()
    stack = MiddlewareStack([mw])

    class MockResponse:
        content = "test"

    await stack.run_after_llm({}, MockResponse())

    assert mw.after_llm_called


@pytest.mark.unit
async def test_middleware_stack_before_tool():
    mw = MockMiddleware()
    stack = MiddlewareStack([mw])

    tool_call = {"name": "test"}
    result = await stack.run_before_tool(tool_call, {})

    assert mw.before_tool_called
    assert result == tool_call


@pytest.mark.unit
async def test_middleware_stack_after_tool():
    mw = MockMiddleware()
    stack = MiddlewareStack([mw])

    tool_call = {"name": "test"}
    result = await stack.run_after_tool(tool_call, "result", {})

    assert mw.after_tool_called
    assert result == "result"
