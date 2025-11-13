"""Tests for Filesystem middleware."""

import pytest

from agentarea_agents_sdk.middleware.filesystem import FilesystemMiddleware


@pytest.mark.unit
async def test_context_eviction():
    mw = FilesystemMiddleware(eviction_threshold=100)
    state = {"files": {}}

    # Large result
    large_result = "x" * 150
    tool_call = {"id": "test123", "function": {"name": "grep_search"}}

    result, state_updates = await mw.after_tool_call(tool_call, large_result, state)

    # Apply state updates
    if state_updates:
        state.update(state_updates)

    assert result["evicted"] is True
    assert "/large_tool_results/test123" in state["files"]
    assert state["files"]["/large_tool_results/test123"] == large_result


@pytest.mark.unit
async def test_no_eviction_for_small_results():
    mw = FilesystemMiddleware(eviction_threshold=100)
    state = {"files": {}}

    small_result = "x" * 50
    tool_call = {"id": "test123", "function": {"name": "grep_search"}}

    result, state_updates = await mw.after_tool_call(tool_call, small_result, state)

    # Apply state updates if any
    if state_updates:
        state.update(state_updates)

    assert result == small_result
    assert "/large_tool_results/test123" not in state["files"]


@pytest.mark.unit
async def test_file_write_operation():
    mw = FilesystemMiddleware()
    state = {}

    tool_call = {
        "id": "test123",
        "function": {
            "name": "write_file",
            "arguments": {"file_name": "/workspace/test.txt", "contents": "hello"},
        },
    }

    result, state_updates = await mw.after_tool_call(tool_call, {"success": True}, state)

    # Apply state updates
    if state_updates:
        state.update(state_updates)

    assert "/workspace/test.txt" in state["files"]
    assert state["files"]["/workspace/test.txt"] == "hello"
