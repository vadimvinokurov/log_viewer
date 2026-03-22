# Application Packaging Specification

**Version**: 1.0  
**Status**: [DRAFT]  
**Created**: 2026-03-19  
**Feature**: Cross-platform application packaging for macOS (.dmg) and Windows (.exe)

---

## §1 Overview

### §1.1 Purpose
Define packaging requirements for distributing Log Viewer as standalone applications on macOS and Windows platforms.

### §1.2 Scope
- Build system configuration
- Platform-specific packaging
- Distribution artifacts
- Installation experience

### §1.3 Out of Scope
- Code signing (future enhancement)
- Auto-update mechanism (future enhancement)
- Linux packaging (future enhancement)
- App Store distribution

---

## §2 Technology Stack

### §2.1 Packaging Tool: PyInstaller

**Rationale**:
- Industry standard for Python GUI applications
- Excellent PySide6/Qt support with `pyside6` hook
- Cross-platform (macOS, Windows, Linux)
- Active maintenance and community support
- Single-file or directory bundle options

**Alternative Considered**: Nuitka
- Better performance (compiles to C)
- Longer build times
- More complex configuration
- Decision: Use PyInstaller for faster iteration, consider Nuitka for v2.0

### §2.2 Build Tool: PyInstaller

**Version**: >= 6.0.0 (latest stable)

**Key Features Used**:
- `--onefile` for single executable (Windows)
- `--onedir` for app bundle (macOS)
- `--windowed` for GUI application (no console)
- `--name` for custom executable name
- `--icon` for application icon
- `--add-data` for resource bundling
- `--hidden-import` for dynamic imports

---

## §3 Project Configuration

### §3.1 Bundle Identifier

```
com.logviewer.app
```

**Format**: Reverse domain notation  
**Usage**: macOS CFBundleIdentifier, Windows AppUserModelId

### §3.2 Application Metadata

| Property | Value |
|----------|-------|
| Name | Log Viewer |
| Version | 0.1.0 (from pyproject.toml) |
| Description | High-performance log viewer with advanced filtering |
| Author | (from pyproject.toml) |
| License | (from pyproject.toml) |

### §3.3 Entry Point

**Module**: `src.main:main`  
**Entry Function**: `main()` → None  
**Console Mode**: False (GUI application)

---

## §4 Platform-Specific Requirements

### §4.1 macOS Packaging

#### §4.1.1 Bundle Structure

```
Log Viewer.app/
├── Contents/
│   ├── MacOS/
│   │   └── Log Viewer          # Executable
│   ├── Resources/
│   │   ├── app.icns           # Application icon
│   │   └── *.qt*              # Qt resources
│   ├── Frameworks/
│   │   └── (Python + PySide6 frameworks)
│   └── Info.plist             # Bundle metadata
```

#### §4.1.2 Info.plist Configuration

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Log Viewer</string>
    <key>CFBundleDisplayName</key>
    <string>Log Viewer</string>
    <key>CFBundleIdentifier</key>
    <string>com.logviewer.app</string>
    <key>CFBundleVersion</key>
    <string>0.1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>Log Viewer</string>
    <key>CFBundleIconFile</key>
    <string>app.icns</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
