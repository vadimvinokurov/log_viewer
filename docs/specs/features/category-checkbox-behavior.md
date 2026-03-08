# Category Panel Checkbox Behavior Specification

**Version:** v1.0  
**Status:** [DRAFT]  
**Created:** 2026-03-13  
**Project Context:** Python Tooling (Log Viewer Application)

---

## §1 Overview

### §1.1 Purpose

This specification defines the checkbox behavior for the category tree panel in the log viewer application. The panel displays a hierarchical tree of log categories with checkboxes for filtering log visibility.

### §1.2 Scope

- Checkbox state management for parent and child categories
- Cascade rules for enabling/disabling categories
- Visual representation of checkbox states
- Persistence of checkbox states across sessions
- Integration with log filtering

### §1.3 References

- Existing implementation: [`CategoryPanel`](../../src/views/category_panel.py:47)
- Category tree model: [`CategoryTree`](../../src/core/category_tree.py:23)
- System node model: [`SystemNode`](../../src/models/system_node.py:1)

---

## §2 Definitions

| Term | Definition |
|------|------------|
| **Category** | A log category path (e.g., `HordeMode/scripts/app`) |
| **Parent Category** | A category that has child categories (e.g., `HordeMode`) |
| **Child Category** | A category nested under a parent (e.g., `HordeMode/scripts`) |
| **Root Category** | Top-level category with no parent |
| **Checked State** | Checkbox is marked (✓), category logs are visible |
| **Unchecked State** | Checkbox is unmarked, category logs are hidden |
| **Custom Category** | User-defined category with pattern matching (marked with 🔍) |

---

## §3 Checkbox Behavior Rules

### §3.1 Parent Enable Rule (Cascade Down)

**Rule:** When a parent category is **enabled** (checked), ALL child categories MUST be automatically enabled (checked).

**Rationale:** Enabling a parent implies the user wants to see all logs under that category tree.

**Example:**
```
Before: Parent (unchecked)
        └── Child A (unchecked)
        └── Child B (unchecked)

Action: User checks Parent

After:  Parent (checked)
        └── Child A (checked)    ← Auto-enabled
        └── Child B (checked)    ← Auto-enabled
```

### §3.2 Parent Disable Rule (Cascade Down)

**Rule:** When a parent category is **disabled** (unchecked), ALL child categories MUST be automatically disabled (unchecked).

**Rationale:** Disabling a parent implies the user wants to hide all logs under that category tree.

**Example:**
```
Before: Parent (checked)
        └── Child A (checked)
        └── Child B (checked)

Action: User unchecks Parent

After:  Parent (unchecked)
        └── Child A (unchecked)    ← Auto-disabled
        └── Child B (unchecked)    ← Auto-disabled
```

### §3.3 Child Enable Rule (No Parent Effect)

**Rule:** When a child category is **enabled** (checked), the parent category MUST NOT be automatically enabled.

**Rationale:** Users may want to see specific sub-categories without enabling the entire parent tree.

**Example:**
```
Before: Parent (unchecked)
        └── Child A (unchecked)
        └── Child B (unchecked)

Action: User checks Child A

After:  Parent (unchecked)         ← Parent state unchanged
        └── Child A (checked)      ← User's explicit action
        └── Child B (unchecked)    ← Sibling unchanged
```

### §3.4 Child Disable Rule (No Parent Effect)

**Rule:** When a child category is **disabled** (unchecked), the parent category MUST NOT be automatically disabled.

**Rationale:** Disabling one child should not affect the parent or siblings.

**Example:**
```
Before: Parent (checked)
        └── Child A (checked)
        └── Child B (checked)

Action: User unchecks Child A

After:  Parent (checked)           ← Parent state unchanged
        └── Child A (unchecked)    ← User's explicit action
        └── Child B (checked)      ← Sibling unchanged
```

### §3.5 Visual State for Enabled Child with Disabled Parent

