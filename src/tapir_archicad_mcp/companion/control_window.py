from __future__ import annotations

import logging

import win32api
import win32con
import win32gui

from tapir_archicad_mcp.companion.config import resolve_tray_icon_path
from tapir_archicad_mcp.companion.controller import CompanionController


logger = logging.getLogger(__name__)

ID_START = 2001
ID_STOP = 2002
ID_RESTART = 2003
ID_COPY_ENDPOINT = 2004
ID_OPEN_LOGS = 2005
ID_CHECK_ARCHICAD = 2006
ID_REFRESH = 2007
ID_QUIT = 2008


class FallbackControlWindow:
    def __init__(self, controller: CompanionController, *, startup_error: str | None = None) -> None:
        self.controller = controller
        self.startup_error = startup_error
        self.class_name = "TapirArchicadMcpFallbackWindow"
        self.hwnd: int | None = None
        self._status_static: int | None = None
        self._intro_static: int | None = None
        self._message_map = {
            win32con.WM_COMMAND: self._on_command,
            win32con.WM_DESTROY: self._on_destroy,
            win32con.WM_CLOSE: self._on_close,
        }

    def run(self) -> None:
        self.show()
        win32gui.PumpMessages()

    def show(self) -> None:
        if self.hwnd is None or not win32gui.IsWindow(self.hwnd):
            self._create_window()
        if self.hwnd is not None:
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNORMAL)
            win32gui.BringWindowToTop(self.hwnd)
            try:
                win32gui.SetForegroundWindow(self.hwnd)
            except win32gui.error:
                logger.exception("Failed to move control window to foreground")
        self._refresh_status()

    def _create_window(self) -> None:
        wnd_class = win32gui.WNDCLASS()
        wnd_class.hInstance = win32api.GetModuleHandle(None)
        wnd_class.lpszClassName = self.class_name
        wnd_class.lpfnWndProc = self._message_map
        wnd_class.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wnd_class.hbrBackground = win32con.COLOR_WINDOW + 1
        wnd_class.hIcon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        try:
            win32gui.RegisterClass(wnd_class)
        except win32gui.error:
            pass

        style = win32con.WS_OVERLAPPED | win32con.WS_CAPTION | win32con.WS_SYSMENU | win32con.WS_MINIMIZEBOX
        self.hwnd = win32gui.CreateWindowEx(
            0,
            self.class_name,
            "Tapir MCP Control",
            style,
            220,
            160,
            520,
            360,
            0,
            0,
            wnd_class.hInstance,
            None,
        )

        self._apply_icon()

        intro = (
            "Tray icon was not available on this system.\r\n"
            "This fallback window gives you direct control over the MCP HTTP server."
        )
        if self.startup_error:
            intro += f"\r\nReason: {self.startup_error}"

        self._intro_static = win32gui.CreateWindow(
            "STATIC",
            intro,
            win32con.WS_CHILD | win32con.WS_VISIBLE,
            16,
            14,
            470,
            62,
            self.hwnd,
            0,
            wnd_class.hInstance,
            None,
        )

        win32gui.CreateWindow(
            "STATIC",
            f"Endpoint: {self.controller.endpoint_url}",
            win32con.WS_CHILD | win32con.WS_VISIBLE,
            16,
            84,
            470,
            22,
            self.hwnd,
            0,
            wnd_class.hInstance,
            None,
        )

        self._status_static = win32gui.CreateWindow(
            "STATIC",
            "",
            win32con.WS_CHILD | win32con.WS_VISIBLE,
            16,
            112,
            470,
            90,
            self.hwnd,
            0,
            wnd_class.hInstance,
            None,
        )

        self._create_button("Start HTTP", ID_START, 16, 220, wnd_class.hInstance)
        self._create_button("Stop HTTP", ID_STOP, 136, 220, wnd_class.hInstance)
        self._create_button("Restart HTTP", ID_RESTART, 256, 220, wnd_class.hInstance)
        self._create_button("Check Archicad", ID_CHECK_ARCHICAD, 376, 220, wnd_class.hInstance)

        self._create_button("Copy Endpoint", ID_COPY_ENDPOINT, 16, 264, wnd_class.hInstance)
        self._create_button("Open Logs", ID_OPEN_LOGS, 136, 264, wnd_class.hInstance)
        self._create_button("Refresh", ID_REFRESH, 256, 264, wnd_class.hInstance)
        self._create_button("Quit", ID_QUIT, 376, 264, wnd_class.hInstance)

        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.UpdateWindow(self.hwnd)

    def _apply_icon(self) -> None:
        if self.hwnd is None:
            return
        icon_path = resolve_tray_icon_path()
        if icon_path is None:
            return
        icon_big = win32gui.LoadImage(
            0,
            str(icon_path),
            win32con.IMAGE_ICON,
            32,
            32,
            win32con.LR_LOADFROMFILE,
        )
        icon_small = win32gui.LoadImage(
            0,
            str(icon_path),
            win32con.IMAGE_ICON,
            16,
            16,
            win32con.LR_LOADFROMFILE,
        )
        if icon_big:
            win32gui.SendMessage(self.hwnd, win32con.WM_SETICON, win32con.ICON_BIG, icon_big)
        if icon_small:
            win32gui.SendMessage(self.hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, icon_small)

    def _create_button(self, label: str, button_id: int, x: int, y: int, instance: int) -> None:
        if self.hwnd is None:
            return
        win32gui.CreateWindow(
            "BUTTON",
            label,
            win32con.WS_TABSTOP | win32con.WS_VISIBLE | win32con.WS_CHILD | win32con.BS_DEFPUSHBUTTON,
            x,
            y,
            140,
            30,
            self.hwnd,
            button_id,
            instance,
            None,
        )

    def _refresh_status(self) -> None:
        if self._status_static is None:
            return
        try:
            snapshot = self.controller.get_status_snapshot()
            win32gui.SetWindowText(self._status_static, self.controller.format_status_text(snapshot))
        except Exception as exc:  # noqa: BLE001
            win32gui.SetWindowText(self._status_static, f"Status refresh failed: {exc}")

    def _on_command(self, hwnd, msg, wparam, lparam):  # noqa: ANN001, D401
        command_id = win32api.LOWORD(wparam)
        self._handle_command(command_id)
        return 0

    def _handle_command(self, command_id: int) -> None:
        try:
            if command_id == ID_START:
                self.controller.start_http_server()
                self._info("HTTP server started.")
            elif command_id == ID_STOP:
                self.controller.stop_http_server()
                self._info("HTTP server stopped.")
            elif command_id == ID_RESTART:
                self.controller.restart_http_server()
                self._info("HTTP server restarted.")
            elif command_id == ID_CHECK_ARCHICAD:
                snapshot = self.controller.get_status_snapshot()
                if snapshot.archicad_connected:
                    self._info(f"Archicad connected ({len(snapshot.archicad_instances)} instance(s)).")
                else:
                    self._error(snapshot.last_error or "No Archicad instance found.")
            elif command_id == ID_COPY_ENDPOINT:
                endpoint = self.controller.copy_endpoint_to_clipboard()
                self._info(f"Endpoint copied: {endpoint}")
            elif command_id == ID_OPEN_LOGS:
                self.controller.open_logs()
            elif command_id == ID_REFRESH:
                self._refresh_status()
            elif command_id == ID_QUIT:
                if self.hwnd is not None:
                    win32gui.DestroyWindow(self.hwnd)
                    return
        except Exception as exc:  # noqa: BLE001
            logger.exception("Fallback control action failed")
            self._error(str(exc))
        finally:
            self._refresh_status()

    def _info(self, message: str) -> None:
        win32gui.MessageBox(self.hwnd, message, "Tapir MCP", win32con.MB_OK | win32con.MB_ICONINFORMATION)

    def _error(self, message: str) -> None:
        win32gui.MessageBox(self.hwnd, message, "Tapir MCP", win32con.MB_OK | win32con.MB_ICONERROR)

    def _on_close(self, hwnd, msg, wparam, lparam):  # noqa: ANN001, D401
        if self.hwnd is not None:
            win32gui.DestroyWindow(self.hwnd)
        return 0

    def _on_destroy(self, hwnd, msg, wparam, lparam):  # noqa: ANN001, D401
        win32gui.PostQuitMessage(0)
        return 0
