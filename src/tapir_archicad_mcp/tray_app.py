from __future__ import annotations

import argparse
import json
import logging
from logging.handlers import RotatingFileHandler

from tapir_archicad_mcp.companion.config import get_tray_log_path, load_tray_config
from tapir_archicad_mcp.companion.controller import CompanionController


def setup_tray_logging() -> None:
    log_path = get_tray_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    file_handler = RotatingFileHandler(log_path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Tapir MCP Windows tray companion.")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--streamable-http-path", default=None)
    parser.add_argument("--server-executable", default=None)
    parser.add_argument("--auto-start-http", action="store_true")
    parser.add_argument("--status-json", action="store_true")
    parser.add_argument("--start-http", action="store_true")
    parser.add_argument("--stop-http", action="store_true")
    parser.add_argument("--restart-http", action="store_true")
    parser.add_argument("--check-archicad", action="store_true")
    return parser


def build_controller(args: argparse.Namespace) -> CompanionController:
    config = load_tray_config()
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port
    if args.streamable_http_path:
        config.streamable_http_path = args.streamable_http_path
    return CompanionController(
        config=config,
        server_executable_override=args.server_executable,
    )


def main() -> None:
    setup_tray_logging()
    parser = build_parser()
    args = parser.parse_args()
    controller = build_controller(args)

    if args.status_json:
        print(json.dumps(controller.get_status_snapshot().to_dict(), ensure_ascii=False, indent=2))
        return
    if args.start_http:
        print(json.dumps(controller.start_http_server().to_dict(), ensure_ascii=False, indent=2))
        return
    if args.stop_http:
        print(json.dumps(controller.stop_http_server().to_dict(), ensure_ascii=False, indent=2))
        return
    if args.restart_http:
        print(json.dumps(controller.restart_http_server().to_dict(), ensure_ascii=False, indent=2))
        return
    if args.check_archicad:
        print(json.dumps(controller.get_status_snapshot().to_dict(), ensure_ascii=False, indent=2))
        return

    from tapir_archicad_mcp.companion.control_window import FallbackControlWindow
    from tapir_archicad_mcp.companion.windows_tray import WindowsTrayApp

    try:
        app = WindowsTrayApp(controller, auto_start_http=args.auto_start_http)
        app.run()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("Tray startup failed, switching to fallback control window")
        fallback = FallbackControlWindow(controller, startup_error=str(exc))
        if args.auto_start_http and not controller.get_status_snapshot().http_server_running:
            try:
                controller.start_http_server()
            except Exception:  # noqa: BLE001
                logging.getLogger(__name__).exception("Fallback auto-start failed")
        fallback.run()


if __name__ == "__main__":
    main()
