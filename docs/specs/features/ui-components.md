# UI Components Specification

**Version:** 1.6
**Last Updated:** 2026-03-18
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

This document specifies the UI components of the Log Viewer application, including the main window, log table, category panel, and supporting widgets.

---

## §2 Architecture

### §2.1 View Hierarchy

```
MainWindow (QMainWindow)
├── SearchToolbar (QWidget)
│   ├── Filter input
│   ├── Mode selector
│   └── Action buttons
├── QSplitter (Horizontal)
│   ├── LogTableView (QTableView)
│   │   └── LogTableModel (QAbstractTableModel)
│   └── CategoryPanel (QWidget)
│       ├── QTabWidget
│       │   ├── Categories tab
│       │   ├── Filters tab
│       │   └── Highlights tab
│       ├── Search input
│       ├── QTreeView
│       │   └── QStandardItemModel
│       └── Button bar
└── MainStatusBar (QStatusBar)
    ├── File label
    ├── Toggle button (panel visibility)
    └── StatisticsBar
```

### §2.2 Signal Flow

```
User Action → View Signal → Controller Slot → Model Update → View Update
```

---

## §3 MainWindow

### §3.1 Purpose

Main application window that coordinates all UI components and emits signals for user actions.

### §3.2 API Reference

```python
class MainWindow(QMainWindow):
    """Main application window with redesigned UI."""
    
    # Signals
    file_opened = Signal(str)              # filepath
    file_closed = Signal()                  # file closed
    refresh_requested = Signal()           # refresh
    find_requested = Signal(str, bool)     # text, case_sensitive
    category_toggled = Signal(str, bool)    # category_path, checked
    filter_applied = Signal(str, str)      # search_text, mode
    filter_cleared = Signal()               # filter cleared
    counter_toggled = Signal(str, bool)    # counter_type, visible
    open_file_requested = Signal()          # open file button
    
    def __init__(self) -> None:
        """Initialize the main window."""
    
    # === Public API ===
    
    @beartype
    def set_current_file(self, filepath: str | None) -> None:
        """Set the current file path."""
    
    def get_current_file(self) -> str | None:
        """Get the current file path."""
    
    def get_log_table(self) -> LogTableView:
        """Return the log table view."""
    
    def get_category_panel(self) -> CategoryPanel:
        """Return the category panel."""
    
    @beartype
    def show_error(self, title: str, message: str) -> None:
        """Show an error message dialog."""
    
    @beartype
    def show_status(self, message: str, timeout: int = 3000) -> None:
        """Show a status message."""
    
    @beartype
    def update_statistics(self, stats: dict[str, int]) -> None:
        """Update statistics counters."""
```

### §3.3 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open file |
| `F5` | Refresh |
| `Ctrl+W` | Close file |
| `Ctrl+F` | Find |
| `Ctrl+Q` | Exit |

---

## §4 LogTableView

### §4.1 Purpose

Table view for displaying log entries with columns: Time, Category, Type, Message.

### §4.2 Columns

| Column | Width | Content | Font | Alignment |
|--------|-------|---------|------|-----------|
| Time | 50px | Timestamp (time only) | Default | Left + VCenter |
| Category | 100px | Category path | Default | Left + VCenter |
| Type | 40px | Log level icon | Monospace | Center |
| Message | Stretch | Display message | Monospace | Left + VCenter |

**Alignment Details:** See [table-column-alignment.md](table-column-alignment.md) for full alignment specification.

### §4.3 API Reference

```python
class LogTableView(QTableView):
    """Table view for log entries."""
    
    # Signals
    selection_changed = Signal()
    find_requested = Signal()
    
    def __init__(self, parent=None) -> None:
        """Initialize the table view."""
    
    def set_entries(self, entries: list[LogEntry]) -> None:
        """Set log entries."""
    
    def get_entry(self, row: int) -> LogEntry | None:
        """Get entry at row."""
    
    def get_selected_entries(self) -> list[LogEntry]:
        """Get all selected entries."""
    
    def clear(self) -> None:
        """Clear all entries."""
    
    def set_highlight_engine(self, engine: HighlightEngine | None) -> None:
        """Set the highlight engine."""
    
    def find_text(self, text: str, case_sensitive: bool = False) -> int:
        """Find text in visible rows. Returns match count."""
    
    def find_next(self) -> None:
        """Navigate to next match."""
    
    def find_previous(self) -> None:
        """Navigate to previous match."""
    
    def clear_find_highlights(self) -> None:
        """Clear find highlights."""
    
    def set_column_widths(self, widths: dict[str, int]) -> None:
        """Set column widths from dictionary."""
    
    def get_column_widths(self) -> dict[str, int]:
        """Get current column widths."""
    
    def copy_selected(self) -> None:
        """Copy selected rows to clipboard."""
```

### §4.4 Model

```python
class LogTableModel(QAbstractTableModel):
    """Model for log table."""
    
    COL_TIME = 0
    COL_CATEGORY = 1
    COL_TYPE = 2
    COL_MESSAGE = 3
    
    def set_entries(self, entries: list[LogEntry]) -> None:
        """Set entries and reset model."""
    
    def get_entry(self, row: int) -> LogEntry | None:
        """Get entry at row."""
    
    def get_entries(self) -> list[LogEntry]:
        """Get all entries."""
```

