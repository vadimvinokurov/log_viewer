# Highlight Panel Specification

**Version:** 1.0  
**Last Updated:** 2026-03-16  
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

The Highlight Panel provides a user interface for managing highlight patterns in the log viewer. Users can add, edit, enable/disable, and delete highlight patterns. Each pattern defines text (plain or regex) and a color for highlighting matching log entries in the table view.

### §1.1 Relationship to Existing Components

- **Reuses:** [`HighlightService`](../../src/services/highlight_service.py) - Pattern management service
- **Reuses:** [`HighlightEngine`](../../src/core/highlight_engine.py) - Pattern matching engine
- **Reuses:** [`HighlightDialog`](../../src/views/widgets/highlight_dialog.py) - Pattern creation/editing dialog
- **Reuses:** [`HighlightPattern`](../../src/core/highlight_engine.py) dataclass with `enabled` field
- **Extends:** [`CategoryPanel`](../../src/views/category_panel.py) - Replaces "Highlights (Coming soon)" placeholder

---

## §2 Architecture

### §2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CategoryPanel                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  TabWidget                                          │   │
│  │  ┌────────────┬────────────┬──────────────────┐   │   │
│  │  │ Categories │  Filters   │   Highlights     │   │   │
│  │  └────────────┴────────────┴──────────────────┘   │   │
│  │                                    │               │   │
│  │                                    ▼               │   │
│  │                         ┌─────────────────────┐   │   │
│  │                         │  HighlightsTabContent│   │   │
│  │                         │  - Pattern list     │   │   │
│  │                         │  - Add/Edit/Delete  │   │   │
│  │                         │  - Enable/Disable   │   │   │
│  │                         └─────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### §2.2 Dependencies

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QListWidgetItem
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from src.core.highlight_engine import HighlightPattern
from src.views.widgets.highlight_dialog import HighlightDialog
```

### §2.3 Signal Flow

```
HighlightsTabContent                 MainController
        │                                  │
        │  pattern_added(text, color,      │
        │              is_regex)           │
        ├─────────────────────────────────►│
        │                                  │  HighlightService.add_user_pattern()
        │                                  │  LogTableView.set_highlight_engine()
        │                                  │
        │  pattern_removed(text)           │
        ├─────────────────────────────────►│
        │                                  │  HighlightService.remove_user_pattern()
        │                                  │  LogTableView.set_highlight_engine()
        │                                  │
        │  pattern_enabled_changed(text,   │
        │                     enabled)     │
        ├─────────────────────────────────►│
        │                                  │  HighlightService pattern.enabled update
        │                                  │  LogTableView.set_highlight_engine()
        │                                  │
        │  pattern_edited(old_text,        │
        │         new_text, color, regex)  │
        ├─────────────────────────────────►│
        │                                  │  HighlightService update pattern
        │                                  │  LogTableView.set_highlight_engine()
        │                                  │
        │                                  ▼
```

**Important:** `LogTableView` maintains its own local `_highlight_service` instance. When highlight patterns change, the controller must call `set_highlight_engine()` to update the LogTableView's service, not just `refresh_highlighting()`. This ensures the delegate receives the updated highlight patterns.

---

## §3 UI Components

### §3.1 HighlightsTabContent Widget

A widget containing the highlight pattern list and action buttons.

```
┌─────────────────────────────────────────────────────────────┐
│  HighlightsTabContent                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │ [✓] [■] error     (text)                   │   │   │
│  │  │ [✓] [■] warning.* (regex)                  │   │   │
│  │  │ [ ] [■] DEBUG     (text)                    │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  │                                                     │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │  [Add]  [Edit]  [Delete]                    │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

Legend:
  [✓] - Checkbox (enabled state)
  [ ] - Unchecked checkbox (disabled state)
  [■] - Color swatch (shows highlight color)