**Rule:** When a parent is unchecked but a child is checked, the child checkbox MUST display as **normally checked** (✓).

**Rationale:** The child's state is independent for display purposes. No indeterminate or dimmed state is used.

**Example:**
```
Visual: Parent [ ] (unchecked)
        └── Child A [✓] (checked, normal appearance)
        └── Child B [ ] (unchecked)
```

---

## §4 Log Display Logic

### §4.1 Visibility Rule

**Rule:** A log entry is visible in the log panel if and only if **its category OR any ancestor category is checked**.

**Formula:**
```
log_visible(category) = category.checked OR any_ancestor(category).checked
```

**Rationale:** This allows users to:
1. Enable a parent to see all child logs
2. Enable specific children while parent is disabled

### §4.2 Examples

| Parent State | Child State | Child Logs Visible | Reason |
|--------------|-------------|-------------------|--------|
| Checked | Checked | ✓ Yes | Parent checked |
| Checked | Unchecked | ✓ Yes | Parent checked (child state ignored) |
| Unchecked | Checked | ✓ Yes | Child checked |
| Unchecked | Unchecked | ✗ No | Neither checked |

### §4.3 Custom Categories

**Rule:** Custom categories follow the same rules as regular categories.

Custom categories can have parent categories and follow all cascade rules defined in §3.

---

## §5 State Persistence

### §5.1 Storage Location

Checkbox states MUST be persisted using the existing [`SettingsManager`](../../src/utils/settings_manager.py:1).

**Storage Key:** `category_states`

**Format:**
```json
{
  "category_states": {
    "HordeMode": true,
    "HordeMode/scripts": true,
    "HordeMode/scripts/app": false
  }
}
```

### §5.2 Save Triggers

