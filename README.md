# Log Viewer

High-performance log viewer for multi-gigabyte log files with advanced filtering capabilities.

## Building

### Prerequisites

- Python 3.12 or higher
- uv package manager ([install guide](https://docs.astral.sh/uv/))
- PyInstaller 6.0+ (installed automatically with `uv sync`)

### Production Build

#### macOS

```bash
bash build/scripts/build-macos.sh
# Output: dist/LogViewer-0.1.0-macos.dmg
```

#### Windows

```bash
python build/scripts/build-windows.py
# Output: dist/LogViewer-0.1.0-windows.zip
```

## Features

- **Large File Support**: Handle multi-gigabyte log files efficiently with lazy loading
- **Advanced Filtering**: Three filter modes - Plain, Regex, Simple query language
- **Category Tree**: Hierarchical category filtering with parent/child toggle behavior
- **Custom Categories**: Define custom categories with pattern matching
- **Text Highlighting**: User-defined highlight patterns with colors
- **Auto-Reload**: Detect file changes and prompt for reload
- **Find in Results**: Search within filtered results with highlighting
- **Statistics**: Real-time log statistics by level and category

### File Association

Open log files directly from your file manager:

- **macOS**: Right-click `.log` or `.txt` file → Open With → Log Viewer
- **Windows**: Right-click `.log` file → Open with → Log Viewer

See [docs/FILE_ASSOCIATION.md](docs/FILE_ASSOCIATION.md) for detailed instructions.

### Multi-Instance Behavior

Log Viewer runs as multiple independent process instances:

- Each app icon click launches a **NEW** process instance
- Each "Open with..." launches a **NEW** process instance
- Each instance is completely independent with its own memory
- Closing one instance doesn't affect other instances

**Memory Usage**: Each instance uses ~80-120 MB of memory.

See [docs/MULTI_INSTANCE.md](docs/MULTI_INSTANCE.md) for more details.

## Requirements

- Python 3.12+
- PySide6

## Installation

### From Source

```bash
# Clone the repository
git clone <repo-url>
cd log_viewer

# Install dependencies
uv sync
```

### Windows Installation

Log Viewer for Windows is distributed as a ZIP archive:

1. Download `LogViewer-{version}-windows.zip` from releases
2. Extract to desired location
3. Run `LogViewer/LogViewer.exe`

**Features**:
- No installation required
- Portable (can run from USB drive)
- Settings stored in application directory

**Startup Time**: < 3 seconds on first launch (cold start).

## Usage

```bash
# Run the application
uv run log-viewer

# Or run directly
python -m src.main
```

## Filter Modes

### Plain Mode
Case-insensitive substring search in the message.

Example: `error` matches any message containing "error" (case-insensitive)

### Regex Mode
Standard Python regular expression matching.

Example: `Error:\s*\d+` matches "Error: 404", "Error:   500", etc.

### Simple Query Language
Custom query language with operators:
- `and` - Logical AND
- `or` - Logical OR
- `not` - Logical NOT
- `` `text` `` - Literal text (use `\`` to escape backticks)

Examples:
- `` `error` and `failed` `` - Messages containing both "error" and "failed"
- `` `error` or `warning` `` - Messages containing either "error" or "warning"
- `` `error` and not `ignored` `` - Error messages that don't contain "ignored"
- `` (`error` or `warning`) and `system` `` - System errors or warnings

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open file |
| F5 | Reload file |
| Ctrl+W | Close file |
| Ctrl+F | Find in results |
| Ctrl+A | Select all |
| Ctrl+C | Copy selected rows |
| Ctrl+Q | Exit application |
| Ctrl+Shift+P | Toggle panels |
| Enter | Apply filter (in filter input) |
| Escape | Clear filter (in filter input) |
