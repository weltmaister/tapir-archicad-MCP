from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_HTTP_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 18791
DEFAULT_HTTP_PATH = "/mcp"
AUTOSTART_REGISTRY_NAME = "TapirArchicadMcpTray"
TRAY_ICON_FILENAME = "tapir_archicad_mcp_tray.ico"


def get_app_home() -> Path:
    override = os.environ.get("TAPIR_MCP_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".tapir_mcp").resolve()


def get_log_dir() -> Path:
    path = get_app_home() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_tray_config_path() -> Path:
    return get_app_home() / "tray_config.json"


def get_runtime_state_path() -> Path:
    return get_app_home() / "tray_runtime.json"


def get_tray_log_path() -> Path:
    return get_log_dir() / "tapir_mcp_tray.log"


def get_http_stdout_log_path() -> Path:
    return get_log_dir() / "tapir_mcp_http.stdout.log"


def get_http_stderr_log_path() -> Path:
    return get_log_dir() / "tapir_mcp_http.stderr.log"


def resolve_tray_icon_path() -> Path | None:
    if getattr(sys, "frozen", False):
        candidates = [
            Path(sys.executable).resolve().with_name(TRAY_ICON_FILENAME),
            Path(getattr(sys, "_MEIPASS", "")).resolve() / TRAY_ICON_FILENAME if getattr(sys, "_MEIPASS", None) else None,
        ]
    else:
        candidates = [
            Path(__file__).resolve().parents[3] / "packaging" / "resources" / TRAY_ICON_FILENAME,
        ]

    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return None


@dataclass(slots=True)
class TrayConfig:
    host: str = DEFAULT_HTTP_HOST
    port: int = DEFAULT_HTTP_PORT
    streamable_http_path: str = DEFAULT_HTTP_PATH
    autostart_on_login: bool = False
    autostart_http_on_launch: bool = False
    server_executable: str | None = None


@dataclass(slots=True)
class RuntimeState:
    pid: int
    host: str
    port: int
    streamable_http_path: str
    server_executable: str


def _normalize_http_path(path: str) -> str:
    normalized = path.strip() or DEFAULT_HTTP_PATH
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized


def load_tray_config() -> TrayConfig:
    path = get_tray_config_path()
    if not path.exists():
        return TrayConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    config = TrayConfig(**data)
    config.streamable_http_path = _normalize_http_path(config.streamable_http_path)
    return config


def save_tray_config(config: TrayConfig) -> None:
    path = get_tray_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(config)
    payload["streamable_http_path"] = _normalize_http_path(config.streamable_http_path)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_runtime_state() -> RuntimeState | None:
    path = get_runtime_state_path()
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    state = RuntimeState(**data)
    state.streamable_http_path = _normalize_http_path(state.streamable_http_path)
    return state


def save_runtime_state(state: RuntimeState) -> None:
    path = get_runtime_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(state)
    payload["streamable_http_path"] = _normalize_http_path(state.streamable_http_path)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def clear_runtime_state() -> None:
    path = get_runtime_state_path()
    if path.exists():
        path.unlink()


def resolve_default_server_executable() -> Path:
    override = os.environ.get("TAPIR_MCP_SERVER_EXE")
    if override:
        return Path(override).expanduser().resolve()

    if getattr(sys, "frozen", False):
        sibling = Path(sys.executable).resolve().with_name("tapir-archicad-mcp.exe")
        if sibling.exists():
            return sibling

    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / "dist" / "tapir-archicad-mcp" / "tapir-archicad-mcp.exe").resolve()


def resolve_server_executable(config: TrayConfig | None = None, override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    if config and config.server_executable:
        return Path(config.server_executable).expanduser().resolve()
    return resolve_default_server_executable()


def resolve_tray_launch_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}" --auto-start-http'
    return f'"{Path(sys.executable).resolve()}" -m tapir_archicad_mcp.tray_app --auto-start-http'
