"""Example: StatefulAgent with TodoList and Filesystem middleware."""

import asyncio

from agentarea_agents_sdk import StatefulAgent
from agentarea_agents_sdk.middleware import FilesystemMiddleware, TodoListMiddleware
from agentarea_agents_sdk.tools.write_todos_tool import WriteTodosTool


async def main():
    print("Creating StatefulAgent with TodoList + Filesystem middleware...")

    agent = StatefulAgent(
        name="DemoAgent",
        instruction="You are a systematic problem solver. Always plan your work using write_todos before starting.",
        model_provider="ollama_chat",
        model_name="qwen2.5",
        max_iterations=10,
        middlewares=[
            TodoListMiddleware(),
            FilesystemMiddleware(eviction_threshold=1000),
        ],
    )

    # Add write_todos tool
    agent.add_tool(WriteTodosTool())

    print("\nTask: Create a simple Python function to calculate fibonacci numbers\n")
    print("=" * 60)

    async for chunk in agent.run_stream(
        "Create a simple Python function to calculate fibonacci numbers. Save it to /workspace/fibonacci.py"
    ):
        print(chunk, end="", flush=True)

    print("\n" + "=" * 60)
    print("\nFinal State:")
    print(f"  Todos: {agent.state.get('todos', [])}")
    print(f"  Files: {list(agent.state.get('files', {}).keys())}")
    print(f"  Iterations: {agent.state.get('iteration', 0)}")


if __name__ == "__main__":
    asyncio.run(main())
