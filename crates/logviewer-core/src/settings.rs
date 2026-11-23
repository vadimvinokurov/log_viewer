//! Settings and command-history persistence (FUNCTIONAL_SPEC §15).
//!
//! All user data lives in one directory (production resolves it to
//! `~/.logviewer/`; core code receives the path from the caller):
//!
//! - `settings.json` — a JSON object; known keys are `history_size` (integer,
//!   default 100), `last_open_dir` (string, default `""`) and
//!   `default_categories_enabled` (boolean, reserved). Missing keys fall back
//!   to their defaults; unknown keys are preserved verbatim across load+save.
//! - `history.json` — a JSON array of command strings.
//!
//! Both files are created with defaults on the first `open` if missing. Disk
//! and parse errors never abort the app: they degrade to defaults, and write
//! methods return `Err(())` while leaving in-memory state untouched.
//!
//! # JSON subset
//!
//! `serde` is deliberately absent (STACK.md lists it, but this module predates
//! the wiring and must not add dependencies). The module hand-rolls a minimal
//! JSON reader/writer; the accepted subset is:
//!
//! - Input must be valid UTF-8 (`fs::read_to_string` rejects anything else).
//! - `settings.json` must be a top-level object (`{ "`key`" : value, ... }`).
//!   Values of known keys are decoded from string / integer / `true`/`false`
//!   literals; a known key whose value has a different type falls back to that
//!   key's default. Values of unknown keys are captured as the exact source
//!   bytes of the value and re-emitted byte-for-byte on save.
//! - `history.json` must be a top-level array of strings. Entries are not
//!   deduplicated or validated beyond being strings; the array is truncated to
//!   `history_size` most-recent entries on load.
//! - Strings use the standard JSON escapes (`\"`, `\\`, `\/`, `\b`, `\f`,
//!   `\n`, `\r`, `\t`, `\uXXXX` including surrogate pairs). A lone surrogate
//!   is a parse error.
//! - No trailing commas; whitespace is allowed between tokens. Numbers are
//!   consumed but only re-validated when a known key needs an integer.
//! - Anything outside the subset (nested containers as known values, other
//!   top-level shapes, truncation, stray bytes) is treated as corrupt data:
//!   the file reads as "missing" and defaults take over at the next save.
//! - Serializer output is human-readable: two-space indent, one entry per
//!   line, trailing newline. The parser accepts any valid subset file.

use std::path::{Path, PathBuf};

const SETTINGS_FILE: &str = "settings.json";
const HISTORY_FILE: &str = "history.json";
const DEFAULT_HISTORY_SIZE: u32 = 100;
/// Nesting budget for `skip_value`; deeper input counts as corrupt. Keeps a
/// hostile settings file from blowing the stack.
const MAX_DEPTH: u32 = 32;

/// The settings the application reads and writes (`settings.json`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Settings {
  /// Maximum number of entries kept in the command history. Default 100.
  pub history_size: u32,
  /// Directory proposed by the next Open dialog. Default empty.
  pub last_open_dir: String,
  /// Reserved placeholder (§15); not yet consulted by any feature.
  pub default_categories_enabled: bool,
}

impl Default for Settings {
  fn default() -> Self {
    Settings {
      history_size: DEFAULT_HISTORY_SIZE,
      last_open_dir: String::new(),
      default_categories_enabled: false,
    }
  }
}

/// Persistent store over one directory holding `settings.json` and
/// `history.json`. Created with [`Store::open`]; mutations go through
/// [`Store::set_settings`] and [`Store::push_history`], each of which writes
/// the corresponding file before committing the in-memory state.
pub struct Store {
  dir: PathBuf,
  settings: Settings,
  history: Vec<String>,
  /// Ordered `(key, raw value text)` entries from the last successful
  /// `settings.json` parse. Known keys are re-serialized canonically on save;
  /// unknown entries are re-emitted verbatim. Empty when the file was absent
  /// or corrupt (the next save writes a file with known keys only).
  raw: Vec<(String, String)>,
}

