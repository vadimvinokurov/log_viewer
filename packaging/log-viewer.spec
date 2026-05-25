# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Log Viewer — macOS .app bundle."""

import sys
from pathlib import Path

# Project root (one level up from packaging/)
ROOT = Path(SPECPATH).parent

APP_NAME = 'Log Viewer'
APP_VERSION = '2.0.0'
BUNDLE_ID = 'com.logviewer.app'

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
        'log_viewer.core._parser_cy',
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
    exclude_binaries=True,
    name='Log Viewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='Log Viewer',
)

app = BUNDLE(
    coll,
    name=f'{APP_NAME}.app',
    icon=str(ROOT / 'assets' / 'icon.icns'),
    bundle_identifier=BUNDLE_ID,
    version=APP_VERSION,
    info_plist={
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleGetInfoString': f'{APP_NAME} {APP_VERSION}',
        'CFBundleVersion': APP_VERSION,
        'CFBundleShortVersionString': APP_VERSION,
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'LSMinimumSystemVersion': '10.15',
        'CFBundleDocumentTypes': [{
            'CFBundleTypeName': 'Log File',
            'CFBundleTypeExtensions': ['log', 'txt'],
            'CFBundleTypeRole': 'Viewer',
        }],
    },
)
