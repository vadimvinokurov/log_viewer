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

## Icon Generation Commands

### macOS (from PNG)

```bash
# Create iconset directory
mkdir app.iconset

# Generate required sizes
sips -z 16 16     app.png --out app.iconset/icon_16x16.png
sips -z 32 32     app.png --out app.iconset/icon_16x16@2x.png
sips -z 32 32     app.png --out app.iconset/icon_32x32.png
sips -z 64 64     app.png --out app.iconset/icon_32x32@2x.png
sips -z 128 128   app.png --out app.iconset/icon_128x128.png
sips -z 256 256   app.png --out app.iconset/icon_128x128@2x.png
sips -z 256 256   app.png --out app.iconset/icon_256x256.png
sips -z 512 512   app.png --out app.iconset/icon_256x256@2x.png
sips -z 512 512   app.png --out app.iconset/icon_512x512.png
sips -z 1024 1024 app.png --out app.iconset/icon_512x512@2x.png

# Convert to icns
iconutil -c icns app.iconset -o app.icns

# Cleanup
rm -rf app.iconset
```

### Windows (from PNG)

```bash
# Using ImageMagick
convert app.png -define icon:auto-resize=256,128,64,48,32,16 app.ico

# Or using png2ico
png2ico app.ico app.png
```

## Temporary Workaround

For initial builds, the spec file references icon paths that don't exist yet. To build without icons:

1. Remove `icon='build/icons/app.icns'` from macOS BUNDLE in `build/logviewer.spec`
2. Remove `icon='build/icons/app.ico'` from Windows EXE in `build/logviewer.spec`

PyInstaller will use the default Qt icon automatically.