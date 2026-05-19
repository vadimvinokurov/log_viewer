# Remember Last Open Directory — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the file open dialog start in the directory of the last opened file, persisted across sessions.

**Architecture:** Add a `last_open_dir` key to the existing ConfigManager defaults. Update `_file_open_dialog()` to read and pass it to `QFileDialog`, then save it after successful selection. Update all other file-opening paths (`:open`, drag-drop, CLI arg) to also persist the directory.

**Tech Stack:** Python 3.9+, PySide6, existing ConfigManager

---

### Task 1: Add `last_open_dir` default to ConfigManager

**Files:**
- Modify: `src/log_viewer/core/config.py:10-15`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_config.py` inside `TestConfigManagerLoad`:

```python
def test_last_open_dir_defaults_to_empty(self, cm: ConfigManager):
    cm.load()
    assert cm.get("last_open_dir") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_config.py::TestConfigManagerLoad::test_last_open_dir_defaults_to_empty -v`
Expected: FAIL — `last_open_dir` key not in config

- [ ] **Step 3: Add default to ConfigManager**

In `src/log_viewer/core/config.py`, add `"last_open_dir": ""` to `_DEFAULTS`:

```python
_DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "history_size": 100,
    "presets_path": "~/.logviewer/presets",
    "default_categories_enabled": True,
    "last_open_dir": "",
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_config.py::TestConfigManagerLoad::test_last_open_dir_defaults_to_empty -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/log_viewer/core/config.py tests/unit/test_config.py
git commit -m "feat: add last_open_dir default to ConfigManager"
```

---

### Task 2: Use last_open_dir in file open dialog

**Files:**
- Modify: `src/log_viewer/gui/app.py:154-157`

- [ ] **Step 1: Update `_file_open_dialog()` to read and write last_open_dir**

Replace the method at `app.py:154-157`:

```python
def _file_open_dialog(self) -> None:
    last_dir = self._config.get("last_open_dir", "")
    path, _ = QFileDialog.getOpenFileName(self, "Open Log File", last_dir)
    if path:
        self._open_file(path)
        dir_path = os.path.dirname(path)
        self._config.set("last_open_dir", dir_path)
        self._config.save()
```

- [ ] **Step 2: Run existing tests to verify nothing breaks**

Run: `uv run pytest tests/unit/ -v`
Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add src/log_viewer/gui/app.py
git commit -m "feat: file open dialog starts in last opened directory"
```

---

### Task 3: Persist last_open_dir from non-dialog file openings

**Files:**
- Modify: `src/log_viewer/gui/app.py` — `_open_file()` method, `:open` command handler, `dropEvent()`

- [ ] **Step 1: Add helper method `_save_last_open_dir()`**

Add after `_open_file()` in `app.py`:

```python
def _save_last_open_dir(self, path: str) -> None:
    """Persist the directory of an opened file for next dialog start."""
    if not path.startswith(("http://", "https://")):
        self._config.set("last_open_dir", os.path.dirname(path))
        self._config.save()
```

- [ ] **Step 2: Call it from `_on_file_loaded()`**

In `_on_file_loaded()` at the end (after `self._refresh_display()`), add:

```python
self._save_last_open_dir(path)
```

This covers all paths: dialog, `:open`, drag-drop, CLI arg — because they all go through `_open_file()` → `_FileLoadWorker` → `_on_file_loaded()`.

- [ ] **Step 3: Remove the per-path save from `_file_open_dialog()`**

Since `_on_file_loaded()` now handles persistence for all paths, remove the duplicate save from `_file_open_dialog()`:

```python
def _file_open_dialog(self) -> None:
    last_dir = self._config.get("last_open_dir", "")
    path, _ = QFileDialog.getOpenFileName(self, "Open Log File", last_dir)
    if path:
        self._open_file(path)
```

- [ ] **Step 4: Run all tests**

Run: `uv run pytest tests/unit/ -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/log_viewer/gui/app.py
git commit -m "feat: persist last open dir for all file opening paths"
```
