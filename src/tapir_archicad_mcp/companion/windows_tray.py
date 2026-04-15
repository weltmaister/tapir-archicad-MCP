from __future__ import annotations

import logging
from typing import Callable

import win32api
import win32con
import win32gui
import winerror

from tapir_archicad_mcp.companion.control_window import FallbackControlWindow
from tapir_archicad_mcp.companion.controller import CompanionController, StatusSnapshot
from tapir_archicad_mcp.companion.config import resolve_tray_icon_path


logger = logging.getLogger(__name__)

WMAPP_NOTIFY = win32con.WM_USER + 20
MSG_TASKBAR_CREATED = win32gui.RegisterWindowMessage("TaskbarCreated")
NIN_SELECT = win32con.WM_USER + 2
NIN_KEYSELECT = win32con.WM_USER + 4

ID_START = 1001
ID_STOP = 1002
ID_RESTART = 1003
ID_STATUS = 1004
ID_CHECK_ARCHICAD = 1005
ID_COPY_ENDPOINT = 1006
ID_OPEN_LOGS = 1007
ID_AUTOSTART_LOGIN = 1008
ID_AUTOSTART_HTTP = 1009
ID_QUIT = 1010


class WindowsTrayApp:
    def __init__(self, controller: CompanionController, *, auto_start_http: bool = False) -> None:
        self.controller = controller
        self.auto_start_http = auto_start_http
        self.class_name = "TapirArchicadMcpTrayWindow"
        self.hwnd: int | None = None
        self._icon_added = False
        self._control_window: FallbackControlWindow | None = None
        self._message_map: dict[int, Callable[..., object]] = {
            MSG_TASKBAR_CREATED: self._on_taskbar_created,
            win32con.WM_DESTROY: self._on_destroy,
            win32con.WM_COMMAND: self._on_command,
            WMAPP_NOTIFY: self._on_tray_notify,
        }

    def run(self) -> None:
        self._create_window()
        self._refresh_icon()
        self._show_balloon(
            "Tapir MCP",
            "Tray is active. Left-click or right-click opens the control window. Double-click shows status.",
            win32gui.NIIF_INFO,
        )
        if self.auto_start_http or self.controller.config.autostart_http_on_launch:
            try:
                snapshot = self.controller.start_http_server()
                self._show_balloon("Tapir MCP", self.controller.build_tooltip(snapshot), win32gui.NIIF_INFO)
            except Exception as exc:  # noqa: BLE001
                self._show_balloon("Tapir MCP", f"HTTP start failed: {exc}", win32gui.NIIF_ERROR)
        win32gui.PumpMessages()

    def _create_window(self) -> None:
        message_map = {key: handler for key, handler in self._message_map.items()}
        window_class = win32gui.WNDCLASS()
        window_class.hInstance = win32api.GetModuleHandle(None)
        window_class.lpszClassName = self.class_name
        window_class.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        window_class.lpfnWndProc = message_map
        window_class.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        window_class.hIcon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        window_class.hbrBackground = win32con.COLOR_WINDOW
        try:
            win32gui.RegisterClass(window_class)
        except win32gui.error as exc:
            if exc.winerror != winerror.ERROR_CLASS_ALREADY_EXISTS:
                raise
        self.hwnd = win32gui.CreateWindow(
            self.class_name,
            self.class_name,
            win32con.WS_OVERLAPPED | win32con.WS_SYSMENU,
            0,
            0,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            0,
            0,
            window_class.hInstance,
            None,
        )
        win32gui.UpdateWindow(self.hwnd)

    def _refresh_icon(self) -> None:
        if self.hwnd is None:
            return
        snapshot = self.controller.get_status_snapshot()
        icon = self._load_icon(snapshot)
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        notify_data = (
            self.hwnd,
            0,
            flags,
            WMAPP_NOTIFY,
            icon,
            self.controller.build_tooltip(snapshot),
        )
        if not self._icon_added:
            try:
                win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, notify_data)
                win32gui.Shell_NotifyIcon(
                    win32gui.NIM_SETVERSION,
                    (self.hwnd, 0, 0, 0, getattr(win32con, "NOTIFYICON_VERSION_4", 4)),
                )
            except win32gui.error as exc:
                raise RuntimeError("Failed to add tray icon.") from exc
            self._icon_added = True
            return

        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, notify_data)
        except win32gui.error:
            self._icon_added = False
            try:
                win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, notify_data)
            except win32gui.error as exc:
                raise RuntimeError("Failed to update tray icon.") from exc
            self._icon_added = True

    def _load_icon(self, snapshot: StatusSnapshot) -> int:
        icon_path = resolve_tray_icon_path()
        if icon_path is not None:
            hinst = win32api.GetModuleHandle(None)
            loaded_icon = win32gui.LoadImage(
                hinst,
                str(icon_path),
                win32con.IMAGE_ICON,
                0,
                0,
                win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
            )
            if loaded_icon:
                return loaded_icon

        if snapshot.state == "running_connected":
            icon_id = win32con.IDI_INFORMATION
        elif snapshot.state == "running_no_archicad":
            icon_id = win32con.IDI_WARNING
        elif snapshot.state == "error":
            icon_id = win32con.IDI_ERROR
        else:
            icon_id = win32con.IDI_APPLICATION
        return win32gui.LoadIcon(0, icon_id)

    def _show_balloon(self, title: str, message: str, info_flags: int) -> None:
        if self.hwnd is None or not self._icon_added:
            return
        snapshot = self.controller.get_status_snapshot()
        notify_data = (
            self.hwnd,
            0,
            win32gui.NIF_INFO | win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
            WMAPP_NOTIFY,
            self._load_icon(snapshot),
            self.controller.build_tooltip(snapshot),
            message[:255],
            200,
            title[:63],
            info_flags,
        )
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, notify_data)
        except win32gui.error:
            logger.exception("Failed to show tray balloon")

    def _show_status_dialog(self) -> None:
        snapshot = self.controller.get_status_snapshot()
        win32gui.MessageBox(
            self.hwnd,
            self.controller.format_status_text(snapshot),
            "Tapir MCP Status",
            win32con.MB_OK | win32con.MB_ICONINFORMATION,
        )

    def _show_menu(self) -> None:
        if self.hwnd is None:
            return
        logger.info("Opening tray menu")
        snapshot = self.controller.get_status_snapshot()
        menu = win32gui.CreatePopupMenu()

        self._append_menu_item(
            menu,
            ID_START,
            "Start HTTP server",
            enabled=not snapshot.http_server_running,
        )
        self._append_menu_item(
            menu,
            ID_STOP,
            "Stop HTTP server",
            enabled=snapshot.http_server_running,
        )
        self._append_menu_item(
            menu,
            ID_RESTART,
            "Restart HTTP server",
            enabled=snapshot.http_server_running,
        )
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, None)
        self._append_menu_item(menu, ID_STATUS, "Show status")
        self._append_menu_item(menu, ID_CHECK_ARCHICAD, "Check Archicad connection")
        self._append_menu_item(menu, ID_COPY_ENDPOINT, "Copy MCP endpoint")
        self._append_menu_item(menu, ID_OPEN_LOGS, "Open logs")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, None)
        self._append_menu_item(
            menu,
            ID_AUTOSTART_LOGIN,
            "Start on login",
            checked=self.controller.config.autostart_on_login,
        )
        self._append_menu_item(
            menu,
            ID_AUTOSTART_HTTP,
            "Start HTTP on launch",
            checked=self.controller.config.autostart_http_on_launch,
        )
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, None)
        self._append_menu_item(menu, ID_QUIT, "Quit")

        win32gui.SetForegroundWindow(self.hwnd)
        cursor_pos = win32gui.GetCursorPos()
        win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_BOTTOMALIGN,
            cursor_pos[0],
            cursor_pos[1],
            0,
            self.hwnd,
            None,
        )
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)

    def _show_control_window(self) -> None:
        logger.info("Opening control window from tray")
        if self._control_window is None:
            self._control_window = FallbackControlWindow(self.controller)
        self._control_window.show()

    @staticmethod
    def _append_menu_item(menu: int, item_id: int, label: str, *, enabled: bool = True, checked: bool = False) -> None:
        flags = win32con.MF_STRING
        if not enabled:
            flags |= win32con.MF_GRAYED
        if checked:
            flags |= win32con.MF_CHECKED
        win32gui.AppendMenu(menu, flags, item_id, label)

    def _on_tray_notify(self, hwnd, msg, wparam, lparam):  # noqa: ANN001, D401
        event_code = win32api.LOWORD(lparam)
        logger.info("Tray notify received: lparam=%s event_code=%s", lparam, event_code)
        if event_code in (
            win32con.WM_LBUTTONDOWN,
            win32con.WM_LBUTTONUP,
            win32con.WM_RBUTTONDOWN,
            win32con.WM_RBUTTONUP,
            win32con.WM_CONTEXTMENU,
            NIN_SELECT,
            NIN_KEYSELECT,
        ):
            self._show_control_window()
        elif event_code == win32con.WM_LBUTTONDBLCLK:
            self._show_status_dialog()
        return 1

    def _on_command(self, hwnd, msg, wparam, lparam):  # noqa: ANN001, D401
        command_id = win32api.LOWORD(wparam)
        logger.info("Tray command selected: %s", command_id)
        self._handle_command(command_id)
        return 0

    def _on_taskbar_created(self, hwnd, msg, wparam, lparam):  # noqa: ANN001, D401
        self._icon_added = False
        try:
            self._refresh_icon()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to restore tray icon after taskbar restart")
        return 0

    def _handle_command(self, command_id: int) -> None:
        try:
            if command_id == ID_START:
                snapshot = self.controller.start_http_server()
                self._show_balloon("Tapir MCP", self.controller.build_tooltip(snapshot), win32gui.NIIF_INFO)
            elif command_id == ID_STOP:
                self.controller.stop_http_server()
                self._show_balloon("Tapir MCP", "HTTP server stopped.", win32gui.NIIF_INFO)
            elif command_id == ID_RESTART:
                snapshot = self.controller.restart_http_server()
                self._show_balloon("Tapir MCP", self.controller.build_tooltip(snapshot), win32gui.NIIF_INFO)
            elif command_id == ID_STATUS:
                self._show_status_dialog()
            elif command_id == ID_CHECK_ARCHICAD:
                snapshot = self.controller.get_status_snapshot()
                if snapshot.archicad_connected:
                    self._show_balloon(
                        "Tapir MCP",
                        f"Archicad connected ({len(snapshot.archicad_instances)} instance(s)).",
                        win32gui.NIIF_INFO,
                    )
                else:
                    self._show_balloon(
                        "Tapir MCP",
                        snapshot.last_error or "No Archicad instance found.",
                        win32gui.NIIF_WARNING,
                    )
            elif command_id == ID_COPY_ENDPOINT:
                endpoint = self.controller.copy_endpoint_to_clipboard()
                self._show_balloon("Tapir MCP", f"Endpoint copied: {endpoint}", win32gui.NIIF_INFO)
            elif command_id == ID_OPEN_LOGS:
                self.controller.open_logs()
            elif command_id == ID_AUTOSTART_LOGIN:
                enabled = self.controller.toggle_autostart_on_login()
                self._show_balloon(
                    "Tapir MCP",
                    f"Autostart on login {'enabled' if enabled else 'disabled'}.",
                    win32gui.NIIF_INFO,
                )
            elif command_id == ID_AUTOSTART_HTTP:
                enabled = self.controller.toggle_http_autostart()
                self._show_balloon(
                    "Tapir MCP",
                    f"Start HTTP on launch {'enabled' if enabled else 'disabled'}.",
                    win32gui.NIIF_INFO,
                )
            elif command_id == ID_QUIT:
                self._quit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Tray action failed")
            self._show_balloon("Tapir MCP", str(exc), win32gui.NIIF_ERROR)
        finally:
            self._refresh_icon()

    def _quit(self) -> None:
        try:
            self.controller.stop_http_server()
        finally:
            if self.hwnd is not None:
                win32gui.DestroyWindow(self.hwnd)

    def _on_destroy(self, hwnd, msg, wparam, lparam):  # noqa: ANN001, D401
        if self.hwnd is not None and self._icon_added:
            try:
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self.hwnd, 0))
            except win32gui.error:
                logger.exception("Failed to delete tray icon")
        win32gui.PostQuitMessage(0)
        return 0
