import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional

log = logging.getLogger(__name__)

DEFAULT_AUDIT_PATH = Path.home() / ".tapir_mcp" / "logs" / "audit.jsonl"

_write_lock = Lock()


def audit_log_path() -> Optional[Path]:
    """
    Resolves the audit log destination from TAPIR_MCP_AUDIT_LOG.
    Unset, empty or '0' disables auditing; '1' uses the default path;
    any other value is used as the file path.
    """
    raw = os.getenv("TAPIR_MCP_AUDIT_LOG", "").strip()
    if raw in ("", "0"):
        return None
    if raw == "1":
        return DEFAULT_AUDIT_PATH
    return Path(raw)


def write_audit_entry(**fields: Any) -> None:
    """
    Appends one JSON line describing a tool call. Auditing is best-effort:
    a failure to write must never break the call itself.
    """
    path = audit_log_path()
    if path is None:
        return

    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), **fields}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _write_lock, path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=True, default=str))
            handle.write("\n")
    except OSError as e:
        log.warning(f"Could not write audit log entry to {path}: {e}")
