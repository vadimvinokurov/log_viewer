//! In-memory file model of one loaded log file: a parsed index over the
//! scanner, plus category and level rollups (FUNCTIONAL_SPEC §2, §4, §16).

use std::collections::BTreeMap;
use std::path::Path;
use std::time::Instant;

use crate::format::Format;
use crate::parser::{Level, Row, UNCATEGORIZED};
use crate::scanner::Scanner;

pub const LEVELS: [Level; 6] = [
  Level::Critical,
  Level::Error,
  Level::Warning,
  Level::Msg,
  Level::Debug,
  Level::Trace,
];

/// Loaded file: every line parsed once at load; row access is O(1).
///
/// Perf note (§16: hundreds of MB must feel instant; no numeric budgets fixed
/// in the spec): lazy/incremental parsing is a future optimization in the
/// perf epic; eager parse is the correctness-first baseline.
pub struct FileModel {
  format: Format,
  rows: Vec<Row>,
  /// Row count per full category string (hierarchical by `/`).
  categories: BTreeMap<String, u64>,
  /// Row count per level, in LEVELS order.
  levels: [u64; 6],
}

pub struct LoadStats {
  /// Time spent scanning + parsing (diagnostics only).
  pub elapsed: std::time::Duration,
}

impl FileModel {
  pub fn load_path(path: &Path) -> std::io::Result<(FileModel, LoadStats)> {
    let t0 = Instant::now();
    let scanner = Scanner::open(path)?;
    let format = scanner.format();
    let max = scanner.line_count();
    let rows: Vec<Row> = (1..=max)
      .map(|i| crate::parser::parse(format, line_no(i), scanner.raw_line(i)))
      .collect();
    let mut categories: BTreeMap<String, u64> = BTreeMap::new();
    let mut levels = [0_u64; 6];
    for row in &rows {
      let key = if row.category.is_empty() {
        UNCATEGORIZED
      } else {
        &row.category
      };
      *categories.entry(key.to_owned()).or_default() += 1;
      levels[level_index(row.level)] += 1;
    }
    Ok((
      FileModel { format, rows, categories, levels },
      LoadStats { elapsed: t0.elapsed() },
    ))
  }

  pub fn format(&self) -> Format {
    self.format
  }

  pub fn line_count(&self) -> u64 {
    self.rows.len() as u64
  }

  pub fn row(&self, i: usize) -> Option<&Row> {
    self.rows.get(i)
  }

  pub fn rows_slice(&self, offset: usize, limit: usize) -> &[Row] {
    let start = offset.min(self.rows.len());
    let end = (offset + limit).min(self.rows.len());
    &self.rows[start..end]
  }

  /// Categories with row counts, sorted by full path.
  pub fn categories(&self) -> impl Iterator<Item = (&str, u64)> + '_ {
    self
      .categories
      .iter()
      .map(|(path, count)| (path.as_str(), *count))
  }

  /// Row count per level.
  pub fn level_count(&self, level: Level) -> u64 {
    self.levels[level_index(level)]
  }
}

fn level_index(level: Level) -> usize {
  LEVELS
    .iter()
    .position(|&l| l == level)
    .expect("LEVELS covers all six levels")
}

fn line_no(i: usize) -> u32 {
  u32::try_from(i).expect("log files longer than u32::MAX lines are out of scope")
}

#[cfg(test)]
mod tests {
  use super::*;

  fn temp_file(name: &str, data: &[u8]) -> std::path::PathBuf {
    let path = std::env::temp_dir().join(name);
    std::fs::write(&path, data).unwrap();
    path
  }

  #[test]
  fn loads_counts_and_categories() {
    let path = temp_file(
      "lv_ws_basic.log",
      concat!(
        "2024-01-01T10:00:00.000 app/main LOG_MSG a\n",
        "2024-01-01T10:00:01.000 app/main/db LOG_ERR b\n",
        "2024-01-01T10:00:02.000 app LOG_TRC c\n",
        "2024-01-01T10:00:03.000 LOG_MSG no category\n",
        "\n",
      )
      .as_bytes(),
    );
    // First line decides the format: timestamp without a 12-byte time-of-day
    // token -> KSIVA.
    let (model, _) = FileModel::load_path(&path).unwrap();
    assert_eq!(model.format(), Format::Ksiva);
    assert_eq!(model.line_count(), 5);
    assert_eq!(
      model
        .categories()
        .collect::<std::vec::Vec<(&str, u64)>>(),
      vec![
        // BTreeMap order: U+004C ("LOG_MSG") sorts before lowercase bytes.
        ("LOG_MSG", 1_u64),
        ("app", 1),
        ("app/main", 1),
        ("app/main/db", 1),
        // the trailing empty line is uncategorized with an empty message (§3)
        ("uncategorized", 1),
      ]
    );
    // "2024-01-01T10:00:03.000 LOG_MSG no category": 4 tokens, so LOG_MSG is
    // the category (§3 rule: 3+ fields -> field 2 is the category).
    assert_eq!(model.level_count(Level::Msg), 3); // lines 1, 4 and the empty line
    assert_eq!(model.level_count(Level::Error), 1);
    assert_eq!(model.level_count(Level::Trace), 1);
    assert_eq!(model.level_count(Level::Critical), 0);
    assert_eq!(model.row(0).unwrap().message, "a");
    assert_eq!(model.rows_slice(1, 2).len(), 2);
    assert_eq!(model.rows_slice(4, 10).len(), 1);
    assert_eq!(model.rows_slice(9, 10).len(), 0);
  }

  #[test]
  fn empty_file_model() {
    let path = temp_file("lv_ws_empty.log", b"");
    let (model, _) = FileModel::load_path(&path).unwrap();
    assert_eq!(model.line_count(), 0);
    assert_eq!(model.categories().count(), 0);
    assert!(model.row(0).is_none());
  }
}
