import json
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

from tapir_archicad_mcp.tools.custom.functions import archicad_call_tool
from tapir_archicad_mcp.tools.tool_registry import (
    TOOL_CALLABLE_REGISTRY,
    register_tool_for_dispatch,
)


@pytest.fixture
def fake_tool():
    """Registers a simple dispatchable fake tool for the duration of a test."""

    def simple_tool(port: int):
        return {"done": True}

    register_tool_for_dispatch(
        simple_tool, name="test_audit_tool", title="Audit", description="test tool"
    )
    yield
    TOOL_CALLABLE_REGISTRY.pop("test_audit_tool", None)


def read_entries(path) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_audit_log_disabled_by_default(monkeypatch, tmp_path, fake_tool):
    """Without TAPIR_MCP_AUDIT_LOG no audit file may be written."""
    monkeypatch.delenv("TAPIR_MCP_AUDIT_LOG", raising=False)
    audit_file = tmp_path / "audit.jsonl"

    archicad_call_tool("test_audit_tool", {"port": 19723})

    assert not audit_file.exists()


def test_successful_call_is_audited(monkeypatch, tmp_path, fake_tool):
    """
    With TAPIR_MCP_AUDIT_LOG pointing to a file, every dispatched call
    must append one JSON line with the essential call metadata.
    """
    audit_file = tmp_path / "audit.jsonl"
    monkeypatch.setenv("TAPIR_MCP_AUDIT_LOG", str(audit_file))

    archicad_call_tool("test_audit_tool", {"port": 19723})

    entries = read_entries(audit_file)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["tool"] == "test_audit_tool"
    assert entry["port"] == 19723
    assert entry["success"] is True
    assert "timestamp" in entry
    assert entry["durationMs"] >= 0


def test_failed_call_is_audited(monkeypatch, tmp_path):
    """A failing call must be recorded with success=false and the error message."""
    audit_file = tmp_path / "audit.jsonl"
    monkeypatch.setenv("TAPIR_MCP_AUDIT_LOG", str(audit_file))

    def failing_tool(port: int):
        raise RuntimeError("Archicad exploded")

    register_tool_for_dispatch(
        failing_tool, name="test_failing_audit_tool", title="Failing", description="test tool"
    )
    try:
        with pytest.raises(RuntimeError):
            archicad_call_tool("test_failing_audit_tool", {"port": 19723})
    finally:
        TOOL_CALLABLE_REGISTRY.pop("test_failing_audit_tool", None)

    entries = read_entries(audit_file)
    assert len(entries) == 1
    assert entries[0]["success"] is False
    assert "Archicad exploded" in entries[0]["error"]


def test_audit_failure_does_not_break_the_call(monkeypatch, fake_tool):
    """
    If the audit file cannot be written the tool call must still succeed;
    observability must never take down execution.
    """
    monkeypatch.setenv("TAPIR_MCP_AUDIT_LOG", "Z:/nonexistent-drive/audit.jsonl")

    result = archicad_call_tool("test_audit_tool", {"port": 19723})

    assert result == {"result": {"done": True}}
