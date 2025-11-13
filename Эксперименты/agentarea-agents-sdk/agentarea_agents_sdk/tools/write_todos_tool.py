"""Write todos tool for task planning."""

from typing import Any

from .base_tool import BaseTool


class WriteTodosTool(BaseTool):
    """Tool for creating or updating TODO list."""

    @property
    def name(self) -> str:
        return "write_todos"

    @property
    def description(self) -> str:
        return (
            "Create and manage a structured task list for your current work session. "
            "This helps you track progress, organize complex tasks, and demonstrate thoroughness to the user. "
            "Use at the START of complex multi-step tasks (3+ steps). "
            "Mark tasks 'in_progress' BEFORE starting work, 'completed' IMMEDIATELY after finishing. "
            "You can revise the list as plans change - add, modify, or remove future tasks. "
            "NEVER change already completed tasks. You can have multiple tasks 'in_progress' if they run in parallel."
        )

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "List of tasks to be done",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "What needs to be done",
                            },
                            "activeForm": {
                                "type": "string",
                                "description": "Present continuous form (e.g., 'Analyzing code')",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                                "description": "Task status",
                            },
                            "id": {
                                "type": "string",
                                "description": "Task ID (optional, for updates)",
                            },
                        },
                        "required": ["content", "activeForm", "status"],
                    },
                }
            },
            "required": ["todos"],
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        # No-op: middleware handles everything
        return {"success": True}
