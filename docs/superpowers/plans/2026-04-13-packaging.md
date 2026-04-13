# Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package Log Viewer TUI into distributable macOS .app/.dmg and prepare Windows .exe support.

**Architecture:** PyInstaller bundles Python + dependencies into a standalone executable. On macOS, a .app bundle wraps the executable and opens it in Terminal.app. `hdiutil` creates the DMG. A custom SVG icon is converted to .icns/.ico formats.

**Tech Stack:** PyInstaller, hdiutil (macOS), sips/iconutil (icon conversion), Python 3.12+

---

## File Structure

| File | Purpose |
|------|---------|
| `packaging/icon.svg` | Source vector icon (terminal + log lines) |
| `packaging/icon.icns` | macOS icon (converted from SVG) |
| `packaging/icon.ico` | Windows icon (converted from SVG) |
| `packaging/log-viewer.spec` | PyInstaller spec file for macOS |
| `packaging/build_dmg.sh` | Shell script to build .app + .dmg on macOS |

---

### Task 1: Create Packaging Directory and SVG Icon

**Files:**
- Create: `packaging/icon.svg`

- [ ] **Step 1: Create packaging directory**

```bash
mkdir -p packaging
```

- [ ] **Step 2: Create SVG icon — terminal window with log lines**

Create `packaging/icon.svg` with a design: dark rounded rectangle (terminal window), colored log lines inside (ERROR red, WARN yellow, INFO green), and a small "LV" badge.

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#1e1e2e"/>
      <stop offset="100%" style="stop-color:#181825"/>
    </linearGradient>
    <linearGradient id="titlebar" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#313244"/>
      <stop offset="100%" style="stop-color:#282838"/>
    </linearGradient>
  </defs>
  <!-- Rounded terminal window -->
  <rect x="64" y="64" width="896" height="896" rx="80" ry="80" fill="url(#bg)" stroke="#45475a" stroke-width="4"/>
  <!-- Title bar -->
  <rect x="64" y="64" width="896" height="120" rx="80" ry="80" fill="url(#titlebar)"/>
  <rect x="64" y="144" width="896" height="40" fill="url(#titlebar)"/>
  <!-- Traffic lights -->
  <circle cx="148" cy="124" r="24" fill="#f38ba8"/>
  <circle cx="224" cy="124" r="24" fill="#f9e2af"/>
  <circle cx="300" cy="124" r="24" fill="#a6e3a1"/>
  <!-- Log lines -->
  <rect x="140" y="260" width="680" height="28" rx="6" fill="#a6e3a1" opacity="0.9"/>
  <rect x="140" y="310" width="540" height="28" rx="6" fill="#89b4fa" opacity="0.7"/>
  <rect x="140" y="360" width="740" height="28" rx="6" fill="#f9e2af" opacity="0.8"/>
  <rect x="140" y="410" width="460" height="28" rx="6" fill="#89b4fa" opacity="0.7"/>
  <rect x="140" y="460" width="820" height="28" rx="6" fill="#f38ba8" opacity="0.9"/>
  <rect x="140" y="510" width="600" height="28" rx="6" fill="#a6e3a1" opacity="0.9"/>
  <rect x="140" y="560" width="500" height="28" rx="6" fill="#89b4fa" opacity="0.7"/>
  <rect x="140" y="610" width="700" height="28" rx="6" fill="#f9e2af" opacity="0.8"/>
  <rect x="140" y="660" width="380" height="28" rx="6" fill="#a6e3a1" opacity="0.9"/>
  <rect x="140" y="710" width="550" height="28" rx="6" fill="#89b4fa" opacity="0.7"/>
  <!-- LV badge -->
  <circle cx="830" cy="830" r="130" fill="#89b4fa" opacity="0.95"/>
  <text x="830" y="878" text-anchor="middle" font-family="monospace" font-size="130" font-weight="bold" fill="#1e1e2e">LV</text>
