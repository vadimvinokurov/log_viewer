# Application Packaging Implementation Plan

**Version**: 1.0  
**Status**: READY  
**Created**: 2026-03-19  
**Based on**: [application-packaging.md](application-packaging.md) v1.0

---

## Overview

This implementation plan breaks down the application packaging specification into actionable tasks for the spec-coder mode.

---

## Task Breakdown

### Phase 1: Build Infrastructure Setup

#### Task 1.1: Create Build Directory Structure
**Priority**: P0 (Critical)  
**Estimated Time**: 15 minutes  
**Dependencies**: None

**Files to Create**:
```
build/
├── icons/
│   └── .gitkeep
├── hooks/
│   └── .gitkeep
└── scripts/
    └── .gitkeep
```

**Acceptance Criteria**:
- [ ] `build/` directory exists at project root
- [ ] Subdirectories created: `icons/`, `hooks/`, `scripts/`
- [ ] `.gitkeep` files added to track empty directories

---

#### Task 1.2: Add PyInstaller Dependency
**Priority**: P0 (Critical)  
**Estimated Time**: 5 minutes  
**Dependencies**: Task 1.1

**File to Modify**: `pyproject.toml`

**Changes**:
```toml
[dependency-groups]
dev = [
    "pytest>=9.0.2",
    "pytest-cov>=7.0.0",
    "pytest-qt>=4.2.0",
    "pyinstaller>=6.0.0",  # ADD THIS LINE
]
```

**Commands**:
```bash
uv sync
```

**Acceptance Criteria**:
- [ ] `pyinstaller>=6.0.0` added to dev dependencies
- [ ] `uv.lock` updated after `uv sync`
- [ ] PyInstaller executable available via `uv run pyinstaller --version`

---

### Phase 2: PyInstaller Configuration

#### Task 2.1: Create PyInstaller Spec File
**Priority**: P0 (Critical)
**Estimated Time**: 30 minutes
**Dependencies**: Task 1.2

**File to Create**: `build/logviewer.spec`

**Content** (based on spec §5.1 with Windows optimizations per §10.1.2):
```python
# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Log Viewer application.

Ref: docs/specs/features/application-packaging.md §5
Windows optimizations: docs/specs/features/application-packaging.md §10.1.2
"""

import sys
from pathlib import Path

# Project root
project_root = Path(SPECPATH).parent

# Application metadata
APP_NAME = 'Log Viewer'
APP_VERSION = '0.1.0'
BUNDLE_ID = 'com.logviewer.app'

# Entry point
ENTRY_POINT = 'src.main:main'

# Hidden imports (PySide6 dynamic loading)
# Per §4.2.1: Include only required modules
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
    ['src/main.py'],
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

# Platform-specific configuration
# This spec file supports both macOS and Windows builds
# Platform detection happens at build time

import platform
system = platform.system()

if system == 'Darwin':  # macOS
    # See spec §5.2 for macOS configuration
    exe = EXE(
        pyz=a.pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Log Viewer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        icon='build/icons/app.icns',
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
        icon='build/icons/app.icns',
        bundle_identifier=BUNDLE_ID,
        version=APP_VERSION,
        info_plist={
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': APP_NAME,
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'LSMinimumSystemVersion': '10.15.0',
            'NSHighResolutionCapable': True,
        },
    )

elif system == 'Windows':
    # See spec §5.3 for Windows configuration
    # Per §10.1.2: Optimized for fast extraction (< 3 second startup)
    exe = EXE(
        pyz=a.pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='LogViewer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,              # §10.1.2: Strip debug symbols (10-20% size reduction)
        upx=False,               # §10.1.2: CRITICAL - Disable UPX (saves 2-5 seconds)
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch='x86_64',
        codesign_identity=None,
        entitlements_file=None,
        icon='build/icons/app.ico',
    )

else:
    raise RuntimeError(f"Unsupported platform: {system}")
```