```

#### §4.1.3 DMG Configuration

**Format**: Compressed DMG (UDZO)  
**Size**: ~150-200 MB estimated  
**Contents**:
- `Log Viewer.app` (application bundle)
- `Applications` symlink (drag-to-install)

**DMG Creation Tool**: `hdiutil` (macOS built-in)

**DMG Filename**: `LogViewer-0.1.0-macos.dmg`

#### §4.1.4 macOS Requirements

| Requirement | Version |
|-------------|---------|
| Minimum macOS | 10.15 (Catalina) |
| Architecture | Universal (x86_64 + arm64) |
| Python | 3.12+ |
| Qt Framework | PySide6 6.6.0+ |

### §4.2 Windows Packaging

#### §4.2.1 Executable Structure

**Mode**: Single-file executable (`--onefile`)
**Filename**: `LogViewer-0.1.0-windows.exe`

**Startup Optimization Strategy** (per §10.1.2):

To achieve < 3 second cold start with `--onefile` mode, the following optimizations are REQUIRED:

1. **Disable UPX Compression**: UPX decompression adds 2-5 seconds overhead
   - Set `upx=False` in EXE configuration
   - Trade-off: Larger file size (~30% increase), faster extraction

2. **Exclude Unused Modules**: Reduce extraction payload
   - Exclude: `tkinter`, `matplotlib`, `numpy`, `scipy`, `PIL`, `cv2`
   - Exclude: Test frameworks (`pytest`, `unittest` modules)
   - Exclude: Development tools (`pylint`, `black`, `mypy`)

3. **Optimize Hidden Imports**: Include only required PySide6 modules
   - Required: `QtCore`, `QtGui`, `QtWidgets`
   - Optional: `QtSvg` (only if SVG icons used)
   - Exclude: `QtMultimedia`, `QtNetwork`, `QtWebEngine`, `QtSql`

4. **Strip Debug Symbols**: Reduce binary size
   - Set `strip=True` in EXE configuration
   - Removes debug info from Python extension modules

**Rationale**: `--onefile` extracts all binaries to temp directory on every launch. By disabling UPX and reducing payload size, extraction time drops from 10+ seconds to < 2 seconds.

**Alternative Considered**: Directory bundle (`--onedir`)
- Pros: Instant startup (no extraction)
- Cons: Distribution complexity (~100 files), less user-friendly
- Decision: Optimize `--onefile` first, revisit `--onedir` if performance target not met

#### §4.2.2 Windows Metadata

| Property | Value |
|----------|-------|
| Internal Name | LogViewer |
| Original Filename | LogViewer.exe |
| File Version | 0.1.0.0 |
| Product Version | 0.1.0.0 |
| Product Name | Log Viewer |
| File Description | High-performance log viewer |
| Company Name | (from pyproject.toml) |
| Legal Copyright | (from pyproject.toml) |

#### §4.2.3 Windows Requirements

| Requirement | Version |
|-------------|---------|
| Minimum Windows | Windows 10 (1809+) |
| Architecture | x64 |
| Python | 3.12+ |
| Qt Framework | PySide6 6.6.0+ |

#### §4.2.4 Installer (Future Enhancement)

**Tool**: Inno Setup or NSIS  
**Features**:
- Start Menu shortcut
- Desktop shortcut (optional)
- File association (.log, .txt)
- Uninstaller

**Current Scope**: Standalone executable (no installer)

---

## §5 Build Configuration

### §5.1 PyInstaller Spec File

**Location**: `build/logviewer.spec`

**Template** (see §5.2 for platform-specific overrides):

```python
# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Log Viewer application."""

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

# Platform-specific bundle configuration
# See §5.2 for macOS and §5.3 for Windows
```

### §5.2 macOS Build Configuration

```python
# macOS-specific bundle (add to spec file)

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
```

### §5.3 Windows Build Configuration

**Performance Optimizations** (per §10.1.2):

The Windows build uses `--onefile` mode which extracts binaries to a temp directory on every launch. To achieve < 3 second startup, the following optimizations are REQUIRED:

```python
# Windows-specific executable (add to spec file)
# Per §10.1.2: Optimized for fast extraction