</svg>
```

- [ ] **Step 3: Verify SVG renders correctly**

```bash
open packaging/icon.svg
```

Expected: Opens in browser/Preview showing a dark terminal with colored log lines and "LV" badge.

- [ ] **Step 4: Commit**

```bash
git add packaging/icon.svg
git commit -m "feat: add log viewer SVG icon"
```

---

### Task 2: Convert Icon to macOS .icns Format

**Files:**
- Create: `packaging/icon.icns`

- [ ] **Step 1: Generate PNG from SVG using sips**

macOS doesn't directly convert SVG→ICNS. We use a Python script to generate the iconset, then `iconutil` to make .icns.

Create a helper script `packaging/make_icons.sh`:

```bash
#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

# Requires: brew install librsvg (for rsvg-convert) or use qlmanage
# Generate 1024x1024 PNG from SVG
if command -v rsvg-convert &>/dev/null; then
    rsvg-convert -w 1024 -h 1024 icon.svg -o icon_1024.png
elif command -v qlmanage &>/dev/null; then
    qlmanage -t -s 1024 -o . icon.svg
    mv icon.svg.png icon_1024.png 2>/dev/null || true
else
    echo "ERROR: Install librsvg (brew install librsvg) for SVG conversion"
    exit 1
fi

# Create iconset directory with all required sizes
mkdir -p icon.iconset
sizes=(16 32 64 128 256 512)
for s in "${sizes[@]}"; do
    sips -z "$s" "$s" icon_1024.png --out "icon.iconset/icon_${s}x${s}.png" >/dev/null 2>&1
done
# Retina variants
for s in 16 32 64 128 256 512; do
    sips -z $((s*2)) $((s*2)) icon_1024.png --out "icon.iconset/icon_${s}x${s}@2x.png" >/dev/null 2>&1
done

# Build .icns
iconutil -c icns icon.iconset -o icon.icns
echo "Created icon.icns"

# Build .ico (requires ImageMagick or use png2ico)
if command -v convert &>/dev/null; then
    convert icon_16x16.png icon_32x32.png icon_48x48.png icon_64x64.png icon_128x128.png icon_256x256.png icon.ico
    echo "Created icon.ico"
else
    echo "Skipping .ico (install ImageMagick for Windows icon)"
fi

# Cleanup
rm -rf icon.iconset icon_1024.png
```

- [ ] **Step 2: Make script executable and run it**

```bash
chmod +x packaging/make_icons.sh
cd packaging && ./make_icons.sh
```

Expected: Creates `packaging/icon.icns` (and optionally `packaging/icon.ico`).

- [ ] **Step 3: Verify icon was created**

```bash
ls -la packaging/icon.icns
```

Expected: File exists, ~200-400KB.

- [ ] **Step 4: Commit**

```bash
git add packaging/icon.icns packaging/icon.ico packaging/make_icons.sh
git commit -m "feat: add macOS/Windows icon files and generation script"
```

---

### Task 3: Create PyInstaller Spec File

**Files:**
- Create: `packaging/log-viewer.spec`

- [ ] **Step 1: Install PyInstaller as dev dependency**

```bash
uv add --dev pyinstaller
```

- [ ] **Step 2: Create spec file**

Create `packaging/log-viewer.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

# Resolve project root (one level up from packaging/)
project_root = Path(SPECPATH).parent
src_dir = project_root / "src"

a = Analysis(
    [str(src_dir / "log_viewer" / "tui" / "app.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[
        # Include all package data from log_viewer
        (str(src_dir / "log_viewer"), "log_viewer"),
    ],
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
    [],
    exclude_binaries=True,
    name="log-viewer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    argv_emulation=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="log-viewer",
)

app = BUNDLE(
    coll,
    name="Log Viewer.app",
    icon=str(Path(SPECPATH) / "icon.icns"),
    bundle_identifier="com.logviewer.app",
    version="0.1.0",
    info_plist={
        "CFBundleName": "Log Viewer",
        "CFBundleDisplayName": "Log Viewer",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "10.15",
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Log File",
                "CFBundleTypeExtensions": ["log", "txt"],
                "CFBundleTypeRole": "Viewer",
            }
        ],
    },
)
```

- [ ] **Step 3: Commit**

```bash
git add packaging/log-viewer.spec pyproject.toml uv.lock
git commit -m "feat: add PyInstaller spec file for macOS packaging"
```

---

### Task 4: Create DMG Build Script

**Files:**
- Create: `packaging/build_dmg.sh`

- [ ] **Step 1: Create the build script**

Create `packaging/build_dmg.sh`:

```bash
#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
PROJECT_ROOT="$(cd .. && pwd)"
APP_NAME="Log Viewer"
DMG_NAME="LogViewer-0.1.0-macOS"
BUILD_DIR="build"
DIST_DIR="dist"