**Acceptance Criteria**:
- [ ] Spec file created at `build/logviewer.spec`
- [ ] Platform detection works (macOS/Windows)
- [ ] Hidden imports include only required PySide6 modules
- [ ] Excludes unused modules (EXCLUDED_MODULES list)
- [ ] Windows EXE has `upx=False` (critical for startup performance)
- [ ] Windows EXE has `strip=True` (size optimization)
- [ ] Console mode disabled (GUI app)

---

#### Task 2.2: Create PySide6 Hook
**Priority**: P1 (High)  
**Estimated Time**: 15 minutes  
**Dependencies**: Task 2.1

**File to Create**: `build/hooks/hook-PySide6.py`

**Content**:
```python
"""PyInstaller hook for PySide6.

Ensures all required Qt plugins and modules are bundled.
Ref: docs/specs/features/application-packaging.md §5.1
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all PySide6 submodules
hiddenimports = collect_submodules('PySide6')

# Collect Qt plugins (platforms, imageformats, etc.)
datas = collect_data_files('PySide6', include_py_files=False)

# Ensure Qt platforms plugin is included (required for GUI)
hiddenimports += [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]
```

**Acceptance Criteria**:
- [ ] Hook file created at `build/hooks/hook-PySide6.py`
- [ ] Collects all PySide6 submodules
- [ ] Includes Qt platform plugins

---

### Phase 3: Build Scripts

#### Task 3.1: Create macOS Build Script
**Priority**: P0 (Critical)  
**Estimated Time**: 20 minutes  
**Dependencies**: Task 2.1

**File to Create**: `build/scripts/build-macos.sh`

**Content** (based on spec §6.2.2):
```bash
#!/bin/bash
# macOS build script for Log Viewer
# Ref: docs/specs/features/application-packaging.md §6.2.2

set -e  # Exit on error

echo "Building Log Viewer for macOS..."

# Configuration
APP_NAME="Log Viewer"
APP_VERSION="0.1.0"
BUNDLE_NAME="Log Viewer.app"
DMG_NAME="LogViewer-${APP_VERSION}-macos.dmg"

# Clean previous build
echo "Cleaning previous build..."
rm -rf build/darwin dist/

# Run PyInstaller
echo "Running PyInstaller..."
uv run pyinstaller \
    --clean \
    --noconfirm \
    build/logviewer.spec

# Verify build
if [ ! -d "dist/${BUNDLE_NAME}" ]; then
    echo "ERROR: Build failed - ${BUNDLE_NAME} not found"
    exit 1
fi

# Create DMG
echo "Creating DMG..."
hdiutil create \
    -volname "Log Viewer" \
    -srcfolder "dist/${BUNDLE_NAME}" \
    -ov -format UDZO \
    "dist/${DMG_NAME}"

# Verify DMG
if [ ! -f "dist/${DMG_NAME}" ]; then
    echo "ERROR: DMG creation failed"
    exit 1
fi

# Generate checksum
echo "Generating checksum..."
shasum -a 256 "dist/${DMG_NAME}" > "dist/${DMG_NAME}.sha256"

# Summary
echo ""
echo "=========================================="
echo "Build complete!"
echo "=========================================="
echo "App Bundle: dist/${BUNDLE_NAME}"
echo "DMG: dist/${DMG_NAME}"
echo "Checksum: dist/${DMG_NAME}.sha256"
echo ""
echo "To test: open dist/${BUNDLE_NAME}"
echo "=========================================="
```

**Commands**:
```bash
chmod +x build/scripts/build-macos.sh
```

**Acceptance Criteria**:
- [ ] Script created at `build/scripts/build-macos.sh`
- [ ] Script is executable (`chmod +x`)
- [ ] Cleans previous build
- [ ] Runs PyInstaller with correct flags
- [ ] Creates DMG with correct naming
- [ ] Generates SHA256 checksum
- [ ] Provides build summary

---

#### Task 3.2: Create Windows Build Script
**Priority**: P0 (Critical)  
**Estimated Time**: 20 minutes  
**Dependencies**: Task 2.1

**File to Create**: `build/scripts/build-windows.py`

