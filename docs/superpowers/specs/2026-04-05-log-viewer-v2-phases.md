# Log Viewer v2.0 — Implementation Phases

**Date:** 2026-04-05
**Status:** Approved
**Structure:** Single package `log_viewer` with `core/` and `tui/` submodules

---

## Package Structure

```
log_viewer/
├── pyproject.toml
├── src/
│   └── log_viewer/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── parser.py
│       │   ├── log_store.py
│       │   ├── filter_engine.py
│       │   ├── command_parser.py
│       │   ├── simple_query.py
│       │   ├── preset_manager.py
│       │   └── config.py
│       └── tui/
│           ├── __init__.py
│           ├── app.py
│           ├── widgets/
│           │   ├── log_panel.py
│           │   ├── category_panel.py
│           │   ├── status_bar.py
│           │   └── command_input.py
│           ├── screens/
│           │   ├── filter_list.py
│           │   ├── highlight_list.py
│           │   └── category_list.py
│           ├── themes.py
│           └── key_bindings.py
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

---

## Phase 1: MVP — Open & View Logs

**Goal:** Launchable app that opens a log file and displays parsed lines.

### Implements
- Project scaffolding (uv, pyproject.toml, single package layout)
- Data models: LogLevel, LogLine, enums (models.py)
- Parser: default format, LOG_* detection, uncategorized fallback (parser.py)
- LogStore: load_lines(), category tree building, level counts (log_store.py)
- App shell: Textual App with Header + LogPanel + StatusBar layout (app.py)
- LogPanel: DataTable with columns Line, Timestamp, Level, Category, Message
- StatusBar: file stats `visible/total │ ⛔C 🛑E ⚠️W ℹ️I 🟪D 🟩T`
- CommandInput: minimal — handles :open and :q only
- File loading: worker thread, streaming parse

### Manual Testing
- Launch with `uv run log-viewer`
- `:open TitleId-RVSC3D9-Ksiva-7CD00.log` → parsed lines in table
- Scroll: j/k, arrows, PgUp/PgDn
- gg → first line, G → last line, 42G → line 42
- Ctrl+D / Ctrl+U → half-page scroll
- Status bar shows correct line counts and level breakdown
- Lines without category → `uncategorized` with ⚠️
- `:q` exits

### Tasks
1. Project scaffolding + uv init + pyproject.toml
2. Models (models.py)
3. Parser (parser.py) with unit tests
4. LogStore basic — load_lines, category tree, counts (log_store.py)
5. TUI app shell + layout (app.py)
6. LogPanel widget (DataTable)
7. StatusBar widget
8. CommandInput widget (minimal: :open, :q)
9. File loading with worker thread
10. Vim navigation + key buffer (j/k/gg/G/{N}G/Ctrl+D/Ctrl+U)

---

## Phase 2: Filtering System

**Goal:** Filter visible log lines by plain text, regex, or simple query (AND/OR/NOT).

### Implements
- FilterEngine: plain, regex, simple matching (filter_engine.py)
- SimpleQuery parser: AST with AND, OR, NOT, quoted strings (simple_query.py)
- CommandParser: full grammar with flags (command_parser.py)
- LogStore filter operations: add/remove/clear, OR combination, apply_filters()
- FilterListScreen: :lsf modal
- Commands: :f, :fr, :fs, :rmf, :lsf

### Manual Testing
- `:f ERROR` → only ERROR lines visible
- `:f/cs/Failed to open` → case-sensitive filter
- `:fr/error_\d+` → regex filter
- `:fs/"Failed" AND "config"` → AND query
- `:fs/"Failed" OR "Successfully"` → OR query
- `:fs/NOT "warning"` → NOT query
- Multiple filters → OR logic
- `:rmf ERROR` → remove specific filter
- `:rmf` → clear all filters
- `:lsf` → modal with active filters

### Tasks
1. CommandParser (command_parser.py) with tests
2. SimpleQuery parser (simple_query.py) with tests
3. FilterEngine (filter_engine.py) with tests
4. LogStore filter operations with tests
5. FilterListScreen modal (:lsf)
6. Integrate filter commands into TUI

---

## Phase 3: Search & Navigation

**Goal:** Search within filtered view, navigate between matches.

### Implements
- SearchState model + LogStore search methods
- Search commands: /text, ?text, :s, :sr, :ss
- Match navigation: n/N keys
- Current match visual highlighting in DataTable
- InputMode state machine (Normal → Command → Search)

### Manual Testing
- `/error` → forward search, first match highlighted
- `n` → next match, `N` → previous
- `?error` → backward search
- `:s/cs/error` → case-sensitive search
- `:sr/error_\d+` → regex search
- `:ss/"Failed" AND "config"` → simple query search
- Search operates within current filtered view
- Esc → cancel search, return to normal mode

### Tasks
1. SearchState model + LogStore search methods
2. InputMode state machine in app.py
3. Search rendering (match highlight in LogPanel)
4. Integrate search commands into TUI

---

## Phase 4: Category Panel

**Goal:** Side panel with category tree, toggle categories on/off with inheritance.

### Implements
- CategoryPanel: Tree widget with ✅/❌/⚠️ icons
- LogStore category operations: enable/disable with inheritance
- Layout: Horizontal split — LogPanel (75%) + CategoryPanel (25%)
- Commands: :cate, :catd, :catea, :catda, :lscat
- CategoryListScreen modal

### Manual Testing
- Category panel shows tree with line counts
- Click name → toggle ✅/❌
- Click arrow → expand/collapse
- `:catd HordeMode` → disable HordeMode + children
- `:cate HordeMode/game_storage` → re-enable subcategory
- `:catda` → disable all, `:catea` → enable all
- `:lscat` → modal with full tree
- Category + filter both active simultaneously

### Tasks
1. CategoryPanel Tree widget
2. LogStore category enable/disable with inheritance + tests
3. CategoryListScreen modal (:lscat)
4. Layout update (horizontal split)
5. Integrate category commands into TUI

---

## Phase 5: Highlights

**Goal:** Color-highlight matching text in log lines.

### Implements
- Highlight model + LogStore highlight operations
- Rich Text spans for colored text in DataTable
- Commands: :h, :hr, :hs, :rmh, :lsh
- HighlightListScreen modal

### Manual Testing
- `:h ERROR` → "ERROR" highlighted red (default color)
- `:h/color=yellow/WARNING` → yellow highlight
- `:h/color=#FF5733/timeout` → custom hex color
- `:hr/error_\d+` → regex highlight
- `:hs/"Failed" AND "config"` → simple query highlight
- Multiple highlights with different colors visible
- `:rmh ERROR` → remove specific, `:rmh` → clear all
- `:lsh` → modal with active highlights
- Highlights don't affect filtering

