# Remember Last Open Directory

## Problem
The file open dialog (`QFileDialog`) always opens in the OS default location instead of the directory the user last opened a file from.

## Solution
Persist the directory of the last opened file in the existing ConfigManager and pass it to `QFileDialog.getOpenFileName()` as the starting directory.

## Changes

### 1. `src/log_viewer/core/config.py`
- Add `"last_open_dir": ""` to `_DEFAULTS`.

### 2. `src/log_viewer/gui/app.py` — `_file_open_dialog()`
- Read `self._config.get("last_open_dir")` before opening the dialog.
- Pass it as the `dir` argument to `QFileDialog.getOpenFileName()`.
- After successful file selection, save `os.path.dirname(path)` back to config via `self._config.set()` + `save()`.

### 3. `src/log_viewer/gui/app.py` — `_open_file()` and other file-opening paths
- Whenever a file is opened (dialog, `:open` command, drag-and-drop), update `last_open_dir` in config.

## Scope
- No UI changes. No new settings screen. Purely behavioral.
- Setting persists across sessions via `~/.logviewer/settings.json`.
