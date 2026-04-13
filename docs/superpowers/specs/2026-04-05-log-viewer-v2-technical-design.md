# Technical Specification: Log Viewer v2.0

**Date:** 2026-04-05
**Status:** Approved
**Stack:** Python 3.9+ / Textual / uv

---

## 1. Architecture Overview

### 1.1 Approach: Event-Driven with Central Store

Two-package architecture with a pure Python core library and a Textual TUI frontend. Core library has zero Textual dependency and is fully testable with plain pytest. TUI layer bridges via Textual's reactive attributes.

```
┌─────────────────────┐     ┌────────────────────────┐
│  log_viewer_core     │     │   log_viewer_tui        │
│  (pure Python)       │     │   (Textual frontend)    │
│                      │     │                         │
│  - LogStore          │◄───►│  - LogPanel (DataTable) │
│  - Parser            │     │  - CategoryPanel (Tree) │
│  - FilterEngine      │     │  - StatusBar            │
│  - CommandParser     │     │  - CommandInput         │
│  - SimpleQueryParser │     │  - Screens (modals)     │
│  - PresetManager     │     │                         │
│  - ConfigManager     │     │  Widgets react to core  │
│  - Models            │     │  state via reactives    │
└─────────────────────┘     └────────────────────────┘
```

### 1.2 Data Flow

```
User input → CommandInput → CommandParser → core operation
                                                  │
LogPanel ◄── reactive watch ◄── LogStore ◄───────┘
CategoryPanel ◄── reactive watch ◄── LogStore
StatusBar ◄── reactive watch ◄── LogStore
```

---

## 2. Project Structure

```
log_viewer/
├── pyproject.toml                  # uv project config, deps for both packages
├── src/
│   ├── log_viewer_core/            # Pure Python library (no Textual)
│   │   ├── __init__.py
│   │   ├── models.py               # Data classes: LogLine, Filter, Highlight, etc.
│   │   ├── parser.py               # Log format parser (default + custom formats)
│   │   ├── log_store.py            # LogStore: holds parsed lines, categories, state
│   │   ├── filter_engine.py        # Filter/Highlight/Search matching engine
│   │   ├── command_parser.py       # Parses :f/cs/text, :h/color=red/X etc.
│   │   ├── simple_query.py         # Simple mode AST parser (AND, OR, NOT)
│   │   ├── preset_manager.py       # Save/load YAML presets
│   │   └── config.py               # Config manager (~/.logviewer/settings.json)
│   │
│   └── log_viewer_tui/             # Textual TUI application
│       ├── __init__.py
│       ├── app.py                  # Main App class, mode state machine
│       ├── widgets/
│       │   ├── log_panel.py        # DataTable wrapper for log lines
│       │   ├── category_panel.py   # Tree widget for category hierarchy
│       │   ├── status_bar.py       # Statistics display
│       │   └── command_input.py    # Input widget for : / ? commands
│       ├── screens/
│       │   ├── filter_list.py      # :lsf / :lsh modal
│       │   └── category_list.py    # :lscat modal
│       ├── themes.py               # Dark/Light theme definitions
│       └── key_bindings.py         # Vim-style key binding definitions
│
└── tests/
    ├── unit/
    │   ├── test_models.py
    │   ├── test_parser.py
    │   ├── test_log_store.py
    │   ├── test_filter_engine.py
    │   ├── test_command_parser.py
    │   ├── test_simple_query.py
    │   └── test_preset_manager.py
    └── integration/
        ├── test_tui_commands.py
        └── test_file_loading.py
```

### 2.1 Dependencies

```toml
[project]
dependencies = [
    "textual>=3.0",
    "rich>=13.0",
    "pyperclip>=1.8",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
    "black>=24.0",
    "mypy>=1.10",
]
```

---

## 3. Data Models (`models.py`)

### 3.1 Enums

```python
class LogLevel(Enum):
    CRITICAL = "LOG_CRITICAL"
    ERROR = "LOG_ERROR"
    WARNING = "LOG_WARNING"
    INFO = "LOG_INFO"
    DEBUG = "LOG_DEBUG"
    TRACE = "LOG_TRACE"

class SearchMode(Enum):
    PLAIN = "plain"
    REGEX = "regex"
    SIMPLE = "simple"

class SearchDirection(Enum):
    FORWARD = "forward"
    BACKWARD = "backward"

class InputMode(Enum):
    NORMAL = "normal"
    COMMAND = "command"
    SEARCH_FORWARD = "search_forward"
    SEARCH_BACKWARD = "search_backward"
```