**Content** (based on spec §6.2.3):
```python
#!/usr/bin/env python3
"""Windows build script for Log Viewer.

Ref: docs/specs/features/application-packaging.md §6.2.3
"""

import subprocess
import shutil
import hashlib
from pathlib import Path


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def build_windows() -> None:
    """Build Log Viewer for Windows."""
    print("Building Log Viewer for Windows...")
    
    # Configuration
    app_name = "LogViewer"
    app_version = "0.1.0"
    exe_name = f"{app_name}-{app_version}-windows.exe"
    
    # Clean previous build
    print("Cleaning previous build...")
    dist_dir = Path("dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    # Run PyInstaller
    print("Running PyInstaller...")
    result = subprocess.run(
        ["uv", "run", "pyinstaller", "--clean", "--noconfirm", "build/logviewer.spec"],
        check=False
    )
    
    if result.returncode != 0:
        print(f"ERROR: PyInstaller failed with code {result.returncode}")
        exit(1)
    
    # Find and rename executable
    original_exe = dist_dir / f"{app_name}.exe"
    if not original_exe.exists():
        print(f"ERROR: Build failed - {original_exe} not found")
        exit(1)
    
    versioned_exe = dist_dir / exe_name
    original_exe.rename(versioned_exe)
    
    # Generate checksum
    print("Generating checksum...")
    checksum = calculate_sha256(versioned_exe)
    checksum_file = dist_dir / f"{exe_name}.sha256"
    with open(checksum_file, "w") as f:
        f.write(f"{checksum}  {exe_name}\n")
    
    # Summary
    print()
    print("=" * 50)
    print("Build complete!")
    print("=" * 50)
    print(f"Executable: dist/{exe_name}")
    print(f"Checksum: dist/{exe_name}.sha256")
    print()
    print(f"To test: dist\\{exe_name}")
    print("=" * 50)


if __name__ == "__main__":
    build_windows()
```

**Acceptance Criteria**:
- [ ] Script created at `build/scripts/build-windows.py`
- [ ] Cleans previous build
- [ ] Runs PyInstaller with correct flags
- [ ] Renames executable with version
- [ ] Generates SHA256 checksum
- [ ] Provides build summary

---

### Phase 4: Icon Assets

#### Task 4.1: Create Placeholder Icons
**Priority**: P2 (Medium)  
**Estimated Time**: 30 minutes  
**Dependencies**: Task 1.1

**Note**: For initial builds, use default Qt icon. Custom icon creation is deferred to v0.2.0.

**File to Create**: `build/icons/README.md`

**Content**:
```markdown
# Application Icons

This directory should contain application icons for packaging.

## Required Files

### macOS: `app.icns`
- Format: Apple Icon Image
- Sizes: 16, 32, 64, 128, 256, 512, 1024 pixels
- Tool: `iconutil` (macOS) or `png2icns`

### Windows: `app.ico`
- Format: Windows Icon
- Sizes: 16, 32, 48, 64, 128, 256 pixels
- Tool: `png2ico` or ImageMagick `convert`

### Source: `app.png`
- Format: PNG with transparency
- Size: 1024x1024 pixels
- Used to generate .icns and .ico

## Current Status

**Placeholder**: Using default Qt icon for initial builds.

**TODO (v0.2.0)**: Create custom icon representing log file viewer concept.

## Icon Design Guidelines

- Simple, recognizable at small sizes
- High contrast for visibility
- Consistent with platform style
- Transparent background
- Represent log file viewer concept (magnifying glass, text lines, etc.)
```

**Acceptance Criteria**:
- [ ] README created at `build/icons/README.md`
- [ ] Documents icon requirements
- [ ] Notes placeholder status

---

### Phase 5: CI/CD Integration

#### Task 5.1: Create GitHub Actions Workflow
**Priority**: P1 (High)  
**Estimated Time**: 30 minutes  
**Dependencies**: Task 3.1, Task 3.2

**File to Create**: `.github/workflows/build.yml`

