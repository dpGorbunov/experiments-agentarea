"""Integration tests for Deep Agent middleware stack.

Tests the complete middleware integration in StatefulAgent including:
- TodoListMiddleware
- FilesystemMiddleware
- SubAgentMiddleware
- SummarizationMiddleware
"""

import asyncio
import pytest
from agentarea_agents_sdk.agents.stateful_agent import StatefulAgent
from agentarea_agents_sdk.tools.file_toolset import FileToolset


@pytest.mark.asyncio
async def test_stateful_agent_with_default_middleware():
    """Test that StatefulAgent initializes with all default middleware."""
    agent = StatefulAgent(
        name="test-agent",
        instruction="You are a test agent",
        model_provider="ollama_chat",
        model_name="qwen2.5:3b",
        enable_default_middleware=True,
    )

    # Check middleware stack
    assert len(agent.middlewares.middlewares) > 0, "Should have default middleware"

    # Check that middleware types are present
    middleware_types = [type(m).__name__ for m in agent.middlewares.middlewares]
    assert "TodoListMiddleware" in middleware_types
    assert "FilesystemMiddleware" in middleware_types
    assert "SubAgentMiddleware" in middleware_types
    assert "SummarizationMiddleware" in middleware_types


@pytest.mark.asyncio
async def test_subagent_middleware_registers_task_tool():
    """Test that SubAgentMiddleware registers the 'task' tool."""
    agent = StatefulAgent(
        name="test-agent",
        instruction="You are a test agent",
        model_provider="ollama_chat",
        model_name="qwen2.5:3b",
        enable_default_middleware=True,
        enable_subagents=True,
    )

    # Check that task tool is registered
    tools = agent.tool_executor.registry.list_tools()
    tool_names = [tool.name for tool in tools]
    assert "task" in tool_names, "task tool should be registered"


@pytest.mark.asyncio
async def test_todolist_middleware():
    """Test TodoListMiddleware handles write_todos tool calls."""
    agent = StatefulAgent(
        name="test-agent",
        instruction="You are a test agent",
        model_provider="ollama_chat",
        model_name="qwen2.5:3b",
        enable_default_middleware=True,
        enable_todolist=True,
    )

    # Check WriteTodosTool is registered
    tools = agent.tool_executor.registry.list_tools()
    tool_names = [tool.name for tool in tools]
    assert "write_todos" in tool_names


@pytest.mark.asyncio
async def test_file_tools_integration():
    """Test that file tools (edit_file, grep) are available via FileToolset."""
    from pathlib import Path
    import shutil

    test_dir = Path("/tmp/test_deep_agents")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)

    file_toolset = FileToolset(
        base_dir=test_dir,
        save_files=True,
        read_files=True,
        edit_files=True,
        grep_files=True,
    )

    # Test save_file
    result = await file_toolset.save_file("test content", "test.txt")
    assert result == "test.txt" or "test.txt" in result, f"Expected 'test.txt', got {result}"

    # Test read_file
    content = await file_toolset.read_file("test.txt")
    assert content == "test content", f"Expected 'test content', got {content}"

    # Test edit_file
    edit_result = await file_toolset.edit_file("test.txt", "test", "modified")
    assert "Successfully replaced" in edit_result, f"Edit failed: {edit_result}"

    # Verify edit
    content = await file_toolset.read_file("test.txt")
    assert content == "modified content", f"Expected 'modified content', got {content}"

    # Test grep
    grep_result = await file_toolset.grep("modified", "*.txt")
    assert "modified" in grep_result, f"Expected 'modified' in grep result: {grep_result}"
    assert "test.txt" in grep_result, f"Expected 'test.txt' in grep result: {grep_result}"

    # Cleanup
    shutil.rmtree(test_dir)


@pytest.mark.asyncio
async def test_filesystem_middleware_context_eviction():
    """Test FilesystemMiddleware evicts large tool results to virtual FS."""
    from agentarea_agents_sdk.middleware.filesystem import FilesystemMiddleware

    middleware = FilesystemMiddleware(eviction_threshold=100)
    state = {"files": {}}

    # Simulate large tool result
    tool_call = {"id": "call_123", "function": {"name": "test_tool"}}
    large_result = "x" * 200  # Exceeds threshold

    result, state_update = await middleware.after_tool_call(tool_call, large_result, state)

    # Check eviction occurred
    assert isinstance(result, dict)
    assert result.get("evicted") is True
    assert "file_path" in result
    assert state_update is not None
    assert "/large_tool_results/call_123" in state_update["files"]


