"""Тест write_todos с 4-шаговой задачей."""

import asyncio
import json
import sys
from pathlib import Path

# Add SDK to path
sdk_path = Path(__file__).parent
sys.path.insert(0, str(sdk_path))

from agentarea_agents_sdk.agents.stateful_agent import StatefulAgent


async def main():
    """Тест write_todos с файловой задачей."""
    print("=== Создание агента ===\n")

    agent = StatefulAgent(
        name="test-agent",
        instruction="You are a helpful assistant.",
        model_provider="anthropic",
        model_name="claude-haiku-4-5-20251001",
        enable_default_middleware=True,
        enable_todolist=True,
    )

    # 4-шаговая задача - должна триггерить write_todos
    task = """1. Create a Python file 'config.py' with:
   - DATABASE_URL = "sqlite:///app.db"
   - API_KEY = "secret123"
   - DEBUG = True

2. Read the file back to verify

3. Replace 'secret123' with 'production_key_456'

4. Search for 'production' in all .py files"""

    print("Задача:")
    print(task)
    print("\n" + "="*80 + "\n")

    # Включаем debug для вывода tool calls
    messages = [{"role": "user", "content": task}]

    try:
        response = await agent.execute(messages)

        # Выводим все tool calls
        print("\n=== Tool Calls ===\n")
        for msg in response.messages:
            if msg.get("role") == "assistant" and "tool_calls" in msg:
                for tool_call in msg["tool_calls"]:
                    print(f"Tool: {tool_call.get('function', {}).get('name')}")
                    args = tool_call.get('function', {}).get('arguments', {})
                    if isinstance(args, str):
                        args = json.loads(args)
                    print(f"Arguments: {json.dumps(args, indent=2, ensure_ascii=False)}")
                    print()

        # Проверяем state
        if "todos" in agent.state:
            print("\n=== Todos в State ===\n")
            print(json.dumps(agent.state["todos"], indent=2, ensure_ascii=False))
        else:
            print("\n⚠️ Todos НЕ созданы в state")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