**Content** (based on spec §9.1):
```yaml
name: Build Application

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:  # Allow manual trigger

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      
      - name: Install dependencies
        run: uv sync
      
      - name: Run tests
        run: uv run pytest tests/ -v
      
      - name: Build macOS app
        run: bash build/scripts/build-macos.sh
      
      - name: Upload DMG artifact
        uses: actions/upload-artifact@v4
        with:
          name: LogViewer-macos
          path: dist/*.dmg
          retention-days: 30
      
      - name: Upload checksum
        uses: actions/upload-artifact@v4
        with:
          name: LogViewer-macos-checksum
          path: dist/*.sha256
          retention-days: 30

  build-windows:
    runs-on: windows-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      
      - name: Install dependencies
        run: uv sync
      
      - name: Run tests
        run: uv run pytest tests/ -v
      
      - name: Build Windows exe
        run: python build/scripts/build-windows.py
      
      - name: Upload EXE artifact
        uses: actions/upload-artifact@v4
        with:
          name: LogViewer-windows
          path: dist/*.exe
          retention-days: 30
      
      - name: Upload checksum
        uses: actions/upload-artifact@v4
        with:
          name: LogViewer-windows-checksum
          path: dist/*.sha256
          retention-days: 30

  release:
    needs: [build-macos, build-windows]
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/')
    steps:
      - name: Download macOS artifact
        uses: actions/download-artifact@v4
        with:
          name: LogViewer-macos
          path: dist/
      
      - name: Download Windows artifact
        uses: actions/download-artifact@v4
        with:
          name: LogViewer-windows
          path: dist/
      
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
          generate_release_notes: true
```

**Acceptance Criteria**:
- [ ] Workflow file created at `.github/workflows/build.yml`
- [ ] Triggers on version tags (`v*`)
- [ ] Builds on both macOS and Windows
- [ ] Runs tests before build
- [ ] Uploads artifacts
- [ ] Creates GitHub Release

---

### Phase 6: Documentation

#### Task 6.1: Update README with Build Instructions
**Priority**: P1 (High)  
**Estimated Time**: 15 minutes  
**Dependencies**: Task 3.1, Task 3.2

**File to Modify**: `README.md`

**Add Section**:
```markdown
## Building

### Prerequisites

- Python 3.12+
- uv package manager
- PyInstaller 6.0+ (installed automatically)

### Development Build

```bash
# Install dependencies
uv sync

# Run PyInstaller (development)
uv run pyinstaller build/logviewer.spec

# Output: dist/Log Viewer.app (macOS) or dist/LogViewer.exe (Windows)
```

### Production Build

#### macOS
```bash
bash build/scripts/build-macos.sh
# Output: dist/LogViewer-0.1.0-macos.dmg
```

#### Windows
```bash
python build/scripts/build-windows.py
# Output: dist/LogViewer-0.1.0-windows.exe
```

### CI/CD

Builds are automatically created via GitHub Actions when version tags are pushed:

```bash
git tag v0.1.0
git push --tags
```

Artifacts are uploaded to GitHub Releases.
```

**Acceptance Criteria**:
- [ ] README updated with build instructions
- [ ] Prerequisites documented
- [ ] Development build commands included
- [ ] Production build commands included
- [ ] CI/CD process documented

---

#### Task 6.2: Create BUILD.md
**Priority**: P2 (Medium)  
**Estimated Time**: 20 minutes  
**Dependencies**: Task 6.1

**File to Create**: `docs/BUILD.md`

**Content**:
```markdown
# Build Documentation

Detailed build instructions for Log Viewer application.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Build](#development-build)
3. [Production Build](#production-build)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Troubleshooting](#troubleshooting)

## Prerequisites

### All Platforms

- Python 3.12 or higher
- uv package manager ([install guide](https://docs.astral.sh/uv/))
- Git (for version control)

### macOS

- Xcode Command Line Tools: `xcode-select --install`
- hdiutil (built-in, for DMG creation)

### Windows

- Visual C++ Build Tools (for Python extensions)
- Windows 10 SDK (optional, for code signing)

## Development Build

### Install Dependencies

```bash
# Clone repository
git clone <repository-url>
cd log_viewer

# Install dependencies
uv sync
```

### Run Application

```bash
# Run from source
uv run python src/main.py
```

### Build Executable (Development)

```bash
# Run PyInstaller with spec file
uv run pyinstaller build/logviewer.spec