impl Store {
  /// Load-or-create both files in `dir`. Missing directory and missing files
  /// are created with defaults; an unreadable or corrupt file degrades to
  /// defaults for this run (and is only rewritten by the next save). This
  /// never fails and never panics - per §15 disk errors must not abort the
  /// app - so it returns `Store` directly rather than a `Result`.
  pub fn open(dir: &Path) -> Store {
    let _ = std::fs::create_dir_all(dir);

    let settings_path = dir.join(SETTINGS_FILE);
    let (settings, raw) = match std::fs::read_to_string(&settings_path) {
      Ok(text) => match parse_settings(&text) {
        Some(entries) => {
          let s = settings_from_entries(&entries);
          (s, entries)
        }
        None => (Settings::default(), Vec::new()),
      },
      Err(err) => {
        // Only touch the file when it is genuinely absent; an unreadable
        // existing file may still hold the user's data in other tools.
        if err.kind() == std::io::ErrorKind::NotFound {
          let _ = std::fs::write(&settings_path, serialize_settings(&[], &Settings::default()));
        }
        (Settings::default(), Vec::new())
      }
    };

    let history_path = dir.join(HISTORY_FILE);
    let mut history = match std::fs::read_to_string(&history_path) {
      Ok(text) => parse_history(&text).unwrap_or_default(),
      Err(err) => {
        if err.kind() == std::io::ErrorKind::NotFound {
          let _ = std::fs::write(&history_path, serialize_history(&[]));
        }
        Vec::new()
      }
    };
    // Defensive cap: a hand-edited file may carry more entries than the
    // configured limit; keep the most recent ones (same rule as push).
    if history.len() > settings.history_size as usize {
      history.drain(..history.len() - settings.history_size as usize);
    }

    Store {
      dir: dir.to_path_buf(),
      settings,
      history,
      raw,
    }
  }

  /// Current settings.
  pub fn settings(&self) -> &Settings {
    &self.settings
  }

  /// Current command history, oldest entry first, most recent last.
  pub fn history(&self) -> &[String] {
    &self.history
  }

  /// Replace the settings and persist them. Unknown keys seen at load are
  /// preserved verbatim; known keys missing from the loaded file are now
  /// written with their current values. On disk failure returns `Err(())`
  /// and leaves the in-memory state unchanged.
  #[allow(clippy::result_unit_err)] // prescribed store API: Err(()) is the generic disk failure
  pub fn set_settings(&mut self, s: Settings) -> Result<(), ()> {
    let new_raw = raw_with_settings(&self.raw, &s);
    let text = serialize_settings(&new_raw, &s);
    self.write_file(SETTINGS_FILE, &text)?;
    self.raw = new_raw;
    self.settings = s;
    Ok(())
  }

  /// Append a command to the history and persist the list. Empty commands
  /// are ignored; a command equal to the most recent one is a no-op
  /// (consecutive duplicates are not stored); the list is trimmed to
  /// `history_size` entries, keeping the most recent. On disk failure
  /// returns `Err(())` and leaves the in-memory history unchanged.
  #[allow(clippy::result_unit_err)] // prescribed store API: Err(()) is the generic disk failure
  pub fn push_history(&mut self, cmd: String) -> Result<(), ()> {
    if cmd.is_empty() {
      return Ok(());
    }
    if self.history.last().is_some_and(|last| *last == cmd) {
      return Ok(());
    }

    let mut next = self.history.clone();
    next.push(cmd);
    let cap = self.settings.history_size as usize;
    if next.len() > cap {
      next.drain(..next.len() - cap);
    }

    let text = serialize_history(&next);
    self.write_file(HISTORY_FILE, &text)?;
    self.history = next;
    Ok(())
  }

  /// Write one data file, creating the directory lazily if it vanished.
  fn write_file(&self, name: &str, text: &str) -> Result<(), ()> {
    let _ = std::fs::create_dir_all(&self.dir);
    std::fs::write(self.dir.join(name), text).map_err(|_| ())
  }
}

/// The three key names this module owns, in canonical (write-out) order.
const KNOWN_KEYS: [&str; 3] = [
  "history_size",
  "last_open_dir",
  "default_categories_enabled",
];

