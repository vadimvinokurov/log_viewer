# -*- mode: python ; coding: utf -*-
# Windows PyInstaller spec — build on Windows or via CI
from pathlib import Path

project_root = Path(SPECPATH).parent
src_dir = project_root / "src"

a = Analysis(
    [str(src_dir / "log_viewer" / "tui" / "app.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[(str(src_dir / "log_viewer"), "log_viewer")],
    hiddenimports=[
        "log_viewer",
        "log_viewer.core",
        "log_viewer.core.parser",
        "log_viewer.core.command_parser",
        "log_viewer.core.command_history",
        "log_viewer.core.config",
        "log_viewer.core.log_store",
        "log_viewer.core.models",
        "log_viewer.core.preset_manager",
        "log_viewer.core.filter_engine",
        "log_viewer.core.simple_query",
        "log_viewer.core.themes",
        "log_viewer.tui",
        "log_viewer.tui.app",
        "log_viewer.tui.key_bindings",
        "log_viewer.tui.widgets",
        "log_viewer.tui.widgets.log_panel",
        "log_viewer.tui.widgets.command_input",
        "log_viewer.tui.widgets.status_bar",
        "log_viewer.tui.widgets.category_panel",
        "log_viewer.tui.widgets.column_resize_mixin",
        "log_viewer.tui.screens",
        "log_viewer.tui.screens.filter_list",
        "log_viewer.tui.screens.highlight_list",
        "log_viewer.tui.screens.category_list",
        "textual",
        "rich",
        "pyperclip",
        "yaml",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="LogViewer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon=str(Path(SPECPATH) / "icon.ico"),
)