### §4.5 Display Entry

```python
@dataclass
class LogEntryDisplay:
    """Display model for log entry."""
    category: str
    time: str
    level: LogLevel
    message: str
    raw_line: str = ""
    
    @property
    def level_icon(self) -> str:
        """Get the icon character for the level."""
    
    @classmethod
    def from_log_entry(cls, entry) -> LogEntryDisplay:
        """Create from LogEntry."""
```

---

## §5 CategoryPanel

### §5.1 Purpose

Panel for category filtering with tabs, tree view, and search.

### §5.2 API Reference

```python
class CategoryPanel(QWidget):
    """Panel for category filtering."""
    
    # Signals
    category_toggled = Signal(str, bool)  # category_path, checked
    search_changed = Signal(str)
    current_tab_changed = Signal(int)
    
    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the category panel."""
    
    # === Category Management ===
    
    def set_categories(self, categories: list[CategoryDisplayNode]) -> None:
        """Populate tree with categories."""
    
    def get_checked_categories(self) -> set[str]:
        """Return set of checked category paths."""
    
    def get_all_categories(self) -> set[str]:
        """Return set of all category paths."""
    
    def get_category_states(self) -> dict[str, bool]:
        """Get all category checkbox states."""
    
    def set_category_states(self, states: dict[str, bool]) -> None:
        """Restore category checkbox states."""
    
    def check_all(self, checked: bool) -> None:
        """Check or uncheck all categories."""
    
    def check_category(self, path: str, checked: bool) -> None:
        """Check or uncheck a specific category."""
    
    def clear(self) -> None:
        """Clear all categories."""
    
    # === Tab Management ===
    
    def set_current_tab(self, index: int) -> None:
        """Set the current tab by index."""
    
    def get_current_tab(self) -> int:
        """Get the current tab index."""
    
    # === Search Management ===
    
    def set_search_text(self, text: str) -> None:
        """Set the search text."""
    
    def get_search_text(self) -> str:
        """Get the current search text."""
    
    def clear_search(self) -> None:
        """Clear the search input."""
```

### §5.3 Checkbox Behavior

Per [category-checkbox-behavior.md](category-checkbox-behavior.md):

- Parent checked → All children checked
- Parent unchecked → All children unchecked
- Child checked/uncheck → Parent unchanged (partial state)
- Visibility: Log visible if self OR any ancestor is checked

---

## §6 SearchToolbar

### §6.1 Purpose

Toolbar containing search input, filter mode selector, and action buttons. Visibility is controlled by the panel toggle button in the status bar.

### §6.2 Components

```
SearchToolbar
├── Filter input (QLineEdit)
├── Mode selector (QComboBox)
│   ├── Plain
│   ├── Regex
│   └── Simple
└── Action buttons
    ├── Open file
    └── Refresh
```

### §6.3 API Reference

```python
class SearchToolbar(QWidget):
    """Toolbar with search input and action buttons.
    
    // Ref: docs/specs/features/ui-components.md §6
    // Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
    """
    
    # Signals
    filter_applied = Signal(str, str)  # text, mode
    filter_cleared = Signal()
    open_file_clicked = Signal()
    refresh_clicked = Signal()
    
    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the search toolbar."""
    
    def set_visible(self, visible: bool) -> None:
        """Set toolbar visibility.
        
        Called by MainWindow when panel toggle button is clicked.
        
        Args:
            visible: True to show, False to hide.
        """
```

---

## §7 MainStatusBar

### §7.1 Purpose

Status bar showing current file, panel toggle button, and status messages.

### §7.2 Components

```
MainStatusBar (QStatusBar)
├── File label (left)
├── Stretch (center)
├── Toggle button (panel visibility)
└── StatisticsBar (right)
```

### §7.3 API Reference

```python
class MainStatusBar(QStatusBar):
    """Main status bar with panel toggle button.
    
    // Ref: docs/specs/features/panel-toggle-button.md §4.1
    // Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
    """
    
    # Signals
    counter_clicked = Signal(str, bool)  # counter_type, visible
    panels_toggled = Signal(bool)  # panels_visible
    
    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the status bar."""
    
    def set_file(self, filename: str | None) -> None:
        """Set the current file name."""
    
    def show_status(self, message: str, timeout: int = 3000) -> None:
        """Show a status message."""
    
    def clear_status(self) -> None:
        """Clear the status message."""
    
    def update_statistics(self, stats: dict[str, int]) -> None:
        """Update statistics counters."""
    
    def set_panels_visible(self, visible: bool) -> None:
        """Set the panels visibility state.
        
        Updates the toggle button icon to reflect current state.
        
        Args:
            visible: True if panels are visible, False if hidden.
        """
    
    def is_panels_visible(self) -> bool:
        """Check if panels are currently visible.
        
        Returns:
            True if panels are visible, False if hidden.
        """
```

