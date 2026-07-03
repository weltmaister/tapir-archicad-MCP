import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional

DEFAULT_DB_PATH = Path.home() / ".tapir_mcp" / "idempotency.sqlite3"


class IdempotencyStore:
    """
    SQLite-backed store that makes mutating tool calls safe to retry.

    Agents pass an 'idempotency_key' with a call. The same key with the
    same payload replays the stored response instead of executing again
    (e.g. creating the same walls twice); the same key with a different
    payload is rejected as an agent error.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_db()

    @staticmethod
    def _fingerprint(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _init_db(self) -> None:
        with closing(sqlite3.connect(self._db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS idempotency_results (
                    tool_name TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tool_name, idempotency_key)
                )
                """
            )
            conn.commit()

    def fetch(
        self,
        tool_name: str,
        idempotency_key: str,
        request_payload: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """
        Returns the stored response for a known key, None for an unknown
        key, and raises ValueError when the key was already used with a
        different payload.
        """
        request_hash = self._fingerprint(request_payload)
        with self._lock, closing(sqlite3.connect(self._db_path)) as conn:
            row = conn.execute(
                """
                SELECT request_hash, response_json
                FROM idempotency_results
                WHERE tool_name = ? AND idempotency_key = ?
                """,
                (tool_name, idempotency_key),
            ).fetchone()

        if row is None:
            return None

        stored_hash, response_json = row
        if stored_hash != request_hash:
            raise ValueError(
                f"idempotency_key '{idempotency_key}' was already used for '{tool_name}' "
                f"with different arguments. Use a new key for a new operation."
            )
        return json.loads(response_json)

    def store(
        self,
        tool_name: str,
        idempotency_key: str,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
    ) -> None:
        """Records a successful response so later retries can replay it."""
        with self._lock, closing(sqlite3.connect(self._db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO idempotency_results
                    (tool_name, idempotency_key, request_hash, response_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    tool_name,
                    idempotency_key,
                    self._fingerprint(request_payload),
                    json.dumps(response_payload, default=str),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
