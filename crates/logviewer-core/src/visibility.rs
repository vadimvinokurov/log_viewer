//! Combined row-visibility engine (FUNCTIONAL_SPEC §7, §11, §12).
//!
//! The engine owns the four independent visibility mechanisms of §7 and
//! answers two questions over a loaded `FileModel`:
//!
//! - `visible_lines`: the 1-based line numbers passing the combined rule
//!   `visible = (text filters empty OR matches at least one ACTIVE filter)
//!   AND level enabled AND category enabled OR pinned`. A pin (§12) bypasses
//!   filters, levels and categories.
//! - `level_counts_excluding_levels`: per-level counters for the level
//!   buttons (§11). They IGNORE the level toggles: for each level they count
//!   the rows that would become visible if that level were enabled, i.e. the
//!   rows passing the text filters and the category rule (pins included).
//!
//! Categories are addressed by FULL path strings (`app/main/db`). The
//! enabled set is a whitelist: `categories_enabled` holds the enabled paths,
//! everything else is disabled. // spec interpretation: rows carry only
//! their exact category path, so the engine treats a category as disabled
//! when its exact path OR ANY ancestor prefix (`/`-separated) is absent from
//! the enabled set — §10 requires that disabling a node hides its children.
//!
//! spec interpretation (default state): a fresh `Visibility` enables all six
//! levels (level toggles are user opt-out, §11) and starts with an empty
//! category whitelist, i.e. every category is disabled; the UI populates the
//! set from `FileModel::categories` and the category tree nodes when a file
//! is loaded (§2.1 keeps category enablement as per-name state). The policy
//! for categories that appear after a reload is a UI concern (§2.1), not
//! part of this engine.

use std::collections::BTreeSet;

use crate::matching::Matcher;
use crate::parser::{self, Level};
use crate::workspace::{FileModel, LEVELS};

/// One user criterion with an on/off switch (filters, pins).
pub struct Criterion {
  pub matcher: Matcher,
  pub enabled: bool,
}

/// Combined visibility state over any loaded file (§7).
pub struct Visibility {
  /// Text filters; they combine with OR (§5, §7).
  filters: Vec<Criterion>,
  /// Pins; an active pin makes its rows visible unconditionally (§12).
  pins: Vec<Criterion>,
  /// Toggle per level, indexed in `LEVELS` order.
  levels_enabled: [bool; 6],
  /// Whitelist of enabled category paths (§7, §10): an absent path — or an
  /// absent ancestor prefix of the row's path — means "disabled".
  categories_enabled: BTreeSet<String>,
}

impl Default for Visibility {
  fn default() -> Self {
    Self::new()
  }
}

/// Index of `level` in `LEVELS` order (mirrors `FileModel`'s rollups).
fn level_index(level: Level) -> usize {
  LEVELS
    .iter()
    .position(|&l| l == level)
    .expect("LEVELS covers all six levels")
}

impl Visibility {
  pub fn new() -> Visibility {
    Visibility {
      filters: Vec::new(),
      pins: Vec::new(),
      levels_enabled: [true; 6],
      categories_enabled: BTreeSet::new(),
    }
  }

  /// Add a text filter, enabled (§10.1: a new filter starts checked).
  pub fn add_filter(&mut self, matcher: Matcher) -> &mut Self {
    self.filters.push(Criterion { matcher, enabled: true });
    self
  }

  /// Remove the filter at `idx` (panics when out of range, like `Vec::remove`).
  pub fn remove_filter(&mut self, idx: usize) -> &mut Self {
    self.filters.remove(idx);
    self
  }

  /// Add a pin, enabled (§10.1: a new pin starts checked).
  pub fn add_pin(&mut self, matcher: Matcher) -> &mut Self {
    self.pins.push(Criterion { matcher, enabled: true });
    self
  }

  /// Remove the pin at `idx` (panics when out of range, like `Vec::remove`).
  pub fn remove_pin(&mut self, idx: usize) -> &mut Self {
    self.pins.remove(idx);
    self
  }

  pub fn set_level_enabled(&mut self, level: Level, on: bool) -> &mut Self {
    self.levels_enabled[level_index(level)] = on;
    self
  }

  pub fn set_category_enabled(&mut self, path: &str, on: bool) -> &mut Self {
    if on {
      self.categories_enabled.insert(path.to_owned());
    } else {
      self.categories_enabled.remove(path);
    }
    self
  }

  /// Currently enabled category paths (exact strings as set by the caller).
  pub fn categories_enabled(&self) -> &BTreeSet<String> {
    &self.categories_enabled
  }

  pub fn set_filter_enabled(&mut self, idx: usize, on: bool) -> &mut Self {
    self.filters[idx].enabled = on;
    self
  }

