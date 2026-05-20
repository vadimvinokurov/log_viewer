# Log Viewer

Desktop log file viewer with filtering, highlighting, and search. Built with Python and PySide6.

## Features

- Open local files via dialog or drag and drop
- Three match modes: plain text, regex, and boolean query language (`AND`, `OR`, `NOT`)
- Hide non-matching lines with filters, color matching text with highlights
- Category tree with checkboxes to show or hide log sources
- Log level toggles (CRITICAL, ERROR, WARNING, INFO, DEBUG, TRACE) with per-level counts
- Pin important lines to keep them visible
- Command bar for search, filter, highlight, and file operations

## Installation

### Download

Download the latest release for your platform:

- **macOS**: `Log Viewer.dmg` — open, drag to Applications
- **Windows**: `Log Viewer.exe` — run directly

### Build from source

Requires [uv](https://docs.astral.sh/uv/) and Python 3.10+.

```bash
git clone <repo-url> && cd log_viewer
uv sync
uv run log-viewer
```

### Build distributable

```bash
# macOS (.app + .dmg)
cd packaging && bash build-macos.sh

# Windows (.exe)
cd packaging && build-windows.bat
```

Both accept `--clean` to remove previous build artifacts.

## Quick start

1. Open a file — press `Ctrl+O` or type `:open /path/to/file.log` in the command bar
2. Filter — type `:f debug` to hide lines containing "debug"
3. Highlight — type `:h ERROR` to highlight all lines containing "ERROR"

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+O` | Open file dialog |
| `Ctrl+R` | Reload current file |
| `Ctrl+B` | Toggle side panel |
| `Ctrl+Q` | Quit |
| `:` | Activate command bar |
| `↑`/`↓` | Navigate search matches (in search mode) |
| `Esc` | Exit search mode |

## Command reference

All commands are typed in the bottom command bar with a `:` prefix.

**Syntax**: `:command text`

### Match modes

Many commands come in three variants. The suffix selects the match mode:

| Suffix | Mode | Description |
|--------|------|-------------|
| *(none)* | Plain | Exact substring match |
| `r` | Regex | Full Python regex |
| `s` | Simple query | Boolean expressions with `AND`, `OR`, `NOT`, quoted terms |

Simple query examples:
- `:ss "error" AND "timeout"`
- `:ss NOT "info"`
- `:ss ("auth" OR "login") AND "failed"`

### Search

Search activates **search mode** when matches are found. The window title shows the active pattern. Use arrow keys to navigate matches, `Esc` to exit.

| Command | Description |
|---------|-------------|
| `:s text` | Search for plain text |
| `:sr regex` | Search with regex |
| `:ss query` | Search with simple query |

In search mode: `↑`/`↓` navigate matches (wrap around), `Esc` exits. Outside search mode, arrow keys work normally.

### Filters

Filters hide lines that do **not** match the pattern. Multiple filters combine with OR logic.

| Command | Description |
|---------|-------------|
| `:f text` | Add plain text filter |
| `:fr regex` | Add regex filter |
| `:fs query` | Add simple query filter |
| `:rmf` | Remove all filters |
| `:rmf text` | Remove a specific filter |

### Highlights

Highlights apply a background color to matching text. Colors cycle through a built-in palette and can be changed in the side panel.

| Command | Description |
|---------|-------------|
| `:h text` | Add plain text highlight |
| `:hr regex` | Add regex highlight |
| `:hs query` | Add simple query highlight |
| `:rmh` | Remove all highlights |
| `:rmh text` | Remove a specific highlight |

### Categories

Categories are extracted from log lines automatically. Enable or disable them by name.

| Command | Description |
|---------|-------------|
| `:cate` | Enable all categories |
| `:cate name` | Enable a specific category |
| `:catd` | Disable all categories |
| `:catd name` | Disable a specific category |

### Pins

Pin specific line numbers to keep them visible regardless of filters.

| Command | Description |
|---------|-------------|
| `:pin number` | Pin a line by line number |
| `:rmpin` | Unpin all lines |
| `:rmpin number` | Unpin a specific line |

### File

| Command | Description |
|---------|-------------|
| `:open path` | Open a local file |
| `:reload` | Reload the current file |

### Other

| Command | Description |
|---------|-------------|
| `:q` | Quit the application |

## Log format

The viewer auto-detects two log formats:

- **1** — `timestamp category [LOG_LEVEL] message` (e.g. `2024-01-01T10:00:00 app/main [LOG_INFO] Starting`)
- **2** — `timestamp duration level message` (e.g. `10:00:00.000 0.123 msg Application started`)

Lines with a `LOG_` prefix in the level field are detected automatically. Missing level defaults to INFO. Missing category defaults to "uncategorized".

## Log levels

Six levels, toggled via buttons in the bottom bar:

| Level | Icon | Description |
|-------|------|-------------|
| CRITICAL | ⛔ | Highest severity |
| ERROR | 🛑 | Error conditions |
| WARNING | ⚠️ | Potential issues |
| INFO | ℹ️ | Informational messages |
| DEBUG | 🟪 | Debug output |
| TRACE | 🟩 | Verbose trace data |

Each button shows the count of visible lines at that level. Click to show or hide.

## Configuration

All configuration is stored in `~/.logviewer/`:

| File | Purpose |
|------|---------|
| `settings.json` | Window size, last open directory |
| `history.json` | Command history |
