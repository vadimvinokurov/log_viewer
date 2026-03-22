# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Log Viewer application.

Ref: docs/specs/features/application-packaging.md §5
"""

import sys
from pathlib import Path

# Project root
project_root = Path(SPECPATH).parent

# Entry point (absolute path)
entry_point = project_root / 'src' / 'main.py'

# Application metadata
APP_NAME = 'Log Viewer'
APP_VERSION = '0.1.0'
BUNDLE_ID = 'com.logviewer.app'

# Entry point
ENTRY_POINT = 'src.main:main'

# Hidden imports (PySide6 dynamic loading)
# Per docs/specs/features/application-packaging.md §4.2.1: Include only required modules
HIDDEN_IMPORTS = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    # Note: QtSvg only if SVG icons are used
]

# Excluded modules (per §4.2.1 startup optimization)
# Reduces extraction payload for Windows --onefile builds
EXCLUDED_MODULES = [
    # Unused Qt modules
    'PySide6.QtMultimedia',
    'PySide6.QtNetwork',
    'PySide6.QtWebEngine',
    'PySide6.QtSql',
    # Unused Python modules
    'tkinter',
    'matplotlib',
    'numpy',
    'scipy',
    'PIL',
    'cv2',
    # Test frameworks
    'pytest',
    'unittest',
    # Development tools
    'pylint',
    'black',
    'mypy',
]

# Data files (if any)
DATAS = []

# Analysis configuration
a = Analysis(
    [str(entry_point)],
    pathex=[str(project_root)],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=['build/hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDED_MODULES,  # Optimized exclusions per §4.2.1
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Platform-specific configuration
# This spec file supports both macOS and Windows builds
# Platform detection happens at build time

import platform
system = platform.system()

if system == 'Darwin':  # macOS
    # See spec §5.2 for macOS configuration
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Log Viewer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Log Viewer',
    )
    
    app = BUNDLE(
        coll,
        name='Log Viewer.app',
        bundle_identifier=BUNDLE_ID,
        version=APP_VERSION,
        icon=str(project_root / 'build' / 'icons' / 'app.icns'),
        info_plist={
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': APP_NAME,
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'LSMinimumSystemVersion': '10.15.0',
            'NSHighResolutionCapable': True,
            
            # File association configuration
            # Per docs/specs/features/file-association.md §5.1
            'CFBundleDocumentTypes': [
                {
                    'CFBundleTypeName': 'Log File',
                    'CFBundleTypeRole': 'Viewer',
                    'LSItemContentTypes': [
                        'public.log',           # System log UTI
                        'public.plain-text',    # Plain text files
                    ],
                    'LSHandlerRank': 'Alternate',  # Not default, but available
                    'CFBundleTypeExtensions': [
                        'log',
                        'txt',
                    ],
                    'CFBundleTypeIconFile': 'app.icns',
                },
            ],
            'UTExportedTypeDeclarations': [
                {
                    'UTTypeIdentifier': 'com.logviewer.log',
                    'UTTypeDescription': 'Log File',
                    'UTTypeConformsTo': ['public.plain-text'],
                    'UTTypeTagSpecification': {
                        'public.filename-extension': ['log'],
                    },
                },
            ],
            
            # Multi-instance configuration
            # Per docs/specs/features/multi-window-instance.md §8.1
            'LSMultipleInstances': True,  # Allow multiple instances
            'NSAppleScriptEnabled': True,  # Enable AppleScript control
        },
    )

elif system == 'Windows':
    # Per docs/specs/features/windows-startup-optimization.md §3.2.1: Use --onedir for instant startup
    # Ref: docs/specs/features/application-packaging.md §5.3
    exe = EXE(
        pyz,
        a.scripts,
        [],  # Empty: exclude_binaries=True for onedir
        exclude_binaries=True,  # CHANGED: Use onedir mode
        name='LogViewer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,  # CHANGED: Enable UPX for onedir (decompress once during install)
        console=False,
        target_arch='x86_64',
        icon=str(project_root / 'build' / 'icons' / 'app.ico'),  # ADDED: Windows icon per §5.3
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='LogViewer',
    )

else:
    raise RuntimeError(f"Unsupported platform: {system}")