  pub fn set_pin_enabled(&mut self, idx: usize, on: bool) -> &mut Self {
    self.pins[idx].enabled = on;
    self
  }

  /// Sorted (ascending) 1-based line numbers of all visible rows.
  pub fn visible_lines(&self, model: &FileModel) -> Vec<u32> {
    let mut lines = Vec::new();
    self.visit_pre_level(model, &mut |row, pinned| {
      // The full §7 rule: visible = (filters OR none) AND level AND category
      // OR pinned — the pin bypasses the level toggle as well, so the level
      // check only gates the non-pinned branch.
      if pinned || self.levels_enabled[level_index(row.level)] {
        lines.push(row.line_no);
      }
    });
    lines
  }

  /// For each level (in `LEVELS` order): rows that would be visible IF that
  /// level were enabled — text filters and categories applied, the level
  /// toggles ignored (§11).
  pub fn level_counts_excluding_levels(&self, model: &FileModel) -> [u64; 6] {
    let mut counts = [0_u64; 6];
    self.visit_pre_level(model, &mut |row, _pinned| counts[level_index(row.level)] += 1);
    counts
  }

  /// Visit every row that passes the combined rule of §7 WITH the level
  /// toggles ignored: `pinned OR (filters OR none) AND category enabled`.
  /// The callback reports whether the row matched through the pin clause.
  fn visit_pre_level<'a>(
    &self,
    model: &'a FileModel,
    sink: &mut dyn FnMut(&'a parser::Row, bool),
  ) {
    let count = model.line_count() as usize;
    for i in 0..count {
      let Some(row) = model.row(i) else { break };
      let text = String::from_utf8_lossy(&row.raw);
      let pinned = self.pinned(&text, row.line_no);
      if pinned
        || (self.matches_any_filter(&text, row.line_no) && self.category_allowed(&row.category))
      {
        sink(row, pinned);
      }
    }
  }

  /// §7, §12: an ACTIVE pin makes its row visible unconditionally.
  fn pinned(&self, text: &str, line_no: u32) -> bool {
    self.pins.iter().any(|c| c.enabled && c.matcher.matches(text, line_no))
  }

  /// §7: a row passes when there is no active filter at all; otherwise at
  /// least one active filter must match (OR).
  fn matches_any_filter(&self, text: &str, line_no: u32) -> bool {
    !self.filters.iter().any(|c| c.enabled) || self.filters.iter().any(|c| c.enabled && c.matcher.matches(text, line_no))
  }

  /// §10 through the engine's path lens: the row's exact category path and
  /// every `/`-separated ancestor prefix must be in the enabled whitelist
  /// (disabling a node hides its children).
  fn category_allowed(&self, path: &str) -> bool {
    let enabled = &self.categories_enabled;
    let mut prefix = path;
    loop {
      if !enabled.contains(prefix) {
        return false;
      }
      match prefix.rfind('/') {
        Some(i) => prefix = &prefix[..i],
        None => return true,
      }
    }
  }
}

#[cfg(test)]
mod tests {
  use super::*;

  // ---------------------------------------------------------------- helpers

  /// The mixed log, format A (KSIVA); line numbers are 1-based:
  ///
  /// | line | category      | level   | raw / message keywords      |
  /// |------|---------------|---------|-----------------------------|
  /// | 1    | app/main      | Error   | "LOG_ERR", "database failed"|
  /// | 2    | app/main      | Msg     | "started fine"              |
  /// | 3    | app/net       | Error   | "LOG_ERR", "timeout"        |
  /// | 4    | app           | Warning | "LOG_WRN", "disk"           |
  /// | 5    | uncategorized | Msg     | "standalone"                |
  /// | 6    | app/net       | Debug   | "retry"                     |
  const MIX: &[u8] = concat!(
    "2024-01-01T10:00:00.000 app/main LOG_ERR database failed\n",
    "2024-01-01T10:00:01.000 app/main LOG_MSG started fine\n",
    "2024-01-01T10:00:02.000 app/net LOG_ERR timeout\n",
    "2024-01-01T10:00:03.000 app LOG_WRN disk almost full\n",
    "2024-01-01T10:00:04.000 standalone\n",
    "2024-01-01T10:00:05.000 app/net LOG_DBG retry done\n",
  )
  .as_bytes();

  fn model_from(name: &str, data: &[u8]) -> FileModel {
    // The process id keeps concurrent cargo runs (other agents) from
    // truncating this file under our mmap (SIGBUS). The one-write-per-path
    // guard keeps parallel test THREADS of this process from truncating it
    // while another thread is reading the mapped file.
    static PREPARED: std::sync::LazyLock<std::sync::Mutex<std::collections::HashSet<String>>> =
      std::sync::LazyLock::new(|| std::sync::Mutex::new(std::collections::HashSet::new()));
    let path = std::env::temp_dir().join(format!("{name}-{}.log", std::process::id()));
    let key = path.to_string_lossy().into_owned();
    let mut prepared = PREPARED.lock().unwrap();
    if std::fs::read(&path).map_or(true, |existing| existing != data) {
      std::fs::write(&path, data).unwrap();
    }
    prepared.insert(key);
    FileModel::load_path(&path).unwrap().0
  }

