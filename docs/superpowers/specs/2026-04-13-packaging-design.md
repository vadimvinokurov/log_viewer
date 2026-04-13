# Packaging Design: Log Viewer

## Goal

Package the Log Viewer TUI application into distributable formats:
- **macOS**: `.app` bundle inside `.dmg`
- **Windows**: `.exe` (future, CI/CD)

## Tool

**PyInstaller** — mature, wide platform support, works well with Textual/Rich apps.

## Architecture

### macOS Bundle

```
Log Viewer.app/
├── Contents/
│   ├── Info.plist
│   ├── MacOS/
│   │   └── log-viewer          # PyInstaller executable
│   ├── Resources/
│   │   └── icon.icns
│   └── Frameworks/
```

- Console-mode app: double-click opens Terminal.app with the TUI
- `LSUIElement=false` — shows in Dock while running
- Bundle identifier: `com.logviewer.app`

### DMG Creation

- Use `hdiutil` to create DMG from the `.app` bundle
- Background: simple DMG with app icon + Applications symlink

### Windows EXE (future)

- Single `.exe` via PyInstaller `--onefile`
- Icon as `.ico`
- Build via GitHub Actions on `windows-latest`

## File Structure

```
packaging/
├── log-viewer.spec        # PyInstaller spec file
├── build_dmg.sh           # macOS DMG builder script
├── build_windows.py       # Windows build script (future)
├── icon.icns              # macOS icon
├── icon.ico               # Windows icon
└── icon.png               # Source icon
```

## Icon

Terminal/log-themed free icon from Flaticon or similar source.
- Source: 1024x1024 PNG
- Converted to `.icns` (macOS) and `.ico` (Windows) via `sips` / `iconutil`

## Dependencies Bundled

- Python 3.12+ runtime
- textual>=3.0
- rich>=13.0
- pyperclip>=1.8
- pyyaml>=6.0

## Verification

1. `pyinstaller log-viewer.spec` builds without errors
2. `open "Log Viewer.app"` launches Terminal with the TUI
3. `./build_dmg.sh` produces a valid `.dmg`
4. Installed app runs correctly from `/Applications`
