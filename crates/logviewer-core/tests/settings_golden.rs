//! Integration tests for the settings & history store (FUNCTIONAL_SPEC §15).
//!
//! Everything is hand-computed against the documented JSON file format in
//! `src/settings.rs`; no fixtures, only unique temp directories. Mirrors the
//! unit tests in the module itself so the public API surface is covered
//! end-to-end through `logviewer_core::settings::Store`.

use logviewer_core::settings::{Settings, Store};
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};

static SEQ: AtomicUsize = AtomicUsize::new(0);

fn temp_dir(tag: &str) -> PathBuf {
  let n = SEQ.fetch_add(1, Ordering::SeqCst);
  let dir = std::env::temp_dir().join(format!(
    "logviewer-settings-golden-{}-{}-{n}-{tag}",
    std::process::id(),
    std::time::SystemTime::now()
      .duration_since(std::time::UNIX_EPOCH)
      .map(|d| d.as_millis())
      .unwrap_or(0)
  ));
  std::fs::create_dir_all(&dir).unwrap();
  dir
}

#[test]
fn open_creates_missing_files_with_defaults() {
  let dir = temp_dir("create");
  let mut store = Store::open(&dir);
  assert_eq!(store.settings(), &Settings::default());
  assert!(store.history().is_empty());
  assert_eq!(
    std::fs::read_to_string(dir.join("settings.json")).unwrap(),
    "{\n  \"history_size\": 100,\n  \"last_open_dir\": \"\",\n  \"default_categories_enabled\": false,\n  \"column_widths\": \"\"\n}\n"
  );
  assert_eq!(std::fs::read_to_string(dir.join("history.json")).unwrap(), "[]\n");
}

#[test]
fn unknown_keys_survive_load_and_save() {
  let dir = temp_dir("unknown");
  std::fs::write(
    dir.join("settings.json"),
    "{\"custom_flag\": true, \"history_size\": 42}",
  )
  .unwrap();
  let mut store = Store::open(&dir);
  assert_eq!(store.settings().history_size, 42);
  store
    .set_settings(Settings {
      history_size: 50,
      last_open_dir: "/var/log".to_string(),
      default_categories_enabled: false,
      column_widths: None,
    })
    .unwrap();
  assert_eq!(
    std::fs::read_to_string(dir.join("settings.json")).unwrap(),
    "{\n  \"custom_flag\": true,\n  \"history_size\": 50,\n  \"last_open_dir\": \"/var/log\",\n  \"default_categories_enabled\": false,\n  \"column_widths\": \"\"\n}\n"
  );
}

#[test]
fn history_dedup_empty_and_cap() {
  let dir = temp_dir("history");
  let mut store = Store::open(&dir);
  store.push_history("a".to_string()).unwrap();
  store.push_history("a".to_string()).unwrap(); // consecutive dup: no-op
  store.push_history(String::new()).unwrap(); // empty: ignored
  store.push_history("b".to_string()).unwrap();
  store.push_history("c".to_string()).unwrap();
  store.push_history("d".to_string()).unwrap(); // cap 100 not hit yet at 3
  assert_eq!(store.history(), ["a", "b", "c", "d"]);

  store
    .set_settings(Settings {
      history_size: 2,
      last_open_dir: String::new(),
      default_categories_enabled: false,
      column_widths: None,
    })
    .unwrap();
  store.push_history("e".to_string()).unwrap();
  assert_eq!(store.history(), ["d", "e"]);
  assert_eq!(
    std::fs::read_to_string(dir.join("history.json")).unwrap(),
    "[\n  \"d\",\n  \"e\"\n]\n"
  );
}

#[test]
fn corrupt_json_falls_back_to_defaults() {
  let dir = temp_dir("corrupt");
  std::fs::write(dir.join("settings.json"), "{{{ nope").unwrap();
  std::fs::write(dir.join("history.json"), "[\"a\",").unwrap();
  let mut store = Store::open(&dir); // must not panic
  assert_eq!(store.settings(), &Settings::default());
  assert!(store.history().is_empty());
}

#[cfg(unix)]
#[test]
fn read_only_dir_write_fails_and_reads_report_disk_truth() {
  use std::os::unix::fs::PermissionsExt;

  let dir = temp_dir("readonly");
  let mut store = Store::open(&dir);
  store.push_history("kept".to_string()).unwrap();

  // A read-only directory still allows rewriting an existing file (that only
  // needs write permission on the file itself), so remove the data files to
  // force a directory-level failure.
  std::fs::remove_file(dir.join("history.json")).unwrap();
  std::fs::remove_file(dir.join("settings.json")).unwrap();
  std::fs::set_permissions(&dir, std::fs::Permissions::from_mode(0o555)).unwrap();
  let probe = dir.join(".probe");
  if std::fs::write(&probe, b"x").is_ok() {
    // Running with enough privilege to write anyway (e.g. root): skip.
    std::fs::remove_file(&probe).ok();
    std::fs::set_permissions(&dir, std::fs::Permissions::from_mode(0o755)).unwrap();
    return;
  }

  assert_eq!(store.push_history("denied".to_string()), Err(()));
  assert_eq!(
    store.set_settings(Settings {
      history_size: 7,
      last_open_dir: "/elsewhere".to_string(),
      default_categories_enabled: true,
      column_widths: None,
    }),
    Err(())
  );
  // Writes are refused (Err), but reads report disk truth: the missing files
  // degrade to defaults (§15). With the shared-file store (design
  // 2026-11-26-multi-instance) the backing files are the source of truth on
  // every access, so the pre-failure in-memory "kept" state is gone.
  assert_eq!(store.history(), Vec::<String>::new());
  assert_eq!(store.settings().history_size, 100);
  assert_eq!(store.settings().last_open_dir, "");
  std::fs::set_permissions(&dir, std::fs::Permissions::from_mode(0o755)).unwrap();
}