  fn mixed_model() -> FileModel {
    model_from("lv_visibility_mix", MIX)
  }

  /// Fresh engine with every category of `model` enabled — the §10 "All"
  /// checkbox state the UI reproduces on load. (The engine itself starts
  /// from an empty whitelist, see the module docs.)
  fn all_categories(model: &FileModel) -> Visibility {
    let mut vis = Visibility::new();
    for (path, _) in model.categories() {
      vis.set_category_enabled(path, true);
    }
    vis
  }

  // ------------------------------------------------------------------ tests

  #[test]
  fn no_filters_and_all_enabled_shows_everything() {
    let model = mixed_model();
    // Default levels are all on; "All" categories checked; no filters.
    assert_eq!(all_categories(&model).visible_lines(&model), vec![1, 2, 3, 4, 5, 6]);
  }

  #[test]
  fn active_filters_combine_with_or() {
    let model = mixed_model();
    let mut vis = all_categories(&model);
    vis.add_filter(Matcher::plain("failed")); // line 1 only
    assert_eq!(vis.visible_lines(&model), vec![1]);
    vis.add_filter(Matcher::plain("started")); // line 2 only
    assert_eq!(vis.visible_lines(&model), vec![1, 2]);
    vis.add_filter(Matcher::plain("retry")); // line 6 only
    assert_eq!(vis.visible_lines(&model), vec![1, 2, 6]);
  }

  #[test]
  fn disabled_filters_do_not_narrow() {
    let model = mixed_model();
    let mut vis = all_categories(&model);
    vis.add_filter(Matcher::plain("failed")).add_filter(Matcher::plain("timeout"));
    vis.set_filter_enabled(0, false).set_filter_enabled(1, false);
    // No ACTIVE filter at all -> the filters do not narrow (§7).
    assert_eq!(vis.visible_lines(&model), vec![1, 2, 3, 4, 5, 6]);
    vis.set_filter_enabled(1, true);
    assert_eq!(vis.visible_lines(&model), vec![3]);
  }

  #[test]
  fn removed_filter_is_gone() {
    let model = mixed_model();
    let mut vis = all_categories(&model);
    vis.add_filter(Matcher::plain("failed")).add_filter(Matcher::plain("retry"));
    vis.remove_filter(0);
    assert_eq!(vis.visible_lines(&model), vec![6]);
  }

  #[test]
  fn filters_match_the_full_raw_line() {
    let model = mixed_model();
    // "LOG_WRN" exists only in the raw line 4, not in its message text.
    let mut vis = all_categories(&model);
    vis.add_filter(Matcher::plain("LOG_WRN"));
    assert_eq!(vis.visible_lines(&model), vec![4]);
    // Line-number criteria select exactly one line.
    let mut vis = all_categories(&model);
    vis.add_filter(Matcher::line_no(5));
    assert_eq!(vis.visible_lines(&model), vec![5]);
  }

  #[test]
  fn level_off_hides_rows() {
    let model = mixed_model();
    let mut vis = all_categories(&model);
    vis.set_level_enabled(Level::Error, false);
    assert_eq!(vis.visible_lines(&model), vec![2, 4, 5, 6]);
    vis.set_level_enabled(Level::Msg, false);
    assert_eq!(vis.visible_lines(&model), vec![4, 6]);
  }

  #[test]
  fn category_disabled_by_exact_path_hides_rows() {
    let model = mixed_model();
    let mut vis = all_categories(&model);
    vis.set_category_enabled("app/net", false);
    assert_eq!(vis.visible_lines(&model), vec![1, 2, 4, 5]);
    // A path that was never enabled cannot be disabled twice to any effect.
    vis.set_category_enabled("app/net", false);
    assert_eq!(vis.visible_lines(&model), vec![1, 2, 4, 5]);
  }

  #[test]
  fn disabling_parent_path_hides_child_rows() {
    let model = mixed_model();
    let mut vis = all_categories(&model);
    // Rows of app/main and app/net survive while only their own exact path
    // matters; disabling the parent "app" hides every app* row at once
    // (§10: disabling a node hides it and its children).
    vis.set_category_enabled("app", false);
    assert_eq!(vis.visible_lines(&model), vec![5]);
  }