### 3.2 Core Data Classes

```python
@dataclass
class LogLine:
    line_number: int        # Original line number in file (1-based)
    timestamp: str          # Raw timestamp string
    category: str           # e.g. "HordeMode/game_storage/folder"
    level: LogLevel         # Enum value; LOG_INFO when no LOG_* found
    message: str            # Full message text
    raw: str                # Original unparsed line (for copy/export)

@dataclass
class Filter:
    pattern: str            # The search text/pattern
    mode: SearchMode        # PLAIN, REGEX, SIMPLE
    case_sensitive: bool    # False by default

@dataclass
class Highlight:
    pattern: str
    mode: SearchMode
    case_sensitive: bool
    color: str              # Named color or #HEX

@dataclass
class SearchState:
    pattern: str
    mode: SearchMode
    case_sensitive: bool
    direction: SearchDirection
    matches: list[int]      # Line numbers of matches
    current_index: int      # Current position in matches list

@dataclass
class CategoryNode:
    name: str               # e.g. "dns"
    full_path: str          # e.g. "network/dns"
    enabled: bool           # True by default
    line_count: int         # Number of log lines in this category
    children: dict[str, "CategoryNode"]  # Child nodes
```

---

## 4. Parser (`parser.py`)

### 4.1 Default Format

The format is hardcoded (not loaded from file):

```json
{
    "name": "default",
    "description": "Format: timestamp category level message",
    "delimiter": {"type": "regex", "pattern": "\\s+", "maxSplits": 3},
    "fields": [
        {"name": "timestamp", "position": 0},
        {"name": "category", "position": 1},
        {"name": "level", "position": 2},
        {"name": "message", "position": 3, "rest": true}
    ]
}
```

### 4.2 Parsing Algorithm

1. Split line by regex `\s+` with `maxSplits=3` → up to 4 parts: `[timestamp, category, level, message]`
2. Validate:
   - **Timestamp** (position 0): check if matches ISO8601-like pattern (`\d{2,4}-\d{2}-\d{2}T...`)
   - **Category** (position 1): accept any non-empty string (may contain `/`)
   - **Level** (position 2): check for `LOG_*` prefix
     - If `LOG_*` found → use corresponding `LogLevel` enum value
     - If no `LOG_*` → default to `LogLevel.INFO`, merge position 2 into message
3. Fallback: if a line has only a timestamp (1 field after split), the entire line (including timestamp) becomes the message with `LogLevel.INFO`, category = `"uncategorized"`. If a line has 2 fields (timestamp + one more), treat as timestamp + message, with category = `"uncategorized"` and level = `LogLevel.INFO`

### 4.3 Uncategorized Lines

Lines with no parseable category go to a virtual category `"uncategorized"`. These display with a ⚠️ icon in the category tree.

---

## 5. LogStore (`log_store.py`)

### 5.1 State

```python
class LogStore:
    lines: list[LogLine]                        # All parsed lines
    category_tree: CategoryNode                  # Root of category hierarchy
    category_counts: dict[str, int]              # Line count per full category path
    level_counts: dict[LogLevel, int]            # Total count per level
    enabled_categories: set[str] | None          # None = all enabled
    disabled_categories: set[str]                # Explicitly disabled categories
    filters: list[Filter]                        # Active filters
    highlights: list[Highlight]                  # Active highlights
    search_state: SearchState | None             # Current search
    current_file: str | None                     # Path or URL of loaded file
    filtered_indices: list[int]                  # Computed from filters + categories
    visible_level_counts: dict[LogLevel, int]    # Counts for visible lines only
```

### 5.2 Operations

| Method | Description |
|--------|-------------|
| `load_lines(lines: list[str])` | Parse and store all lines. Build category tree and counts. |
| `add_filter(filter: Filter)` | Add filter, recompute `filtered_indices`. |
| `remove_filter(pattern: str, cs: bool)` | Remove by exact match, recompute. |
| `clear_filters()` | Remove all filters, recompute. |
| `add_highlight(h: Highlight)` | Add highlight (no recompute needed — display-only). |
| `remove_highlight(pattern: str, cs: bool, color: str)` | Remove by exact match. |
| `clear_highlights()` | Remove all highlights. |
| `enable_category(path: str)` | Enable category and all children (inheritance down). |
| `disable_category(path: str)` | Disable category and all children (inheritance down). |
| `enable_all_categories()` | Reset to all enabled. |
| `disable_all_categories()` | Disable everything. |
| `search(pattern, mode, cs, direction)` | Compute match indices within filtered view. |
| `next_match()` | Move to next match. Returns line number. |
| `prev_match()` | Move to previous match. Returns line number. |
| `apply_filters()` | Recompute `filtered_indices` from filters + category state. |

