"""Build script for Log Viewer desktop packages.

Usage:
    python build.py          # Build for current platform
    python build.py --dmg    # Build macOS DMG (macOS only)
    python build.py --clean  # Clean build artifacts before building
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGING = ROOT / "packaging"
DIST = PACKAGING / "dist"
BUILD = PACKAGING / "build"
APP_NAME = "Log Viewer"


def clean() -> None:
    """Remove build artifacts."""
    for d in (DIST, BUILD):
        if d.exists():
            shutil.rmtree(d)
            print(f"Removed {d}")


def run_pyinstaller(spec: Path) -> None:
    """Run PyInstaller with the given spec file."""
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--distpath",
        str(DIST),
        "--workpath",
        str(BUILD),
        str(spec),
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd)


def create_dmg() -> None:
    """Create a DMG from the .app bundle using create-dmg."""
    app_bundle = DIST / f"{APP_NAME}.app"
    if not app_bundle.exists():
        print(f"Error: {app_bundle} not found. Run PyInstaller first.")
        sys.exit(1)

    dmg_path = DIST / f"{APP_NAME}.dmg"

    # Remove existing DMG if any
    if dmg_path.exists():
        dmg_path.unlink()

    # Try create-dmg first, fall back to hdiutil
    if shutil.which("create-dmg"):
        cmd = [
            "create-dmg",
            "--volname",
            APP_NAME,
            "--app-drop-link",
            "600",
            "185",
            str(dmg_path),
            str(app_bundle),
        ]
        print(f"Creating DMG with create-dmg: {' '.join(cmd)}")
        subprocess.check_call(cmd)
    else:
        # Fallback: use hdiutil to create a simple DMG
        print("create-dmg not found, using hdiutil fallback")
        _create_dmg_hdiutil(app_bundle, dmg_path)

    print(f"DMG created: {dmg_path}")


def _create_dmg_hdiutil(app_bundle: Path, dmg_path: Path) -> None:
    """Create DMG using hdiutil (fallback when create-dmg is not available)."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "dmg_staging"
        staging.mkdir()

        # Copy app bundle to staging
        shutil.copytree(app_bundle, staging / app_bundle.name)

        # Create a symlink to /Applications for drag-and-drop install
        applications_link = staging / "Applications"
        applications_link.symlink_to("/Applications")

        # Create the DMG
        cmd = [
            "hdiutil",
            "create",
            "-volname",
            APP_NAME,
            "-srcfolder",
            str(staging),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        ]
        subprocess.check_call(cmd)


def build(clean_first: bool = False, make_dmg: bool = False) -> None:
    """Build for the current platform."""
    if clean_first:
        clean()

    system = platform.system()

    if system == "Darwin":
        spec = PACKAGING / "log-viewer.spec"
        run_pyinstaller(spec)
        print(f"macOS .app bundle created: {DIST / f'{APP_NAME}.app'}")

        if make_dmg:
            create_dmg()
    elif system == "Windows":
        spec = PACKAGING / "log-viewer-windows.spec"
        run_pyinstaller(spec)
        print(f"Windows .exe created: {DIST / f'{APP_NAME}.exe'}")
    else:
        print(f"Unsupported platform: {system}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Log Viewer packages")
    parser.add_argument("--clean", action="store_true", help="Clean before building")
    parser.add_argument("--dmg", action="store_true", help="Create DMG (macOS only)")
    args = parser.parse_args()

    build(clean_first=args.clean, make_dmg=args.dmg)


if __name__ == "__main__":
    main()
