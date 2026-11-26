# Multi-instance design (debug single instance, release multi)

Date: 2026-11-26. Owner approved approach B in conversation.

## Intent

Release builds must allow several app instances to run at once. Debug builds
keep the current single-instance guard (the live-verification driver writes a
fixed shared port file that two instances would race on, so keeping one
instance in debug removes that whole class of problem). Settings
(`~/.logviewer/settings`) and command history (`~/.logviewer/history`) are
shared files: every instance reads and writes the same data.

## Goals

- Release: launching a second instance opens a second independent window.
- Debug: unchanged — a second start exits with code 3 before any window.
- Shared settings/history: no lost updates between instances in the normal
  user-paced case; each command sees the other instances' latest data.

## Non-goals

- Cross-process file locking for settings/history. Writes are user-paced and
  sub-millisecond on tiny files; the read-modify-write race window (~1 ms per
  command) is accepted. Revisit only if a real lost-update is ever observed.
  (Torn-read corruption — one instance reading a half-written file during the
  other's write — is closed instead: writes publish atomically through a
  per-process temp file + rename, review fix 2026-11-26.)
- Debug multi-instance (with per-PID port files). The owner keeps debug
  single-instance on purpose.
- Live sync of in-memory state *between* instances (e.g. column widths
  changing in the other window every repaint). Reads/writes only.
- Updater behavior with several release instances running at once (two
  simultaneous auto-update downloads/installations). Unexamined; revisit only
  if it ever misbehaves.

## Approaches

- **A. Last-writer-wins (rejected).** Each instance keeps its startup-loaded
  in-memory `Store` and overwrites the file whole. Minimal code (just a
  `cfg` on the lock), but two instances silently lose each other's history
  entries and settings updates.
- **B. Re-read files on each access (chosen).** The store reloads
  settings/history from disk before every read or write
  (`settings_get`, `set_settings`, `history_get`, `push_history`). Files are
  tiny (tens of lines) and access is rare and user-driven, so the cost is
  nil; every access merges with whatever other instances saved, and unknown
  keys (`raw`) are re-preserved per reload.

## Design

1. `src-tauri/src/lib.rs` — wrap the instance-lock acquisition in `run()`
   with `#[cfg(debug_assertions)]` (release `run()` starts without a lock).
   The `InstanceLock`/`try_acquire_instance` code and its tests stay.
2. `crates/logviewer-core/src/settings.rs` — `Store` gains a reload step:
   before `settings()`/`set_settings()`/`history()`/`push_history()` results
   are served, the backing files are re-parsed (defaults on absence/corruption
   per §15) and merged with the in-memory raw-keys blob, same as `open()`
   does today. Public API unchanged.
3. `ipc.rs` needs no changes: it talks to `SettingsState` (`Store`) only.
4. Debug behavior is unchanged by design of 1–3; the driver port file stays
   fixed-path because debug still runs one instance.

## What's left to the builder

- Exact reload mechanics (a private `fn reload(&mut self)` reusing the
  load-or-degrade logic vs. splitting `open` into load-parts) — whichever
  keeps `open()` and the tests clean.
- TDD per repo rules; vitest is unaffected (no UI change).
