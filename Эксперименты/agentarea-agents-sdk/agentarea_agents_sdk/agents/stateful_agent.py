"""Stateful agent with middleware support."""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from ..middleware.base import Middleware, MiddlewareStack
from ..middleware.state import InMemoryState, StateBackend
from ..models.llm_model import LLMModel, LLMRequest
from ..prompts import PromptBuilder, ToolInfo
from ..tools.completion_tool import CompletionTool
from ..tools.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


class StatefulAgent:
    """Stateful agent with middleware support."""

    def __init__(
        self,
        name: str,
        instruction: str,
        model_provider: str,
        model_name: str,
        endpoint_url: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
        max_iterations: int = 10,
        tools: list[Any] | None = None,
        include_default_tools: bool = True,
        middlewares: list[Middleware] | None = None,
        state_backend: StateBackend | None = None,
    ):
        self.name = name
        self.instruction = instruction
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_iterations = max_iterations

        self.model = LLMModel(
            provider_type=model_provider,
            model_name=model_name,
            endpoint_url=endpoint_url,
        )

        self.tool_executor = ToolExecutor()

        if include_default_tools:
            self.tool_executor.registry.register(CompletionTool())

        if tools:
            for tool in tools:
                self.tool_executor.registry.register(tool)

        self.state = state_backend or InMemoryState()
        self.middlewares = MiddlewareStack(middlewares or [])

    def _build_system_prompt(self, goal: str, success_criteria: list[str] | None = None) -> str:
        available_tools: list[ToolInfo] = []
        for tool_instance in self.tool_executor.registry.list_tools():
            available_tools.append(
                {
                    "name": tool_instance.name,
                    "description": getattr(
                        tool_instance, "description", f"Tool: {tool_instance.name}"
                    ),
                }
            )

        if success_criteria is None:
            success_criteria = [
                "Understand the task requirements",
                "Use available tools when needed",
                "Provide clear reasoning for actions",
                "Complete the task successfully",
            ]

        return PromptBuilder.build_react_system_prompt(
            agent_name=self.name,
            agent_instruction=self.instruction,
            goal_description=goal,
            success_criteria=success_criteria,
            available_tools=available_tools,
        )

    async def _execute_agent_loop(
        self,
        task: str,
        goal: str | None = None,
        success_criteria: list[str] | None = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        goal = goal or task

        # Initialize state if needed
        if not self.state.get("initialized"):
            self.state.update(
                {
                    "messages": [],
                    "iteration": 0,
                    "initialized": True,
                }
            )

        system_prompt = self._build_system_prompt(goal, success_criteria)
        messages = self.state.get("messages", [])

        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": task})
        self.state.set("messages", messages)

        tools = self.tool_executor.get_openai_functions()
        iteration = 0
        done = False

        while not done and iteration < self.max_iterations:
            iteration += 1
            self.state.set("iteration", iteration)

            # Before LLM - pass state._data directly for mutations
            await self.middlewares.run_before_llm(self.state._data)

            messages = self.state.get("messages", [])
            request = LLMRequest(
                messages=messages,
                tools=tools,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            response_stream = self.model.ainvoke_stream(request)
            full_content = ""
            final_tool_calls = None

            async for chunk in response_stream:
                if chunk.content:
                    full_content += chunk.content
                    if stream:
                        yield chunk.content
                if chunk.tool_calls:
                    final_tool_calls = chunk.tool_calls

            assistant_message = {"role": "assistant", "content": full_content}
            if final_tool_calls:
                assistant_message["tool_calls"] = final_tool_calls

            messages.append(assistant_message)
            self.state.set("messages", messages)

            # After LLM (mock response object)
            class MockResponse:
                def __init__(self, content, tool_calls):
                    self.content = content
                    self.tool_calls = tool_calls

            await self.middlewares.run_after_llm(
                self.state._data, MockResponse(full_content, final_tool_calls)
            )

            if final_tool_calls:
                for tool_call in final_tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]
                    tool_id = tool_call["id"]

                    try:
                        tool_args = (
                            json.loads(tool_args_str)
                            if isinstance(tool_args_str, str)
                            else tool_args_str
                        )

                        # Before tool
                        tool_call_dict = {
                            "id": tool_id,
                            "name": tool_name,
                            "function": {"name": tool_name, "arguments": tool_args},
                        }
                        tool_call_dict = await self.middlewares.run_before_tool(
                            tool_call_dict, self.state._data
                        )

                        # Check if middleware wants to skip execution
                        if tool_call_dict.get("_skip_execution"):
                            result = tool_call_dict.get("_result", {"success": True})
                        else:
                            result = await self.tool_executor.execute_tool(tool_name, tool_args)

                        if tool_name == "completion":
                            done = True

                        # After tool
                        result = await self.middlewares.run_after_tool(
                            tool_call_dict, result, self.state._data
                        )

                        tool_result = str(result.get("result", result))
                        messages = self.state.get("messages", [])
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "name": tool_name,
                                "content": tool_result,
                            }
                        )
                        self.state.set("messages", messages)

                        if stream:
                            yield f"\n[Tool {tool_name}: {tool_result}]\n"

                    except Exception as e:
                        error_msg = f"Error: {str(e)}"
                        messages = self.state.get("messages", [])
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "name": tool_name,
                                "content": error_msg,
                            }
                        )
                        self.state.set("messages", messages)
                        if stream:
                            yield f"\n[Tool Error: {error_msg}]\n"

        if not stream:
            messages = self.state.get("messages", [])
            final_content = ""
            for msg in messages:
                if msg["role"] == "assistant":
                    final_content += msg["content"] + "\n"
            yield final_content.strip()

    async def run_stream(
        self,
        task: str,
        goal: str | None = None,
        success_criteria: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        async for content in self._execute_agent_loop(task, goal, success_criteria, stream=True):
            yield content

    async def run(
        self,
        task: str,
        goal: str | None = None,
        success_criteria: list[str] | None = None,
    ) -> str:
        result = ""
        async for content in self._execute_agent_loop(task, goal, success_criteria, stream=False):
            result += content
        return result

    def add_tool(self, tool: Any) -> None:
        self.tool_executor.registry.register(tool)
