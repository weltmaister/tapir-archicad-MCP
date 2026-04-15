from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client import StreamableHttpTransport
import psutil

from tapir_archicad_mcp.companion.config import (
    AUTOSTART_REGISTRY_NAME,
    RuntimeState,
    TrayConfig,
    clear_runtime_state,
    get_http_stderr_log_path,
    get_http_stdout_log_path,
    load_runtime_state,
    load_tray_config,
    resolve_server_executable,
    resolve_tray_launch_command,
    save_runtime_state,
    save_tray_config,
)


logger = logging.getLogger(__name__)

CREATE_NO_WINDOW = 0x08000000
HTTP_STATUS_TIMEOUT_SECONDS = 30


@dataclass(slots=True)
class StatusSnapshot:
    state: str
    pid: int | None
    endpoint_url: str
    host: str
    port: int
    streamable_http_path: str
    server_executable: str
    http_server_running: bool
    endpoint_responding: bool
    archicad_connected: bool
    archicad_instances: list[dict[str, Any]]
    autostart_on_login: bool
    autostart_http_on_launch: bool
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CompanionController:
    def __init__(
        self,
        *,
        config: TrayConfig | None = None,
        server_executable_override: str | None = None,
        process_factory=None,
    ) -> None:
        self.config = config or load_tray_config()
        self.server_executable = resolve_server_executable(
            self.config,
            override=server_executable_override,
        )
        self._process_factory = process_factory or subprocess.Popen
        self._process: subprocess.Popen | None = None

    @property
    def endpoint_url(self) -> str:
        return f"http://{self.config.host}:{self.config.port}{self.config.streamable_http_path}"

    def start_http_server(self, *, timeout_seconds: int = 45) -> StatusSnapshot:
        current = self.get_status_snapshot()
        if current.http_server_running:
            return current

        if not self.server_executable.exists():
            raise FileNotFoundError(f"MCP executable not found: {self.server_executable}")

        stdout_handle = open(get_http_stdout_log_path(), "ab")
        stderr_handle = open(get_http_stderr_log_path(), "ab")
        command = [
            str(self.server_executable),
            "--transport",
            "streamable-http",
            "--host",
            self.config.host,
            "--port",
            str(self.config.port),
            "--streamable-http-path",
            self.config.streamable_http_path,
        ]

        logger.info("Starting MCP HTTP server: %s", command)
        try:
            self._process = self._process_factory(
                command,
                cwd=str(self.server_executable.parent),
                stdout=stdout_handle,
                stderr=stderr_handle,
                creationflags=CREATE_NO_WINDOW,
            )
        finally:
            stdout_handle.close()
            stderr_handle.close()
        save_runtime_state(
            RuntimeState(
                pid=self._process.pid,
                host=self.config.host,
                port=self.config.port,
                streamable_http_path=self.config.streamable_http_path,
                server_executable=str(self.server_executable),
            )
        )

        deadline = time.time() + timeout_seconds
        last_error = None
        while time.time() < deadline:
            snapshot = self.get_status_snapshot()
            if snapshot.endpoint_responding:
                return snapshot
            last_error = snapshot.last_error
            time.sleep(0.5)

        raise TimeoutError(f"HTTP MCP server did not become ready: {last_error or 'timed out'}")

    def stop_http_server(self) -> StatusSnapshot:
        state = load_runtime_state()
        if state is None:
            return self.get_status_snapshot()

        logger.info("Stopping MCP HTTP server pid=%s", state.pid)
        subprocess.run(
            ["taskkill", "/PID", str(state.pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
        if self._process is not None:
            self._process = None
        clear_runtime_state()
        return self.get_status_snapshot()

    def restart_http_server(self) -> StatusSnapshot:
        self.stop_http_server()
        return self.start_http_server()

    def get_status_snapshot(self) -> StatusSnapshot:
        runtime = load_runtime_state()
        pid = runtime.pid if runtime else None
        if runtime and not self._is_pid_running(runtime.pid):
            clear_runtime_state()
            runtime = None
            pid = None

        instances: list[dict[str, Any]] = []
        last_error: str | None = None
        endpoint_responding = False
        archicad_connected = False

        if runtime is not None:
            try:
                instances = self._list_active_archicads()
                endpoint_responding = True
                archicad_connected = len(instances) > 0
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)

        state = "stopped"
        if runtime is None:
            state = "stopped"
        elif last_error:
            state = "error"
        elif endpoint_responding and archicad_connected:
            state = "running_connected"
        elif endpoint_responding:
            state = "running_no_archicad"
        else:
            state = "starting"

        return StatusSnapshot(
            state=state,
            pid=pid,
            endpoint_url=self.endpoint_url,
            host=self.config.host,
            port=self.config.port,
            streamable_http_path=self.config.streamable_http_path,
            server_executable=str(self.server_executable),
            http_server_running=runtime is not None,
            endpoint_responding=endpoint_responding,
            archicad_connected=archicad_connected,
            archicad_instances=instances,
            autostart_on_login=self.config.autostart_on_login,
            autostart_http_on_launch=self.config.autostart_http_on_launch,
            last_error=last_error,
        )

    def format_status_text(self, snapshot: StatusSnapshot | None = None) -> str:
        current = snapshot or self.get_status_snapshot()
        lines = [
            f"Status: {current.state}",
            f"HTTP server: {'running' if current.http_server_running else 'stopped'}",
            f"Endpoint: {current.endpoint_url}",
            f"PID: {current.pid if current.pid is not None else '-'}",
            f"Archicad connected: {'yes' if current.archicad_connected else 'no'}",
            f"Detected instances: {len(current.archicad_instances)}",
            f"Autostart on login: {'on' if current.autostart_on_login else 'off'}",
            f"Start HTTP on launch: {'on' if current.autostart_http_on_launch else 'off'}",
        ]
        if current.last_error:
            lines.extend(["", f"Last error: {current.last_error}"])
        return "\n".join(lines)

    def build_tooltip(self, snapshot: StatusSnapshot | None = None) -> str:
        current = snapshot or self.get_status_snapshot()
        if current.state == "running_connected":
            base = f"Tapir MCP: running on {current.host}:{current.port}"
        elif current.state == "running_no_archicad":
            base = "Tapir MCP: running, Archicad not connected"
        elif current.state == "starting":
            base = "Tapir MCP: starting"
        elif current.state == "error":
            base = "Tapir MCP: error"
        else:
            base = "Tapir MCP: stopped"
        return base[:127]

    def toggle_autostart_on_login(self) -> bool:
        enabled = not self.config.autostart_on_login
        self.set_autostart_on_login(enabled)
        return enabled

    def set_autostart_on_login(self, enabled: bool) -> None:
        import winreg

        run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key_path, 0, winreg.KEY_SET_VALUE) as run_key:
            if enabled:
                winreg.SetValueEx(run_key, AUTOSTART_REGISTRY_NAME, 0, winreg.REG_SZ, resolve_tray_launch_command())
            else:
                try:
                    winreg.DeleteValue(run_key, AUTOSTART_REGISTRY_NAME)
                except FileNotFoundError:
                    pass

        self.config.autostart_on_login = enabled
        save_tray_config(self.config)

    def toggle_http_autostart(self) -> bool:
        self.config.autostart_http_on_launch = not self.config.autostart_http_on_launch
        save_tray_config(self.config)
        return self.config.autostart_http_on_launch

    def copy_endpoint_to_clipboard(self) -> str:
        import win32clipboard

        endpoint = self.endpoint_url
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(endpoint)
        finally:
            win32clipboard.CloseClipboard()
        return endpoint

    def open_logs(self) -> None:
        os.startfile(str(get_http_stdout_log_path().parent))  # type: ignore[attr-defined]

    def save_config(self) -> None:
        save_tray_config(self.config)

    @staticmethod
    def _is_pid_running(pid: int) -> bool:
        return pid > 0 and psutil.pid_exists(pid)

    def _list_active_archicads(self) -> list[dict[str, Any]]:
        return asyncio.run(self._list_active_archicads_async())

    async def _list_active_archicads_async(self) -> list[dict[str, Any]]:
        transport = StreamableHttpTransport(self.endpoint_url)
        async with Client(transport, timeout=HTTP_STATUS_TIMEOUT_SECONDS) as client:
            result = self._normalize(await client.call_tool("discovery_list_active_archicads", {}))
        return result["data"]["result"]

    @staticmethod
    def _normalize(value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, list):
            return [CompanionController._normalize(item) for item in value]
        if isinstance(value, tuple):
            return [CompanionController._normalize(item) for item in value]
        if isinstance(value, dict):
            return {str(key): CompanionController._normalize(item) for key, item in value.items()}
        if hasattr(value, "model_dump"):
            return CompanionController._normalize(
                value.model_dump(mode="json", by_alias=True, exclude_none=True)
            )
        if hasattr(value, "__dict__"):
            return CompanionController._normalize(vars(value))
        return value
