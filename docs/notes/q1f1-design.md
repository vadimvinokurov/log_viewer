# q1f.1 — pins UI: design (final)

Spec: §12 (pin = rule in modes p/pr/ps/pn N; pinned rows always visible
overriding filters/levels/categories §7; Pinned tab like the Filters tab;
context-menu Unpin; §2.1 — a reload clears ALL pins), §10.1 (tab layout),
§4 (menu items Pin/Unpin present by selection coverage).

## Backend (landed already, bindings regenerarated)

- `load_file_inner` clears all pins on reload (tests: reload_clears_pins...,
  clear_pins_clears_all_and_invalidates).
- New RAW command `clear_pins` (the future :rmp; no panel button — §10.1
  shows no clear-all control).

## Console actions

- `pinSelected()` → one add_pin("lineno", "<line>") per selected row, inside
  ONE mutating critical section (single snapshot refetch at the end — the
  2wu.1 lesson). `unpinSelected()` → remove_pin(id) for every EXACT-ROW pin
  whose line number is among the selected rows' line numbers; `clearAllPins()` →
  clear_pins. Headless mirrors + snapshot (pins already in the snapshot).

## Menu semantics (documented interpretation)

- §4 presence: Pin is available when at least one selected row is NOT pinned;
  Unpin when at least one selected row is pinned.
- Pinned-ness evaluation UI-side from the snapshot's pin list: exact-row pins
  (lineno mode) cover their parsed line numbers; broad pins (plain/regex)
  cover rows whose cached raw text they match; simple pins are NOT evaluated
  (the simple engine is Rust-side) — they neither enable Unpin nor count a
  row pinned **for the menu's presence logic** (documented limitation).
- Unpin removes ONLY exact-row pins covering the selection. Rows pinned by a
  broad rule stay pinned (removal goes through the panel delete button —
  §12 says per-one removal via panel; the menu deliberately never nukes a
  rule matching an unknown number of rows).

## Panels

- Pinned tab mirrors FiltersTab anatomy (checkbox, command text with the
  :p-/-:pn- prefixes via the same canonicalizer shape, delete ✕, dimmed off).
- Replace the placeholder in SidePanel; Highlights keeps its placeholder
  (exx.2).

## e2e

- Golden: Pinned tab with entries + a disabled one.
- Golden: pins survive filter narrowing — a filter that hides everything
  except matched rows, pinned rows still visible (§7/§12 override), then
  context-menu unpin on a pinned row -> it disappears (if not filter-matched).
- Context-menu goldens with live Pin/Unpin items may re-baseline 14-selection-menu.
- §4: reload via __headless.clearAllPins equivalent — reload clears pins:
  assert pins empty after a reload-driven snapshot.

## Gates

Full gates from ui/; live-check section (h) by the coordinator at the
milestone; design oracle after any visual change.