### Tasks
1. Highlight model + LogStore highlight operations + tests
2. Rich Text rendering with color spans in LogPanel
3. HighlightListScreen modal (:lsh)
4. Integrate highlight commands into TUI

---

## Phase 6: Presets & Config

**Goal:** Save/load filter+highlight+category combos, persistent settings.

### Implements
- PresetManager: YAML save/load/delete (preset_manager.py)
- ConfigManager: ~/.logviewer/settings.json (config.py)
- Command history: ~/.logviewer/history.json, ↑/↓ navigation
- Commands: :preset, :presetl, :rmpreset, :lspreset

### Manual Testing
- Set up filters + highlights + disabled categories
- `:preset save my-debug` → saves to YAML
- Clear all, `:preset load my-debug` → restores state
- `:lspreset` → list saved presets
- `:rmpreset my-debug` → delete
- Config persists theme across sessions
- Command history: `:` then ↑/↓

### Tasks
1. ConfigManager (config.py) with tests
2. PresetManager (preset_manager.py) with tests
3. Command history persistence
4. Integrate preset commands into TUI

---

## Phase 7: Polish & Completeness

**Goal:** Themes, clipboard, HTTP loading, error handling polish.

### Implements
- Themes: dark/light CSS, :theme command, instant toggle
- Clipboard: yy (copy line), Ctrl+C (copy selection)
- HTTP loading: :open http://... with progress bar
- :reload — re-read file, preserve state
- Error display: red text, auto-clear after 3s

### Manual Testing
- `:theme light` / `:theme dark` → instant switch
- Theme persists after restart
- `yy` → copy current line to clipboard
- `:reload` → re-reads file, filters preserved
- `:open http://...` → loads remote with progress bar
- Invalid command → red error, auto-clears
- `:open nonexistent.log` → "File not found" error

### Tasks
1. Themes (dark/light CSS + toggle)
2. Clipboard (yy, Ctrl+C)
3. HTTP file loading with progress
4. :reload command
5. Error display polish (red text, auto-clear)
