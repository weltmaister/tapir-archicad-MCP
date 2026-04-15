from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import win32gui


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tapir_archicad_mcp.companion.windows_tray import WMAPP_NOTIFY, WindowsTrayApp


class WindowsTrayAppTests(unittest.TestCase):
    def _build_app(self) -> WindowsTrayApp:
        controller = Mock()
        controller.get_status_snapshot.return_value = SimpleNamespace(state="stopped")
        controller.build_tooltip.return_value = "Tapir MCP: stopped"
        return WindowsTrayApp(controller)

    def test_refresh_icon_treats_none_return_from_shell_notify_add_as_success(self) -> None:
        app = self._build_app()
        app.hwnd = 123

        with (
            patch.object(app, "_load_icon", return_value=456),
            patch("tapir_archicad_mcp.companion.windows_tray.win32gui.Shell_NotifyIcon", return_value=None) as notify,
        ):
            app._refresh_icon()

        self.assertTrue(app._icon_added)
        self.assertEqual(notify.call_count, 2)
        self.assertEqual(notify.call_args_list[0].args[0], win32gui.NIM_ADD)
        notify_data = notify.call_args_list[0].args[1]
        self.assertEqual(notify_data[0], 123)
        self.assertEqual(notify_data[3], WMAPP_NOTIFY)
        self.assertEqual(notify_data[4], 456)
        self.assertEqual(notify_data[5], "Tapir MCP: stopped")
        self.assertEqual(notify.call_args_list[1].args[0], win32gui.NIM_SETVERSION)

    def test_refresh_icon_retries_with_add_after_modify_error(self) -> None:
        app = self._build_app()
        app.hwnd = 123
        app._icon_added = True
        modify_error = win32gui.error(5, "Shell_NotifyIcon", "modify failed")

        with (
            patch.object(app, "_load_icon", return_value=456),
            patch(
                "tapir_archicad_mcp.companion.windows_tray.win32gui.Shell_NotifyIcon",
                side_effect=[modify_error, None],
            ) as notify,
        ):
            app._refresh_icon()

        self.assertTrue(app._icon_added)
        self.assertEqual(notify.call_count, 2)
        self.assertEqual(notify.call_args_list[0].args[0], win32gui.NIM_MODIFY)
        self.assertEqual(notify.call_args_list[1].args[0], win32gui.NIM_ADD)


if __name__ == "__main__":
    unittest.main()