/// Apply the parsed `settings.json` entries: known keys decode, unknown keys
/// and keys with values of the wrong shape are ignored (they keep their raw
/// text for save; decode failures fall back to defaults).
fn settings_from_entries(entries: &[(String, String)]) -> Settings {
  let mut s = Settings::default();
  for (key, raw) in entries {
    match key.as_str() {
      "history_size" => {
        if let Some(v) = parse_u32(raw) {
          s.history_size = v;
        }
      }
      "last_open_dir" => {
        if let Some(v) = decode_string(raw) {
          s.last_open_dir = v;
        }
      }
      "default_categories_enabled" => {
        if let Some(v) = parse_bool(raw) {
          s.default_categories_enabled = v;
        }
      }
      _ => {}
    }
  }
  s
}

/// Produce the entry list for the next save: known keys carry their canonical
/// serialization (in the order they appear in the loaded file, missing ones
/// appended at the end), unknown keys keep their verbatim raw text. This is
/// also the serializer for the create-defaults case: `raw = &[]` yields a
/// file with all three known keys.
fn raw_with_settings(raw: &[(String, String)], s: &Settings) -> Vec<(String, String)> {
  let mut next: Vec<(String, String)> = Vec::with_capacity(raw.len() + KNOWN_KEYS.len());
  let mut seen = [false; 3];
  for (key, old_value) in raw {
    if let Some(slot) = KNOWN_KEYS.iter().position(|k| *k == key.as_str()) {
      seen[slot] = true;
      next.push((key.clone(), serialize_known(slot, s)));
    } else {
      next.push((key.clone(), old_value.clone()));
    }
  }
  for (slot, key) in KNOWN_KEYS.iter().enumerate() {
    if !seen[slot] {
      next.push(((*key).to_string(), serialize_known(slot, s)));
    }
  }
  next
}

/// Canonical serialization of a known key's value under `s`.
fn serialize_known(slot: usize, s: &Settings) -> String {
  match slot {
    0 => s.history_size.to_string(),
    1 => encode_string(&s.last_open_dir),
    2 => s.default_categories_enabled.to_string(),
    _ => unreachable!(),
  }
}

/// Render `settings.json`: known keys in file order (then missing ones),
/// unknown keys verbatim, two-space indent, trailing newline.
fn serialize_settings(raw: &[(String, String)], s: &Settings) -> String {
  let next = raw_with_settings(raw, s);
  let mut out = String::from("{\n");
  for (i, (key, value)) in next.iter().enumerate() {
    out.push_str("  ");
    out.push_str(&encode_string(key));
    out.push_str(": ");
    out.push_str(value);
    if i + 1 < next.len() {
      out.push(',');
    }
    out.push('\n');
  }
  out.push_str("}\n");
  out
}

/// Render `history.json`: one string per line, two-space indent.
fn serialize_history(history: &[String]) -> String {
  if history.is_empty() {
    return "[]\n".to_string();
  }
  let mut out = String::from("[\n");
  for (i, cmd) in history.iter().enumerate() {
    out.push_str("  ");
    out.push_str(&encode_string(cmd));
    if i + 1 < history.len() {
      out.push(',');
    }
    out.push('\n');
  }
  out.push_str("]\n");
  out
}

/// Encode a string as a JSON string literal (with surrounding quotes).
fn encode_string(s: &str) -> String {
  let mut out = String::with_capacity(s.len() + 2);
  out.push('"');
  for c in s.chars() {
    match c {
      '"' => out.push_str("\\\""),
      '\\' => out.push_str("\\\\"),
      '\n' => out.push_str("\\n"),
      '\r' => out.push_str("\\r"),
      '\t' => out.push_str("\\t"),
      '\u{08}' => out.push_str("\\b"),
      '\u{0C}' => out.push_str("\\f"),
      c if (c as u32) < 0x20 || c as u32 == 0x7F => {
        out.push_str(&format!("\\u{:04x}", c as u32));
      }
      c => out.push(c),
    }
  }
  out.push('"');
  out
}

/// Minimal decoder for the exact raw text of one value.
fn parse_u32(raw: &str) -> Option<u32> {
  raw.trim().parse().ok()
}

fn parse_bool(raw: &str) -> Option<bool> {
  match raw.trim() {
    "true" => Some(true),
    "false" => Some(false),
    _ => None,
  }
}

