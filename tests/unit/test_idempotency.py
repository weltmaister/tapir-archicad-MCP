import sys
import pytest
from unittest.mock import MagicMock

# ==========================================
# SPEED OPTIMIZATION: Mock search_index in sys.modules
# to prevent heavy ML imports (PyTorch/Faiss) from slowing down test startup
# ==========================================
mock_search_index = MagicMock()
mock_search_index.create_or_load_index = lambda: None
mock_search_index.search_tools = lambda query: []
sys.modules["tapir_archicad_mcp.tools.search_index"] = mock_search_index

from tapir_archicad_mcp.idempotency import IdempotencyStore
from tapir_archicad_mcp.tools.custom import functions
from tapir_archicad_mcp.tools.custom.functions import archicad_call_tool
from tapir_archicad_mcp.tools.tool_registry import (
    TOOL_CALLABLE_REGISTRY,
    register_tool_for_dispatch,
)


# ==========================================
# IdempotencyStore unit tests
# ==========================================

@pytest.fixture
def store(tmp_path) -> IdempotencyStore:
    return IdempotencyStore(tmp_path / "idempotency.sqlite3")


def test_store_miss_returns_none(store):
    """An unknown key must return None so the call executes normally."""
    assert store.fetch("elements_create_walls", "key-1", {"port": 19723}) is None


def test_store_replays_same_payload(store):
    """The same key with the same payload must return the stored response."""
    store.store("elements_create_walls", "key-1", {"port": 19723}, {"executionResults": []})

    cached = store.fetch("elements_create_walls", "key-1", {"port": 19723})

    assert cached == {"executionResults": []}


def test_store_rejects_key_reuse_with_different_payload(store):
    """Reusing a key with a different payload is an agent error and must fail loudly."""
    store.store("elements_create_walls", "key-1", {"port": 19723}, {"executionResults": []})

    with pytest.raises(ValueError, match="key-1"):
        store.fetch("elements_create_walls", "key-1", {"port": 19999})


def test_store_keys_are_scoped_per_tool(store):
    """The same key on a different tool must not collide."""
    store.store("elements_create_walls", "key-1", {"port": 19723}, {"walls": True})

    assert store.fetch("elements_create_slabs", "key-1", {"port": 19723}) is None


# ==========================================
# archicad_call_tool dispatch integration
# ==========================================

@pytest.fixture
def fake_tool(monkeypatch, tmp_path):
    """
    Registers a counting fake tool and points the dispatcher at a
    temporary idempotency database.
    """
    monkeypatch.setattr(
        functions, "_idempotency_store", IdempotencyStore(tmp_path / "test.sqlite3")
    )

    calls = {"count": 0}

    def counting_tool(port: int):
        calls["count"] += 1
        return {"created": calls["count"]}

    register_tool_for_dispatch(
        counting_tool, name="test_counting_tool", title="Counting", description="test tool"
    )

    yield calls

    TOOL_CALLABLE_REGISTRY.pop("test_counting_tool", None)


def test_repeated_call_with_same_key_is_replayed(fake_tool):
    """
    A retry with the same idempotency_key and identical arguments must
    not execute the tool again and must return the first response.
    """
    args = {"port": 19723, "idempotency_key": "wall-batch-1"}

    first = archicad_call_tool("test_counting_tool", dict(args))
    second = archicad_call_tool("test_counting_tool", dict(args))

    assert first == second
    assert fake_tool["count"] == 1


def test_same_key_with_different_arguments_fails(fake_tool):
    """
    Reusing an idempotency_key with different arguments must raise
    instead of silently replaying the wrong response.
    """
    archicad_call_tool(
        "test_counting_tool", {"port": 19723, "idempotency_key": "wall-batch-1"}
    )

    with pytest.raises(ValueError, match="wall-batch-1"):
        archicad_call_tool(
            "test_counting_tool", {"port": 19999, "idempotency_key": "wall-batch-1"}
        )


def test_input_schema_advertises_idempotency_key(fake_tool):
    """
    Agents can only use idempotency if they can discover it: every
    registered tool's input schema must document the optional key.
    """
    from tapir_archicad_mcp.tools.tool_registry import TOOL_DISCOVERY_CATALOG

    entry = next(e for e in TOOL_DISCOVERY_CATALOG if e["name"] == "test_counting_tool")

    assert "idempotency_key" in entry["input_schema"]["properties"]
    assert "idempotency_key" not in entry["input_schema"]["required"]


def test_calls_without_key_always_execute(fake_tool):
    """Without an idempotency_key the previous behaviour is unchanged."""
    archicad_call_tool("test_counting_tool", {"port": 19723})
    archicad_call_tool("test_counting_tool", {"port": 19723})

    assert fake_tool["count"] == 2


def test_failed_calls_are_not_cached(monkeypatch, tmp_path):
    """
    Only successful responses may be stored: after a failure the same
    key must execute the tool again.
    """
    monkeypatch.setattr(
        functions, "_idempotency_store", IdempotencyStore(tmp_path / "test.sqlite3")
    )

    calls = {"count": 0}

    def flaky_tool(port: int):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("Archicad connection lost")
        return {"created": True}

    register_tool_for_dispatch(
        flaky_tool, name="test_flaky_tool", title="Flaky", description="test tool"
    )
    try:
        with pytest.raises(RuntimeError):
            archicad_call_tool(
                "test_flaky_tool", {"port": 19723, "idempotency_key": "retry-1"}
            )

        result = archicad_call_tool(
            "test_flaky_tool", {"port": 19723, "idempotency_key": "retry-1"}
        )
    finally:
        TOOL_CALLABLE_REGISTRY.pop("test_flaky_tool", None)

    assert result == {"result": {"created": True}}
    assert calls["count"] == 2