@pytest.mark.asyncio
async def test_summarization_middleware_token_counting():
    """Test SummarizationMiddleware counts tokens correctly."""
    from agentarea_agents_sdk.middleware.summarization import (
        SummarizationMiddleware,
        count_messages_tokens,
    )

    middleware = SummarizationMiddleware(
        model_provider="ollama_chat",
        model_name="qwen2.5:3b",
        max_tokens_before_summary=100,
        messages_to_keep=2,
    )

    # Test token counting
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
        {"role": "user", "content": "how are you"},
    ]

    token_count = count_messages_tokens(messages)
    assert token_count > 0, "Should count tokens"


@pytest.mark.asyncio
async def test_middleware_system_prompts_integration():
    """Test that middleware system prompts are added to agent prompt."""
    agent = StatefulAgent(
        name="test-agent",
        instruction="You are a test agent",
        model_provider="ollama_chat",
        model_name="qwen2.5:3b",
        enable_default_middleware=True,
        enable_subagents=True,
    )

    # Build system prompt
    system_prompt = agent._build_system_prompt("test goal")

    # Check that middleware prompts are included
    assert "write_todos" in system_prompt or "## `task`" in system_prompt, (
        "Should include middleware system prompts"
    )


@pytest.mark.asyncio
async def test_disable_individual_middleware():
    """Test that individual middleware can be disabled."""
    agent = StatefulAgent(
        name="test-agent",
        instruction="You are a test agent",
        model_provider="ollama_chat",
        model_name="qwen2.5:3b",
        enable_default_middleware=True,
        enable_subagents=False,
        enable_summarization=False,
    )

    middleware_types = [type(m).__name__ for m in agent.middlewares.middlewares]

    # Should have TodoList and Filesystem
    assert "TodoListMiddleware" in middleware_types
    assert "FilesystemMiddleware" in middleware_types

    # Should NOT have SubAgent and Summarization
    assert "SubAgentMiddleware" not in middleware_types
    assert "SummarizationMiddleware" not in middleware_types


@pytest.mark.asyncio
async def test_custom_subagent_configuration():
    """Test custom subagent configurations."""
    custom_subagents = [
        {
            "name": "researcher",
            "description": "Agent specialized in research tasks",
            "system_prompt": "You are a research specialist",
        },
        {
            "name": "coder",
            "description": "Agent specialized in coding tasks",
            "system_prompt": "You are a coding specialist",
        },
    ]

    agent = StatefulAgent(
        name="test-agent",
        instruction="You are a test agent",
        model_provider="ollama_chat",
        model_name="qwen2.5:3b",
        enable_default_middleware=True,
        enable_subagents=True,
        subagents=custom_subagents,
    )

    # Find SubAgentMiddleware
    subagent_middleware = None
    for m in agent.middlewares.middlewares:
        if type(m).__name__ == "SubAgentMiddleware":
            subagent_middleware = m
            break

    assert subagent_middleware is not None
    assert len(subagent_middleware.subagents) == 2
    assert subagent_middleware.subagents[0]["name"] == "researcher"
    assert subagent_middleware.subagents[1]["name"] == "coder"


def test_all():
    """Run all tests."""
    import sys

    sys.exit(pytest.main([__file__, "-v"]))


if __name__ == "__main__":
    # Run basic tests without pytest
    print("Running basic integration tests...")

    async def run_basic_tests():
        print("\n1. Testing StatefulAgent initialization...")
        await test_stateful_agent_with_default_middleware()
        print("✓ StatefulAgent initialized with default middleware")

        print("\n2. Testing SubAgent task tool registration...")
        await test_subagent_middleware_registers_task_tool()
        print("✓ Task tool registered")

        print("\n3. Testing TodoList middleware...")
        await test_todolist_middleware()
        print("✓ TodoList middleware works")

        print("\n4. Testing file tools...")
        await test_file_tools_integration()
        print("✓ File tools work")

        print("\n5. Testing filesystem middleware context eviction...")
        await test_filesystem_middleware_context_eviction()
        print("✓ Context eviction works")

        print("\n6. Testing summarization middleware...")
        await test_summarization_middleware_token_counting()
        print("✓ Summarization works")

        print("\n7. Testing middleware system prompts...")
        await test_middleware_system_prompts_integration()
        print("✓ System prompts integrated")

        print("\n8. Testing individual middleware disable...")
        await test_disable_individual_middleware()
        print("✓ Can disable individual middleware")

        print("\n9. Testing custom subagent configuration...")
        await test_custom_subagent_configuration()
        print("✓ Custom subagents work")

        print("\n✅ All integration tests passed!")

    asyncio.run(run_basic_tests())
