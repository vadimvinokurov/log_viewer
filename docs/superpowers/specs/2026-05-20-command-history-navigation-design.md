# Command history navigation via arrow keys

## Problem

The app has three keyboard states but arrow keys only behave contextually in two of them:
- **Normal**: arrows scroll the log table (default Qt behavior)
- **Search mode**: arrows navigate matches (via eventFilter)
- **Command input**: arrows do nothing useful (QLineEdit cursor Home/End)

`CommandHistory` exists in `core/` with `navigate_up/navigate_down` but is not connected to the GUI.

## Design

### State machine (no explicit states needed)

Arrow key behavior is determined by focus:
- `log_table` has focus → Qt default scrolling
- `command_input` has focus → history navigation
- Search mode active + `log_table` has focus → match navigation (already works)

No new state enum required — focus is the discriminator.

### Changes

**1. Wire CommandHistory into CommandInput**

`CommandInput.__init__` accepts a `CommandHistory` instance. `keyPressEvent` handles:

| Key | Action |
|-----|--------|
| Return | Emit `command_submitted`, call `history.add()`, clear text, emit focus-back signal |
| Escape | Clear text, emit focus-back signal |
| Up | `history.navigate_up()` → `setText(result)` |
| Down | `history.navigate_down()` → `setText(result)` |

A new signal `editing_finished = Signal()` notifies MainWindow to return focus to the table.

**2. Connect in MainWindow**

- Create `CommandHistory(config)` in `MainWindow.__init__`
- Pass it to `CommandInput` (via `BottomBar` or directly)
- Connect `editing_finished` to `self.log_table.setFocus()`
- In `_on_command_submitted`: remove `self.log_table.setFocus()` (CommandInput handles it via signal)

**3. No changes to eventFilter**

The existing `in_command_input` guard already prevents the search-mode arrow handler from intercepting when command input is focused.

### Files touched

- `src/log_viewer/gui/command_input.py` — add history param, Up/Down/Escape/Return handling, `editing_finished` signal
- `src/log_viewer/gui/bottom_bar.py` — pass history through to CommandInput
- `src/log_viewer/gui/app.py` — create CommandHistory, wire signals

### Test plan

- Unit tests for CommandHistory already exist
- GUI test: type commands, press Up/Down in command input, verify text cycles through history
- GUI test: press Escape in command input, verify focus returns to log table
