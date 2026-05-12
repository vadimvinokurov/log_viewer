#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"
DIST="$ROOT/packaging/dist"
BUILD="$ROOT/packaging/build"
APP_NAME="Log Viewer"

# Parse args
CLEAN=0
SKIP_DMG=0
for arg in "$@"; do
    case "$arg" in
        --clean)   CLEAN=1 ;;
        --no-dmg)  SKIP_DMG=1 ;;
        --help)    echo "Usage: $0 [--clean] [--no-dmg]"; exit 0 ;;
        *)         echo "Unknown arg: $arg"; exit 1 ;;
    esac
done

# Clean
if [ "$CLEAN" -eq 1 ]; then
    rm -rf "$DIST" "$BUILD"
    echo "Cleaned build artifacts"
fi

# Install pyinstaller if needed
uv run --with pyinstaller python -c "import PyInstaller" 2>/dev/null || {
    echo "Installing PyInstaller..."
    uv pip install pyinstaller
}

# Build .app bundle
echo "Building macOS .app bundle..."
uv run --with pyinstaller python -m PyInstaller \
    --noconfirm \
    --distpath "$DIST" \
    --workpath "$BUILD" \
    "$ROOT/packaging/log-viewer.spec"

echo "App bundle: $DIST/$APP_NAME.app"

# Build DMG
if [ "$SKIP_DMG" -eq 0 ]; then
    echo "Creating DMG..."
    DMG_PATH="$DIST/$APP_NAME.dmg"
    rm -f "$DMG_PATH"

    if command -v create-dmg &>/dev/null; then
        create-dmg \
            --volname "$APP_NAME" \
            --app-drop-link 600 185 \
            "$DMG_PATH" \
            "$DIST/$APP_NAME.app"
    else
        # hdiutil fallback
        STAGING="$(mktemp -d)/dmg_staging"
        mkdir -p "$STAGING"
        cp -R "$DIST/$APP_NAME.app" "$STAGING/"
        ln -s /Applications "$STAGING/Applications"
        hdiutil create \
            -volname "$APP_NAME" \
            -srcfolder "$STAGING" \
            -ov \
            -format UDZO \
            "$DMG_PATH"
        rm -rf "$(dirname "$STAGING")"
    fi

    echo "DMG: $DMG_PATH"
fi

echo "Done."
