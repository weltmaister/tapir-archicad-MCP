# -*- mode: python ; coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


REPO_ROOT = Path(SPECPATH).resolve().parent
SRC_DIR = REPO_ROOT / "src"
TRAY_ICON = REPO_ROOT / "packaging" / "resources" / "tapir_archicad_mcp_tray.ico"

datas = []
binaries = []
hiddenimports = []

for package_name in [
    "fastmcp",
    "mcp",
    "anyio",
    "httpx",
    "httpcore",
]:
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package_name, include_py_files=True)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

datas.append((str(TRAY_ICON), "."))

hiddenimports += [
    "tapir_archicad_mcp.companion.windows_tray",
    "win32api",
    "win32con",
    "win32gui",
    "win32gui_struct",
    "win32clipboard",
]


a = Analysis(
    [str(SRC_DIR / "tapir_archicad_mcp" / "tray_app.py")],
    pathex=[str(SRC_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=False,
    name="tapir-archicad-mcp-tray",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(TRAY_ICON),
)