---

## §8 StatisticsBar

### §8.1 Purpose

Widget showing log level counters with clickable buttons.

### §8.2 API Reference

```python
class StatisticsBar(QWidget):
    """Statistics bar with counters."""
    
    # Signals
    counter_clicked = Signal(str, bool)  # counter_type, visible
    
    def __init__(self) -> None:
        """Initialize the statistics bar."""
    
    def update_counts(self, stats: dict[str, int]) -> None:
        """Update counter values."""
    
    def set_shown_count(self, shown: int) -> None:
        """Set the shown count."""
```

### §8.3 Counter Types

| Type | Color | Icon |
|------|-------|------|
| Critical | Red | ⚠ |
| Error | Orange | ✗ |
| Warning | Yellow | ⚡ |
| MSG | White | ○ |
| Debug | Gray | ◯ |
| Trace | Light Gray | · |

---

## §9 FindDialog

### §9.1 Purpose

Dialog for finding text in log entries.

### §9.2 API Reference

```python
class FindDialog(QDialog):
    """Find dialog for searching log entries."""
    
    # Signals
    find_requested = Signal(str, bool)  # text, case_sensitive
    find_next = Signal()
    find_previous = Signal()
    highlight_all = Signal(str, bool)
    clear_highlights = Signal()
    
    def __init__(self, parent: QWidget) -> None:
        """Initialize the find dialog."""
    
    def update_match_count(self, current: int, total: int) -> None:
        """Update the match count display."""
```

---

## §10 HighlightDialog

### §10.1 Purpose

Dialog for managing highlight patterns.

### §10.2 API Reference

```python
class HighlightDialog(QDialog):
    """Dialog for managing highlight patterns."""
    
    def __init__(self, parent: QWidget) -> None:
        """Initialize the highlight dialog."""
    
    def get_patterns(self) -> list[HighlightPatternData]:
        """Get the current highlight patterns."""
    
    def set_patterns(self, patterns: list[HighlightPatternData]) -> None:
        """Set the highlight patterns."""
```

---

## §11 Delegates

### §11.1 HighlightDelegate

```python
class HighlightDelegate(QStyledItemDelegate):
    """Delegate for highlighting text in table cells."""
    
    def __init__(self, parent=None) -> None:
        """Initialize the delegate."""
    
    def set_highlight_engine(self, engine: HighlightEngine | None) -> None:
        """Set the highlight engine."""
    
    def paint(self, painter, option, index) -> None:
        """Paint with highlighting."""
```

---

## §12 Styling References

For styling specifications, see:

- **UI Design System:** [ui-design-system.md](ui-design-system.md) - Master design system (colors, typography, components)
- **Table Styles:** [table-unified-styles.md](table-unified-styles.md) - Complete table styling specification
- **Table Column Alignment:** [table-column-alignment.md](table-column-alignment.md) - Column alignment specification
- **Table Text Overflow:** [table-cell-text-overflow.md](table-cell-text-overflow.md) - Text overflow behavior
- **Colors Implementation:** [src/constants/colors.py](../../src/constants/colors.py)
- **Dimensions Implementation:** [src/constants/dimensions.py](../../src/constants/dimensions.py)
- **Stylesheet Implementation:** [src/styles/stylesheet.py](../../src/styles/stylesheet.py)

---

## §13 Testing

### §13.1 Unit Tests

```python
def test_log_table_set_entries(log_table):
    """Test setting entries in log table."""
    entries = [create_entry("test")]
    log_table.set_entries(entries)
    
    assert log_table.get_row_count() == 1
    assert log_table.get_entry(0) == entries[0]

def test_category_panel_check_all(category_panel):
    """Test checking all categories."""
    category_panel.set_categories([
        CategoryDisplayNode(name="A", path="A", checked=False),
        CategoryDisplayNode(name="B", path="B", checked=False),
    ])
    
    category_panel.check_all(True)
    
    assert category_panel.get_checked_categories() == {"A", "B"}
```

---

## §14 Cross-References

- **Category Checkbox Behavior:** [category-checkbox-behavior.md](category-checkbox-behavior.md)
- **Main Controller:** [main-controller.md](main-controller.md)
- **Filter Controller:** [filter-controller.md](filter-controller.md)
- **Memory Model:** [../global/memory-model.md](../global/memory-model.md)

---

## §15 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.6 | 2026-03-18 | Removed CollapsiblePanel/ToggleStrip from SearchToolbar; added panel toggle button to MainStatusBar; simplified view hierarchy |
| 1.5 | 2026-03-18 | Removed auto_reload_toggled signal (file watching feature deprecated) |
| 1.4 | 2026-03-15 | Replaced §12 Styling section with cross-references to specialized styling specs |
| 1.3 | 2026-03-14 | Renamed SystemNode → CategoryDisplayNode |
| 1.2 | 2026-03-14 | Renamed CategoryPanel tabs: Processes→Filters, Threads→Highlights |
| 1.1 | 2026-03-14 | Removed custom categories from CategoryPanel |
| 1.0 | 2026-03-13 | Initial UI components specification |