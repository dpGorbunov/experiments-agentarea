"""Full integration test with real LLM - TodoList + Filesystem + Summarization."""

import asyncio

from agentarea_agents_sdk import StatefulAgent
from agentarea_agents_sdk.middleware import (
    FilesystemMiddleware,
    SummarizationMiddleware,
    TodoListMiddleware,
)
from agentarea_agents_sdk.tools.write_todos_tool import WriteTodosTool


async def main():
    print("=" * 80)
    print("FULL INTEGRATION TEST: TodoList + Filesystem + Summarization")
    print("=" * 80)

    agent = StatefulAgent(
        name="IntegrationTestAgent",
        instruction=(
            "You are a systematic software engineer. "
            "ALWAYS use write_todos to create a plan BEFORE starting work. "
            "Mark tasks as 'in_progress' BEFORE starting, 'completed' AFTER finishing."
        ),
        model_provider="ollama_chat",
        model_name="qwen2.5",
        max_iterations=30,  # Allow long running
        temperature=0.3,
        max_tokens=500,
        middlewares=[
            TodoListMiddleware(),
            FilesystemMiddleware(eviction_threshold=1000),  # Low threshold to trigger
            SummarizationMiddleware(max_tokens=5000, keep_last=4),  # Low to trigger
        ],
    )

    agent.add_tool(WriteTodosTool())

    print("\n📋 Task: Create a Python web scraper with error handling")
    print("Expected behavior:")
    print("  1. Agent creates TODO list")
    print("  2. Updates task statuses as it works")
    print("  3. Large results get evicted to virtual FS")
    print("  4. Context gets summarized when exceeding limit")
    print("\n" + "=" * 80 + "\n")

    iteration_count = 0
    todo_updates = 0
    evictions = 0
    summarizations = 0

    async for chunk in agent.run_stream(
        "Create a Python web scraper that fetches a URL and extracts all links. "
        "Add proper error handling and save the code to /workspace/scraper.py"
    ):
        print(chunk, end="", flush=True)

        # Track metrics from state
        current_iteration = agent.state.get("iteration", 0)
        if current_iteration > iteration_count:
            iteration_count = current_iteration

        todos = agent.state.get("todos", [])
        if todos and len(todos) > todo_updates:
            todo_updates = len(todos)

        files = agent.state.get("files", {})
        evicted_files = [f for f in files.keys() if "/large_tool_results/" in f]
        if len(evicted_files) > evictions:
            evictions = len(evicted_files)

        summarizations = agent.state.get("summarization_count", 0)

    print("\n" + "=" * 80)
    print("RESULTS:")
    print("=" * 80)

    # Check TODOs
    todos = agent.state.get("todos", [])
    print(f"\n✓ TODOs created: {len(todos)}")
    for i, todo in enumerate(todos, 1):
        status_emoji = {
            "pending": "☐",
            "in_progress": "⏳",
            "completed": "✓",
        }.get(todo["status"], "?")
        print(f"  {status_emoji} {todo['content']} [{todo['status']}]")

    completed = len([t for t in todos if t["status"] == "completed"])
    print(f"\n✓ Completed: {completed}/{len(todos)}")

    # Check filesystem
    files = agent.state.get("files", {})
    print(f"\n✓ Files in virtual FS: {len(files)}")
    for path in files.keys():
        size = len(files[path]) if isinstance(files[path], str) else 0
        print(f"  - {path} ({size} chars)")

    # Check evictions
    evicted_files = [f for f in files.keys() if "/large_tool_results/" in f]
    print(f"\n✓ Context evictions: {len(evicted_files)}")

    # Check summarizations
    summarizations = agent.state.get("summarization_count", 0)
    print(f"✓ Summarizations: {summarizations}")

    # Check iterations
    print(f"✓ Iterations used: {iteration_count}/{agent.max_iterations}")

    # Check messages
    messages = agent.state.get("messages", [])
    print(f"✓ Messages in context: {len(messages)}")

    print("\n" + "=" * 80)
    print("VALIDATION:")
    print("=" * 80)

    # Validate expected behaviors
    validations = []

    if len(todos) > 0:
        validations.append(("✓", "TodoList: Agent created plan"))
    else:
        validations.append(("✗", "TodoList: No plan created"))

    if completed > 0:
        validations.append(("✓", f"TodoList: {completed} tasks completed"))
    else:
        validations.append(("✗", "TodoList: No tasks completed"))

    if len(files) > 0:
        validations.append(("✓", "Filesystem: Files saved to virtual FS"))
    else:
        validations.append(("✗", "Filesystem: No files saved"))

    if len(evicted_files) > 0:
        validations.append(("✓", f"Filesystem: {len(evicted_files)} large results evicted"))
    else:
        validations.append(("⚠", "Filesystem: No evictions (might not have large results)"))

    if summarizations > 0:
        validations.append(("✓", f"Summarization: {summarizations} summarizations triggered"))
    else:
        validations.append(("⚠", "Summarization: No summarizations (context stayed small)"))

    if iteration_count < agent.max_iterations:
        validations.append(("✓", f"Completion: Finished in {iteration_count} iterations"))
    else:
        validations.append(("✗", "Completion: Hit max iterations limit"))

    for emoji, msg in validations:
        print(f"\n{emoji} {msg}")

    print("\n" + "=" * 80)

    # Success criteria
    success = (
        len(todos) > 0
        and completed > 0
        and len(files) > 0
        and iteration_count < agent.max_iterations
    )

    if success:
        print("✅ INTEGRATION TEST PASSED")
    else:
        print("❌ INTEGRATION TEST FAILED")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