# Output location:
# - macOS: dist/Log Viewer.app
# - Windows: dist/LogViewer.exe
```

## Production Build

### macOS

```bash
# Run build script
bash build/scripts/build-macos.sh

# Output:
# - dist/Log Viewer.app (application bundle)
# - dist/LogViewer-0.1.0-macos.dmg (disk image)
# - dist/LogViewer-0.1.0-macos.dmg.sha256 (checksum)
```

### Windows

```bash
# Run build script
python build/scripts/build-windows.py

# Output:
# - dist/LogViewer-0.1.0-windows.exe (executable)
# - dist/LogViewer-0.1.0-windows.exe.sha256 (checksum)
```

## CI/CD Pipeline

### GitHub Actions Workflow

The build process is automated via GitHub Actions (`.github/workflows/build.yml`).

#### Triggers

- Push of version tag: `git tag v0.1.0 && git push --tags`
- Manual trigger via GitHub UI

#### Build Matrix

| Platform | Runner | Output |
|----------|--------|--------|
| macOS | macos-latest | LogViewer-{version}-macos.dmg |
| Windows | windows-latest | LogViewer-{version}-windows.exe |

#### Process

1. Checkout repository
2. Install uv
3. Install dependencies (`uv sync`)
4. Run tests (`uv run pytest tests/ -v`)
5. Build application
6. Upload artifacts
7. Create GitHub Release (on tag)

### Release Process

1. **Update version** in `pyproject.toml` and `build/logviewer.spec`
2. **Commit changes**: `git commit -am "Bump version to 0.1.0"`
3. **Create tag**: `git tag v0.1.0`
4. **Push tag**: `git push --tags`
5. **Wait for CI**: GitHub Actions builds and uploads artifacts
6. **Verify release**: Download and test artifacts
7. **Publish**: GitHub Release is created automatically

## Troubleshooting

### Common Issues

#### ModuleNotFoundError

**Error**: `ModuleNotFoundError: No module named 'PySide6.QtCore'`

**Solution**: Add missing module to `HIDDEN_IMPORTS` in `build/logviewer.spec`:

```python
HIDDEN_IMPORTS = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    # Add missing module here
]
```

#### Qt Platform Error

**Error**: `Could not find the Qt platform plugin "cocoa" in ""`

**Solution**: Ensure Qt plugins are bundled. Check `build/hooks/hook-PySide6.py` includes:

```python
datas = collect_data_files('PySide6', include_py_files=False)
```

#### UPX Error

**Error**: `UPX compression failed`

**Solution**: Install UPX or disable in spec file:

```python
exe = EXE(
    # ...
    upx=False,  # Disable UPX
)
```

#### Icon Not Found

**Error**: `Icon file not found: build/icons/app.icns`

**Solution**: Create icon files or remove icon parameter from spec file.

### Build Logs

Build logs are available in GitHub Actions under the workflow run.

### Getting Help

1. Check [PyInstaller documentation](https://pyinstaller.org/)
2. Check [PySide6 packaging guide](https://doc.qt.io/qtforpython/deployment.html)
3. Open an issue on GitHub

## Build Verification

### Automated Tests

```bash
# Run test suite before build
uv run pytest tests/ -v
```

### Manual QA Checklist

- [ ] Application launches without console window
- [ ] File open dialog works
- [ ] Log file parsing works
- [ ] Filtering and search work
- [ ] Settings persist across sessions
- [ ] Application icon displays correctly
- [ ] Window title shows application name

## Security Notes

### Unsigned Builds

Current builds are **unsigned**. Users may see warnings:

**macOS**: Right-click the app → Open → Click "Open" in the dialog

**Windows**: Click "More info" → "Run anyway" if SmartScreen warning appears

### Code Signing (Future)

Code signing will be implemented before v1.0 public release.

**Requirements**:
- macOS: Apple Developer certificate ($99/year)
- Windows: Authenticode certificate ($100-400/year)
```

**Acceptance Criteria**:
- [ ] BUILD.md created at `docs/BUILD.md`
- [ ] Prerequisites documented
- [ ] Development build instructions included
- [ ] Production build instructions included
- [ ] CI/CD process documented
- [ ] Troubleshooting section included
- [ ] Security notes included

