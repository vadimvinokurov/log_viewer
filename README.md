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
