"""Planning tool for creating structured task plans."""

from typing import Any

from .base_tool import BaseTool


class PlanningTool(BaseTool):
    """Tool for creating structured plans for task execution.

    This tool allows agents to create explicit, step-by-step plans
    before executing complex tasks.
    """

    @property
    def name(self) -> str:
        return "create_plan"

    @property
    def description(self) -> str:
        return (
            "Create a structured plan for completing a task. "
            "Use this tool to break down complex tasks into clear, actionable steps. "
            "Each step should be specific and measurable."
        )

    def get_schema(self) -> dict[str, Any]:
        """Get JSON schema for the planning tool."""
        return {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": "Brief description of the task to plan",
                },
                "steps": {
                    "type": "array",
                    "description": "List of steps to complete the task",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_number": {
                                "type": "integer",
                                "description": "Sequential step number",
                            },
                            "action": {
                                "type": "string",
                                "description": "What action to take in this step",
                            },
                            "expected_outcome": {
                                "type": "string",
                                "description": "What should be achieved after this step",
                            },
                        },
                        "required": ["step_number", "action", "expected_outcome"],
                    },
                },
                "success_criteria": {
                    "type": "array",
                    "description": "List of criteria to determine if the plan succeeded",
                    "items": {"type": "string"},
                },
            },
            "required": ["task_description", "steps", "success_criteria"],
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute the planning tool - store and return the plan.

        Args:
            task_description: Description of the task
            steps: List of plan steps
            success_criteria: Success criteria for the plan

        Returns:
            Dictionary with plan details and confirmation
        """
        task_description = kwargs.get("task_description", "")
        steps = kwargs.get("steps", [])
        success_criteria = kwargs.get("success_criteria", [])

        # Validate inputs
        if not task_description:
            return {
                "success": False,
                "error": "task_description is required",
            }

        if not steps or len(steps) == 0:
            return {
                "success": False,
                "error": "At least one step is required",
            }

        # Format plan for display
        plan_text = f"Plan Created for: {task_description}\n\n"
        plan_text += "Steps:\n"
        for step in steps:
            step_num = step.get("step_number", "?")
            action = step.get("action", "")
            outcome = step.get("expected_outcome", "")
            plan_text += f"  {step_num}. {action}\n"
            plan_text += f"     Expected: {outcome}\n"

        plan_text += "\nSuccess Criteria:\n"
        for i, criterion in enumerate(success_criteria, 1):
            plan_text += f"  - {criterion}\n"

        return {
            "success": True,
            "result": plan_text,
            "plan_details": {
                "task_description": task_description,
                "steps": steps,
                "success_criteria": success_criteria,
                "total_steps": len(steps),
            },
        }