---

### Phase 7: Windows Startup Performance Optimization

#### Task 7.1: Verify Windows Startup Performance
**Priority**: P0 (Critical)
**Estimated Time**: 30 minutes
**Dependencies**: Task 2.1, Task 3.2

**Objective**: Verify that Windows build achieves < 3 second cold start per spec §10.1.2

**Test Procedure**:
```powershell
# Windows PowerShell startup time test
Measure-Command { Start-Process -Wait -NoNewWindow .\dist\LogViewer.exe }

# Expected: < 3 seconds
# Before optimization: 10+ seconds
# After optimization: < 3 seconds
```

**Verification Checklist**:
- [ ] Windows EXE has `upx=False` in build/logviewer.spec
- [ ] Windows EXE has `strip=True` in build/logviewer.spec
- [ ] EXCLUDED_MODULES list includes all unused modules
- [ ] Build completes without errors
- [ ] Application launches successfully on Windows
- [ ] Cold start time < 3 seconds (measured with PowerShell)
- [ ] File size increase acceptable (~30% larger than UPX-compressed)

**Performance Budget** (per spec §10.1.2):
- Extraction: < 2 seconds
- Python initialization: < 0.5 seconds
- Qt/PySide6 loading: < 0.5 seconds
- Total: < 3 seconds

**If Performance Target Not Met**:
1. Profile extraction time with Process Monitor
2. Add additional modules to EXCLUDED_MODULES
3. Consider switching to `--onedir` mode (requires spec amendment)

---

## Task Summary

| Phase | Task | Priority | Est. Time | Dependencies |
|-------|------|----------|-----------|--------------|
| 1 | Create build directory structure | P0 | 15 min | None |
| 1 | Add PyInstaller dependency | P0 | 5 min | Task 1.1 |
| 2 | Create PyInstaller spec file | P0 | 30 min | Task 1.2 |
| 2 | Create PySide6 hook | P1 | 15 min | Task 2.1 |
| 3 | Create macOS build script | P0 | 20 min | Task 2.1 |
| 3 | Create Windows build script | P0 | 20 min | Task 2.1 |
| 4 | Create placeholder icons | P2 | 30 min | Task 1.1 |
| 5 | Create GitHub Actions workflow | P1 | 30 min | Task 3.1, 3.2 |
| 6 | Update README | P1 | 15 min | Task 3.1, 3.2 |
| 6 | Create BUILD.md | P2 | 20 min | Task 6.1 |
| 7 | Verify Windows startup performance | P0 | 30 min | Task 2.1, 3.2 |

**Total Estimated Time**: ~3.5 hours

---

## Execution Order

### Critical Path (P0)
1. Task 1.1 → Task 1.2 → Task 2.1 → Task 3.1 & Task 3.2 (parallel)

### High Priority (P1)
2. Task 2.2 (can run after Task 2.1)
3. Task 5.1 (can run after Task 3.1 & 3.2)
4. Task 6.1 (can run after Task 3.1 & 3.2)

### Medium Priority (P2)
5. Task 4.1 (can run anytime)
6. Task 6.2 (can run after Task 6.1)

---

## Verification Checklist

After all tasks complete:

- [ ] `uv sync` installs PyInstaller
- [ ] `uv run pyinstaller build/logviewer.spec` succeeds
- [ ] `bash build/scripts/build-macos.sh` creates DMG (on macOS)
- [ ] `python build/scripts/build-windows.py` creates EXE (on Windows)
- [ ] GitHub Actions workflow runs successfully
- [ ] README includes build instructions
- [ ] BUILD.md provides detailed documentation
- [ ] **Windows startup time < 3 seconds** (per spec §10.1.2)
- [ ] Windows EXE has `upx=False` and `strip=True`
- [ ] EXCLUDED_MODULES list applied correctly

---

## Ready for Implementation

This plan is **READY** for spec-orchestrator to delegate to spec-coder.

**Recommended Mode**: Switch to **spec-orchestrator** to begin implementation.

**Suggested Prompt**: "Execute implementation plan for application packaging"