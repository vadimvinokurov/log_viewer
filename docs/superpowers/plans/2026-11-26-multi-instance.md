# Multi-Instance (debug single / release multi) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Release builds run several app instances at once; debug keeps the single-instance lock; settings/history files are shared without lost updates.

**Architecture:** Two independent edits: (1) the instance lock in `run()` becomes `#[cfg(debug_assertions)]`; (2) the settings `Store` re-reads its two small files from disk before every access, so concurrent instances always merge instead of overwrite.

**Tech Stack:** Rust (tauri workspace, `logviewer-core` crate). No UI change.

**Spec:** `docs/superpowers/specs/2026-11-26-multi-instance-design.md` (approved approach B). IPC contract: `docs/FUNCTIONAL_SPEC.html` §15 (store persists, disk errors never abort).

## Global Constraints

- All code, comments, commit messages in English (CLAUDE.md rule 6).
- `crates/logviewer-core/src/settings.rs` never panics on disk errors and never fails loading: absence/corruption degrades to defaults, per §15.
- Never bare `cargo build` in `src-tauri/` (CLAUDE.md rule 10); release acceptance uses `cargo build --release --features tauri/custom-protocol` there.
- Run Rust tests from the repo root: `cargo test -p logviewer-core <pattern>` / `cargo test -p logviewer <pattern>`; no `ui/` work is in this plan.
- Public API of other commands/IPC shapes must not change (`bindings.ts` diff should be empty; bindings export already covered by the debug build gate).

## Review Focus

- Two instances writing simultaneously: the read-modify-write race (~1 ms window) is accepted by design — if a lost update is ever reported, that is the place to add a file lock, not a bug fix elsewhere. (Pinning test not possible headless; noted, not tested.)
- `history_size` shrink: another instance caps `history_size` to 3 while 10 entries exist on disk — the next access must return the **most recent 3**, not error. Test: `reloaded_history_is_capped_again_after_disk_shrink` (Task 2).
- Corrupt settings file appearing between accesses (e.g. hand-edited mid-run): re-read degrades to defaults, never aborts. Test: `reload_degrades_to_defaults_on_corrupt_settings` (Task 2).
- Unknown keys written by the other instance survive locally-issued writes. Test: `reload_preserves_unknown_keys_from_disk` (Task 2).
- Release build without a lock must still hold every other startup assumption intact (no window before the builder, no panic path). Covered by two-instance launch acceptance (Task 1).

---

### Task 1: Debug-only instance lock

**Files:**
- Modify: `src-tauri/src/lib.rs:103-114` (`run()`)

**Interfaces:**
- Consumes: existing `try_acquire_instance(&dirs_home())` (unchanged) and its existing tests (unchanged).
- Produces: release `run()` acquires no lock; debug `run()` behavior byte-identical to today (exit 3 + stderr message on second start).

- [ ] **Step 1: Wrap the lock in `cfg(debug_assertions)`**

In `run()`, change

```rust
let _instance = match try_acquire_instance(&dirs_home()) { ... };
```

to an attribute-gated binding (no other body changes):

```rust
#[cfg(debug_assertions)]
let _instance = match try_acquire_instance(&dirs_home()) {
  Ok(l) => l,
  Err(msg) => {
    eprintln!("logviewer: {msg}");
    std::process::exit(3);
  }
};
```

Do not touch `dirs_home`, `try_acquire_instance`, `InstanceLock`, or the test module.

- [ ] **Step 2: Run the lock unit tests**

Run: `cargo test -p logviewer instance_lock`
Expected: PASS (`instance_lock_refuses_a_second_holder_until_the_first_releases` green).

- [ ] **Step 3: Verify the release binary allows two instances**

```bash
npm --prefix ui run build
(cd src-tauri && cargo build --release --features tauri/custom-protocol)
./target/release/logviewer & sleep 2; ./target/release/logviewer & sleep 2
pgrep -x logviewer | wc -l
```

Expected: `2` (both alive 2 s after the second start). Then `pkill -x logviewer`.
Repeat the same shape with the debug binary (`cargo build --features tauri/custom-protocol`) to confirm the old behavior: the second start exits with code 3 — `./target/debug/logviewer; echo $?` prints `3` while one release instance holds the lock.

- [ ] **Step 4: Commit**

```bash
git add src-tauri/src/lib.rs
git commit -m "feat(app): allow multiple instances in release, keep debug single-instance"
```

---

### Task 2: Store re-reads settings and history before every access

**Files:**
- Modify: `crates/logviewer-core/src/settings.rs` (`Store`: `settings()`, `history()`, `set_settings()`, `push_history()`; private `reload()`; test module)
- Modify: `src-tauri/src/ipc.rs` (`settings_get`, `history_get` — `guard` bindings become `mut`)

