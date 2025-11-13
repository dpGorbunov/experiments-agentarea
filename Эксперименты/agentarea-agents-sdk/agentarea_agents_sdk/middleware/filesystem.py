"""Filesystem middleware for virtual FS and context eviction."""

from typing import Any


class FilesystemMiddleware:
    """Manages virtual filesystem and context eviction."""

    def __init__(self, eviction_threshold: int = 80_000):
        self.eviction_threshold = eviction_threshold

    async def before_llm_call(self, state: dict):
        if "files" not in state:
            state["files"] = {}

    async def after_llm_call(self, state: dict, response):
        pass

    async def before_tool_call(self, tool_call: dict, state: dict):
        return tool_call

    async def after_tool_call(self, tool_call: dict, result: Any, state: dict):
        # Context eviction for large results
        if isinstance(result, str) and len(result) > self.eviction_threshold:
            file_path = f"/large_tool_results/{tool_call.get('id', 'unknown')}"

            # Ensure files dict exists
            if "files" not in state:
                state["files"] = {}

            state["files"][file_path] = result

            return {
                "evicted": True,
                "original_size": len(result),
                "file_path": file_path,
                "message": f"Result too large ({len(result)} chars). Saved to {file_path}. Use read_file() to access.",
            }

        # Handle file write operations
        tool_name = tool_call.get("function", {}).get("name")
        if tool_name in ["write_file", "save_file"]:
            args = tool_call.get("function", {}).get("arguments", {})
            path = args.get("file_name") or args.get("path")
            content = args.get("contents") or args.get("content")

            if path and content:
                if "files" not in state:
                    state["files"] = {}
                state["files"][path] = content

        return result