  #[test]
  fn ancestor_prefix_disabled_hides_child_even_if_child_enabled() {
    let model = mixed_model();
    // Children ("app/main", "app/net") explicitly enabled while the
    // ancestor "app" is not in the whitelist: the rows stay hidden because
    // a category is disabled when ANY ancestor prefix is disabled.
    let mut vis = Visibility::new();
    for path in ["app/main", "app/net", "uncategorized"] {
      vis.set_category_enabled(path, true);
    }
    assert_eq!(vis.visible_lines(&model), vec![5]);
  }

  #[test]
  fn categories_start_disabled_and_enable_by_exact_path() {
    let model = mixed_model();
    // Default state: empty whitelist -> nothing visible.
    let mut vis = Visibility::new();
    assert!(vis.visible_lines(&model).is_empty());
    vis.set_category_enabled("uncategorized", true);
    assert_eq!(vis.visible_lines(&model), vec![5]);
    assert!(vis.categories_enabled().contains("uncategorized"));
    vis.set_category_enabled("uncategorized", false);
    assert!(vis.categories_enabled().is_empty());
    assert!(vis.visible_lines(&model).is_empty());
  }

  #[test]
  fn pin_overrides_filter_level_and_category() {
    let model = mixed_model();
    let mut vis = all_categories(&model);
    vis.add_filter(Matcher::plain("failed")); // matches only line 1
    vis.set_level_enabled(Level::Error, false);
    vis.set_category_enabled("app/main", false); // line 1's category
    // Line 1 is hidden by all three mechanisms together.
    assert!(vis.visible_lines(&model).is_empty());
    // The pin bypasses all of them (§12).
    vis.add_pin(Matcher::plain("database"));
    assert_eq!(vis.visible_lines(&model), vec![1]);
  }

  #[test]
  fn disabled_pin_stops_overriding() {
    let model = mixed_model();
    let mut vis = all_categories(&model);
    vis.add_filter(Matcher::plain("failed"));
    vis.set_level_enabled(Level::Error, false);
    vis.set_category_enabled("app/main", false);
    vis.add_pin(Matcher::plain("database"));
    assert_eq!(vis.visible_lines(&model), vec![1]);
    vis.set_pin_enabled(0, false);
    assert!(vis.visible_lines(&model).is_empty());
  }

  #[test]
  fn removed_pin_is_gone() {
    let model = mixed_model();
    let mut vis = all_categories(&model);
    vis.add_filter(Matcher::plain("failed"));
    vis.add_pin(Matcher::line_no(5)).add_pin(Matcher::line_no(3));
    assert_eq!(vis.visible_lines(&model), vec![1, 3, 5]);
    vis.remove_pin(0);
    assert_eq!(vis.visible_lines(&model), vec![1, 3]);
  }

  #[test]
  fn level_counts_ignore_level_toggles() {
    let model = mixed_model();
    let mut vis = all_categories(&model);
    // No filters, all categories: two Error, one Warning, two Msg, one Debug.
    assert_eq!(vis.level_counts_excluding_levels(&model), [0, 2, 1, 2, 1, 0]);
    // Toggling levels off must not change the counters (§11), while the
    // actual visibility does lose the Error rows.
    vis.set_level_enabled(Level::Error, false).set_level_enabled(Level::Msg, false);
    assert_eq!(vis.level_counts_excluding_levels(&model), [0, 2, 1, 2, 1, 0]);
    assert_eq!(vis.visible_lines(&model), vec![4, 6]);
  }

  #[test]
  fn level_counts_respect_filters_and_categories() {
    let model = mixed_model();
    let mut vis = all_categories(&model);
    vis.add_filter(Matcher::plain("failed")); // Error row 1 only
    assert_eq!(vis.level_counts_excluding_levels(&model), [0, 1, 0, 0, 0, 0]);
    vis.set_category_enabled("app/main", false); // hides row 1 as well
    assert_eq!(vis.level_counts_excluding_levels(&model), [0, 0, 0, 0, 0, 0]);
  }

  #[test]
  fn level_counts_respect_pins() {
    let model = mixed_model();
    let mut vis = all_categories(&model);
    vis.add_filter(Matcher::plain("failed"));
    vis.set_level_enabled(Level::Error, false);
    // Pin on the Error line 3: counted for Error (a pinned row would be
    // visible at its level because the pin bypasses level toggles, §7/§12).
    vis.add_pin(Matcher::plain("timeout"));
    assert_eq!(vis.level_counts_excluding_levels(&model), [0, 2, 0, 0, 0, 0]);
    // ... and the pinned row is truly visible although its level is off.
    assert_eq!(vis.visible_lines(&model), vec![3]);
  }

  #[test]
  fn empty_model_yields_nothing() {
    let model = model_from("lv_visibility_empty", b"");
    assert_eq!(model.line_count(), 0);
    let vis = all_categories(&model);
    assert!(vis.visible_lines(&model).is_empty());
    assert_eq!(vis.level_counts_excluding_levels(&model), [0_u64; 6]);
  }
}