```

### §3.2 List Item Layout

Each list item displays:
1. **Checkbox** - Enable/disable the pattern
2. **Color Swatch** - Visual indicator of highlight color
3. **Pattern Text** - The text/regex pattern
4. **Type Indicator** - "(text)" or "(regex)" label

```
┌────────────────────────────────────────────────────────────┐
│ [✓] [■ Yellow] error (text)                               │
│ [✓] [■ Green ] warning.* (regex)                          │
│ [ ] [■ Cyan  ] DEBUG (text)                               │
└────────────────────────────────────────────────────────────┘
```

### §3.3 Action Buttons

| Button | Action | Enabled When |
|--------|--------|--------------|
| Add | Opens `HighlightDialog` to create new pattern | Always |
| Edit | Opens `HighlightDialog` to edit selected pattern | Pattern selected |
| Delete | Removes selected pattern immediately | Pattern selected |

---

## §4 API Reference

### §4.1 HighlightsTabContent Class

```python
class HighlightsTabContent(QWidget):
    """Widget for managing highlight patterns.
    
    // Ref: docs/specs/features/highlight-panel.md §3.1
    // Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
    // Thread: Main thread only (Qt UI component per docs/specs/global/threading.md §8.1)
    """
    
    # Signals
    pattern_added = Signal(str, QColor, bool)      # text, color, is_regex
    pattern_removed = Signal(str)                   # text
    pattern_enabled_changed = Signal(str, bool)    # text, enabled
    pattern_edited = Signal(str, str, QColor, bool)  # old_text, new_text, color, is_regex
    
    @beartype
    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the highlights tab content."""
    
    def set_patterns(self, patterns: list[HighlightPattern]) -> None:
        """Set the list of highlight patterns.
        
        Args:
            patterns: List of HighlightPattern objects.
        """
    
    def get_patterns(self) -> list[HighlightPattern]:
        """Get all highlight patterns.
        
        Returns:
            List of HighlightPattern objects.
        """
    
    def add_pattern(self, pattern: HighlightPattern) -> None:
        """Add a single pattern to the list.
        
        Args:
            pattern: HighlightPattern to add.
        """
    
    def clear(self) -> None:
        """Clear all patterns from the list."""
```

### §4.2 List Item Widget

```python
class HighlightPatternItem(QWidget):
    """Widget for a single highlight pattern in the list.
    
    Displays: [checkbox] [color swatch] [pattern text] [type indicator]
    """
    
    # Signals
    enabled_changed = Signal(str, bool)  # text, enabled
    edit_requested = Signal(str)           # text
    
    @beartype
    def __init__(self, pattern: HighlightPattern, parent: QWidget | None = None) -> None:
        """Initialize the pattern item.
        
        Args:
            pattern: The highlight pattern to display.
            parent: Parent widget.
        """
    
    def set_enabled(self, enabled: bool) -> None:
        """Set the enabled state of the pattern.
        
        Args:
            enabled: Whether the pattern is enabled.
        """
    
    def set_color(self, color: QColor) -> None:
        """Set the highlight color.
        
        Args:
            color: The new highlight color.
        """
    
    def set_pattern_text(self, text: str) -> None:
        """Set the pattern text.
        
        Args:
            text: The new pattern text.
        """
```

---

## §5 Behavior

### §5.1 Adding a Pattern

1. User clicks "Add" button
2. `HighlightDialog` opens with empty fields
3. User enters pattern text, selects color, optionally enables regex
4. User clicks OK
5. **Pattern added to QListWidget first** via `add_pattern()` - ensures UI is updated before signal
6. Signal `pattern_added` emitted with (text, color, is_regex)
7. `MainController` adds pattern to `HighlightService`
8. `MainController` calls `set_highlight_engine()` to update LogTableView's delegate
9. Pattern appears in list with checkbox checked by default
10. Table view shows highlights

**Important:** The pattern must be added to the UI list before emitting the signal to ensure the UI reflects the pattern immediately, even if the controller handler encounters an error.

### §5.2 Editing a Pattern

1. User selects pattern in list
2. User clicks "Edit" button (or double-clicks item)
3. `HighlightDialog` opens with current pattern values
4. User modifies pattern text, color, or regex flag
5. User clicks OK
6. **Widget updated in-place** with new color, text, and regex flag
7. Signal `pattern_edited` emitted with (old_text, new_text, color, is_regex)
8. `MainController` updates pattern in `HighlightService`
9. `MainController` calls `set_highlight_engine()` to update LogTableView's delegate
10. Table view shows updated highlights

**Important:** The widget must be updated before emitting the signal to ensure the UI reflects changes immediately.

### §5.3 Enabling/Disabling a Pattern

1. User clicks checkbox on pattern item
2. Signal `pattern_enabled_changed` emitted with (text, enabled)
3. `MainController` updates pattern's `enabled` field in `HighlightService`
4. `HighlightService._update_combined()` rebuilds combined engine
5. Table view refreshes to show/hide highlights for this pattern

### §5.4 Deleting a Pattern

1. User selects pattern in list
2. User clicks "Delete" button
3. Signal `pattern_removed` emitted with (text)
4. `MainController` removes pattern from `HighlightService`
5. Pattern removed from list
6. Table view refreshes to remove highlights

### §5.5 Pattern Matching Behavior

Per [`HighlightEngine`](../../src/core/highlight_engine.py):
- **Text patterns**: Case-insensitive substring matching
- **Regex patterns**: Case-insensitive regex matching
- **Overlapping matches**: Later patterns overwrite earlier ones
- **Disabled patterns**: Skipped during matching (per `enabled` field)

---

## §6 Persistence

### §6.1 Settings Integration

Patterns are persisted via [`SettingsManager`](../../src/utils/settings_manager.py):

```python
# Per docs/specs/features/highlight-panel.md §6.1
# HighlightPatternData already exists in settings_manager.py
@dataclass
class HighlightPatternData:
    text: str
    color_hex: str
    is_regex: bool = False
    enabled: bool = True  # Already supported
```

### §6.2 Load on Startup

Per [`MainController._load_settings()`](../../src/controllers/main_controller.py:147):

```python
# Load highlight patterns
for pattern_data in settings.highlight_patterns:
    try:
        color = QColor(pattern_data.color_hex)
        self._highlight_service.add_user_pattern(
            pattern=pattern_data.text,
            color=color,
            is_regex=pattern_data.is_regex,
            enabled=pattern_data.enabled  # Already supported
        )
    except Exception as e:
        logger.warning(f"Failed to load highlight pattern: {e}")
```

### §6.3 Save on Change

Patterns are saved when:
1. Application closes (per `_save_settings()`)
2. Pattern added/edited/removed (immediate save recommended)

---

## §7 Integration Points

### §7.1 CategoryPanel Integration

Replace the "Highlights (Coming soon)" placeholder in [`CategoryPanel`](../../src/views/category_panel.py:198-202):

```python
# Current placeholder:
highlights_layout = QVBoxLayout(self._highlights_tab)
highlights_label = QLabel("Highlights\n(Coming soon)")
highlights_label.setAlignment(Qt.AlignCenter)
highlights_label.setStyleSheet("color: #999; font-style: italic;")
highlights_layout.addWidget(highlights_label)

# Replace with:
self._highlights_content = HighlightsTabContent()
highlights_layout = QVBoxLayout(self._highlights_tab)
highlights_layout.setContentsMargins(4, 4, 4, 4)
highlights_layout.addWidget(self._highlights_content)

# Connect signals
self._highlights_content.pattern_added.connect(self.highlight_pattern_added)
self._highlights_content.pattern_removed.connect(self.highlight_pattern_removed)
self._highlights_content.pattern_enabled_changed.connect(self.highlight_pattern_enabled_changed)
self._highlights_content.pattern_edited.connect(self.highlight_pattern_edited)
```

### §7.2 CategoryPanel New Signals

```python
class CategoryPanel(QWidget):
    # ... existing signals ...
    
    # Highlight signals (forwarded from HighlightsTabContent)
    highlight_pattern_added = Signal(str, QColor, bool)      # text, color, is_regex
    highlight_pattern_removed = Signal(str)                   # text
    highlight_pattern_enabled_changed = Signal(str, bool)    # text, enabled
    highlight_pattern_edited = Signal(str, str, QColor, bool)  # old_text, new_text, color, is_regex
```

### §7.3 MainController Integration

Add signal handlers in [`MainController._connect_signals()`](../../src/controllers/main_controller.py:90):

```python
# Highlight panel signals
self._window.get_category_panel().highlight_pattern_added.connect(
    self._on_highlight_pattern_added
)
self._window.get_category_panel().highlight_pattern_removed.connect(
    self._on_highlight_pattern_removed
)
self._window.get_category_panel().highlight_pattern_enabled_changed.connect(
    self._on_highlight_pattern_enabled_changed
)
self._window.get_category_panel().highlight_pattern_edited.connect(
    self._on_highlight_pattern_edited
)
```

### §7.4 MainController New Handlers

```python
@beartype
def _on_highlight_pattern_added(self, text: str, color: QColor, is_regex: bool) -> None:
    """Handle highlight pattern added.
    
    Args:
        text: Pattern text.
        color: Highlight color.
        is_regex: Whether pattern is regex.
    """
    self._highlight_service.add_user_pattern(
        pattern=text,
        color=color,
        is_regex=is_regex,
        enabled=True
    )
    # Must use set_highlight_engine() to update LogTableView's delegate
    self._window.get_log_table().set_highlight_engine(
        self._highlight_service.get_combined_engine()
    )
    self._save_settings()
    self._window.show_status(f"Highlight added: {text}", 3000)

@beartype
def _on_highlight_pattern_removed(self, text: str) -> None:
    """Handle highlight pattern removed.
    
    Args:
        text: Pattern text.
    """
    self._highlight_service.remove_user_pattern(text)
    # Must use set_highlight_engine() to update LogTableView's delegate
    self._window.get_log_table().set_highlight_engine(
        self._highlight_service.get_combined_engine()
    )
    self._save_settings()
    self._window.show_status(f"Highlight removed: {text}", 3000)

@beartype
def _on_highlight_pattern_enabled_changed(self, text: str, enabled: bool) -> None:
    """Handle highlight pattern enabled/disabled.
    
    Args:
        text: Pattern text.
        enabled: New enabled state.
    """
    # Update pattern enabled state
    patterns = self._highlight_service.get_user_patterns()
    for p in patterns:
        if p.text == text:
            p.enabled = enabled
            break
    self._highlight_service.set_user_patterns(patterns)
    # Must use set_highlight_engine() to update LogTableView's delegate
    self._window.get_log_table().set_highlight_engine(
        self._highlight_service.get_combined_engine()
    )
    self._save_settings()

@beartype
def _on_highlight_pattern_edited(
    self, old_text: str, new_text: str, color: QColor, is_regex: bool
) -> None:
    """Handle highlight pattern edited.
    
    Args:
        old_text: Original pattern text.
        new_text: New pattern text.
        color: New highlight color.
        is_regex: Whether pattern is regex.
    """
    # Remove old pattern and add new one
    self._highlight_service.remove_user_pattern(old_text)
    self._highlight_service.add_user_pattern(
        pattern=new_text,
        color=color,
        is_regex=is_regex,
        enabled=True
    )
    # Must use set_highlight_engine() to update LogTableView's delegate
    self._window.get_log_table().set_highlight_engine(
        self._highlight_service.get_combined_engine()
    )
    self._save_settings()
    self._window.show_status(f"Highlight updated: {new_text}", 3000)
```

**Important:** All highlight pattern handlers must call `set_highlight_engine()` instead of `refresh_highlighting()`. This is because `LogTableView` maintains its own local `_highlight_service` instance, and the delegate needs to receive the updated highlight patterns through `set_highlight_engine()`.

---

## §8 Styling

### §8.1 List Item Styling

Per [`stylesheet.py`](../../src/styles/stylesheet.py) patterns:

```python
# Highlight pattern list item
HIGHLIGHT_ITEM_STYLE = """
    QListWidget::item {
        padding: 4px;
        border-bottom: 1px solid #3c3c3c;
    }
    QListWidget::item:selected {
        background-color: #094771;
    }
    QListWidget::item:hover {
        background-color: #2a2d2e;
    }
