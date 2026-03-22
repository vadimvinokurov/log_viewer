#!/usr/bin/env python3
"""Windows build script for Log Viewer.

Ref: docs/specs/features/windows-startup-optimization.md §3.2.3
Master: docs/SPEC.md §1
"""

from __future__ import annotations

import subprocess
import shutil
import hashlib
from pathlib import Path


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file.

    Ref: docs/specs/features/windows-startup-optimization.md §3.2.3
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def build_windows() -> None:
    """Build Log Viewer for Windows (ZIP archive only).

    Ref: docs/specs/features/windows-startup-optimization.md §3.2.3
    Memory: N/A (build-time script)
    Thread: N/A (no threading)
    Performance: Build time < 5 minutes
    """
    print("Building Log Viewer for Windows...")

    # Configuration
    # Ref: docs/specs/features/windows-startup-optimization.md §3.2.3
    app_name = "LogViewer"
    app_version = "0.1.0"

    # Clean previous build
    print("Cleaning previous build...")
    dist_dir = Path("dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    # Run PyInstaller (onedir mode per T-001)
    # Ref: docs/specs/features/windows-startup-optimization.md §3.2.1
    print("Running PyInstaller...")
    result = subprocess.run(
        ["uv", "run", "pyinstaller", "--clean", "--noconfirm", "build/logviewer.spec"],
        check=False
    )

    if result.returncode != 0:
        print(f"ERROR: PyInstaller failed with code {result.returncode}")
        exit(1)

    # Verify onedir build
    # Ref: docs/specs/features/windows-startup-optimization.md §3.2.3
    app_dir = dist_dir / app_name
    if not app_dir.exists():
        print(f"ERROR: Build failed - {app_dir} not found")
        exit(1)

    # Create ZIP archive
    # Ref: docs/specs/features/windows-startup-optimization.md §3.2.3
    print("Creating ZIP archive...")
    archive_path = dist_dir / f"{app_name}-{app_version}-windows"
    shutil.make_archive(
        str(archive_path),
        "zip",
        app_dir
    )

    # Generate checksum
    # Ref: docs/specs/features/windows-startup-optimization.md §3.2.3
    print("Generating checksum...")
    archive_zip = Path(f"{archive_path}.zip")
    checksum = calculate_sha256(archive_zip)
    checksum_file = dist_dir / f"{archive_zip.name}.sha256"

    with open(checksum_file, "w") as f:
        f.write(f"{checksum}  {checksum_file.stem}\n")

    # Summary
    print()
    print("=" * 50)
    print("Build complete!")
    print("=" * 50)
    print(f"Archive: dist/{archive_zip.name}")
    print(f"Checksum: dist/{checksum_file.name}")
    print()
    print(f"To test: Extract and run {app_name}/{app_name}.exe")
    print("=" * 50)


if __name__ == "__main__":
    build_windows()