State MUST be saved when:
1. User checks/unchecks any category
2. Application closes (save current state)
3. User switches to a different log file (save previous file's state)

### §5.3 Restore Triggers

State MUST be restored when:
1. Application starts (load last state)
2. User opens a previously-viewed log file (restore that file's state)
3. New log file opened (default: all categories checked)

### §5.4 Default State

When no saved state exists for a log file, all categories MUST default to **checked** (enabled).

---

## §6 API Contract

### §6.1 CategoryTree Methods

#### §6.1.1 `toggle(path: str, enabled: bool) -> None`

**Current Behavior (to be modified):**
- Sets category state
- Cascades to all children

**Required Behavior:**
- Same as current - cascade down on enable/disable

**Location:** [`CategoryTree.toggle()`](../../src/core/category_tree.py:64)

#### §6.1.2 `set_enabled(path: str, enabled: bool) -> None`

**Current Behavior:**
- Sets category state WITHOUT cascading

**Required Behavior:**
- Same - use for child-only changes

**Location:** [`CategoryTree.set_enabled()`](../../src/core/category_tree.py:83)

#### §6.1.3 NEW: `is_category_visible(path: str) -> bool`

**Purpose:** Determine if logs from a category should be displayed.

**Logic:**
```python
def is_category_visible(self, path: str) -> bool:
    """
    Check if a category's logs should be visible.
    
    A category is visible if it OR any ancestor is enabled.
    
    Args:
        path: Category path
        
    Returns:
        True if visible, False otherwise
    """
    # Check self
    if self.is_enabled(path):
        return True
    
    # Check ancestors
    node = self.get_node(path)
    while node.parent:
        if node.parent.is_enabled:
            return True
        node = node.parent
    
    return False
```

### §6.2 CategoryPanel Signals

#### §6.2.1 `category_toggled` Signal

**Signature:** `category_toggled = Signal(str, bool)`

**Location:** [`CategoryPanel.category_toggled`](../../src/views/category_panel.py:59)

**Behavior:** Emitted when user changes checkbox state. Emits `(path, checked)`.

### §6.3 FilterController Integration

**Location:** [`FilterController`](../../src/controllers/filter_controller.py:1)

**Required Change:** Use `is_category_visible()` instead of checking individual category states.

---

## §7 Error Handling

### §7.1 Invalid Category Path

**Condition:** Category path not found in tree.

**Behavior:** 
- Log warning at DEBUG level
- Return default state (enabled)
- Do not crash

### §7.2 Corrupted Settings

**Condition:** Saved state file is corrupted or invalid JSON.

**Behavior:**
- Log error at WARNING level
- Reset to default state (all enabled)
- Continue application startup

---

## §8 Performance Requirements

### §8.1 State Changes

- Checkbox state change MUST complete within **16ms** (60 FPS target)
- Cascade to children MUST be O(n) where n = number of descendants
- No blocking of UI thread during state updates

### §8.2 Visibility Check

- `is_category_visible()` MUST be O(h) where h = tree height
- For deep trees (h > 20), consider caching ancestor states

---

## §9 Testing Requirements

### §9.1 Unit Tests

Required test cases in [`tests/test_category_tree.py`](../../tests/test_category_tree.py:1):

1. **Test Parent Enable Cascade**
   - Enable parent → verify all children enabled

2. **Test Parent Disable Cascade**
   - Disable parent → verify all children disabled

3. **Test Child Enable No Parent Effect**
   - Enable child → verify parent unchanged

4. **Test Child Disable No Parent Effect**
   - Disable child → verify parent unchanged

5. **Test Visibility With Enabled Parent**
   - Parent enabled, child disabled → child logs visible

6. **Test Visibility With Disabled Parent, Enabled Child**
   - Parent disabled, child enabled → child logs visible

7. **Test Visibility With All Disabled**
   - Parent disabled, child disabled → child logs hidden

8. **Test Deep Nesting**
   - 5+ level hierarchy → cascade works correctly

9. **Test Custom Categories**
   - Custom category follows same rules

### §9.2 Integration Tests

Required test cases in [`tests/test_integration.py`](../../tests/test_integration.py:1):

1. **Test UI Cascade**
   - Click parent checkbox → verify UI updates all children

2. **Test Persistence**
   - Change states → close app → reopen → verify states restored

---

## §10 Implementation Notes

### §10.1 Current Implementation Gap

The current [`_on_item_changed()`](../../src/views/category_panel.py:266) method in `CategoryPanel` already implements cascade-down behavior:

```python
# Update all children recursively
self._update_children_recursive(item, checked)
```

**Required Changes:**

1. **Add visibility check method** to `CategoryTree` (see §6.1.3)

2. **Update filter logic** to use visibility check instead of simple state check

3. **Add persistence** for checkbox states via `SettingsManager`

### §10.2 No Changes Required

- Cascade-down behavior already implemented
- Child enable/disable doesn't affect parent (already correct)
- Visual state is normal checkbox (already correct)

---

## §11 Migration Plan

### §11.1 Phase 1: Add Visibility Method

1. Add `is_category_visible()` to `CategoryTree`
2. Add unit tests for visibility logic

### §11.2 Phase 2: Update Filter Logic

1. Modify `FilterController` to use `is_category_visible()`
2. Add integration tests

### §11.3 Phase 3: Add Persistence

1. Add `category_states` to settings schema
2. Implement save/restore in `CategoryPanel`
3. Add persistence tests

---

## §12 Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | Enabling parent enables all children | Unit test |
| 2 | Disabling parent disables all children | Unit test |
| 3 | Enabling child does not affect parent | Unit test |
| 4 | Disabling child does not affect parent | Unit test |
| 5 | Child checkbox displays normally when parent disabled | Visual inspection |
| 6 | Logs visible when child OR ancestor enabled | Integration test |
| 7 | State persists across sessions | Integration test |
| 8 | Custom categories follow same rules | Unit test |
| 9 | Performance within 16ms budget | Benchmark |
| 10 | No crashes on invalid paths | Error test |

---

## §13 Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| v1.0 | 2026-03-13 | Spec Architect | Initial draft |
