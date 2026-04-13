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
