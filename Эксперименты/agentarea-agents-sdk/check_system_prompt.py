"""Проверка system prompt главного агента."""

import sys
from pathlib import Path

# Add SDK to path
sdk_path = Path(__file__).parent
sys.path.insert(0, str(sdk_path))

from agentarea_agents_sdk.agents.stateful_agent import StatefulAgent


def main():
    """Проверить system prompt главного агента."""
    print("=== Инициализация агента ===\n")

    agent = StatefulAgent(
        name="test-agent",
        instruction="Вы - полезный AI-ассистент с навыками планирования и делегирования задач.",
        model_provider="anthropic",
        model_name="claude-haiku-4-5-20251001",
        enable_default_middleware=True,
        enable_todolist=True,
        enable_filesystem=True,
        enable_subagents=True,
        enable_summarization=True,
    )

    print("=== Зарегистрированные инструменты ===\n")
    tools = agent.tool_executor.registry.list_tools()
    for tool in tools:
        print(f"- {tool.name}")

    print("\n=== Активные middleware ===\n")
    for middleware in agent.middlewares.middlewares:
        print(f"- {type(middleware).__name__}")

    print("\n=== System Prompt ===\n")
    system_prompt = agent._build_system_prompt(
        goal="Проанализировать код и найти потенциальные проблемы"
    )

    print(system_prompt)

    print("\n=== Анализ промптов ===\n")

    has_planning = "write_todos" in system_prompt and "PLANNING" in system_prompt.upper()
    has_task = "task" in system_prompt and "subagent" in system_prompt.lower()

    print(f"PLANNING_INSTRUCTIONS присутствуют: {has_planning}")
    print(f"TASK_SYSTEM_PROMPT присутствует: {has_task}")

    if has_planning:
        print("\n✓ write_todos инструкции найдены")
    else:
        print("\n✗ write_todos инструкции НЕ найдены")

    if has_task:
        print("✓ task инструкции найдены")
    else:
        print("✗ task инструкции НЕ найдены")


if __name__ == "__main__":
    main()
