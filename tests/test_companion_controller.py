from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tapir_archicad_mcp.companion.config import RuntimeState, TrayConfig, load_runtime_state
from tapir_archicad_mcp.companion.controller import CompanionController


class _FakeProcess:
    def __init__(self, pid: int = 4242) -> None:
        self.pid = pid


class CompanionControllerTests(unittest.TestCase):
    def test_start_http_server_uses_expected_command_and_persists_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_home = os.environ.get("TAPIR_MCP_HOME")
            os.environ["TAPIR_MCP_HOME"] = temp_dir
            try:
                fake_exe = Path(temp_dir) / "tapir-archicad-mcp.exe"
                fake_exe.write_text("", encoding="utf-8")
                controller = CompanionController(
                    config=TrayConfig(port=18891, streamable_http_path="/mcp"),
                    server_executable_override=str(fake_exe),
                )
                process_factory = mock.Mock(return_value=_FakeProcess())
                controller._process_factory = process_factory

                snapshots = [
                    mock.Mock(http_server_running=False),
                    mock.Mock(endpoint_responding=True),
                ]

                with mock.patch.object(controller, "get_status_snapshot", side_effect=snapshots):
                    controller.start_http_server(timeout_seconds=1)

                runtime = load_runtime_state()
            finally:
                if original_home is None:
                    os.environ.pop("TAPIR_MCP_HOME", None)
                else:
                    os.environ["TAPIR_MCP_HOME"] = original_home

        process_factory.assert_called_once()
        command = process_factory.call_args.args[0]
        self.assertEqual(command[0], str(fake_exe))
        self.assertIn("--transport", command)
        self.assertIn("streamable-http", command)
        self.assertIn("--port", command)
        self.assertIn("18891", command)

        self.assertIsNotNone(runtime)
        self.assertEqual(runtime.pid, 4242)

    def test_get_status_snapshot_reports_connected_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_home = os.environ.get("TAPIR_MCP_HOME")
            os.environ["TAPIR_MCP_HOME"] = temp_dir
            try:
                fake_exe = Path(temp_dir) / "tapir-archicad-mcp.exe"
                fake_exe.write_text("", encoding="utf-8")
                controller = CompanionController(
                    config=TrayConfig(port=18891),
                    server_executable_override=str(fake_exe),
                )
                runtime = RuntimeState(
                    pid=1234,
                    host="127.0.0.1",
                    port=18891,
                    streamable_http_path="/mcp",
                    server_executable=str(fake_exe),
                )
                from tapir_archicad_mcp.companion.config import save_runtime_state

                save_runtime_state(runtime)

                with mock.patch.object(controller, "_is_pid_running", return_value=True):
                    with mock.patch.object(controller, "_list_active_archicads", return_value=[{"port": 19723}]):
                        snapshot = controller.get_status_snapshot()
            finally:
                if original_home is None:
                    os.environ.pop("TAPIR_MCP_HOME", None)
                else:
                    os.environ["TAPIR_MCP_HOME"] = original_home

        self.assertEqual(snapshot.state, "running_connected")
        self.assertTrue(snapshot.archicad_connected)
        self.assertEqual(snapshot.archicad_instances, [{"port": 19723}])
        self.assertIn("running", controller.build_tooltip(snapshot))

    def test_is_pid_running_works_for_live_and_missing_processes(self) -> None:
        process = subprocess.Popen(
            [
                os.environ.get(
                    "COMSPEC",
                    r"C:\Windows\System32\cmd.exe",
                ),
                "/c",
                "timeout",
                "/t",
                "5",
                "/nobreak",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            self.assertTrue(CompanionController._is_pid_running(process.pid))
        finally:
            process.terminate()
            process.wait(timeout=5)

        self.assertFalse(CompanionController._is_pid_running(999999))