echo "=== Building Log Viewer DMG ==="

# Step 1: Run PyInstaller
echo "[1/3] Running PyInstaller..."
cd "$PROJECT_ROOT"
uv run pyinstaller packaging/log-viewer.spec \
    --clean \
    --noconfirm \
    --distpath "packaging/$DIST_DIR" \
    --workpath "packaging/$BUILD_DIR"

# Step 2: Verify .app was created
echo "[2/3] Verifying .app bundle..."
APP_PATH="packaging/$DIST_DIR/$APP_NAME.app"
if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: $APP_PATH not found!"
    exit 1
fi
echo "  Created: $APP_PATH"

# Step 3: Create DMG
echo "[3/3] Creating DMG..."
DMG_PATH="packaging/$DIST_DIR/$DMG_NAME.dmg"
hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$APP_PATH" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

echo ""
echo "=== Build Complete ==="
echo "  DMG: $DMG_PATH"
echo "  Size: $(du -sh "$DMG_PATH" | cut -f1)"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x packaging/build_dmg.sh
```

- [ ] **Step 3: Commit**

```bash
git add packaging/build_dmg.sh
git commit -m "feat: add DMG build script for macOS packaging"
```

---

### Task 5: Build and Verify DMG

**Files:** (no new files, build artifacts)

- [ ] **Step 1: Generate icon files**

```bash
cd packaging && ./make_icons.sh && cd ..
```

Expected: `packaging/icon.icns` created.

- [ ] **Step 2: Build the DMG**

```bash
cd packaging && ./build_dmg.sh
```

Expected: Creates `packaging/dist/LogViewer-0.1.0-macOS.dmg`.

- [ ] **Step 3: Verify DMG contents**

```bash
hdiutil attach packaging/dist/LogViewer-0.1.0-macOS.dmg
ls "/Volumes/Log Viewer/"
hdiutil detach "/Volumes/Log Viewer"
```

Expected: Shows `Log Viewer.app` inside the mounted DMG.

- [ ] **Step 4: Test the app launches**

```bash
open "packaging/dist/Log Viewer.app"
```

Expected: Terminal.app opens and Log Viewer TUI starts.

- [ ] **Step 5: Add build artifacts to .gitignore**

Append to `.gitignore`:

```
# Packaging build artifacts
packaging/build/
packaging/dist/
packaging/*.png
```

- [ ] **Step 6: Commit .gitignore and packaging files**

```bash
git add .gitignore packaging/
git commit -m "feat: complete macOS DMG packaging with build artifacts in gitignore"
```

---

### Task 6: Add Windows Build Configuration (Future-Ready)

**Files:**
- Create: `packaging/log-viewer-windows.spec`

- [ ] **Step 1: Create Windows spec file**

Create `packaging/log-viewer-windows.spec`:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add packaging/log-viewer-windows.spec
git commit -m "feat: add Windows PyInstaller spec for future CI builds"
```

---

## Self-Review

**Spec coverage:**
- macOS .app bundle → Task 3 (spec), Task 5 (build)
- macOS .dmg → Task 4 (script), Task 5 (build)
- Windows .exe → Task 6 (spec, future-ready)
- Icon → Task 1 (SVG), Task 2 (convert)

**Placeholder scan:** No TBDs, all code shown in full.

**Type consistency:** All paths use `pathlib.Path`, entry point matches `pyproject.toml` (`log_viewer.tui.app:main`).
