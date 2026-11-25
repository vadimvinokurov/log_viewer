# Column resize — short design (2026-11-25)

Spec ref: `docs/FUNCTIONAL_SPEC.html` §4 ("Ширины по умолчанию" — defaults imply
changeable widths). Horizontal-scrollbar behavior discussed in the same session
(click-only scrollbar, trackpad-gesture gate) is explicitly **out of scope** for
this design; it follows as its own task once columns can overflow.

## Intent and why

The table column widths in §4 are defaults, not constants. The owner wants to
drag column borders in the header to change widths, so wide Time/Category values
or narrow windows can be accommodated without touching data layout.

## Decisions (owner, 2026-11-25)

- **All four columns** are resizable: Line, Time, Category, Message.
- **Minimum width any column: 20px.**
- **Message stays rubber-band:** its effective width is
  `max(user width, window width − sum(other three))` (clamped to the 20px floor
  when the other columns alone overflow the window). Consequences:
  - while the user-width sum fits the window, the table always fills it exactly;
    the Message drag handle physically stops at the "window remainder" point —
    it cannot be dragged smaller;
  - a horizontal scrollbar (native `overflow: auto` for this task) appears only
    when the user-width sum exceeds the window width.
- **Persistence: yes.** Widths survive restarts.

## Mechanism

- Drag the border between header cells (grab zone ~5px, `col-resize` cursor,
  **live resize** — the table re-lays out while dragging).
- **Double-click** a border resets that column to the §4 default
  (50 / 110 / 150 / 600).
- Pure logic lives in `ui/src/columnWidths.ts` (vitest-covered): border hit-test,
  clamp to [20px, ∞), Message effective-width computation, per-column reset.
  Components only wire drag events + width state to markup (rule: thin UI).
- Headless surface: `window.__headless` exposes `columnWidths` in the document
  snapshot and a `resizeColumn` action; the e2e golden set gains a
  "column dragged" state rendering.

## Persistence (my call, not owner-vetoed)

IPC pair `column_widths` (get) / `column_widths_set` (save) — JSON file in the
app data dir. Rust side: `ts-rs` schema + generated TS binding, no hand-written
bindings (building-testable-apps rule). Load once at startup (into the
`columnWidths` state), save at the end of a drag / on reset — not per pixel.
The IPC adapter is the single normalization point.

## Non-goals / anti-goals

- No click-only scrollbar or trackpad-gate in this task (next step).
- No long-line content width expansion (rows stay clipped at column width).
- No per-column min besides the 20px floor; no persisted "collapsed" columns.