### 5.3 Filter Combination Rules

- **Multiple filters** → OR logic (line shown if ANY filter matches)
- **Category filtering** → applied first, filters applied on top
- **Search** → operates within filtered+category-selected view
- **Highlights** → display-only, do not affect filtering

### 5.4 Category Inheritance

- `enable_category("network")` → enables `network` and all descendants
- `disable_category("network/dns")` → disables `network/dns` and all descendants
- **Leaf Priority**: explicitly set child state overrides parent inheritance
- When checking if a line's category is visible:
  1. Find the most specific (deepest) explicitly set category in the path
  2. If that category is disabled → line hidden
  3. If no explicit setting → inherit from nearest ancestor
  4. Default → all enabled

---

## 6. FilterEngine (`filter_engine.py`)

### 6.1 Match Methods

```python
def match(line: str, filter: Filter) -> bool:
    """Check if a line matches a filter/search/highlight pattern."""
```

**Plain mode:**
- Case insensitive (default): `pattern.lower() in line.lower()`
- Case sensitive: `pattern in line`
- No escaping needed — literal substring search

**Regex mode:**
- `re.search(pattern, line, flags)` where flags include `re.IGNORECASE` unless case_sensitive
- Invalid regex → raise `RegexError` with message

**Simple mode:**
- Parse expression via `simple_query.py` → AST
- Evaluate AST against line text
- Syntax errors → raise `QuerySyntaxError` with position

### 6.2 Performance

For filter application on large files:
- Iterate all lines once per filter
- Accumulate matching indices in a set (OR combination)
- Convert to sorted list for display
- Target: <100ms for 500K lines with a single filter

---

## 7. CommandParser (`command_parser.py`)

### 7.1 Command Grammar

```
command      := name [ "/" flags "/" ] text
             |  name text
             |  name                    (for zero-arg commands)

flags        := flag ("," flag)*
flag         := "cs" | "color=" <color_name> | "color=#" <hex>
text         := <any string>

name         := "s" | "sr" | "ss"       (search)
             |  "f" | "fr" | "fs"       (filter)
             |  "h" | "hr" | "hs"       (highlight)
             |  "rmf" | "rmh"           (remove filter/highlight)
             |  "lsf" | "lsh" | "lscat" (list active)
             |  "cate" | "catd"         (category enable/disable)
             |  "catea" | "catda"       (category all)
             |  "open" | "reload"       (file ops)
             |  "preset" | "presetl" | "rmpreset" | "lspreset"  (presets)
             |  "theme" | "q" | "n" | "N"  (misc)
```

### 7.2 Parsing Algorithm

1. **Extract command name**: characters before first `/` or space
2. **Check for flags**: if `/` follows the command name, extract everything between first `/` and next `/` as flags
3. **Parse flags**: split by `,`, validate each flag
4. **Extract text**: everything after the second `/` (or after first space if no flags)
5. **Validate**:
   - Empty flags → error (`f//text` is invalid)
   - Unknown flags → error
   - Missing text for commands that require it → error

### 7.3 Command Output

```python
@dataclass
class ParsedCommand:
    name: str
    flags: dict[str, str]     # {"cs": "", "color": "red"}
    text: str                  # The pattern/text argument
    raw: str                   # Original input string
```

### 7.4 Special Cases

- `/text` and `?text` in normal mode → treated as alias for `:s text` and `:s text` (with direction flag)
- `rmf` and `rmh` with no text → clear all (parsed from flags/text to match the exact original)
- First space after command is a separator. To search for text starting with space: `:f  text` (double space — first is separator, second is part of the pattern)

---

## 8. SimpleQuery Parser (`simple_query.py`)

### 8.1 Grammar

```
expression   := or_expr
or_expr      := and_expr ("OR" and_expr)*
and_expr     := not_expr ("AND" not_expr)*
not_expr     := "NOT" not_expr | primary
primary      := "(" expression ")" | STRING
STRING       := '"' ... '"'
```

**Operator precedence:** NOT > AND > OR

### 8.2 AST

