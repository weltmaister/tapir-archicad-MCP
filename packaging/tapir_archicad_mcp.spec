# -*- mode: python ; coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


REPO_ROOT = Path(SPECPATH).resolve().parent
SRC_DIR = REPO_ROOT / "src"
MODEL_DIR = REPO_ROOT / "build_support" / "models" / "all-MiniLM-L6-v2"

datas = []
binaries = []
hiddenimports = []

for package_name in [
    "tapir_archicad_mcp",
    "fastmcp",
    "mcp",
    "archicad",
    "multiconn_archicad",
    "faiss",
    "sentence_transformers",
    "transformers",
    "tokenizers",
    "huggingface_hub",
    "torch",
    "sklearn",
    "scipy",
    "numpy",
    "safetensors",
]:
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package_name, include_py_files=True)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

if MODEL_DIR.exists():
    datas.append((str(MODEL_DIR), "models/all-MiniLM-L6-v2"))


a = Analysis(
    [str(SRC_DIR / "tapir_archicad_mcp" / "server.py")],
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
    exclude_binaries=True,
    name="tapir-archicad-mcp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="tapir-archicad-mcp",
)
