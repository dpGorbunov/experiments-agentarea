"""Mock integration test - demonstrates middleware functionality without LLM."""

import asyncio

from agentarea_agents_sdk.middleware import (
    FilesystemMiddleware,
    SummarizationMiddleware,
    TodoListMiddleware,
)


async def simulate_agent_execution():
    """Simulate agent execution with middleware."""

    print("=" * 80)
    print("MOCK INTEGRATION TEST: Demonstrating Middleware Functionality")
    print("=" * 80)

    # Initialize middleware
    todo_mw = TodoListMiddleware()
    fs_mw = FilesystemMiddleware(eviction_threshold=100)
    sum_mw = SummarizationMiddleware(max_tokens=500, keep_last=3)

    # Simulate state
    state = {"messages": [], "todos": [], "files": {}, "iteration": 0}

    print("\n📋 Simulating agent workflow:\n")

    # ====== ITERATION 1: Create TODO list ======
    print("Iteration 1: Creating TODO list...")
    state["iteration"] = 1

    tool_call = {
        "function": {
            "name": "write_todos",
            "arguments": {
                "todos": [
                    {
                        "content": "Setup project structure",
                        "activeForm": "Setting up project structure",
                        "status": "pending",
                    },
                    {
                        "content": "Implement main function",
                        "activeForm": "Implementing main function",
                        "status": "pending",
                    },
                    {
                        "content": "Add error handling",
                        "activeForm": "Adding error handling",
                        "status": "pending",
                    },
                    {
                        "content": "Write tests",
                        "activeForm": "Writing tests",
                        "status": "pending",
                    },
                ]
            },
        }
    }

    tool_call, updates = await todo_mw.before_tool_call(tool_call, state)
    if updates:
        state.update(updates)

    print(f"✓ Created {len(state.get('todos', []))} todos")
    for todo in state.get("todos", []):
        print(f"  ☐ {todo['content']} [{todo['status']}]")

    # ====== ITERATION 2: Large result eviction ======
    print("\nIteration 2: Processing large result...")
    state["iteration"] = 2

    large_result = "x" * 500  # Exceeds eviction_threshold=100
    tool_call = {"id": "search_1", "function": {"name": "grep_search"}}

    result, updates = await fs_mw.after_tool_call(tool_call, large_result, state)
    if updates:
        state.update(updates)

    if isinstance(result, dict) and result.get("evicted"):
        print(f"✓ Large result ({result['original_size']} chars) evicted to {result['file_path']}")
        print(f"  Virtual FS now has {len(state.get('files', {}))} files")

    # ====== ITERATION 3-10: Update TODO statuses ======
    print("\nIterations 3-10: Working through tasks...")

    # Update first task
    state["todos"][0]["status"] = "in_progress"
    print(f"  ⏳ {state['todos'][0]['content']} [in_progress]")
    await asyncio.sleep(0.1)

    state["todos"][0]["status"] = "completed"
    print(f"  ✓ {state['todos'][0]['content']} [completed]")

    # Update second task
    state["todos"][1]["status"] = "in_progress"
    print(f"  ⏳ {state['todos'][1]['content']} [in_progress]")
    await asyncio.sleep(0.1)

    state["todos"][1]["status"] = "completed"
    print(f"  ✓ {state['todos'][1]['content']} [completed]")

    # Add messages to trigger summarization
    for i in range(20):
        state["messages"].append({"role": "user", "content": "test " * 200})
        state["messages"].append({"role": "assistant", "content": "response " * 200})

    print(f"\n✓ Added {len(state['messages'])} messages to context")

    # ====== ITERATION 11: Summarization ======
    print("\nIteration 11: Checking for summarization...")
    state["iteration"] = 11

    initial_msg_count = len(state["messages"])
    updates = await sum_mw.before_llm_call(state)
    if updates:
        state.update(updates)

    if state.get("summarization_count", 0) > 0:
        print(
            f"✓ Summarization triggered: {initial_msg_count} → {len(state['messages'])} messages"
        )
        print(f"  Summarization count: {state['summarization_count']}")
    else:
        print("⚠ Summarization not triggered (threshold not reached)")

    # ====== ITERATION 12-15: Finish remaining tasks ======
    print("\nIterations 12-15: Finishing remaining tasks...")

    state["todos"][2]["status"] = "in_progress"
    state["todos"][2]["status"] = "completed"
    print(f"  ✓ {state['todos'][2]['content']} [completed]")

    state["todos"][3]["status"] = "in_progress"
    state["todos"][3]["status"] = "completed"
    print(f"  ✓ {state['todos'][3]['content']} [completed]")

    # ====== FINAL REPORT ======
    print("\n" + "=" * 80)
    print("FINAL STATE:")
    print("=" * 80)

    print(f"\n✓ Total iterations: {state['iteration']}")

    print(f"\n✓ TODOs: {len(state['todos'])}")
    completed = len([t for t in state["todos"] if t["status"] == "completed"])
    in_progress = len([t for t in state["todos"] if t["status"] == "in_progress"])
    pending = len([t for t in state["todos"] if t["status"] == "pending"])

    for todo in state["todos"]:
        emoji = {"pending": "☐", "in_progress": "⏳", "completed": "✓"}.get(
            todo["status"], "?"
        )
        print(f"  {emoji} {todo['content']} [{todo['status']}]")

    print(f"\n  Summary: {completed} completed, {in_progress} in_progress, {pending} pending")

    print(f"\n✓ Virtual Filesystem: {len(state['files'])} files")
    for path, content in state["files"].items():
        size = len(content) if isinstance(content, str) else 0
        print(f"  - {path} ({size} chars)")

    print(f"\n✓ Context: {len(state['messages'])} messages")
    print(f"✓ Summarizations: {state.get('summarization_count', 0)}")

    # ====== VALIDATION ======
    print("\n" + "=" * 80)
    print("VALIDATION:")
    print("=" * 80)

    validations = [
        (len(state["todos"]) > 0, "TodoList: Created plan"),
        (completed > 0, f"TodoList: {completed} tasks completed"),
        (len(state["files"]) > 0, "Filesystem: Saved files to virtual FS"),
        (
            any("/large_tool_results/" in f for f in state["files"].keys()),
            "Filesystem: Large results evicted",
        ),
        (state.get("summarization_count", 0) > 0, "Summarization: Context compressed"),
        (completed == len(state["todos"]), "All tasks completed"),
    ]

    for passed, msg in validations:
        emoji = "✓" if passed else "✗"
        print(f"{emoji} {msg}")

    success = all(v[0] for v in validations)

    print("\n" + "=" * 80)
    if success:
        print("✅ MOCK INTEGRATION TEST PASSED")
    else:
        print("⚠️  MOCK INTEGRATION TEST PARTIAL SUCCESS")
    print("=" * 80 + "\n")

    return success


if __name__ == "__main__":
    result = asyncio.run(simulate_agent_execution())
    exit(0 if result else 1)