```python
class QueryNode(ABC):
    @abstractmethod
    def evaluate(self, text: str, case_sensitive: bool) -> bool: ...

class TermNode(QueryNode):
    text: str

class AndNode(QueryNode):
    left: QueryNode
    right: QueryNode

class OrNode(QueryNode):
    left: QueryNode
    right: QueryNode

class NotNode(QueryNode):
    child: QueryNode
```

### 8.3 Evaluation

- `TermNode.evaluate`: substring check (with case sensitivity flag)
- `AndNode.evaluate`: left AND right
- `OrNode.evaluate`: left OR right
- `NotNode.evaluate`: NOT child

---

## 9. PresetManager (`preset_manager.py`)

### 9.1 Preset Format (YAML)

```yaml
name: my-errors
filters:
    - ':fs "ERROR" AND "timeout"'
    - ':fr/error_\\d+'
highlights:
    - ':h/color=red/ERROR'
    - ':h/color=yellow/WARNING'
disabledCategories:
    - network/dns
    - application/debug
```

### 9.2 Operations

| Operation | Behavior |
|-----------|----------|
| **Save** | Serialize current filters/highlights + disabled categories to YAML file |
| **Load** (partial apply) | Parse YAML. Apply disabled categories. Add filters/highlights (skip duplicates). Ignore non-existent categories silently. |
| **Delete** | Remove YAML file |
| **List** | Scan `~/.logviewer/presets/` for `.yaml` files |

### 9.3 Preset Application Rules

- Categories: only those listed in `disabledCategories` are changed; others keep current state
- Filters/highlights: added to current; exact duplicates (same pattern + mode + flags) are skipped
- Non-existent preset: error `❌ Preset 'name' not found`

---

## 10. ConfigManager (`config.py`)

### 10.1 Config File

Path: `~/.logviewer/settings.json`

```json
{
    "theme": "dark",
    "historySize": 100,
    "presetsPath": "~/.logviewer/presets",
    "defaultFormat": "default",
    "highlightColors": ["red", "yellow", "green", "cyan", "magenta", "blue", "white"],
    "defaultCategoriesEnabled": true
}
```

### 10.2 Behavior

- Load on startup; create with defaults if file missing
- `theme` persists across sessions
- `historySize` caps command history
- `presetsPath` configures where presets are stored
- `highlightColors` defines the rotation for default highlight colors
- `defaultCategoriesEnabled` controls whether categories start enabled or disabled

---

## 11. TUI Architecture

### 11.1 Screen Layout

```
┌─ LogViewerApp ───────────────────────────────────────────────────┐
│  Header("LogViewer v2.0")                                        │
│  ┌─ MainContainer (Horizontal, 1fr) ───────────────────────────┐ │
│  │  ┌─ LogPanel (75% width) ────┐  ┌─ CategoryPanel (25%) ───┐ │ │
│  │  │  DataTable                │  │  Tree                    │ │ │
│  │  │  Columns:                 │  │  ✅ application (1,200)  │ │ │
│  │  │   Line | Timestamp        │  │  ✅ network (500)        │ │ │
│  │  │   | Level | Category      │  │  ❌ database (300)       │ │ │
│  │  │   | Message               │  │  ⚠️ uncategorized (127)  │ │ │
│  │  └───────────────────────────┘  └─────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  ┌─ StatusBar (Horizontal, height: 1) ─────────────────────────┐ │
│  │  CommandInput("> _")           │ FileStats("1,287/15,432")  │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  Footer (key hints)                                               │
└──────────────────────────────────────────────────────────────────┘
```

### 11.2 Mode State Machine

```
            ┌─────────────┐
            │ NORMAL_MODE │◄──────────────────────┐
            │ (default)   │                        │
            └──┬───┬───┬──┘                        │
         ":" │   / │   \ ?                        │
               │    │     │                        │
            ┌──▼──┐ │  ┌──▼──────────────────┐    │
            │ CMD │ │  │ SEARCH_FORWARD/BACK │    │
            │MODE │ │  │ (alias for :s)      │    │
            └──┬──┘ │  └──┬──────────────────┘    │
         Enter│    │     │ Enter                   │
               │    │     │                        │
               ▼    ▼     ▼                        │
          ┌────────────────────┐   Esc/complete    │
          │ Execute command    │──────────────────┘
          │ Return to NORMAL   │
          └────────────────────┘
```

### 11.3 Key Bindings

