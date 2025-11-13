"""Tests for TodoList middleware."""

import pytest

from agentarea_agents_sdk.middleware.todolist import TodoListMiddleware


@pytest.mark.unit
async def test_todolist_creates_tasks():
    mw = TodoListMiddleware()
    state = {}

    tool_call = {
        "function": {
            "name": "write_todos",
            "arguments": {
                "todos": [
                    {"content": "Task 1", "activeForm": "Doing task 1", "status": "pending"},
                    {"content": "Task 2", "activeForm": "Doing task 2", "status": "pending"},
                ]
            },
        }
    }

    result = await mw.before_tool_call(tool_call, state)

    assert "todos" in state
    assert len(state["todos"]) == 2
    assert "id" in state["todos"][0]


@pytest.mark.unit
async def test_todolist_updates_status():
    mw = TodoListMiddleware()
    state = {}

    # Create
    tool_call = {
        "function": {
            "name": "write_todos",
            "arguments": {
                "todos": [{"content": "Task 1", "activeForm": "Doing task 1", "status": "pending"}]
            },
        }
    }
    await mw.before_tool_call(tool_call, state)
    task_id = state["todos"][0]["id"]

    # Update
    tool_call["function"]["arguments"]["todos"][0]["id"] = task_id
    tool_call["function"]["arguments"]["todos"][0]["status"] = "completed"
    await mw.before_tool_call(tool_call, state)

    # Verify in TaskService
    from uuid import UUID

    from agentarea_agents_sdk.tasks.tasks import TaskStatus

    task = mw.task_service.get(UUID(task_id))
    assert task.status == TaskStatus.COMPLETED
