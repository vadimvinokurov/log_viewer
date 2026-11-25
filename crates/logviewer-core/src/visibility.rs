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

use std::collections::{BTreeSet, HashMap};

use crate::matching::Matcher;
use crate::parser::Level;
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
    self.visible_with_counts(model).0
  }

  /// For each level (in `LEVELS` order): rows that would be visible IF that
  /// level were enabled — text filters and categories applied, the level
  /// toggles ignored (§11).
  pub fn level_counts_excluding_levels(&self, model: &FileModel) -> [u64; 6] {
    self.visible_with_counts(model).1
  }

  /// One shared walk over the rows (§7, the single pass behind both
  /// `visible_lines` and `level_counts_excluding_levels`): fills the
  /// visible-line list AND the §11 per-level counters from the same
  /// pre-level row stream, so a snapshot after a mutation costs one pass
  /// instead of two. The line rule is the full §7 formula
  /// `pinned OR (filters OR none) AND category`, AND level enabled (the pin
  /// bypasses the level toggle as well); the counters ignore the level
  /// toggles and count pinned rows at their own level.
  pub fn visible_with_counts(&self, model: &FileModel) -> (Vec<u32>, [u64; 6]) {
    // The interned-path index is rebuilt per recompute from the model's
    // distinct categories only — O(distinct paths), not O(rows).
    let index = CategoryIndex::build(model, &self.categories_enabled);
    let mut lines = Vec::new();
    let mut counts = [0_u64; 6];
    let count = model.line_count() as usize;
    for i in 0..count {
      let Some(row) = model.row(i) else { break };
      let text = String::from_utf8_lossy(&row.raw);
      let pinned = self.pinned(&text, row.line_no);
      if !pinned
        && !(self.matches_any_filter(&text, row.line_no)
          && index.row_allowed(self, &row.category))
      {
        continue;
      }
      counts[level_index(row.level)] += 1;
      if pinned || self.levels_enabled[level_index(row.level)] {
        lines.push(row.line_no);
      }
    }
    (lines, counts)
  }

  #[cfg(test)]
  /// The naive combined walk — the dual-path test oracle: identical
  /// row-by-row decisions to `visible_with_counts`, but every passing row
  /// re-walks its `/`-separated ancestor prefixes against the whitelist.
  fn visible_with_counts_reference(&self, model: &FileModel) -> (Vec<u32>, [u64; 6]) {
    let mut lines = Vec::new();
    let mut counts = [0_u64; 6];
    let count = model.line_count() as usize;
    for i in 0..count {
      let Some(row) = model.row(i) else { break };
      let text = String::from_utf8_lossy(&row.raw);
      let pinned = self.pinned(&text, row.line_no);
      if !pinned
        && !(self.matches_any_filter(&text, row.line_no)
          && self.category_allowed_reference(&row.category))
      {
        continue;
      }
      counts[level_index(row.level)] += 1;
      if pinned || self.levels_enabled[level_index(row.level)] {
        lines.push(row.line_no);
      }
    }
    (lines, counts)
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

  #[cfg(test)]
  /// §10 through the engine's path lens, per-row (the naive reference kept
  /// as the oracle for `interned_category_paths_match_the_naive_reference`):
  /// the row's exact category path and every `/`-separated ancestor prefix
  /// must be in the enabled whitelist (disabling a node hides its children).
  fn category_allowed_reference(&self, path: &str) -> bool {
    CategoryIndex::path_allowed(path, &self.categories_enabled)
  }
}

/// Interned category table for one recompute (§10): every distinct category
/// path of the model gets an id plus a precomputed allowed bit meaning "the
/// exact path AND all ancestor prefixes are in the whitelist". Built at
/// recompute start over borrowed keys and dropped after the walk; the
/// `Visibility` struct holds no interior shared state (the shell's vis
/// mutex serializes recomputes), so the layout stays `Sync`-safe.
struct CategoryIndex<'m> {
  /// `false` when the whitelist is empty: no path can pass, ids/allowed
  /// stay empty and every row check short-circuits.
  any_enabled: bool,
  /// Full path -> id, over the model's distinct category keys.
  ids: HashMap<&'m str, u32>,
  /// Allowed bit per id, in the build enumeration order.
  allowed: Vec<bool>,
}

