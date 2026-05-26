# Pin Precomputed Masks Optimization

## Problem

Pin rules currently match lines in `_apply_filters()` via a per-line Python loop with decode + `filter_engine.match()` — O(n * rules) on every filter change. Filters already use precomputed boolean masks (`_filter_masks`) computed once via `_compute_filter_mask()`, with vectorized numpy for plain CI patterns.

## Solution

Mirror the filter mask pattern for pins: add `_pin_masks: list[np.ndarray]`, compute each mask via the same `_compute_filter_mask()` function at `add_pin` time. In `_apply_filters`, combine active pin masks with OR into a single `pin_mask`, then merge into result via `_merge_sorted`. The only difference between filters and pins remains in the final merge: filters intersect with category+level masks, pins bypass all filters via union.

## Changes (single file: `log_store.py`)

### `__init__`
Add `self._pin_masks: list[np.ndarray] = []`.

### `add_pin`
Append `self._compute_filter_mask(filt)` to `_pin_masks`.

### `remove_pin`
`del self._pin_masks[index]`.

### `unpin_all`
`self._pin_masks.clear()`.

### `_apply_filters` pin block (lines 619-638)
Replace per-line loop with vectorized OR over active pin masks:
```python
if has_pins:
    active_pin_masks = [m for m, e in zip(self._pin_masks, self.pinned_enabled) if e]
    if active_pin_masks:
        pin_mask = np.zeros(self.n, dtype=bool)
        for m in active_pin_masks:
            pin_mask |= m
        pinned_indices = np.nonzero(pin_mask)[0].astype(np.uint32)
        self.pinned_line_numbers = {int(idx) + 1 for idx in pinned_indices}
        result = _merge_sorted(result, pinned_indices)
    else:
        self.pinned_line_numbers = set()
else:
    self.pinned_line_numbers = set()
```

### `_finalize_load`
Add `self._pin_masks = []` alongside existing pin state clear.

## Not changed
- `_compute_filter_mask` — reused as-is
- `PinnedListWidget` — GUI unchanged
- All existing tests pass unchanged (behavior is identical, just faster)

## Performance impact
- Pin mask computed once at `add_pin` time (amortized O(n) with vectorized numpy for plain CI)
- `_apply_filters` pin merge becomes O(n) mask OR instead of O(n * rules) Python loop
- No decode per line on every filter change