/// Decode raw text that must decode to a string.
fn decode_string(raw: &str) -> Option<String> {
  let mut p = P::new(raw.as_bytes());
  p.ws();
  let s = p.string()?;
  p.ws();
  if p.i != raw.len() {
    return None;
  }
  Some(s)
}

// ---------------------------------------------------------------------------
// Hand-rolled JSON reader. See the module docs for the accepted subset.
// ---------------------------------------------------------------------------

struct P<'a> {
  b: &'a [u8],
  i: usize,
}

impl<'a> P<'a> {
  fn new(b: &'a [u8]) -> P<'a> {
    P { b, i: 0 }
  }

  fn peek(&self) -> Option<u8> {
    self.b.get(self.i).copied()
  }

  fn ws(&mut self) {
    while matches!(self.peek(), Some(b' ' | b'\t' | b'\n' | b'\r')) {
      self.i += 1;
    }
  }

  fn eat(&mut self, byte: u8) -> bool {
    if self.peek() == Some(byte) {
      self.i += 1;
      true
    } else {
      false
    }
  }

  fn literal(&mut self, word: &str) -> bool {
    if self.b[self.i..].starts_with(word.as_bytes()) {
      self.i += word.len();
      true
    } else {
      false
    }
  }

  /// Parse a JSON string literal (opening quote at the cursor).
  fn string(&mut self) -> Option<String> {
    if !self.eat(b'"') {
      return None;
    }
    let mut out: Vec<u8> = Vec::new();
    loop {
      let c = self.peek()?;
      self.i += 1;
      match c {
        b'"' => break,
        b'\\' => {
          let e = self.peek()?;
          self.i += 1;
          match e {
            b'"' => out.push(b'"'),
            b'\\' => out.push(b'\\'),
            b'/' => out.push(b'/'),
            b'b' => out.push(0x08),
            b'f' => out.push(0x0C),
            b'n' => out.push(b'\n'),
            b'r' => out.push(b'\r'),
            b't' => out.push(b'\t'),
            b'u' => {
              let hi = self.hex4()?;
              let ch = if (0xD800..=0xDBFF).contains(&hi) {
                // Surrogate pair requires an immediately following \uDC00-\uDFFF.
                if self.eat(b'\\') && self.eat(b'u') {
                  let lo = self.hex4()?;
                  if !(0xDC00..=0xDFFF).contains(&lo) {
                    return None;
                  }
                  let code = 0x1_0000 + ((u32::from(hi) - 0xD800) << 10) + (u32::from(lo) - 0xDC00);
                  char::from_u32(code)?
                } else {
                  return None;
                }
              } else {
                char::from_u32(u32::from(hi))?
              };
              let mut buf = [0u8; 4];
              out.extend_from_slice(ch.encode_utf8(&mut buf).as_bytes());
            }
            _ => return None,
          }
        }
        c if c < 0x20 => return None, // raw control characters are invalid JSON
        c => out.push(c),
      }
    }
    String::from_utf8(out).ok()
  }

  fn hex4(&mut self) -> Option<u16> {
    if self.i + 4 > self.b.len() {
      return None;
    }
    let mut v: u16 = 0;
    for _ in 0..4 {
      let c = self.b[self.i];
      let d = match c {
        b'0'..=b'9' => c - b'0',
        b'a'..=b'f' => c - b'a' + 10,
        b'A'..=b'F' => c - b'A' + 10,
        _ => return None,
      };
      v = v.checked_mul(16)?.checked_add(u16::from(d))?;
      self.i += 1;
    }
    Some(v)
  }

  /// Consume one JSON value of any shape and return its exact source text.
  /// Used for unknown key preservation and for skipping. Values deeper than
  /// [`MAX_DEPTH`] are rejected as corrupt.
  fn value_text(&mut self, depth: u32) -> Option<String> {
    if depth > MAX_DEPTH {
      return None;
    }
    let start = self.i;
    match self.peek()? {
      b'"' => self.string().map(|_| ())?,
      b't' => self.literal("true").then_some(())?,
      b'f' => self.literal("false").then_some(())?,
      b'n' => self.literal("null").then_some(())?,
      b'-' | b'0'..=b'9' => self.number()?,
      b'[' => {
        self.i += 1;
        self.ws();
        if !self.eat(b']') {
          loop {
            self.ws();
            self.value_text(depth + 1)?;
            self.ws();
            if self.eat(b',') {
              continue;
            }
            if self.eat(b']') {
              break;
            }
            return None;
          }
        }
      }
      b'{' => {
        self.i += 1;
        self.ws();
        if !self.eat(b'}') {
          loop {
            self.ws();
            self.string()?;
            self.ws();
            if !self.eat(b':') {
              return None;
            }
            self.ws();
            self.value_text(depth + 1)?;
            self.ws();
            if self.eat(b',') {
              continue;
            }
            if self.eat(b'}') {
              break;
            }
            return None;
          }
        }
      }
      _ => return None,
    }
    // The span consumed here is exactly the value; it is plain source text, so
    // slicing it back out of &str cannot split a UTF-8 sequence.
    Some(String::from_utf8_lossy(&self.b[start..self.i]).into_owned())
  }

  /// Consume a JSON number (`[-]digits[.digits][eE[+-]digits]`).
  fn number(&mut self) -> Option<()> {
    self.eat(b'-');
    if !self.eat_any_digits() {
      return None;
    }
    if self.eat(b'.') && !self.eat_any_digits() {
      return None;
    }
    if self.peek() == Some(b'e') || self.peek() == Some(b'E') {
      self.i += 1;
      if self.peek() == Some(b'+') || self.peek() == Some(b'-') {
        self.i += 1;
      }
      if !self.eat_any_digits() {
        return None;
      }
    }
    Some(())
  }

  fn eat_any_digits(&mut self) -> bool {
    let mut any = false;
    while matches!(self.peek(), Some(b'0'..=b'9')) {
      self.i += 1;
      any = true;
    }
    any
  }
}

/// Parse the contents of `settings.json` into ordered `(key, raw value)`
/// entries, preserving file order and unknown-value bytes.
fn parse_settings(text: &str) -> Option<Vec<(String, String)>> {
  let mut p = P::new(text.as_bytes());
  p.ws();
  if !p.eat(b'{') {
    return None;
  }
  let mut entries = Vec::new();
  p.ws();
  if !p.eat(b'}') {
    loop {
      p.ws();
      let key = p.string()?;
      p.ws();
      if !p.eat(b':') {
        return None;
      }
      p.ws();
      let value = p.value_text(0)?;
      entries.push((key, value));
      p.ws();
      if p.eat(b',') {
        continue;
      }
      if p.eat(b'}') {
        break;
      }
      return None;
    }
  }
  p.ws();
  if p.i != text.len() {
    return None;
  }
  Some(entries)
}

/// Parse the contents of `history.json` as an array of strings.
fn parse_history(text: &str) -> Option<Vec<String>> {
  let mut p = P::new(text.as_bytes());
  p.ws();
  if !p.eat(b'[') {
    return None;
  }
  let mut out = Vec::new();
  p.ws();
  if !p.eat(b']') {
    loop {
      p.ws();
      out.push(p.string()?);
      p.ws();
      if p.eat(b',') {
        continue;
      }
      if p.eat(b']') {
        break;
      }
      return None;
    }
  }
  p.ws();
  if p.i != text.len() {
    return None;
  }
  Some(out)
}

// ---------------------------------------------------------------------------
// Tests. Expectations are hand-computed from the serializer contract in the
// module docs; temp directories are unique per test, no fixtures needed.
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
  use super::*;
  use std::sync::atomic::{AtomicUsize, Ordering};

