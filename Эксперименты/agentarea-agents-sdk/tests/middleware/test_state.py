"""Tests for state backend."""

import pytest

from agentarea_agents_sdk.middleware import InMemoryState


@pytest.mark.unit
def test_in_memory_state_get_set():
    state = InMemoryState()

    state.set("key", "value")
    assert state.get("key") == "value"


@pytest.mark.unit
def test_in_memory_state_get_default():
    state = InMemoryState()

    assert state.get("missing", "default") == "default"


@pytest.mark.unit
def test_in_memory_state_update():
    state = InMemoryState()

    state.update({"key1": "value1", "key2": "value2"})

    assert state.get("key1") == "value1"
    assert state.get("key2") == "value2"


@pytest.mark.unit
def test_in_memory_state_snapshot():
    state = InMemoryState()

    state.update({"key": "value"})
    snapshot = state.snapshot()

    assert snapshot == {"key": "value"}
    assert snapshot is not state._data  # Different object
