"""TodoList middleware for live task planning."""

from uuid import UUID

from ..tasks.task_service import InMemoryTaskService
from ..tasks.tasks import TaskStatus


class TodoListMiddleware:
    """Manages TODO list in agent state using TaskService."""

    def __init__(self):
        self.task_service = InMemoryTaskService()

    async def before_llm_call(self, state: dict):
        pass

    async def after_llm_call(self, state: dict, response):
        pass

    async def before_tool_call(self, tool_call: dict, state: dict):
        if tool_call.get("function", {}).get("name") == "write_todos":
            todos = tool_call.get("function", {}).get("arguments", {}).get("todos", [])

            # Sync with TaskService
            for todo in todos:
                if "id" in todo and todo["id"]:
                    # Update existing
                    try:
                        self.task_service.set_status(UUID(todo["id"]), TaskStatus(todo["status"]))
                    except (ValueError, KeyError):
                        pass
                else:
                    # Create new
                    task = self.task_service.create(
                        title=todo["content"],
                        metadata={"activeForm": todo.get("activeForm", todo["content"])},
                    )
                    todo["id"] = str(task.id)

            # Update state
            state["todos"] = todos

        return tool_call

    async def after_tool_call(self, tool_call: dict, result, state: dict):
        return result
