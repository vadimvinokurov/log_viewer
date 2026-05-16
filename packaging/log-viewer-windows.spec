# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Log Viewer — Windows .exe."""

from pathlib import Path

# Project root (one level up from packaging/)
ROOT = Path(SPECPATH).parent

APP_NAME = 'Log Viewer'
APP_VERSION = '2.0.0'

block_cipher = None

a = Analysis(
    [str(ROOT / 'packaging' / 'entry.py')],
    pathex=[str(ROOT / 'src')],
    binaries=[],
    datas=[],
    hiddenimports=[
        'log_viewer',
        'log_viewer.core',
        'log_viewer.core.command_history',
        'log_viewer.core.command_parser',
        'log_viewer.core.config',
        'log_viewer.core.filter_engine',
        'log_viewer.core.log_store',
        'log_viewer.core.models',
        'log_viewer.core.palette',
        'log_viewer.core.parser',
        'log_viewer.core.preset_manager',
        'log_viewer.core.simple_query',
        'log_viewer.core.suggester',
        'log_viewer.core.themes',
        'log_viewer.core.typography',
        'log_viewer.gui',
        'log_viewer.gui.app',
        'log_viewer.gui.bottom_bar',
        'log_viewer.gui.category_tree',
        'log_viewer.gui.command_input',
        'log_viewer.gui.filter_list',
        'log_viewer.gui.highlight_delegate',
        'log_viewer.gui.highlight_list',
        'log_viewer.gui.log_table',
        'log_viewer.gui.pinned_list',
        'log_viewer.gui.scroll_utils',
        'log_viewer.gui.side_panel',
        'pyperclip',
        'yaml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / 'assets' / 'icon.ico'),
)