| Key | Mode | Action |
|-----|------|--------|
| `j` | Normal | Cursor down one line |
| `k` | Normal | Cursor up one line |
| `↑`/`↓` | Normal | Cursor up/down |
| `g` then `g` | Normal | Go to first line |
| `G` | Normal | Go to last line |
| `{N}G` | Normal | Go to line N (e.g. `42G`) |
| `Ctrl+D` | Normal | Half page down |
| `Ctrl+U` | Normal | Half page up |
| `n` | Normal | Next search match |
| `N` | Normal | Previous search match |
| `y` then `y` | Normal | Copy current line to clipboard |
| `:` | Normal | Enter command mode |
| `/` | Normal | Search forward (alias `:s`) |
| `?` | Normal | Search backward (alias `:s`) |
| `Esc` | Any | Return to Normal mode |
| `Enter` | Command/Search | Execute |
| `↑`/`↓` | Command | Navigate command history |
| `Ctrl+C`/`Cmd+C` | Normal | Copy selected lines to clipboard |

**Key combos (`gg`, `yy`, `{N}G`):** Implemented via a key buffer. First key starts a timer (200ms). If matching second key arrives, execute combo. Otherwise, execute single-key action. `{N}G` accumulates digit characters until `G` is pressed.

### 11.4 Widget Specifications

#### LogPanel (`log_panel.py`)

- **Base widget:** `DataTable`
- **Columns:** Line, Timestamp, Level, Category, Message
- **Column widths:** auto-sized to content initially, resizable via drag
- **Data population:** on filter change, clear table and add rows from `filtered_indices`
- **Highlighting:** use Rich `Text` objects with spans for colored text matching highlights
- **Selection:** row-type cursor, multi-select via Shift+click and Ctrl/Cmd+click
- **Performance:** Textual DataTable handles virtual scrolling natively

#### CategoryPanel (`category_panel.py`)

- **Base widget:** `Tree`
- **Node labels:** `✅ name (count)` or `❌ name (count)` or `⚠️ uncategorized (count)`
- **Expand/collapse:** `▶`/`▼` icons, all collapsed at start
- **Interaction:** click name → toggle enable/disable; click arrow → expand/collapse
- **Header:** `Categories [±]` buttons for expand/collapse all
- **Resize:** panel width defaults to 25%, resizable via drag border

#### CommandInput (`command_input.py`)

- **Base widget:** `Input`
- **Prefix display:** shows `:` / `/` / `?` before input cursor
- **Command history:** `↑`/`↓` arrows navigate history
- **Submit:** Enter → parse via CommandParser → execute → back to Normal mode
- **Cancel:** Esc → clear input → back to Normal mode

#### StatusBar (`status_bar.py`)

- **Layout:** Horizontal split — command input left, stats right
- **Stats format:** `filename: visible/total │ ⛔C 🛑E ⚠️W ℹ️I 🟪D 🟩T`
- **Level stats**: show all levels including zero counts, using emoji: ⛔ CRITICAL, 🛑 ERROR, ⚠️ WARNING, ℹ️ INFO, 🟪 DEBUG, 🟩 TRACE
- **Dynamic:** when command text is long, stats section hides, full width given to input
- **Error display:** red text, auto-clear after 3 seconds
- **Progress:** during HTTP load, shows progress bar

### 11.5 Modal Screens

| Screen | Trigger | Content |
|--------|---------|---------|
| `FilterListScreen` | `:lsf` | List of active filters with indices |
| `HighlightListScreen` | `:lsh` | List of active highlights with indices |
| `CategoryListScreen` | `:lscat` | Category tree with enable/disable state |

Format for `:lsf`:
```
Active filters (2):
  1. :f Some text
  2. :f/cs/Some text
```

---

## 12. Theming

### 12.1 CSS Variables

```css
/* Dark theme (default) */
App {
    --background: #1E1E1E;
    --foreground: #D4D4D4;
    --selection: #264F78;
    --accent: #569CD6;
}

/* Light theme */
App.-light {
    --background: #FFFFFF;
    --foreground: #1E1E1E;
    --selection: #C7DEF8;
    --accent: #0066CC;
}
```

### 12.2 Level Colors

| Level | Style | Dark Theme | Light Theme |
|-------|-------|------------|-------------|
| CRITICAL | Bold, inverted background | `#FF5555` on `#1E1E1E` | `#CC0000` on `#FFFFFF` |
| ERROR | Red text | `#FF5555` | `#CC0000` |
| WARNING | Yellow/amber text | `#FFB86C` | `#CC8800` |
| INFO | Standard theme color | `#D4D4D4` | `#1E1E1E` |
| DEBUG | Standard theme color | `#D4D4D4` | `#1E1E1E` |
| TRACE | Standard theme color | `#D4D4D4` | `#1E1E1E` |

