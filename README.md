# Log Viewer

High-performance log viewer for multi-gigabyte log files with advanced filtering capabilities.

## Features

- **Large File Support**: Handle multi-gigabyte log files efficiently with lazy loading
- **Advanced Filtering**: Three filter modes - Plain, Regex, Simple query language
- **Category Tree**: Hierarchical category filtering with parent/child toggle behavior
- **Custom Categories**: Define custom categories with pattern matching
- **Text Highlighting**: User-defined highlight patterns with colors
- **Auto-Reload**: Detect file changes and prompt for reload
- **Find in Results**: Search within filtered results with highlighting
- **Statistics**: Real-time log statistics by level and category

## Requirements

- Python 3.12+
- PySide6

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd log_viewer

# Install dependencies
uv sync
```

## Usage

```bash
# Run the application
uv run log-viewer

# Or run directly
python -m src.main
```

## Log Format

The application expects log lines in the following format:
```
TIMESTAMP CATEGORY MESSAGE
```

Example:
```
25-02-2026T18:31:00.965 HordeMode/scripts/app LOG_ERROR Main_Story - Start Activity
25-02-2026T18:31:01.043 server_dll/LEECH/CORE LOG_WARNING disconnect client called
25-02-2026T18:31:02.123 app/controllers LOG_MSG User logged in
```

### Log Levels

Log levels are detected from the first word of the message:
- `LOG_ERROR` - Displayed with red background
- `LOG_WARNING` - Displayed with yellow background
- `LOG_MSG` or no marker - Default white background

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
| Ctrl+R | Reload file |
| Ctrl+F | Find in results |
| Ctrl+C | Copy selected rows |
| Ctrl+A | Select all |
| Enter | Apply filter |
| Escape | Clear filter |

## Project Structure

```
log_viewer/
├── src/
│   ├── core/           # Business logic (UI-agnostic)
│   │   ├── category_tree.py    # Category tree management
│   │   ├── filter_engine.py    # Filtering logic
│   │   ├── highlight_engine.py # Text highlighting
│   │   ├── parser.py           # Log parsing
│   │   ├── simple_query_parser.py  # Query language parser
│   │   └── statistics.py       # Statistics calculator
│   ├── models/         # Data models
│   │   ├── filter_state.py     # Filter state model
│   │   ├── log_document.py     # Document model
│   │   └── log_entry.py        # Log entry model
│   ├── views/          # PySide6 UI components
│   │   ├── category_panel.py   # Category tree panel
│   │   ├── filter_toolbar.py   # Filter toolbar
│   │   ├── find_dialog.py      # Find dialog
│   │   ├── log_table_view.py   # Main table view
│   │   ├── main_window.py      # Main window
│   │   ├── statistics_panel.py # Statistics panel
│   │   └── widgets/            # Custom widgets
│   ├── controllers/    # MVC controllers
│   │   ├── file_watcher.py     # File change watcher
│   │   ├── filter_controller.py # Filter control
│   │   └── main_controller.py  # Main controller
│   └── utils/          # Utility functions
│       ├── clipboard.py        # Clipboard utilities
│       └── settings_manager.py # Settings persistence
└── tests/              # Test suite
    ├── conftest.py             # Pytest fixtures
    ├── test_category_tree.py   # Category tree tests
    ├── test_filter_engine.py   # Filter engine tests
    ├── test_highlight_engine.py # Highlight engine tests
    ├── test_integration.py     # Integration tests
    ├── test_parser.py          # Parser tests
    ├── test_settings_manager.py # Settings tests
    └── test_statistics.py      # Statistics tests
```

## Development

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src

# Run linter
uv run ruff check .

# Run type checker
uv run mypy src
```

## Architecture

### MVC Pattern

The application follows the Model-View-Controller (MVC) pattern:

- **Models**: Data structures and business logic (`src/models/`, `src/core/`)
- **Views**: UI components (`src/views/`)
- **Controllers**: Coordination between models and views (`src/controllers/`)

### Lazy Loading

The `LogDocument` class implements lazy loading for large files:
- Builds byte-offset index during initial load
- Reads lines on-demand from file
- Memory-efficient for multi-gigabyte files

### Category Tree

The `CategoryTree` class manages hierarchical categories:
- Parent toggle affects all children
- Child toggle does not affect parent
- Supports custom categories with regex patterns

### Filter Engine

The `FilterEngine` supports three filter modes:
- Plain text (case-insensitive substring)
- Regex (Python regular expressions)
- Simple query language (AND/OR/NOT operations)

## Testing

The test suite includes:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Performance Tests**: Test with large datasets

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_filter_engine.py

# Run with verbose output
uv run pytest -v

# Run specific test class
uv run pytest tests/test_filter_engine.py::TestFilterEngine

# Run specific test
uv run pytest tests/test_filter_engine.py::TestFilterEngine::test_plain_filter
```

## License

MIT License