  static SEQ: AtomicUsize = AtomicUsize::new(0);

  fn temp_dir(tag: &str) -> PathBuf {
    let n = SEQ.fetch_add(1, Ordering::SeqCst);
    let dir = std::env::temp_dir().join(format!(
      "logviewer-settings-{}-{}-{n}-{tag}",
      std::process::id(),
      std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or(0)
    ));
    std::fs::create_dir_all(&dir).unwrap();
    dir
  }

  fn read(dir: &Path, name: &str) -> String {
    std::fs::read_to_string(dir.join(name)).unwrap()
  }

  fn write(dir: &Path, name: &str, text: &str) {
    std::fs::write(dir.join(name), text).unwrap();
  }

  #[test]
  fn open_creates_missing_dir_and_files_with_defaults() {
    let dir = temp_dir("create");
    let store = Store::open(&dir);
    assert_eq!(store.settings(), &Settings::default());
    assert!(store.history().is_empty());
    assert_eq!(
      read(&dir, SETTINGS_FILE),
      "{\n  \"history_size\": 100,\n  \"last_open_dir\": \"\",\n  \"default_categories_enabled\": false\n}\n"
    );
    assert_eq!(read(&dir, HISTORY_FILE), "[]\n");
  }

  #[test]
  fn missing_keys_fall_back_to_defaults_and_are_written_on_save() {
    let dir = temp_dir("missing_keys");
    write(&dir, SETTINGS_FILE, "{\"last_open_dir\": \"C:\\\\logs\"}");
    let mut store = Store::open(&dir);
    assert_eq!(store.settings().last_open_dir, "C:\\logs");
    assert_eq!(store.settings().history_size, 100);
    assert!(!store.settings().default_categories_enabled);
    // Save applies the current in-memory settings; last_open_dir keeps its
    // position, the keys missing from the file are appended canonically.
    let s = store.settings().clone();
    store.set_settings(s).unwrap();
    assert_eq!(
      read(&dir, SETTINGS_FILE),
      "{\n  \"last_open_dir\": \"C:\\\\logs\",\n  \"history_size\": 100,\n  \"default_categories_enabled\": false\n}\n"
    );
  }

