# Build Documentation

Detailed build instructions for Log Viewer application.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Build](#development-build)
3. [Production Build](#production-build)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Troubleshooting](#troubleshooting)

## Prerequisites

### All Platforms

- Python 3.12 or higher
- uv package manager ([install guide](https://docs.astral.sh/uv/))
- Git (for version control)

### macOS

- Xcode Command Line Tools: `xcode-select --install`
- hdiutil (built-in, for DMG creation)

### Windows

- Visual C++ Build Tools (for Python extensions)
- Windows 10 SDK (optional, for code signing)

## Development Build

### Install Dependencies

```bash
# Clone repository
git clone <repository-url>
cd log_viewer

# Install dependencies
uv sync
```

### Run Application

```bash
# Run from source
uv run python src/main.py
```

### Build Executable (Development)

```bash
# Run PyInstaller with spec file
uv run pyinstaller build/logviewer.spec

# Output location:
# - macOS: dist/Log Viewer.app
# - Windows: dist/LogViewer.exe
```

## Production Build

### macOS

```bash
# Run build script
bash build/scripts/build-macos.sh

# Output:
# - dist/Log Viewer.app (application bundle)
# - dist/LogViewer-0.1.0-macos.dmg (disk image)
# - dist/LogViewer-0.1.0-macos.dmg.sha256 (checksum)
```

### Windows

```bash
# Run build script
python build/scripts/build-windows.py

# Output:
# - dist/LogViewer-0.1.0-windows.zip (ZIP archive)
# - dist/LogViewer-0.1.0-windows.zip.sha256 (checksum)
```

#### Windows Distribution Format

The build script creates a ZIP archive:

- **ZIP Archive**: `LogViewer-{version}-windows.zip`
  - Contains `LogViewer/LogViewer.exe` directory
  - Extract and run directly (no installation required)
  - Portable (can run from USB drive)

## CI/CD Pipeline

### GitHub Actions Workflow

The build process is automated via GitHub Actions (`.github/workflows/build.yml`).

#### Triggers

- Push of version tag: `git tag v0.1.0 && git push --tags`
- Manual trigger via GitHub UI

#### Build Matrix

| Platform | Runner | Output |
|----------|--------|--------|
| macOS | macos-latest | LogViewer-{version}-macos.dmg |
| Windows | windows-latest | LogViewer-{version}-windows.exe |

#### Process

1. Checkout repository
2. Install uv
3. Install dependencies (`uv sync`)
4. Run tests (`uv run pytest tests/ -v`)
5. Build application
6. Upload artifacts
7. Create GitHub Release (on tag)

### Release Process

1. **Update version** in `pyproject.toml` and `build/logviewer.spec`
2. **Commit changes**: `git commit -am "Bump version to 0.1.0"`
3. **Create tag**: `git tag v0.1.0`
4. **Push tag**: `git push --tags`
5. **Wait for CI**: GitHub Actions builds and uploads artifacts
6. **Verify release**: Download and test artifacts
7. **Publish**: GitHub Release is created automatically

## Troubleshooting

### Common Issues

#### ModuleNotFoundError

**Error**: `ModuleNotFoundError: No module named 'PySide6.QtCore'`

**Solution**: Add missing module to `HIDDEN_IMPORTS` in `build/logviewer.spec`:

```python
HIDDEN_IMPORTS = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    # Add missing module here
]
```

#### Qt Platform Error

**Error**: `Could not find the Qt platform plugin "cocoa" in ""`

**Solution**: Ensure Qt plugins are bundled. Check `build/hooks/hook-PySide6.py` includes:

```python
datas = collect_data_files('PySide6', include_py_files=False)
```

#### UPX Error

**Error**: `UPX compression failed`

**Solution**: Install UPX or disable in spec file:

```python
exe = EXE(
    # ...
    upx=False,  # Disable UPX
)
```

#### Icon Not Found

**Error**: `Icon file not found: build/icons/app.icns`

**Solution**: Create icon files or remove icon parameter from spec file.

### Build Logs

Build logs are available in GitHub Actions under the workflow run.

### Getting Help

1. Check [PyInstaller documentation](https://pyinstaller.org/)
2. Check [PySide6 packaging guide](https://doc.qt.io/qtforpython/deployment.html)
3. Open an issue on GitHub

## Build Verification

### Automated Tests

```bash
# Run test suite before build
uv run pytest tests/ -v
```

### Manual QA Checklist

- [ ] Application launches without console window
- [ ] File open dialog works
- [ ] Log file parsing works
- [ ] Filtering and search work
- [ ] Settings persist across sessions
- [ ] Application icon displays correctly
- [ ] Window title shows application name

## Security Notes

### Unsigned Builds

Current builds are **unsigned**. Users may see warnings:

**macOS**: Right-click the app → Open → Click "Open" in the dialog

**Windows**: Click "More info" → "Run anyway" if SmartScreen warning appears

### Code Signing (Future)

Code signing will be implemented before v1.0 public release.

**Requirements**:
- macOS: Apple Developer certificate ($99/year)
- Windows: Authenticode certificate ($100-400/year)