"""

# Color swatch
COLOR_SWATCH_STYLE = """
    QLabel {
        border: 1px solid #888;
        border-radius: 3px;
        min-width: 20px;
        max-width: 20px;
        min-height: 14px;
        max-height: 14px;
    }
"""
```

### §8.2 Button Styling

Use existing button styles from [`stylesheet.py`](../../src/styles/stylesheet.py).

---

## §9 Performance

### §9.1 Pattern List Performance

| Patterns | List Load Time | Enable/Disable |
|----------|---------------|----------------|
| 10 | <10ms | <5ms |
| 50 | <20ms | <5ms |
| 100 | <50ms | <5ms |

### §9.2 Highlighting Performance

Per [`highlight-service.md`](highlight-service.md) §8:
- Pattern matching is O(n*m) where n = text length, m = pattern count
- Regex patterns compiled once and cached
- Highlight ranges computed on-demand during paint

---

## §10 Testing

### §10.1 Unit Tests

```python
def test_highlights_tab_content_add_pattern(highlights_tab):
    """Test adding a pattern via the Add button."""
    # Click Add button
    # Dialog opens
    # Enter pattern
    # Click OK
    # Verify pattern_added signal emitted
    
def test_highlights_tab_content_enable_disable(highlights_tab):
    """Test enabling/disabling patterns."""
    # Set patterns
    # Click checkbox
    # Verify pattern_enabled_changed signal emitted
    
def test_highlights_tab_content_edit_pattern(highlights_tab):
    """Test editing a pattern."""
    # Set patterns
    # Select pattern
    # Click Edit button
    # Modify values
    # Verify pattern_edited signal emitted
    
def test_highlights_tab_content_delete_pattern(highlights_tab):
    """Test deleting a pattern."""
    # Set patterns
    # Select pattern
    # Click Delete button
    # Confirm dialog
    # Verify pattern_removed signal emitted

def test_pattern_persistence(settings_manager):
    """Test that patterns persist across sessions."""
    # Add pattern
    # Save settings
    # Create new settings manager
    # Verify pattern loaded
```

### §10.2 Integration Tests

```python
def test_highlight_panel_to_table_integration(main_controller):
    """Test that enabling/disabling pattern updates table highlighting."""
    # Add highlight pattern
    # Verify table shows highlights
    # Disable pattern
    # Verify table hides highlights for that pattern
    # Re-enable pattern
    # Verify table shows highlights again
```

---

## §11 Cross-References

- **Highlight Service:** [highlight-service.md](highlight-service.md)
- **Highlight Engine:** [highlight-service.md](highlight-service.md) §6
- **Settings Manager:** [settings-manager.md](settings-manager.md)
- **Main Controller:** [main-controller.md](main-controller.md)
- **Category Panel:** [category-panel-styles.md](category-panel-styles.md)
- **Threading:** [../global/threading.md](../global/threading.md) §8.1 (Main thread only)

---

## §12 HighlightDialog Initialization

### §12.1 Initialization Order

The `HighlightDialog` must initialize UI components in the correct order to avoid null reference errors:

```python
def _setup_ui(self, text: str, is_regex: bool) -> None:
    # ... form layout setup ...
    
    # Color picker - MUST create _color_label BEFORE calling _update_color_button
    color_layout = QHBoxLayout()
    self._color_button = QPushButton()
    self._color_button.setFixedSize(60, 30)
    self._color_button.clicked.connect(self._choose_color)
    color_layout.addWidget(self._color_button)

    self._color_label = QLabel(self._color.name())  # Create label first
    color_layout.addWidget(self._color_label)
    self._update_color_button()  # Now safe to call - _color_label exists
    color_layout.addStretch()
```

**Important:** The `_update_color_button()` method references `self._color_label`, so the label must be created before calling this method. Failure to follow this order results in an `AttributeError` when the dialog is created.

---

## §13 File Load Highlight Pattern Population

### §13.1 Pattern Loading Flow

When a file is loaded, the highlights tab must be populated with the previously saved highlight patterns:

```python
def _on_index_complete(self, filepath: str) -> None:
    # ... file loading logic ...
    
    # Populate highlights tab with loaded patterns
    # Ref: docs/specs/features/highlight-panel.md §13.1
    highlight_patterns = self._highlight_service.get_user_patterns()
    self._window.get_category_panel().get_highlights_content().set_patterns(highlight_patterns)
```

**Important:** This ensures that highlight patterns saved from a previous session are displayed in the UI when a file is loaded. Without this step, the highlights tab would appear empty even though patterns exist in the service.

---

## §14 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-03-17 | Updated signal flow to use set_highlight_engine(), added HighlightDialog initialization order, added file load pattern population |
| 1.0 | 2026-03-16 | Initial highlight panel specification |