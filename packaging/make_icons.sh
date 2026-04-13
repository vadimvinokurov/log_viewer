#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

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

# Build .ico (requires ImageMagick)
if command -v convert &>/dev/null; then
    convert icon_16x16.png icon_32x32.png icon_48x48.png icon_64x64.png icon_128x128.png icon_256x256.png icon.ico
    echo "Created icon.ico"
else
    echo "Skipping .ico (install ImageMagick for Windows icon: brew install imagemagick)"
fi

# Cleanup
rm -rf icon.iconset icon_1024.png
