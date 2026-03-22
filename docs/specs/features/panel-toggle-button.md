# Panel Toggle Button Specification

**Version:** 1.1
**Last Updated:** 2026-03-18
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

The Panel Toggle Button provides a quick way to hide all auxiliary panels and focus on the log table. This is useful when users want maximum screen space for viewing log entries.

### §1.1 Feature Summary

- A toggle button in the status bar that hides/shows all panels except the log table
- Single-click operation: click to hide panels, click again to restore panels
- Visual indicator shows current state (panels visible/hidden)
- Keyboard shortcut support for quick access

### §1.2 Affected Panels

| Panel | Location | Toggle Behavior |
|-------|----------|-----------------|
| Search Toolbar | Top (toolbar area) | Hide/Show via `setVisible()` |
| Category Panel | Right (splitter) | Hide/Show via splitter |

---

## §2 Architecture

### §2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TOOLBAR AREA (SearchToolbar)                                               │
│  [Search Toolbar]                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                           │                                                 │
│    LOG TABLE VIEW         │    CATEGORY PANEL                              │
│    (75% width)            │    (25% width)                                 │
│                           │                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  STATUS BAR                                                                  │
│  filename.log  │  👁️  │      │ [⛔ 0] [🛑 0] [⚠️ 0] ... │                   │
│                │(toggle)│     │ Statistics Bar                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### §2.2 Signal Flow

```
MainStatusBar                    MainWindow                    MainController
      │                              │                               │
      │  panels_toggled(bool)        │                               │
      ├─────────────────────────────►│                               │
      │                              │  toggle_panels()               │
      │                              ├──────────────────────────────►│
      │                              │                               │
      │                              │  (optional: save state)       │
      │                              │◄──────────────────────────────┤
      │                              │                               │
      │  update_button_state(bool)   │                               │
      │◄─────────────────────────────┤                               │
      │                              │                               │
```

### §2.3 State Management

The toggle button maintains two states:
- **Panels Visible** (default): All panels shown in normal layout
- **Panels Hidden**: Only log table visible, maximized

State is NOT persisted across sessions (each session starts with panels visible).

---

## §3 UI Components

### §3.1 Toggle Button

**Location:** Status bar, rightmost position (after statistics bar)

**Appearance:**

| State | Icon | Tooltip |
|-------|------|---------|
| Panels Visible | 👁️ (U+1F441) | "Hide panels (Ctrl+Shift+P)" |
| Panels Hidden | 👁️‍🗨️ (U+1F5E8) or 👁️‍🗨️ with strikethrough | "Show panels (Ctrl+Shift+P)" |

**Alternative Icon Options:**
- `👁️` (eye) / `👁️‍🗨️` (eye in speech bubble)
- `◀` (left triangle) / `▶` (right triangle) - indicates panel direction
- `⬜` (square) / `⬛` (square with panels)

**Dimensions:**
- Button padding: 4px 8px
- Icon size: 16px
- Border radius: 3px

### §3.2 Button Styling

Per [ui-design-system.md](ui-design-system.md) §4.1.1:

| State | Background | Border | Text |
|-------|------------|--------|------|
| Default | `#F5F5F5` | `#C0C0C0` | `#333333` |
| Hover | `#E8E8E8` | `#A0A0A0` | `#333333` |
| Active/Pressed | `#D0D0D0` | `#A0A0A0` | `#333333` |
| Focus | `#F5F5F5` | `#0066CC` | `#333333` |

---

## §4 API Reference

### §4.1 MainStatusBar Extensions

```python
class MainStatusBar(QStatusBar):
    """Custom status bar for the main window.
    
    // Ref: docs/specs/features/panel-toggle-button.md §4.1
    // Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
    """
    
    # Existing signals
    counter_clicked = Signal(str, bool)  # counter_type, visible
    
    # New signal
    panels_toggled = Signal(bool)  # panels_visible
    
    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the status bar with toggle button."""
    
    def _setup_ui(self) -> None:
        """Set up status bar widgets including toggle button."""
        # File label on the left
        # Toggle button (NEW)
        # Stretch in the middle
        # Statistics bar on the right
    
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

### §4.2 MainWindow Extensions

```python
class MainWindow(QMainWindow):
    """Main application window with panel toggle support.
    
    // Ref: docs/specs/features/panel-toggle-button.md §4.2
    """
    
    # New signal
    panels_toggled = Signal(bool)  # panels_visible
    
    def toggle_panels(self) -> None:
        """Toggle visibility of all auxiliary panels.
        
        Hides/shows:
        - Search toolbar (top)
        - Category panel (right)
        """
    
    def set_panels_visible(self, visible: bool) -> None:
        """Set panels visibility directly.
        
        Args:
            visible: True to show panels, False to hide.
        """
    
    def is_panels_visible(self) -> bool:
        """Check if panels are currently visible.
        
        Returns:
            True if panels are visible, False if hidden.
        """
