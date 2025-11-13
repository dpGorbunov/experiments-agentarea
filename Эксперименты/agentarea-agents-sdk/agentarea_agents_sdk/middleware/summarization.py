"""Summarization middleware for context management."""

from typing import Any


def count_tokens_approx(text: str) -> int:
    """Approximate token count (1 token ≈ 4 chars)."""
    return len(text) // 4


def count_messages_tokens(messages: list[dict]) -> int:
    """Count tokens in messages."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += count_tokens_approx(content)
    return total


class SummarizationMiddleware:
    """Auto-summarizes context when token limit exceeded."""

    def __init__(self, max_tokens: int = 50_000, keep_last: int = 6):
        self.max_tokens = max_tokens
        self.keep_last = keep_last

    async def before_llm_call(self, state: dict) -> dict[str, Any] | None:
        messages = state.get("messages", [])

        if len(messages) <= self.keep_last + 1:
            return None

        token_count = count_messages_tokens(messages)

        if token_count > self.max_tokens:
            # Keep system message, summarize middle, keep recent
            system_msg = None
            if messages and messages[0].get("role") == "system":
                system_msg = messages[0]
                messages = messages[1:]

            recent = messages[-self.keep_last :]
            old = messages[: -self.keep_last]

            # Simple summarization (concatenate with truncation)
            summary_parts = []
            for msg in old:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if isinstance(content, str):
                    summary_parts.append(f"{role}: {content[:200]}")

            summary_text = "\n".join(summary_parts[:20])  # Max 20 old messages

            summary_msg = {
                "role": "system",
                "content": f"[Previous context summary - {len(old)} messages]:\n{summary_text}\n[End summary]",
            }

            new_messages = []
            if system_msg:
                new_messages.append(system_msg)
            new_messages.append(summary_msg)
            new_messages.extend(recent)

            new_token_count = count_messages_tokens(new_messages)

            print(
                f"\n[SUMMARIZATION] {token_count} tokens → {new_token_count} tokens "
                f"({len(old)} messages summarized, keeping last {self.keep_last})\n"
            )

            return {
                "messages": new_messages,
                "summarization_count": state.get("summarization_count", 0) + 1,
            }

        return None

    async def after_llm_call(self, state: dict, response: Any) -> dict[str, Any] | None:
        return None

    async def before_tool_call(
        self, tool_call: dict, state: dict
    ) -> tuple[dict, dict[str, Any] | None]:
        return tool_call, None

    async def after_tool_call(
        self, tool_call: dict, result: Any, state: dict
    ) -> tuple[Any, dict[str, Any] | None]:
        return result, None