impl<'m> CategoryIndex<'m> {
  fn build(model: &'m FileModel, enabled: &BTreeSet<String>) -> CategoryIndex<'m> {
    if enabled.is_empty() {
      return CategoryIndex {
        any_enabled: false,
        ids: HashMap::new(),
        allowed: Vec::new(),
      };
    }
    let paths: Vec<&'m str> = model.categories().collect();
    let mut ids: HashMap<&'m str, u32> = HashMap::with_capacity(paths.len());
    for (id, path) in paths.iter().enumerate() {
      ids.insert(path, id as u32);
    }
    let allowed = paths.iter().map(|path| Self::path_allowed(path, enabled)).collect();
    CategoryIndex {
      any_enabled: true,
      ids,
      allowed,
    }
  }

  /// §10 over one distinct path: the exact path and every `/`-separated
  /// ancestor prefix must be in the whitelist. The same logic as
  /// `category_allowed_reference`, but run once per distinct path instead
  /// of once per row — that relocation is the whole optimization.
  fn path_allowed(path: &str, enabled: &BTreeSet<String>) -> bool {
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

  /// §10 for a row: one map lookup plus one bit. A path outside the
  /// interned set falls back to the naive per-row check (the reference
  /// logic), so parity never depends on the index being complete. An empty
  /// whitelist lets no path through at all, so the check stays O(1) without
  /// any lookup — the fresh-engine floor keeps its pre-interning cost.
  fn row_allowed(&self, vis: &Visibility, category: &str) -> bool {
    if !self.any_enabled {
      return false;
    }
    self.ids.get(category).map_or_else(
      || Self::path_allowed(category, &vis.categories_enabled),
      |&id| self.allowed[id as usize],
    )
  }
}

#[cfg(test)]
mod tests {
  use super::*;
  use crate::format::Format;

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
    for path in model.categories() {
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

  // --------------------------------------------- shared walk + dual-path parity

  /// The single shared walk must agree with the two separate passes for any
  /// config: visible lines (level toggles + pins applied) and the §11
  /// counters (level toggles ignored).
  #[test]
  fn shared_walk_matches_the_two_separate_passes() {
    let model = mixed_model();
    let mut vis = all_categories(&model);
    vis.add_filter(Matcher::plain("LOG_WRN")); // line 4 only
    vis.set_level_enabled(Level::Error, false);
    vis.add_pin(Matcher::line_no(5)); // an uncategorized row
    let (lines, counts) = vis.visible_with_counts(&model);
    assert_eq!(lines, vis.visible_lines(&model));
    assert_eq!(counts, vis.level_counts_excluding_levels(&model));
  }

  #[test]
  fn shared_walk_on_empty_model_yields_nothing() {
    let model = model_from("lv_visibility_empty", b"");
    let vis = all_categories(&model);
    assert_eq!(vis.visible_with_counts(&model), (Vec::<u32>::new(), [0_u64; 6]));
  }

  /// Deterministic generated row set (no test_logs/ content): 48 rows per
  /// format covering nested latin paths, unicode paths, and uncategorized
  /// rows, all six levels. Only counts and shapes — no corpus bytes.
  const GEN_PATHS: [&str; 10] = [
    "app",
    "app/main",
    "app/net",
    "app/main/db",
    "α",
    "α/β",
    "α/β/δ",
    "café/sélection",
    "svc",
    "путь/вложенный/узел",
  ];

  fn generated_model(format: Format) -> FileModel {
    let level_tags_a = ["LOG_CRT", "LOG_ERR", "LOG_WRN", "LOG_MSG", "LOG_DBG", "LOG_TRC"];
    let level_tags_b = ["crt", "err", "wrn", "msg", "dbg", "trc"];
    let mut data = String::new();
    for i in 0..48_u32 {
      if i % 11 == 7 {
        // A two-field line: uncategorized (§3), format-dependent prefix.
        let line = match format {
          Format::Ksiva => format!("2024-01-01T10:00:{:02}.000 standalone{}", i % 60, i),
          Format::Plain => format!("10:00:{:02}.000 standalone{}", i % 60, i),
        };
        data.push_str(&line);
        data.push('\n');
        continue;
      }
      let path = GEN_PATHS[i as usize % GEN_PATHS.len()];      let k = (i % 6) as usize;
      let line = match format {
        Format::Ksiva => format!(
          "2024-01-01T10:00:{:02}.{:03} {path} {} message {i}",
          i % 60,
          i % 1000,
          level_tags_a[k],
        ),
        Format::Plain => format!(
          "10:00:{:02}.{:03} 0.0{i} {} {path} message {i}",
          i % 60,
          i % 1000,
          level_tags_b[k],
        ),
      };
      data.push_str(&line);
      data.push('\n');
    }
    model_from("lv_visibility_parity", data.as_bytes())
  }

  /// Every category AND its ancestor prefixes enabled — the shell's
  /// post-load whitelist.
  fn all_with_ancestors(path: &str, set: &mut Visibility) {
    let mut prefix: &str = path;
    loop {
      set.set_category_enabled(prefix, true);
      match prefix.rfind('/') {
        Some(i) => prefix = &prefix[..i],
        None => break,
      }
    }
  }

  /// Dual-path oracle: the optimized (interned-path) walk must decide the
  /// naive per-row ancestor walk row by row.
  fn check_parity(vis: &Visibility, model: &FileModel, ctx: &str) {
    assert_eq!(
      vis.visible_with_counts(model),
      vis.visible_with_counts_reference(model),
      "parity failed: {ctx}"
    );
  }

  #[test]
  fn interned_category_paths_match_the_naive_reference() {
    for (format_label, format) in [("a", Format::Ksiva), ("b", Format::Plain)] {
      let model = generated_model(format);

      // Full whitelist with ancestors: plenty of visible rows.
      let mut vis = Visibility::new();
      for path in model.categories() {
        all_with_ancestors(path, &mut vis);
      }
      check_parity(&vis, &model, &format!("[{format_label}] all enabled"));
      let (lines, _) = vis.visible_with_counts(&model);
      assert!(!lines.is_empty(), "[{format_label}] all enabled must show rows");

      // Empty whitelist: nothing visible, both engine paths hidden.
      check_parity(&Visibility::new(), &model, &format!("[{format_label}] empty whitelist"));
      let (lines, counts) = Visibility::new().visible_with_counts(&model);
      assert!(lines.is_empty(), "[{format_label}] empty whitelist must hide all");
      assert_eq!(counts, [0_u64; 6]);

      // Leaf paths only: the missing ancestors hide the leaves (§10).
      let mut vis = Visibility::new();
      for path in ["app/main/db", "α/β/δ", "uncategorized"] {
        vis.set_category_enabled(path, true);
      }
      check_parity(&vis, &model, &format!("[{format_label}] leaves only"));

      // Parents disabled on top of a full whitelist.
      let mut vis = Visibility::new();
      for path in model.categories() {
        all_with_ancestors(path, &mut vis);
      }
      vis.set_category_enabled("app", false);
      vis.set_category_enabled("α", false);
      check_parity(&vis, &model, &format!("[{format_label}] parents disabled"));

      // A mid-node disabled: its children hide too.
      let mut vis = Visibility::new();
      for path in model.categories() {
        all_with_ancestors(path, &mut vis);
      }
      vis.set_category_enabled("путь/вложенный", false);
      vis.set_category_enabled("café", false);
      check_parity(&vis, &model, &format!("[{format_label}] mid nodes disabled"));

      // Pins: pinned rows bypass the category rule entirely (§12).
      vis.set_category_enabled("app", false);
      vis.add_pin(Matcher::line_no(2)).add_pin(Matcher::line_no(17));
      // And a filter narrows the passing set (OR semantics).
      vis.add_filter(Matcher::plain("message"));
      check_parity(&vis, &model, &format!("[{format_label}] pins + filter + disabled parents"));

      // Level toggles off must not disturb the per-level counters.
      vis.set_level_enabled(Level::Error, false);
      vis.set_level_enabled(Level::Trace, false);
      check_parity(&vis, &model, &format!("[{format_label}] pins + filter + levels off"));
      let (lines, _) = vis.visible_with_counts(&model);
      assert!(!lines.is_empty(), "[{format_label}] pins must stay visible");

      // Disabled pin: the rows fall back under the category rule.
      vis.set_pin_enabled(0, false);
      check_parity(&vis, &model, &format!("[{format_label}] half-disabled pins"));
    }
  }
}
