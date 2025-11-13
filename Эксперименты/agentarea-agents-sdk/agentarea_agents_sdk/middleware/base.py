"""Base middleware protocol and stack implementation."""

from typing import Any, Protocol

from ..models.llm_model import LLMResponse


class Middleware(Protocol):
    """Protocol for middleware components."""

    async def before_llm_call(self, state: dict) -> None:
        """Called before each LLM call."""
        ...

    async def after_llm_call(self, state: dict, response: LLMResponse) -> None:
        """Called after LLM responds."""
        ...

    async def before_tool_call(self, tool_call: dict, state: dict) -> dict:
        """Called before tool execution."""
        ...

    async def after_tool_call(self, tool_call: dict, result: Any, state: dict) -> Any:
        """Called after tool execution."""
        ...


class MiddlewareStack:
    """Manages execution of multiple middleware."""

    def __init__(self, middlewares: list[Middleware]):
        self.middlewares = middlewares

    async def run_before_llm(self, state: dict) -> None:
        for mw in self.middlewares:
            await mw.before_llm_call(state)

    async def run_after_llm(self, state: dict, response: LLMResponse) -> None:
        for mw in self.middlewares:
            await mw.after_llm_call(state, response)

    async def run_before_tool(self, tool_call: dict, state: dict) -> dict:
        for mw in self.middlewares:
            tool_call = await mw.before_tool_call(tool_call, state)
        return tool_call

    async def run_after_tool(self, tool_call: dict, result: Any, state: dict) -> Any:
        for mw in self.middlewares:
            result = await mw.after_tool_call(tool_call, result, state)
        return result