exe = EXE(
    pyz=a.pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LogViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,             # §10.1.2: Disabled on Windows (requires MinGW/strip tool)
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
```

**Key Changes from Default**:
- `upx=False`: Disables UPX compression (saves 2-5 seconds extraction time)
- `strip=False`: Disabled on Windows (requires MinGW/strip tool, not available by default)
- `excludes=EXCLUDED_MODULES`: Reduces payload by excluding unused modules (see §5.1)

**Performance Impact**:
- File size: Increases by ~30% (no UPX compression)
- Startup time: Reduces from 10+ seconds to < 3 seconds
- Trade-off: Larger download, faster launch

---

## §6 Build Process

### §6.1 Build Directory Structure

```
build/
├── icons/
│   ├── app.icns          # macOS icon (512x512)
│   ├── app.ico           # Windows icon (256x256)
│   └── app.png           # Source icon (1024x1024)
├── hooks/
│   └── hook-PySide6.py   # PyInstaller hook for PySide6
├── logviewer.spec        # PyInstaller spec file
└── scripts/
    ├── build-macos.sh    # macOS build script
    └── build-windows.py  # Windows build script
```

### §6.2 Build Commands

#### §6.2.1 Development Build

```bash
# Install build dependencies
uv add --dev pyinstaller

# Run PyInstaller (development)
uv run pyinstaller build/logviewer.spec

# Output: dist/Log Viewer.app (macOS) or dist/LogViewer.exe (Windows)
```

#### §6.2.2 Production Build (macOS)

```bash
#!/bin/bash
# build/scripts/build-macos.sh

set -e

echo "Building Log Viewer for macOS..."

# Clean previous build
rm -rf build/darwin dist/

# Create build directories
mkdir -p build/darwin

# Run PyInstaller
uv run pyinstaller \
    --clean \
    --noconfirm \
    build/logviewer.spec

# Create DMG
hdiutil create \
    -volname "Log Viewer" \
    -srcfolder "dist/Log Viewer.app" \
    -ov -format UDZO \
    "dist/LogViewer-0.1.0-macos.dmg"

echo "Build complete: dist/LogViewer-0.1.0-macos.dmg"
```

#### §6.2.3 Production Build (Windows)

```python
# build/scripts/build-windows.py
"""Windows build script for Log Viewer."""

import subprocess
import shutil
from pathlib import Path

def build_windows():
    print("Building Log Viewer for Windows...")
    
    # Clean previous build
    if Path("dist").exists():
        shutil.rmtree("dist")
    
    # Run PyInstaller
    subprocess.run([
        "uv", "run", "pyinstaller",
        "--clean",
        "--noconfirm",
        "build/logviewer.spec"
    ], check=True)
    
    # Rename executable with version
    exe_path = Path("dist/LogViewer.exe")
    versioned_name = Path("dist/LogViewer-0.1.0-windows.exe")
    if exe_path.exists():
        exe_path.rename(versioned_name)
    
    print(f"Build complete: {versioned_name}")

if __name__ == "__main__":
    build_windows()
```

### §6.3 Build Verification

#### §6.3.1 Automated Tests

```bash
# Run test suite before build
uv run pytest tests/ -v

# Verify executable runs
./dist/Log\ Viewer.app/Contents/MacOS/Log\ Viewer --version  # macOS
dist/LogViewer-0.1.0-windows.exe --version                    # Windows
```

#### §6.3.2 Manual QA Checklist

- [ ] Application launches without console window
- [ ] File open dialog works
- [ ] Log file parsing works
- [ ] Filtering and search work
- [ ] Settings persist across sessions
- [ ] Application icon displays correctly
- [ ] Window title shows application name
- [ ] About dialog shows version info

---

## §7 Icon Requirements

### §7.1 Icon Specifications

| Platform | Format | Sizes Required |
|----------|--------|----------------|
| macOS | .icns | 16, 32, 64, 128, 256, 512, 1024 |
| Windows | .ico | 16, 32, 48, 64, 128, 256 |

### §7.2 Icon Generation

**Source**: `build/icons/app.png` (1024x1024 PNG with transparency)

**Generation Tools**:
- macOS: `iconutil` (built-in) or `png2icns`
- Windows: `png2ico` or ImageMagick `convert`

**Icon Design Guidelines**:
- Simple, recognizable at small sizes
- High contrast for visibility
- Consistent with platform style
- Transparent background

### §7.3 Default Icon (Temporary)

If no custom icon provided, use PySide6 default Qt icon.

**Future**: Create custom icon representing log file viewer concept.

---

## §8 Distribution Artifacts

### §8.1 macOS Artifact

**Filename**: `LogViewer-{version}-macos.dmg`  
**Example**: `LogViewer-0.1.0-macos.dmg`

**Contents**:
- `Log Viewer.app` (application bundle)
- `Applications` symlink

**Size Estimate**: 150-200 MB

### §8.2 Windows Artifact

**Filename**: `LogViewer-{version}-windows.exe`  
**Example**: `LogViewer-0.1.0-windows.exe`

**Type**: Standalone executable (no installer)

**Size Estimate**: 50-100 MB

### §8.3 Checksums

Generate SHA256 checksums for verification:

```bash
# macOS
shasum -a 256 dist/LogViewer-0.1.0-macos.dmg > dist/checksums.txt

# Windows (PowerShell)
Get-FileHash dist/LogViewer-0.1.0-windows.exe -Algorithm SHA256
```

---

## §9 CI/CD Integration

### §9.1 GitHub Actions Workflow

**File**: `.github/workflows/build.yml`

```yaml
name: Build Application

on:
  push:
    tags:
      - 'v*'

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      
      - name: Install dependencies
        run: uv sync
      
      - name: Build macOS app
        run: bash build/scripts/build-macos.sh
      
      - name: Upload DMG artifact
        uses: actions/upload-artifact@v4
        with:
          name: LogViewer-macos
          path: dist/*.dmg

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      
      - name: Install dependencies
        run: uv sync
      
      - name: Build Windows exe
        run: python build/scripts/build-windows.py
      
      - name: Upload EXE artifact
        uses: actions/upload-artifact@v4
        with:
          name: LogViewer-windows
          path: dist/*.exe
```

### §9.2 Release Process

1. **Tag Release**: `git tag v0.1.0 && git push --tags`
2. **CI Build**: GitHub Actions builds artifacts
3. **Download Artifacts**: From GitHub Actions
4. **Manual QA**: Verify on target platforms
5. **Publish Release**: GitHub Releases page

---

## §10 Performance Considerations

### §10.1 Startup Time

**Target**: < 3 seconds cold start

**Platform-Specific Strategy**:

#### §10.1.1 macOS (Instant Startup)

**Mode**: `--onedir` (app bundle)
**Startup Time**: < 1 second (no extraction)
**Configuration**: See §5.2

**Optimizations**:
- Pre-extracted binaries in app bundle
- No extraction overhead on launch
- UPX compression acceptable (decompress once during build)

#### §10.1.2 Windows (Optimized Extraction)

**Mode**: `--onefile` (single executable)
**Startup Time Target**: < 3 seconds
**Configuration**: See §5.3 and §4.2.1

**Required Optimizations**:

1. **Disable UPX Compression** (Critical)
   - UPX decompression adds 2-5 seconds to startup
   - Set `upx=False` in Windows EXE configuration
   - Trade-off: ~30% larger file size, but 50-70% faster startup

2. **Exclude Unused Modules** (High Impact)
   - Reduce extraction payload from ~100 MB to ~50 MB
   - See §4.2.1 for complete exclusion list
   - Estimated savings: 1-2 seconds extraction time

3. **Strip Debug Symbols** (Medium Impact) - **DISABLED on Windows**
   - `strip=True` requires Unix `strip` command (not available on Windows by default)
   - Requires MinGW or similar Unix tools installed on Windows
   - **Recommendation**: Keep `strip=False` on Windows unless MinGW is installed
   - Alternative: Use `--exclude-module` to reduce size instead
   - Estimated savings if available: 10-20% file size reduction

4. **Optimize Hidden Imports** (Low Impact)
   - Include only required PySide6 modules
   - See §4.2.1 for module list
   - Estimated savings: 5-10% file size reduction

**Performance Budget**:
- Extraction: < 2 seconds (with optimizations)
- Python initialization: < 0.5 seconds
- Qt/PySide6 loading: < 0.5 seconds
- Total: < 3 seconds

**Measurement Method**:
```powershell
# Windows PowerShell startup time test
Measure-Command { Start-Process -Wait -NoNewWindow .\dist\LogViewer.exe }
```

### §10.2 Memory Footprint

**Baseline**: ~80-120 MB (PySide6 + Python runtime)

**Optimizations**:
- Lazy load non-critical modules
- Release unused resources
- Profile memory usage during development

### §10.3 Bundle Size

**Targets**:
- macOS DMG: < 200 MB
- Windows EXE: < 100 MB

**Size Reduction**:
- Exclude unused Qt modules (QtSvg, QtMultimedia, etc.)
- Strip debug symbols
- UPX compression

---

## §11 Security Considerations

### §11.1 Unsigned Builds (Current)

**macOS**: Users must right-click → Open on first launch  
**Windows**: SmartScreen may show warning

**User Instructions**:
```
macOS: Right-click the app → Open → Click "Open" in the dialog
Windows: Click "More info" → "Run anyway" if SmartScreen warning appears
```

### §11.2 Code Signing (Future)

**macOS**:
- Apple Developer certificate required
- Notarization required for Gatekeeper
- Cost: $99/year

**Windows**:
- Authenticode certificate required
- Cost: $100-400/year

**Recommendation**: Implement code signing before v1.0 public release

---

## §12 Error Handling

### §12.1 Build Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Missing hidden import | Add to `HIDDEN_IMPORTS` |
| `Qt platform error` | Missing Qt plugins | Add `--add-data` for plugins |
| `UPX error` | UPX not installed | Install UPX or disable |
| `Icon not found` | Missing icon file | Create icon assets |

### §12.2 Runtime Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Library not loaded` | Missing framework | Bundle Qt frameworks |
| `Cannot find module` | Missing data file | Add to `DATAS` |
| `Segmentation fault` | Qt platform issue | Check platform plugins |

---

## §13 Testing Strategy

### §13.1 Build Testing

**Unit Tests**: N/A (build scripts)  
**Integration Tests**: Run application from bundle  
**Manual Tests**: QA checklist (see §6.3.2)

### §13.2 Platform Testing

| Platform | Versions | Architecture |
|----------|----------|--------------|
| macOS | 10.15, 11, 12, 13, 14 | x86_64, arm64 |
| Windows | 10, 11 | x64 |

### §13.3 Test Matrix

```yaml
test_matrix:
  macos:
    - os: macos-14 (arm64)
      versions: [macos-14]
    - os: macos-13 (x86_64)
      versions: [macos-13]
  windows:
    - os: windows-10
      versions: [10.0.19041+]
    - os: windows-11
      versions: [10.0.22000+]
```

---

## §14 Documentation

### §14.1 User Documentation

**Location**: `README.md` or `docs/INSTALLATION.md`

**Contents**:
- System requirements
- Download links
- Installation instructions
- Known issues
- Troubleshooting

### §14.2 Developer Documentation

**Location**: `docs/DEVELOPMENT.md`

**Contents**:
- Build prerequisites
- Build commands
- CI/CD process
- Release checklist

---

## §15 Future Enhancements

### §15.1 Short-term (v0.2.0)

- [ ] Custom application icon
- [ ] Code signing (macOS + Windows)
- [ ] Windows installer (Inno Setup)
- [ ] Auto-update mechanism

### §15.2 Long-term (v1.0+)

- [ ] Linux packaging (AppImage, deb, rpm)
- [ ] Mac App Store distribution
- [ ] Microsoft Store distribution
- [ ] Portable mode (settings in app directory)

---

## §16 References

- PyInstaller Documentation: https://pyinstaller.org/
- PySide6 Packaging Guide: https://doc.qt.io/qtforpython/deployment.html
- macOS App Bundle Guide: https://developer.apple.com/library/archive/documentation/CoreFoundation/Conceptual/CFBundles/
- Windows Application Packaging: https://docs.microsoft.com/en-us/windows/win32/appxpkg/

---

## §17 Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Spec Author | [Author] | 2026-03-19 | [DRAFT] |
| Spec Reviewer | [Reviewer] | [Date] | [PENDING] |

---

**End of Specification**