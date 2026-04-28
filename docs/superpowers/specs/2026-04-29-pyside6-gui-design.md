# PySide6 GUI for Log Viewer

Date: 2026-04-29

## Goal

Replace the Textual TUI with a PySide6 desktop GUI that preserves the console-like command interaction model while adding native OS widgets.

## Design Decisions

1. **Command-driven interaction** — bottom bar doubles as status line and command input (`:` activates it, Tab autocompletes, Enter executes)
2. **Platform-native styling** — use QPalette, system fonts, standard margins, no custom CSS theming. macOS and Windows get their native look
3. **Light theme only** — no dark mode, no theme switching, no system theme detection
4. **Collapsible side panel** — hidden by default, toggled via `:lscat`, View menu, or keyboard shortcut
5. **Reuse core layer** — `src/log_viewer/core/` (models, services, parsers) stays untouched. Only the TUI layer (`src/log_viewer/tui/`) is replaced by a new `src/log_viewer/gui/` layer

## Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ Menu bar: File | Edit | View | Help                              │
├──────────────────────────────────────────────┬───────────────────┤
│                                              │ Categories        │
│  Log Table                                   │ Filters           │
│  (Line | Time | Category | Message)          │ Highlights        │
│                                              │                   │
│  - Vim navigation (j/k/gg/G/Ctrl-D/Ctrl-U)  │ [tab content]     │
│  - Mouse click/scroll                        │                   │
│  - Current line highlighted                  │                   │
│                                              │                   │
├──────────────────────────────────────────────┴───────────────────┤
│ :command input (flex)                │ Status: file │ stats     │
└──────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Main Window (QMainWindow)

- Menu bar: File (Open, Reload, Quit), Edit (Copy), View (Toggle Side Panel), Help
- Central widget: QSplitter (horizontal) — log table | side panel
- Status bar: replaced by custom bottom bar (command input + status info)

### 2. Log Table (QTableView + custom model)

- Fixed columns: Line (int), Time (str), Category (str), Message (str)
- Column widths: proportional defaults, user-resizable
- Current row: system highlight color (QPalette.Highlight)
- Vim navigation: j/k, gg/G, Ctrl-D/Ctrl-U, n/N for search
- Row highlighting: background color applied via model data based on active highlights
- Copy: `yy` copies current line, Ctrl+C copies selection

### 3. Command Input (QLineEdit in bottom bar)

- Sits in bottom bar, left side, takes all available space
- Always visible — status info is right-aligned beside it
- `:` in log table focus = activates command input with `:` prefix
- Tab: autocomplete (cycles through matches, same logic as TUI)
- Enter: execute command
- Escape: return focus to log table, clear input
- Autocomplete popup: QCompleter with command list + argument suggestions

### 4. Side Panel (QTabWidget, collapsible)

- Hidden by default, toggled by `:lscat`, View menu, or shortcut
- Resizable via splitter handle
- Three tabs:

**Categories tab:**
- Search field at top (QLineEdit with placeholder)
- QTreeWidget with checkboxes
- Root node "All" — toggling it checks/unchecks all children
- Hierarchy reflects category paths (e.g. app > api, app > error)
- Each node shows count in parentheses

**Filters tab:**
- List of active filters, each row: checkbox | command text | delete button
- Command shown as entered (e.g. `:f error`, `:fr /timeout/i`)
- Disabled filters: grayed out, strikethrough text
- Bottom hint: `:f <text> · :fr <regex> · :fs <query>`
- Delete button (✕) removes the filter

**Highlights tab:**
- Same layout as filters, plus a colored dot (QLabel with colored background) before command text
- Color extracted from command (`:h/color=red/error`) or defaults to red
- Disabled highlights: same visual treatment as disabled filters

### 5. File Opening

- `:open <path>` in command input (expands `~`)
- File → Open menu (QFileDialog)
- Drag & Drop files onto the main window

### 6. Search

- Only via `:s`/`:sr`/`:ss` commands in command input
- Matches highlighted in the log table (same highlight color for all search matches)
- `n`/`N` to navigate between matches

## Platform-Native Conventions

- **Fonts**: system default (San Francisco on macOS, Segoe UI on Windows). Monospace for log table and command input only
- **Font sizes**: system default sizes, no hardcoded pixel sizes
- **Spacing**: standard QLayout margins (9px content, 6px spacing — Qt defaults)
- **Colors**: QPalette-based. Highlight row uses QPalette.Highlight/HighlightedText
- **Menus**: standard QMenuBar — native macOS menu bar integration
- **Dialogs**: native QFileDialog, not custom widgets
- **Drag & Drop**: standard Qt DnD with file URL handling

## Command Compatibility

All TUI commands carry over unchanged:

| Command | Action |
|---------|--------|
| `:open <path>` | Open file |
| `:reload` | Reload current file |
| `:s/:sr/:ss <query>` | Search |
| `:f/:fr/:fs <query>` | Add filter |
| `:rmf <text>` | Remove filter |
| `:h/:hr/:hs <query>` | Add highlight |
| `:h/color=<c>/<text>` | Add highlight with color |
| `:rmh <text>` | Remove highlight |
| `:cate/:catd <path>` | Enable/disable category |
| `:lscat` | Toggle side panel |
| `:preset save/load <name>` | Preset management |
| `:lspreset` / `:rmpreset` | List/remove presets |
| `:q` | Quit |

## Architecture

```
src/log_viewer/
├── core/          # UNCHANGED — models, services, parsers
│   ├── models.py
│   ├── log_store.py
│   ├── parser.py
│   ├── filter_engine.py
│   ├── config.py
│   └── ...
├── gui/           # NEW — replaces tui/
│   ├── app.py              # Main window, menu, layout assembly
│   ├── log_table.py        # QTableView + custom model
│   ├── command_input.py    # QLineEdit with autocomplete
│   ├── side_panel.py       # QTabWidget with 3 tabs
│   ├── category_tree.py    # Categories tab (QTreeWidget)
│   ├── filter_list.py      # Filters tab (QListWidget)
│   ├── highlight_list.py   # Highlights tab (QListWidget)
│   └── bottom_bar.py       # Command input + status layout
├── tui/           # KEPT — not deleted, but not imported
└── main.py        # Updated to launch GUI instead of TUI
```

Key principle: `gui/` imports from `core/`, never from `tui/`. Core layer is the single source of truth for all business logic.

## Not in scope

- Dark theme / theme switching
- Custom styling beyond QPalette
- Separate search bar (only `:s` commands)
- Configurable columns (fixed set)
- Preset management UI in side panel (command-only)
- Copy-on-select (only `yy` and Ctrl+C)