```

### §4.3 MainController Extensions

```python
class MainController:
    """Main application controller with panel toggle support.
    
    // Ref: docs/specs/features/panel-toggle-button.md §4.3
    """
    
    def _connect_signals(self) -> None:
        """Connect window signals including panel toggle."""
        # ... existing connections ...
        
        # Panel toggle signal
        self._window.panels_toggled.connect(self._on_panels_toggled)
    
    def _on_panels_toggled(self, visible: bool) -> None:
        """Handle panel toggle signal.
        
        Args:
            visible: True if panels should be visible, False if hidden.
        """
        # Update window panels visibility
        self._window.set_panels_visible(visible)
        
        # Update status bar button state
        self._window.statusBar().set_panels_visible(visible)
```

---

## §5 Behavior

### §5.1 Toggle Flow

1. User clicks toggle button in status bar (or presses Ctrl+Shift+P)
2. `MainStatusBar.panels_toggled` signal emitted with new state
3. `MainWindow.toggle_panels()` called
4. If panels visible:
   - Hide search toolbar (call `setVisible(False)`)
   - Hide category panel (set splitter sizes to [100%, 0%])
5. If panels hidden:
   - Show search toolbar (call `setVisible(True)`)
   - Show category panel (restore splitter sizes to [75%, 25%])
6. Update toggle button icon to reflect new state

### §5.2 State Transitions

```
┌─────────────────┐     Click/Shortcut     ┌─────────────────┐
│  Panels Visible │ ─────────────────────► │  Panels Hidden  │
│  (default)      │                        │  (maximized)    │
│  Icon: 👁️       │ ◄───────────────────── │  Icon: 👁️‍🗨️    │
└─────────────────┘     Click/Shortcut     └─────────────────┘
```

### §5.3 Keyboard Shortcut

| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl+Shift+P` | Toggle panels | Global |

**Implementation:**
```python
# In MainWindow._setup_shortcuts()
SHORTCUT_TOGGLE_PANELS = "Ctrl+Shift+P"

shortcut = QShortcut(QKeySequence(SHORTCUT_TOGGLE_PANELS), self)
shortcut.activated.connect(self._on_toggle_panels)
```

### §5.4 Edge Cases

#### §5.4.1 Window Resize

When window is resized while panels are hidden:
- Log table should expand to fill available space
- When panels are restored, they should use the stored ratio (75%/25%)

#### §5.4.2 File Open/Close

Opening or closing a file should NOT affect panel visibility:
- Panels remain in their current state (visible/hidden)
- Status bar button state remains unchanged

#### §5.4.3 Application Restart

Panel visibility is NOT persisted:
- Application always starts with panels visible
- User must toggle again if they want panels hidden

---

## §6 Implementation Details

### §6.1 Hiding Panels

```python
def set_panels_visible(self, visible: bool) -> None:
    """Set panels visibility."""
    if visible:
        # Restore search toolbar
        self._search_toolbar.setVisible(True)
        
        # Restore category panel
        splitter = self.centralWidget().findChild(QSplitter)
        if splitter:
            left_size = int(self.width() * SPLITTER_LEFT_RATIO / 100)
            right_size = int(self.width() * SPLITTER_RIGHT_RATIO / 100)
            splitter.setSizes([left_size, right_size])
    else:
        # Hide search toolbar
        self._search_toolbar.setVisible(False)
        
        # Hide category panel
        splitter = self.centralWidget().findChild(QSplitter)
        if splitter:
            splitter.setSizes([self.width(), 0])
    
    # Store state for button update
    self._panels_visible = visible
```

### §6.2 Status Bar Button

