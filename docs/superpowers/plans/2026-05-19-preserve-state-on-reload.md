# Preserve State on Reload — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the user reloads a log file, preserve filters, highlights, and disabled categories; clear pins and search state.

**Architecture:** All changes in `load_lines` in `log_store.py`. Snapshot disabled category names before rebuilding, restore by name after. Clear pins and search state. No `app.py` changes needed — `load_lines` handles everything.

**Tech Stack:** Python 3.9+, PySide6, numpy, pytest

---

### Task 1: Update existing pin-survives-reload test to expect pins cleared

The existing test `test_load_lines_does_not_reset_pins` (line 857) asserts that pins survive reload. With the new behavior, pins must be cleared on reload, so this test needs to assert the opposite.

**Files:**
- Modify: `tests/unit/test_log_store.py:857-863`

- [ ] **Step 1: Update the test to expect pins cleared on reload**

Replace the method at line 857:

```python
def test_load_lines_clears_pins(self) -> None:
    """Pinned lines are cleared on file reload."""
    store = LogStore()
    store.load_lines(SAMPLE_LINES)
    store.pin_line(2)
    store.load_lines(SAMPLE_LINES)
    assert store.pinned_line_numbers == set()
```

- [ ] **Step 2: Run the test to verify it fails (pins currently persist)**

Run: `uv run pytest tests/unit/test_log_store.py::TestLogStorePinnedLines::test_load_lines_clears_pins -v`
Expected: FAIL — pins currently survive reload

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_log_store.py
git commit -m "test: expect pins cleared on reload (currently fails)"
```

---

### Task 2: Write failing tests for reload state preservation

**Files:**
- Modify: `tests/unit/test_log_store.py` — add new test class at end of file

- [ ] **Step 1: Add `TestReloadStatePreservation` class**

Append at the end of the file:

```python
class TestReloadStatePreservation:
    """Test that filters, highlights, and disabled categories survive reload."""

    def test_preserves_filters_on_reload(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_filter(Filter(pattern="Failed", mode=SearchMode.PLAIN))
        store.load_lines(SAMPLE_LINES)
        assert len(store.filters) == 1
        assert store.filters[0].pattern == "Failed"

    def test_preserves_highlights_on_reload(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.add_highlight(Highlight(pattern="ERROR", mode=SearchMode.PLAIN))
        store.load_lines(SAMPLE_LINES)
        assert len(store.highlights) == 1
        assert store.highlights[0].pattern == "ERROR"

    def test_preserves_disabled_categories_on_reload(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        assert len(store.disabled_categories) > 0
        store.load_lines(SAMPLE_LINES)
        folder_id = store._category_name_to_id["my_app/storage/folder"]
        db_id = store._category_name_to_id["my_app/storage/db"]
        assert folder_id in store.disabled_categories
        assert db_id in store.disabled_categories

    def test_disabled_category_skipped_if_removed_on_reload(self) -> None:
        """Category that no longer exists after reload is silently skipped."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        store.load_lines(["01-01-2024T08:00:00.100 other LOG_INFO hello"])
        assert store.disabled_categories == set()

    def test_new_category_enabled_by_default_on_reload(self) -> None:
        """Category not in disabled set is enabled after reload."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES[:2])
        store.disable_category("my_lib/core")
        store.load_lines(SAMPLE_LINES)
        core_id = store._category_name_to_id["my_lib/core"]
        assert core_id in store.disabled_categories
        system_id = store._category_name_to_id["SYSTEM"]
        assert system_id not in store.disabled_categories

    def test_clears_pins_on_reload(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.pin_line(1)
        store.pin_line(3)
        store.load_lines(SAMPLE_LINES)
        assert store.pinned_line_numbers == set()

    def test_clears_search_on_reload(self) -> None:
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.search("Failed", SearchMode.PLAIN, direction=SearchDirection.FORWARD)
        assert store.search_state is not None
        store.load_lines(SAMPLE_LINES)
        assert store.search_state is None

    def test_disabled_category_tree_nodes_match_set_on_reload(self) -> None:
        """Category tree node.enabled flags match disabled_categories after reload."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        store.load_lines(SAMPLE_LINES)
        my_app_node = store.category_tree.children["my_app"]
        assert my_app_node.enabled is False
        assert my_app_node.children["storage"].enabled is False

    def test_filtered_indices_correct_after_reload(self) -> None:
        """Filtered indices reflect preserved disabled categories."""
        store = LogStore()
        store.load_lines(SAMPLE_LINES)
        store.disable_category("my_app")
        store.load_lines(SAMPLE_LINES)
        # my_app lines (1,2,3,5) hidden, only my_lib/core (0) and SYSTEM (4)
        assert set(store.filtered_indices.tolist()) == {0, 4}
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run pytest tests/unit/test_log_store.py::TestReloadStatePreservation -v`
Expected: FAIL — disabled categories reset, pins persist, search state persists

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_log_store.py
git commit -m "test: add reload state preservation tests (currently failing)"
```

---

### Task 3: Implement in `load_lines`

Replace lines 135-143 of `src/log_viewer/core/log_store.py`. The ordering matters: snapshot from OLD `_category_names` BEFORE overwriting with new ones.

Current code (lines 135-143):

```python
        self._category_names = cat_names
        self._category_name_to_id = cat_name_to_id
        self.current_file = file_path
        self.disabled_levels = set()
        self.disabled_categories = set()

        self._build_category_tree()
        self._count_levels()
        self._apply_filters()
```

- [ ] **Step 1: Replace with snapshot + restore logic**

```python
        # Snapshot disabled category names before overwriting
        disabled_cat_names = {
            self._category_names[cid]
            for cid in self.disabled_categories
            if cid < len(self._category_names)
        }

        self._category_names = cat_names
        self._category_name_to_id = cat_name_to_id
        self.current_file = file_path
        self.disabled_levels = set()
        self.disabled_categories = set()
        self.pinned_line_numbers = set()
        self.search_state = None

        # Restore disabled categories by name (new IDs)
        for name in disabled_cat_names:
            if name in self._category_name_to_id:
                self.disabled_categories.add(self._category_name_to_id[name])

        self._build_category_tree()

        # Sync tree node.enabled flags with restored disabled set
        for name in disabled_cat_names:
            if name in self._category_name_to_id:
                node = self._find_category_node(name)
                if node:
                    self._set_enabled_recursive(node, False)

        self._count_levels()
        self._apply_filters()
```

- [ ] **Step 2: Run all unit tests**

Run: `uv run pytest tests/unit/test_log_store.py -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add src/log_viewer/core/log_store.py
git commit -m "feat: preserve disabled categories on reload, clear pins and search"
```

---

### Task 4: Run full test suite and lint

- [ ] **Step 1: Run all tests**

Run: `uv run pytest`
Expected: ALL PASS

- [ ] **Step 2: Run linter**

Run: `uv run --with ruff ruff check src/`
Expected: No errors