**Interfaces:**
- Consumes: `Store::open(dir) -> Store` (existing; used verbatim by the reload).
- Produces: `pub fn settings(&mut self) -> &Settings`, `pub fn history(&mut self) -> &[String]` — note the `&mut self`; call sites in `ipc.rs` must hold a mutable `MutexGuard`. `set_settings`/`push_history` signatures unchanged. No `bindings.ts` change (DTO shapes untouched).

- [ ] **Step 1: Write the failing tests**

In the `settings.rs` test module (uses existing helpers: a temp `dir`, `Store::open`, `push_history`, `set_settings`, hand-`write` of file text):

```rust
#[test]
fn history_is_shared_between_stores() {
  let dir = temp_dir();
  let mut a = Store::open(&dir);
  let mut b = Store::open(&dir);
  a.push_history("one".to_owned()).unwrap();
  assert_eq!(b.history(), &["one".to_owned()]);
}

#[test]
fn settings_are_shared_between_stores() {
  let dir = temp_dir();
  let mut a = Store::open(&dir);
  let mut b = Store::open(&dir);
  let mut s = a.settings().clone();
  s.last_open_dir = "/tmp/elsewhere".to_owned();
  a.set_settings(s).unwrap();
  assert_eq!(b.settings().last_open_dir, "/tmp/elsewhere");
}

#[test]
fn reload_preserves_unknown_keys_from_disk() {
  let dir = temp_dir();
  let mut a = Store::open(&dir);
  let mut b = Store::open(&dir);
  // b writes an unknown key by hand (simulating another instance's newer raw),
  // then a replaces settings — a's write must not delete b's unknown key.
  write(&dir, SETTINGS_FILE, "{\"foo\":1,\"history_size\":10}");
  let s = a.settings().clone();
  a.set_settings(s).unwrap();
  let text = std::fs::read_to_string(dir.join(SETTINGS_FILE)).unwrap();
  assert!(text.contains("\"foo\""), "unknown key survived: {text}");
  assert_eq!(b.history_size_value(), 10); // via existing accessor, if any
}

#[test]
fn reloaded_history_is_capped_again_after_disk_shrink() {
  let dir = temp_dir();
  let mut a = Store::open(&dir);
  let mut b = Store::open(&dir);
  // 10 lines on disk, cap 3 via a's settings; next read on b trims to 3.
  write(&dir, HISTORY_FILE, "h1\nh2\nh3\nh4\nh5\nh6\nh7\nh8\nh9\nh10\n");
  assert_eq!(b.history().len(), 3);
}

#[test]
fn reload_degrades_to_defaults_on_corrupt_settings() {
  let dir = temp_dir();
  let mut a = Store::open(&dir);
  write(&dir, SETTINGS_FILE, "not json at all");
  assert_eq!(a.settings().history_size, DEFAULT_HISTORY_SIZE);
}
```

Adjust names of helpers (`temp_dir`, `write`, `DEFAULT_HISTORY_SIZE`, `SETTINGS_FILE`, `HISTORY_FILE`, unknown-key handling) to what the module already provides — the intent of each assertion is fixed, the plumbing follows the file's existing test style. `history_size_value` is illustrative: assert via whatever accessor returns the loaded `history_size`; if none exists, assert on the file text instead (`contains("\"history_size\":10")`).

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cargo test -p logviewer-core settings`
Expected: FAIL — the `*_shared_between_stores` and cap tests observe stale in-memory state (empty/old histories), i.e. `b` does not see `a`'s write.

- [ ] **Step 3: Implement the reload**

In `Store` (private):

```rust
fn reload(&mut self) { *self = Store::open(&self.dir); }
```

Then: `settings()` and `history()` take `&mut self`, call `reload()` first, and return from the fresh state; `set_settings()` and `push_history()` call `reload()` as their first statement. Everything else (dedupe, capping, `raw_with_settings`) keeps working unchanged on the reloaded state.

- [ ] **Step 4: Fix the `ipc.rs` call sites**

`settings_get` and `history_get`: change the immutable `let guard = state.lock()...` to `let mut guard = ...`. `set_last_open_dir`/`set_column_widths`/`push_history` already hold `mut` guards; their `guard.settings().clone()` calls pick up the `&mut self` signature with no further change.

- [ ] **Step 5: Run the module tests, then the workspace gates**

```bash
cargo test -p logviewer-core settings
cargo test -p logviewer
cargo test --workspace
```

Expected: all PASS. (`bindings.ts` must be unchanged — `git diff -- ui/src/bindings.ts` empty.)

- [ ] **Step 6: Commit**

```bash
git add crates/logviewer-core/src/settings.rs src-tauri/src/ipc.rs
git commit -m "feat(core): shared settings/history — store reloads from disk on every access"
```

---

### Task 3: Release-gate check and bead closure

**Files:** none (verification only).

- [ ] **Step 1: Full workspace suite + clippy once**

```bash
cargo test --workspace && cargo clippy --workspace -- -D warnings
```

Expected: green.

- [ ] **Step 2: Close the bead**

`bd close <id>` with acceptance evidence (two-instance launch numbers, test names green).
