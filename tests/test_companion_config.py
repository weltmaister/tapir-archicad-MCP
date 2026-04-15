from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from tapir_archicad_mcp.companion.config import (
    TrayConfig,
    load_tray_config,
    resolve_server_executable,
    save_tray_config,
)


class CompanionConfigTests(unittest.TestCase):
    def test_save_and_load_roundtrip_normalizes_http_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_home = os.environ.get("TAPIR_MCP_HOME")
            os.environ["TAPIR_MCP_HOME"] = temp_dir
            try:
                save_tray_config(
                    TrayConfig(
                        host="0.0.0.0",
                        port=18800,
                        streamable_http_path="custom",
                        autostart_on_login=True,
                        autostart_http_on_launch=True,
                    )
                )
                loaded = load_tray_config()
            finally:
                if original_home is None:
                    os.environ.pop("TAPIR_MCP_HOME", None)
                else:
                    os.environ["TAPIR_MCP_HOME"] = original_home

        self.assertEqual(loaded.host, "0.0.0.0")
        self.assertEqual(loaded.port, 18800)
        self.assertEqual(loaded.streamable_http_path, "/custom")
        self.assertTrue(loaded.autostart_on_login)
        self.assertTrue(loaded.autostart_http_on_launch)

    def test_server_executable_env_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_exe = Path(temp_dir) / "tapir-archicad-mcp.exe"
            fake_exe.write_text("", encoding="utf-8")
            original_override = os.environ.get("TAPIR_MCP_SERVER_EXE")
            os.environ["TAPIR_MCP_SERVER_EXE"] = str(fake_exe)
            try:
                resolved = resolve_server_executable()
            finally:
                if original_override is None:
                    os.environ.pop("TAPIR_MCP_SERVER_EXE", None)
                else:
                    os.environ["TAPIR_MCP_SERVER_EXE"] = original_override

        self.assertEqual(resolved, fake_exe.resolve())

