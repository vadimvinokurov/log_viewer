# exx.2 — highlights: design (final)

Spec: §9 (auto palette color rotation over a 10-color palette, semi-transparent
rectangles behind matched text, Message column only, overlapping rules,
per-rule checkbox/delete, color change via the SYSTEM color picker, rmh
later-but-command-now, highlights SURVIVE reload §2.1), §10.1 (tab item with
a color dot instead of the command prefix).

## Core (landed at exx.1, do not modify)

`HighlightEngine`: rules Pattern{matcher} / LineNo{line_no}, color_index
round-robin 0..PALETTE_SIZE, `row_spans(message) -> Vec<(start, len)>` byte
ranges in the MESSAGE text. Palette HEXES live in the UI layer.

## Shell (Rust agent)

- New managed `HighlightState`: core engine + parallel meta
  `Vec<HighlightMeta { mode, pattern, enabled, override_color: Option<String> }>`.
  Persists across `load_file` (§2.1 the OPPOSITE of pins — no reset).
- Commands (specta): `add_highlight(mode, pattern)` (rotation assigned by the
  core; unknown mode → Err in the dsq.3 style), `remove_highlight(id)`,
  `set_highlight_enabled(id, on)`, `set_highlight_color(id, hex)`
  (hex = CSS "#rrggbb" or null to reset to the palette rotation color),
  `clear_highlights()` (the future :rmh).
- `get_rows` RowDto gains `spans: Vec<SpanDto>`; spans are computed per row
  from the engine (cheap: only active rules) — byte offsets in the MESSAGE
  text.

## RAW shapes

```ts
SpanDto { start: number; len: number; color_index: number; override_color: string | null }
HighlightDto { id: number; mode: string; pattern: string; enabled: boolean; color_index: number; override_color: string | null }
```

`RowDto` gains `spans: SpanDto[]` (additive). Byte→JS string index conversion
happens ONCE in ipcClient (single normalization point).

## UI (second agent)

- Palette table `HIGHLIGHT_HEX: string[10]` from docs/UI_DESIGN.html tokens
  (§3.1); the resolved span color = `override_color ?? HIGHLIGHT_HEX[color_index]`.
- Highlights tab: checkbox, command text (:h :hr :hs :hn via the filtersTab
  canonicalizer shape), color dot (click → `<input type="color">`, the
  webview's system picker), delete ✕, dimmed off. Replaces the placeholder;
  rmh is NOT a tab button (§10.1 shows none).
- LogTable Message cell: overlapped semi-transparent rectangles behind the
  matched ranges (opacity from the design reference); level colors stay
  underneath (§9).
- Snapshot gains `highlights`; headless RPC: addHighlight, setHighlightEnabled,
  setHighlightColor, removeHighlight, clearHighlights.

## e2e + interpretations documented

- Goldens: two overlapping highlights (Message-only tinting), a disabled
  one (dimmed, no spans), a user-picked color dot; the hn whole-line case.
- Interpretation: an invalid pattern → never-match rule (renders nothing but
  keeps the slot), matching add_filter behavior.
- Interpretation: color rotation continues from the current engine counter
  across removals (core behavior; no re-indexing of existing rules).