  #[test]
  fn unknown_keys_preserved_verbatim_across_roundtrip() {
    let dir = temp_dir("unknown");
    write(
      &dir,
      SETTINGS_FILE,
      "{\"custom_flag\": true,  \"nested\": {\"a\": [1, 2]}, \"history_size\": 42}",
    );
    let store = Store::open(&dir);
    assert_eq!(store.settings().history_size, 42);
    let mut store = store;
    store
      .set_settings(Settings {
        history_size: 50,
        last_open_dir: "/var/log".to_string(),
        default_categories_enabled: false,
      })
      .unwrap();
    // Order comes from the file: unknown keys stay put, history_size is
    // rewritten in place, keys missing from the file are appended.
    assert_eq!(
      read(&dir, SETTINGS_FILE),
      "{\n  \"custom_flag\": true,\n  \"nested\": {\"a\": [1, 2]},\n  \"history_size\": 50,\n  \"last_open_dir\": \"/var/log\",\n  \"default_categories_enabled\": false\n}\n"
    );
    let store = Store::open(&dir);
    assert_eq!(store.settings().history_size, 50);
    assert_eq!(store.settings().last_open_dir, "/var/log");
  }

  #[test]
  fn known_key_with_wrong_value_shape_falls_back_to_default() {
    let dir = temp_dir("wrong_shape");
    write(
      &dir,
      SETTINGS_FILE,
      "{\"history_size\": \"many\", \"last_open_dir\": null}",
    );
    let store = Store::open(&dir);
    assert_eq!(store.settings().history_size, 100);
    assert_eq!(store.settings().last_open_dir, "");
  }

  #[test]
  fn push_history_dedups_consecutive_and_skips_empty() {
    let dir = temp_dir("dedup");
    let mut store = Store::open(&dir);
    store.push_history("open a.log".to_string()).unwrap();
    store.push_history("open a.log".to_string()).unwrap(); // consecutive dup: no-op
    store.push_history(String::new()).unwrap(); // empty: ignored
    store.push_history("filter err".to_string()).unwrap();
    store.push_history("open a.log".to_string()).unwrap(); // non-consecutive repeat: kept
    assert_eq!(
      store.history(),
      ["open a.log", "filter err", "open a.log"]
    );
    assert_eq!(
      read(&dir, HISTORY_FILE),
      "[\n  \"open a.log\",\n  \"filter err\",\n  \"open a.log\"\n]\n"
    );
  }