### 12.3 Highlight Colors

Default rotation: `red`, `yellow`, `green`, `cyan`, `magenta`, `blue`, `white`

Named colors: `red`, `green`, `blue`, `yellow`, `cyan`, `magenta`, `white`, `black`, `orange`, `purple`, `pink`, `brown`, `grey`

Custom colors: HEX format `#RRGGBB` (e.g. `/color=#FF5733`)

### 12.4 Theme Toggle

- `:theme dark` / `:theme light`
- Theme persisted in `~/.logviewer/settings.json`
- Applied instantly (<50ms) via Textual's `self.dark` toggle + CSS variable swap

---

## 13. File Management

### 13.1 Local Files

- `:open <path>` — read file line by line
- Worker thread (`@work(thread=True)`) to avoid blocking UI
- Progress updates via `call_from_thread`
- Supports absolute and relative paths
- `:open` closes current file, opens new one

### 13.2 HTTP Sources

- `:open http://...` — `urllib.request.urlopen` in worker thread
- Progress bar in status bar during download
- Error message on failure: `❌ HTTP 404: Not Found`
- No authentication support

### 13.3 Reload

- `:reload` — re-read current file
- Preserves: filters, highlights, category states, search state
- Resets: line data, category counts, level counts

### 13.4 Memory Model

- All lines loaded into RAM
- No size limit in v2.0
- LogLine objects are lightweight (~200 bytes each)
- 1M lines ≈ 200MB RAM

---

## 14. Clipboard

- `yy` (Normal mode): copy current line to system clipboard
- `Ctrl+C`/`Cmd+C`: copy selected lines; if no selection, copy current line
- Uses `pyperclip` library for cross-platform clipboard access
- Copies `LogLine.raw` (original formatting preserved)

---

## 15. Command History

- Storage: `~/.logviewer/history.json` — JSON array of command strings
- Max size: from `config.historySize` (default 100)
- Navigation: `↑`/`↓` in Command mode
- Duplicate policy: non-consecutive duplicates preserved; consecutive duplicates removed

---

## 16. Error Handling

| Error | Source | User Feedback |
|-------|--------|--------------|
| Invalid command syntax | CommandParser | `❌ Invalid command: <reason>` in status bar |
| File not found | File loading | `❌ File not found: <path>` in status bar |
| HTTP error | Worker thread | `❌ HTTP <code>: <message>` in status bar |
| Preset not found | PresetManager | `❌ Preset '<name>' not found` in status bar |
| Invalid regex | FilterEngine | `❌ Invalid regex: <reason>` in status bar |
| Invalid simple query | SimpleQueryParser | `❌ Invalid query: <reason>` in status bar |

All errors: red text in status bar, auto-clear after 3 seconds. No modal popups.

---

## 17. Performance Targets

| Operation | Target | Strategy |
|-----------|--------|----------|
| File load (1GB) | <10s | Worker thread, streaming parse |
| Filter apply | <100ms | Single pass per filter, set accumulation |
| Theme switch | <50ms | CSS variable swap |
| DataTable scroll | 60fps | Textual virtual scroll (built-in) |
| Statistics | O(1) display | Pre-computed during parse, updated on filter |

---

## 18. Testing Strategy

### 18.1 Unit Tests (Core Library)

All core modules are pure Python with no TUI dependency:

| Module | Test Focus |
|--------|-----------|
| `test_parser.py` | Default format parsing, LOG_* detection, fallback to INFO, uncategorized |
| `test_log_store.py` | Filter add/remove, category enable/disable, inheritance, OR combination |
| `test_filter_engine.py` | Plain/regex/simple matching, case sensitivity, edge cases |
| `test_command_parser.py` | All command formats, flags, error cases |
| `test_simple_query.py` | AST parsing, AND/OR/NOT, precedence, grouping |
| `test_preset_manager.py` | Save/load/delete, partial apply, duplicates |

### 18.2 Integration Tests (TUI)

| Test | Focus |
|------|-------|
| `test_tui_commands.py` | Command input → filter applied → DataTable updated |
| `test_file_loading.py` | Open file → lines parsed → category tree built |

### 18.3 TDD Approach

Red-Green-Refactor cycle for every feature:
1. Write failing test for desired behavior
2. Implement minimal code to pass
3. Refactor while keeping tests green