```python
def _setup_ui(self) -> None:
    """Set up status bar widgets."""
    # File label on the left
    self._file_label = QLabel("No file open")
    self._file_label.setStyleSheet("padding: 0 8px;")
    self.addWidget(self._file_label)
    
    # Stretch in the middle
    self._stretch = QWidget()
    self._stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    self.addWidget(self._stretch)
    
    # Statistics bar on the right
    self._statistics_bar = StatisticsBar()
    self.addPermanentWidget(self._statistics_bar)
    
    # Panel toggle button (NEW) - rightmost position
    self._toggle_button = QPushButton("👁️")
    self._toggle_button.setFlat(True)
    self._toggle_button.setToolTip("Hide panels (Ctrl+Shift+P)")
    self._toggle_button.clicked.connect(self._on_toggle_clicked)
    self.addPermanentWidget(self._toggle_button)

def _on_toggle_clicked(self) -> None:
    """Handle toggle button click."""
    self.panels_toggled.emit(self._panels_visible)

def set_panels_visible(self, visible: bool) -> None:
    """Update button state to reflect panel visibility."""
    self._panels_visible = visible
    if visible:
        self._toggle_button.setText("👁️")
        self._toggle_button.setToolTip("Hide panels (Ctrl+Shift+P)")
    else:
        self._toggle_button.setText("👁️‍🗨️")
        self._toggle_button.setToolTip("Show panels (Ctrl+Shift+P)")
```

---

## §7 Testing

### §7.1 Unit Tests

```python
def test_toggle_button_initial_state(qtbot):
    """Test toggle button starts with panels visible."""
    status_bar = MainStatusBar()
    assert status_bar.is_panels_visible() is True

def test_toggle_button_click(qtbot):
    """Test clicking toggle button emits signal."""
    status_bar = MainStatusBar()
    
    signal_emitted = []
    status_bar.panels_toggled.connect(lambda v: signal_emitted.append(v))
    
    status_bar._toggle_button.click()
    qtbot.wait(10)
    
    assert len(signal_emitted) == 1
    assert signal_emitted[0] is False  # First click hides panels

def test_toggle_button_state_update(qtbot):
    """Test button state updates correctly."""
    status_bar = MainStatusBar()
    
    status_bar.set_panels_visible(False)
    assert status_bar.is_panels_visible() is False
    assert "Show" in status_bar._toggle_button.toolTip()
    
    status_bar.set_panels_visible(True)
    assert status_bar.is_panels_visible() is True
    assert "Hide" in status_bar._toggle_button.toolTip()

def test_main_window_toggle_panels(qtbot):
    """Test MainWindow toggle functionality."""
    window = MainWindow()
    
    # Initial state: panels visible
    assert window.is_panels_visible() is True
    
    # Toggle to hide
    window.toggle_panels()
    assert window.is_panels_visible() is False
    
    # Toggle to show
    window.toggle_panels()
    assert window.is_panels_visible() is True
```

### §7.2 Integration Tests

```python
def test_toggle_panels_keyboard_shortcut(qtbot):
    """Test Ctrl+Shift+P toggles panels."""
    window = MainWindow()
    controller = MainController(window)
    
    # Initial state
    assert window.is_panels_visible() is True
    
    # Press shortcut
    qtbot.keyPress(window, Qt.Key_P, Qt.ControlModifier | Qt.ShiftModifier)
    qtbot.wait(10)
    
    assert window.is_panels_visible() is False
    
    # Press again
    qtbot.keyPress(window, Qt.Key_P, Qt.ControlModifier | Qt.ShiftModifier)
    qtbot.wait(10)
    
    assert window.is_panels_visible() is True

def test_toggle_panels_persists_during_session(qtbot):
    """Test panel state persists during session but not across restarts."""
    window = MainWindow()
    controller = MainController(window)
    
    # Hide panels
    window.set_panels_visible(False)
    assert window.is_panels_visible() is False
    
    # Open file (panels should stay hidden)
    controller.open_file("test.log")
    assert window.is_panels_visible() is False
    
    # Close file (panels should stay hidden)
    controller.close_file()
    assert window.is_panels_visible() is False
```

---

## §8 Cross-References

- **UI Design System:** [ui-design-system.md](ui-design-system.md) §4.1.1 (Button styling)
- **UI Components:** [ui-components.md](ui-components.md) §6 (SearchToolbar), §7 (MainStatusBar)
- **Main Window:** [main-controller.md](main-controller.md)
- **Status Bar:** [src/views/widgets/main_status_bar.py](../../src/views/widgets/main_status_bar.py)
- **Splitter Dimensions:** [src/constants/dimensions.py](../../src/constants/dimensions.py)

---

## §9 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-03-18 | Updated to use SearchToolbar.setVisible() instead of CollapsiblePanel; removed ToggleStrip references |
| 1.0 | 2026-03-18 | Initial specification for panel toggle button |