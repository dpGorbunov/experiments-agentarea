"""Tests for Summarization middleware."""

import pytest

from agentarea_agents_sdk.middleware.summarization import SummarizationMiddleware


@pytest.mark.unit
async def test_no_summarization_below_threshold():
    mw = SummarizationMiddleware(max_tokens=10000, keep_last=2)
    state = {
        "messages": [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
    }

    updates = await mw.before_llm_call(state)

    # No updates means no summarization
    assert updates is None
    assert len(state["messages"]) == 3


@pytest.mark.unit
async def test_summarization_above_threshold():
    mw = SummarizationMiddleware(max_tokens=100, keep_last=2)

    # Create large messages
    state = {
        "messages": [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "x" * 1000},
            {"role": "assistant", "content": "y" * 1000},
            {"role": "user", "content": "z" * 1000},
            {"role": "assistant", "content": "a" * 1000},
            {"role": "user", "content": "recent1"},
            {"role": "assistant", "content": "recent2"},
        ]
    }

    updates = await mw.before_llm_call(state)

    # Apply updates
    if updates:
        state.update(updates)

    # Should have: system + summary + 2 recent
    assert len(state["messages"]) == 4
    assert state["messages"][0]["role"] == "system"
    assert state["messages"][1]["role"] == "system"
    assert "summary" in state["messages"][1]["content"].lower()
    assert state["messages"][2]["content"] == "recent1"
    assert state["messages"][3]["content"] == "recent2"
    assert state["summarization_count"] == 1
