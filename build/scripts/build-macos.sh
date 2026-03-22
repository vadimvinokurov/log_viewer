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