  #[test]
  fn push_history_trims_to_history_size() {
    let dir = temp_dir("trim");
    let mut store = Store::open(&dir);
    store
      .set_settings(Settings {
        history_size: 2,
        last_open_dir: String::new(),
        default_categories_enabled: false,
      })
      .unwrap();
    store.push_history("c1".to_string()).unwrap();
    store.push_history("c2".to_string()).unwrap();
    store.push_history("c3".to_string()).unwrap();
    assert_eq!(store.history(), ["c2", "c3"]);
    assert_eq!(read(&dir, HISTORY_FILE), "[\n  \"c2\",\n  \"c3\"\n]\n");
  }

  #[test]
  fn corrupt_json_falls_back_to_defaults_without_writing() {
    let dir = temp_dir("corrupt");
    write(&dir, SETTINGS_FILE, "{{{ nope");
    write(&dir, HISTORY_FILE, "[\"a\",");
    let store = Store::open(&dir);
    assert_eq!(store.settings(), &Settings::default());
    assert!(store.history().is_empty());
    // Corrupt means "unreadable", not "missing": open must not destroy the
    // file; the defaults are written only by the next save.
    assert_eq!(read(&dir, SETTINGS_FILE), "{{{ nope");
    assert_eq!(read(&dir, HISTORY_FILE), "[\"a\",");
    let mut store = store;
    store.push_history("cmd".to_string()).unwrap();
    assert_eq!(read(&dir, HISTORY_FILE), "[\n  \"cmd\"\n]\n");
  }

  #[test]
  fn string_escapes_roundtrip() {
    let dir = temp_dir("escapes");
    let mut store = Store::open(&dir);
    let cmd = "open \"new\\line\"\t\u{7}x /y".to_string();
    store.push_history(cmd.clone()).unwrap();
    assert!(read(&dir, HISTORY_FILE).contains("\\u0007"));
    let store = Store::open(&dir);
    assert_eq!(store.history(), [cmd.as_str()]);
  }

  #[test]
  fn corrupt_history_loads_as_empty_but_settings_survive() {
    let dir = temp_dir("corrupt_hist");
    write(&dir, SETTINGS_FILE, "{\"history_size\": 7}");
    write(&dir, HISTORY_FILE, "not json");
    let store = Store::open(&dir);
    assert_eq!(store.settings().history_size, 7);
    assert!(store.history().is_empty());
  }

  #[cfg(unix)]
  #[test]
  fn read_only_dir_yields_err_and_keeps_memory_state() {
    use std::os::unix::fs::PermissionsExt;

    let dir = temp_dir("readonly");
    let mut store = Store::open(&dir);
    store.push_history("kept".to_string()).unwrap();

    // A read-only directory still allows rewriting an existing file (that
    // only needs write permission on the file itself), so the realistic
    // failure case is writing a file that is missing from the now read-only
    // directory.
    std::fs::remove_file(dir.join(HISTORY_FILE)).unwrap();
    std::fs::remove_file(dir.join(SETTINGS_FILE)).unwrap();
    std::fs::set_permissions(&dir, std::fs::Permissions::from_mode(0o555)).unwrap();
    let probe = dir.join(".probe");
    if std::fs::write(&probe, b"x").is_ok() {
      // Running with enough privilege to write anyway (e.g. root): skip.
      std::fs::remove_file(&probe).ok();
      std::fs::set_permissions(&dir, std::fs::Permissions::from_mode(0o755)).unwrap();
      return;
    }

    assert_eq!(store.push_history("denied".to_string()), Err(()));
    assert_eq!(store.history(), ["kept"]);
    let changed = Settings {
      history_size: 7,
      last_open_dir: "/elsewhere".to_string(),
      default_categories_enabled: true,
    };
    assert_eq!(store.set_settings(changed), Err(()));
    assert_eq!(store.settings().history_size, 100);
    assert_eq!(store.settings().last_open_dir, "");

    std::fs::set_permissions(&dir, std::fs::Permissions::from_mode(0o755)).unwrap();
  }

  #[test]
  fn history_is_capped_on_load() {
    let dir = temp_dir("load_cap");
    write(&dir, SETTINGS_FILE, "{\"history_size\": 2}");
    write(&dir, HISTORY_FILE, "[\"a\", \"b\", \"c\"]");
    let store = Store::open(&dir);
    assert_eq!(store.history(), ["b", "c"]);
  }
}
