# README User Guide — Design Spec

## Goal

Write a single-file README.md for end users who download the binary (macOS .dmg, Windows .exe). The README must be scannable, searchable, and cover all functionality without being a tutorial.

## Decisions

- **Language:** English
- **Audience:** End users (binary downloaders), not developers building from source
- **Style:** Flat reference — tables and bullet lists, no walkthrough sections
- **Length target:** 200-300 lines
- **Screenshots:** None
- **Separate docs:** No — everything in README.md

## Structure

1. **Header** — project name, one-line tagline, version badge (2.0.0)
2. **Features** — 8-10 bullets covering: filtering, highlighting, search (plain/regex/simple query), category tree, log level toggles, vim-style navigation, presets, drag-and-drop, persistent settings
3. **Installation**
   - Download binary: macOS (.dmg), Windows (.exe)
   - Build from source (brief): `uv sync` → `uv run log-viewer`
   - Build distributable: `packaging/build-macos.sh` / `build-windows.bat`
4. **Quick Start** — 4 terse steps: open file, navigate, filter, highlight
5. **Keyboard Shortcuts** — table: key → action (j, k, gg, G, Ctrl-D, Ctrl-U, yy, Ctrl-O, Ctrl-R, Ctrl-Q, Ctrl-B, /, ?, n, N)
6. **Command Reference** — one table grouped by category:
   - Search: `s`, `sr`, `ss`, `n`, `N`, `/`, `?`
   - Filter: `f`, `fr`, `fs`, `rmf`, `lsf`
   - Highlight: `h`, `hr`, `hs`, `rmh`, `lsh`
   - Category: `cate`, `catd`, `lscat`
   - Preset: `preset`, `rmpreset`, `lspreset`, `presetl`
   - Pin: `pin`, `unpin`
   - File: `open`, `reload`
   - System: `q`
   Each row: syntax, flags (`/cs/`, `/color=red/`), description, example
7. **Log Levels** — brief: 6 levels (CRITICAL, ERROR, WARNING, INFO, DEBUG, TRACE), toggled via bottom bar buttons
8. **Themes & Presets** — theme switching, preset save/load workflow
9. **Configuration** — file paths: `~/.logviewer/settings.json`, `history.json`, `presets/*.yaml`
10. **License** — placeholder if project has a license

## Command Syntax Reference

All commands typed in the bottom bar with `:` prefix.
Grammar: `:command[/flags/]text`

### Flags
- `/cs/` — case sensitive matching
- `/color=red/` or `/color=#ff0000/` — highlight color

### Match Modes
- No suffix → plain text
- `r` suffix → regex
- `s` suffix → simple query (AND, OR, NOT, parentheses, quoted terms)

## Verification

- All commands from command_parser.py are documented
- All keyboard shortcuts from log_table.py and app.py are listed
- Build instructions match packaging/ scripts
- No fabricated commands or flags
