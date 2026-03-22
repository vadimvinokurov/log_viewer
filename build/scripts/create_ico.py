#!/usr/bin/env python3
"""Convert PNG to Windows ICO format with multiple sizes.

Ref: docs/specs/features/application-packaging.md §7
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image


def create_ico() -> None:
    """Create ICO file from PNG source with multiple sizes."""
    # Paths
    icons_dir = Path(__file__).parent.parent / "icons"
    source_png = icons_dir / "app.PNG"
    output_ico = icons_dir / "app.ico"
    
    # Required sizes per spec §7 (largest first for better quality)
    sizes = [256, 128, 64, 48, 32, 16]
    
    print(f"Loading source image: {source_png}")
    with Image.open(source_png) as img:
        print(f"Source image size: {img.size}")
        print(f"Source image mode: {img.mode}")
        
        # Convert to RGBA if needed
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        # Create images at each size
        icon_images = []
        for size in sizes:
            print(f"Creating {size}x{size} variant...")
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            icon_images.append(resized)
        
        # Save as ICO with PNG compression
        print(f"Saving ICO to: {output_ico}")
        
        # Use bitmap_format='png' for PNG compression within ICO
        icon_images[0].save(
            output_ico,
            format="ICO",
            sizes=[(s, s) for s in sizes],
            append_images=icon_images[1:],
            bitmap_format="png",
        )
    
    # Verify output
    output_size = output_ico.stat().st_size
    print(f"ICO file size: {output_size:,} bytes ({output_size / 1024:.1f} KB)")
    
    if output_size > 500 * 1024:
        print("WARNING: ICO exceeds 500 KB limit")
    else:
        print("✓ ICO file created successfully")
    
    # Verify all sizes are present
    import struct
    with open(output_ico, "rb") as f:
        reserved, ico_type, count = struct.unpack("<HHH", f.read(6))
        print(f"\nICO contains {count} icon sizes:")
        for i in range(count):
            entry = struct.unpack("<BBBBHHII", f.read(16))
            width, height, colors, res, planes, bpp, size, offset = entry
            print(f"  {i+1}. {width}x{height}, {bpp} bits, {size} bytes")


if __name__ == "__main__":
    create_ico()