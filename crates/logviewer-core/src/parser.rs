//! Row parsing for formats A ("KSIVA") and B ("PLAIN") (FUNCTIONAL_SPEC §3).

use crate::format::Format;

/// Category of rows that carry no category field (§3: "uncategorized").
pub const UNCATEGORIZED: &str = "uncategorized";

/// Severity of a parsed row (§3.1). The row text is colored by this level.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Level {
  Critical,
  Error,
  Warning,
  Msg,
  Debug,
  Trace,
}

/// One parsed source line (§3).
#[derive(Debug, Clone, PartialEq)]
pub struct Row {
  /// 1-based line number in the source file, stable across filtering (§4).
  pub line_no: u32,
  /// Time of day `HH:MM:SS.mmm`; for format A the date part before `T` is stripped.
  pub time_display: String,
  /// Full category string, hierarchical by `/`; `uncategorized` when missing (§3).
  pub category: String,
  pub level: Level,
  /// Message text: the rest of the line after the recognized fields.
  pub message: String,
  /// Original bytes exactly as they were passed in (line without its terminator).
  pub raw: Vec<u8>,
}

/// Parse one raw line (without its line terminator) into a row (FUNCTIONAL_SPEC §3).
pub fn parse(format: Format, line_no: u32, raw: &[u8]) -> Row {
  let (time_display, category, level, message) = match format {
    Format::Ksiva => parse_ksiva(raw),
    Format::Plain => parse_plain(raw),
  };
  Row {
    line_no,
    time_display,
    category,
    level,
    message,
    raw: raw.to_vec(),
  }
}

/// Level-tag vocabulary (FUNCTIONAL_SPEC §3/§3.1), compared case-insensitively:
/// bare short codes (`crt.err.wrn.msg.dbg.trc`), `LOG_` + the short code and
/// `LOG_` + the long level name.
// spec interpretation: bare long names ("ERROR", "MSG", ...) are deliberately
// NOT level tags — §3.1 shows long names only in the LOG_* form, and treating
// a bare common word as a level would swallow real message text.
const LEVEL_TAGS: &[(&str, Level)] = &[
  ("crt", Level::Critical),
  ("err", Level::Error),
  ("wrn", Level::Warning),
  ("msg", Level::Msg),
  ("dbg", Level::Debug),
  ("trc", Level::Trace),
  ("log_crt", Level::Critical),
  ("log_err", Level::Error),
  ("log_wrn", Level::Warning),
  ("log_msg", Level::Msg),
  ("log_dbg", Level::Debug),
  ("log_trc", Level::Trace),
  ("log_critical", Level::Critical),
  ("log_error", Level::Error),
  ("log_warning", Level::Warning),
  ("log_debug", Level::Debug),
  ("log_trace", Level::Trace),
];

/// Recognize a level-candidate token (§3: unrecognized → MSG).
fn recognize_level(token: &[u8]) -> Option<Level> {
  let bare = strip_level_brackets(token);
  LEVEL_TAGS
    .iter()
    .find(|(tag, _)| bare.eq_ignore_ascii_case(tag.as_bytes()))
    .map(|&(_, level)| level)
}

/// spec interpretation: exactly one pair of matching brackets or parentheses
/// is removed before matching (`[LOG_MSG]` -> `LOG_MSG`, `(dbg)` -> `dbg`).
fn strip_level_brackets(token: &[u8]) -> &[u8] {
  match token {
    [b'[', middle @ .., b']'] if middle.len() >= 2 => middle,
    [b'(', middle @ .., b')'] if middle.len() >= 2 => middle,
    _ => token,
  }
}

/// A whitespace-separated token with its start offset in the raw line.
/// The separator runs are arbitrary space/tab sequences (§3). Tokens are
/// non-contiguous: separators between them are re-derivable from `raw`.
type Tokens<'a> = Vec<(usize, &'a [u8])>;

fn tokenize(line: &[u8]) -> Tokens<'_> {
  let mut tokens = Tokens::new();
  let mut i = 0;
  while i < line.len() {
    if line[i] == b' ' || line[i] == b'\t' {
      i += 1;
      continue;
    }
    let start = i;
    while i < line.len() && line[i] != b' ' && line[i] != b'\t' {
      i += 1;
    }
    tokens.push((start, &line[start..i]));
  }
  tokens
}

/// Start offset of token `k + 1` (first byte of the message), or `line_len`
/// when token `k` is the last one: the message ends with the line, verbatim.
// spec interpretation: the single separator run between the last structural
// token and the first message token is consumed; the rest of the message is
// kept byte-for-byte (internal and trailing whitespace preserved).
fn message_start(tokens: &Tokens<'_>, line_len: usize, k: usize) -> usize {
  tokens
    .get(k + 1)
    .map_or(line_len, |&(start, _)| start)
}

/// Format A "ksiva" (§3): `timestamp category [LOG_LEVEL] message`.
/// 1 field = uncategorized, empty message; 2 fields = uncategorized, the
/// second field is the message; 3+ fields: field 2 = category, field 3 = level
/// candidate (unrecognized → MSG, candidate and rest = message).
fn parse_ksiva(line: &[u8]) -> (String, String, Level, String) {
  let tokens = tokenize(line);
  let ts = tokens.first().map_or(&[][..], |&(_, t)| t);
  let time_display = ksiva_time_display(ts);
  match tokens.len() {
    0 | 1 => (time_display, UNCATEGORIZED.to_string(), Level::Msg, String::new()),
    2 => {
      let category = UNCATEGORIZED.to_string();
      let message = message_at_start(line, tokens[1].0);
      (time_display, category, Level::Msg, message)
    }
    _ => {
      let category = lossy(tokens[1].1);
      match recognize_level(tokens[2].1) {
        Some(level) => {
          let message = message_at_start(line, message_start(&tokens, line.len(), 2));
          (time_display, category, level, message)
        }
        None => {
          let message = message_at_start(line, tokens[2].0);
          (time_display, category, Level::Msg, message)
        }
      }
    }
  }
}

/// Format B "plain" (§3): `time elapsed level_short category message`.
/// Edge rules mirror format A with one fewer structural field: 1 field =
/// uncategorized, empty message; 2 fields = uncategorized, field 2 is the
/// message (the elapsed slot stays absent); 3 fields = field 3 is the level
/// candidate, category uncategorized; 4+ fields: field 4 = category.
fn parse_plain(line: &[u8]) -> (String, String, Level, String) {
  let tokens = tokenize(line);
  let time_display = tokens.first().map_or(String::new(), |&(_, t)| lossy(t));
  match tokens.len() {
    0 | 1 => (time_display, UNCATEGORIZED.to_string(), Level::Msg, String::new()),
    2 => {
      let category = UNCATEGORIZED.to_string();
      let message = message_at_start(line, tokens[1].0);
      (time_display, category, Level::Msg, message)
    }
    3 => match recognize_level(tokens[2].1) {
      Some(level) => (time_display, UNCATEGORIZED.to_string(), level, String::new()),
      None => {
        let message = message_at_start(line, tokens[2].0);
        (time_display, UNCATEGORIZED.to_string(), Level::Msg, message)
      }
    },
    _ => match recognize_level(tokens[2].1) {
      Some(level) => {
        let category = lossy(tokens[3].1);
        let message = message_at_start(line, message_start(&tokens, line.len(), 3));
        (time_display, category, level, message)
      }
      None => {
        let message = message_at_start(line, tokens[2].0);
        (time_display, UNCATEGORIZED.to_string(), Level::Msg, message)
      }
    },
  }
}

/// Time-of-day display for a format A timestamp (§3): if the timestamp carries
/// a date, it is separated by a `T` and only the part after it is shown.
fn ksiva_time_display(ts: &[u8]) -> String {
  let part = match ts.iter().position(|&b| b == b'T') {
    Some(i) => &ts[i + 1..],
    None => ts,
  };
  lossy(part)
}

/// Text of `line` from byte offset `start` to the end of the line.
fn message_at_start(line: &[u8], start: usize) -> String {
  lossy(&line[start..])
}

/// `String` from raw line bytes; non-UTF-8 never panics (lossy conversion).
fn lossy(bytes: &[u8]) -> String {
  String::from_utf8_lossy(bytes).into_owned()
}

#[cfg(test)]
mod tests {
  use super::*;

  // ---------------------------------------------------------------- helpers

  fn ksiva(raw: &[u8]) -> Row {
    parse(Format::Ksiva, 1, raw)
  }

  fn plain(raw: &[u8]) -> Row {
    parse(Format::Plain, 1, raw)
  }

  fn assert_row(row: &Row, time: &str, category: &str, level: Level, message: &str) {
    assert_eq!(row.time_display, time);
    assert_eq!(row.category, category);
    assert_eq!(row.level, level);
    assert_eq!(row.message, message);
  }

  const FIXTURES: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures");

  /// Lines of a fixture file: split on `\n`, trailing `\r` removed, the final
  /// segment after a trailing newline dropped.
  fn fixture_lines(name: &str) -> Vec<Vec<u8>> {
    let path = std::path::Path::new(FIXTURES).join(name);
    let data = std::fs::read(&path).unwrap_or_else(|e| panic!("read {path:?}: {e}"));
    let mut lines: Vec<Vec<u8>> = data
      .split(|&b| b == b'\n')
      .map(|l| {
        if let Some(stripped) = l.strip_suffix(b"\r") {
          stripped.to_vec()
        } else {
          l.to_vec()
        }
      })
      .collect();
    if lines.last().is_some_and(|l| l.is_empty()) {
      lines.pop(); // trailing newline: no phantom final line
    }
    lines
  }

  // ------------------------------------------------------------ format A

  #[test]
  fn a_full_line_with_level_tag() {
    let row = ksiva(b"2024-01-01T10:00:00.000 app/main LOG_MSG Starting application");
    assert_row(&row, "10:00:00.000", "app/main", Level::Msg, "Starting application");
  }

  #[test]
  fn a_full_line_without_level_tag() {
    // The candidate "Process" is not a level: it stays MSG and joins the message.
    let row = ksiva(b"2024-01-01T10:00:00.000 app Process   failed to start");
    assert_row(&row, "10:00:00.000", "app", Level::Msg, "Process   failed to start");
  }

  #[test]
  fn a_two_field_line() {
    // Exactly two tokens: the whole second token is the message (§3).
    let row = ksiva(b"2024-01-01T10:00:01.000 standalone");
    assert_row(&row, "10:00:01.000", "uncategorized", Level::Msg, "standalone");
  }

  #[test]
  fn a_single_field_line() {
    let row = ksiva(b"2024-01-01T10:00:04.000");
    assert_row(&row, "10:00:04.000", "uncategorized", Level::Msg, "");
  }

  #[test]
  fn a_empty_line() {
    let row = ksiva(b"");
    assert_row(&row, "", "uncategorized", Level::Msg, "");
  }

  #[test]
  fn a_two_field_line_even_if_second_is_a_level_code() {
    // Exactly two fields: the second is always the message (§3), never a level tag.
    let row = ksiva(b"2024-01-01T10:00:02.000 crt");
    assert_row(&row, "10:00:02.000", "uncategorized", Level::Msg, "crt");
  }

  #[test]
  fn a_missing_message_after_level() {
    let row = ksiva(b"2024-01-01T10:00:03.000 app LOG_ERR");
    assert_row(&row, "10:00:03.000", "app", Level::Error, "");
  }

  #[test]
  fn a_time_display_strips_date_part() {
    let row = ksiva(b"2024-01-01T23:59:59.999 app LOG_MSG done");
    assert_eq!(row.time_display, "23:59:59.999");
  }

  #[test]
  fn a_multiple_space_separators() {
    let row = ksiva(b"2024-01-01T10:00:00.000   app   LOG_MSG   starts   now");
    assert_row(&row, "10:00:00.000", "app", Level::Msg, "starts   now");
  }

  #[test]
  fn a_short_code_levels_all_six() {
    for (code, level) in [
      ("crt", Level::Critical),
      ("err", Level::Error),
      ("wrn", Level::Warning),
      ("msg", Level::Msg),
      ("dbg", Level::Debug),
      ("trc", Level::Trace),
    ] {
      let line = format!("2024-01-01T10:00:00.500 app {code} body");
      let row = ksiva(line.as_bytes());
      assert_eq!(row.level, level, "short code {code:?}");
      assert_eq!(row.message, "body", "short code {code:?}");
    }
  }

  #[test]
  fn a_log_prefixed_long_and_short_tags() {
    for (tag, level) in [
      ("LOG_CRT", Level::Critical),
      ("LOG_ERR", Level::Error),
      ("LOG_WRN", Level::Warning),
      ("LOG_MSG", Level::Msg),
      ("LOG_DBG", Level::Debug),
      ("LOG_TRC", Level::Trace),
      ("LOG_CRITICAL", Level::Critical),
      ("LOG_ERROR", Level::Error),
      ("LOG_WARNING", Level::Warning),
      ("LOG_DEBUG", Level::Debug),
      ("LOG_TRACE", Level::Trace),
    ] {
      let line = format!("2024-01-01T10:00:00.500 app {tag} payload");
      let row = ksiva(line.as_bytes());
      assert_eq!(row.level, level, "tag {tag:?}");
      assert_eq!(row.message, "payload", "tag {tag:?}");
    }
  }

  #[test]
  fn a_level_tag_case_insensitive() {
    for (tag, level) in [
      ("log_err", Level::Error),
      ("Log_Msg", Level::Msg),
      ("WRN", Level::Warning),
      ("Dbg", Level::Debug),
    ] {
      let line = format!("2024-01-01T10:00:00.500 app {tag} rest");
      let row = ksiva(line.as_bytes());
      assert_eq!(row.level, level, "tag {tag:?}");
      assert_eq!(row.message, "rest", "tag {tag:?}");
    }
  }

  #[test]
  fn a_bracketed_level_tags() {
    let row = ksiva(b"2024-01-01T10:00:00.000 app [LOG_ERR] bracketed tag");
    assert_row(&row, "10:00:00.000", "app", Level::Error, "bracketed tag");

    let row = ksiva(b"2024-01-01T10:00:00.100 app (dbg) parenthesized");
    assert_row(&row, "10:00:00.100", "app", Level::Debug, "parenthesized");
  }

  #[test]
  fn a_bare_long_names_are_not_level_tags() {
    // Spec interpretation: §3.1 shows long names only in the LOG_* form, so a
    // bare "error" is an unrecognized candidate and stays in the message.
    let row = ksiva(b"2024-01-01T10:00:00.000 app error words after");
    assert_row(&row, "10:00:00.000", "app", Level::Msg, "error words after");
  }

  #[test]
  fn category_keeps_hierarchical_path() {
    let row = ksiva(b"2024-01-01T10:00:00.000 app/main/db LOG_MSG x");
    assert_eq!(row.category, "app/main/db");
  }

  #[test]
  fn raw_bytes_are_preserved() {
    let raw: &[u8] = b"2024-01-01T10:00:00.000 app/main LOG_MSG Starting application";
    let row = ksiva(raw);
    assert_eq!(row.raw, raw);
  }

  #[test]
  fn line_number_is_preserved() {
    let row = parse(Format::Ksiva, 42, b"2024-01-01T10:00:00.000 app LOG_MSG x");
    assert_eq!(row.line_no, 42);
  }

  // ------------------------------------------------------------ format B

  #[test]
  fn b_full_line() {
    let row = plain(b"10:00:00.000 0.123 msg cfg Application started");
    assert_row(&row, "10:00:00.000", "cfg", Level::Msg, "Application started");
  }

  #[test]
  fn b_elapsed_field_is_discarded() {
    let row = plain(b"10:00:01.000 7.980 err cfg/db Boom happened");
    assert_row(&row, "10:00:01.000", "cfg/db", Level::Error, "Boom happened");
    assert_eq!(row.message, "Boom happened");
  }

  #[test]
  fn b_unrecognized_level_candidate_becomes_message() {
    let row = plain(b"10:00:00.000 0.123 oops cfg words here");
    assert_row(&row, "10:00:00.000", "uncategorized", Level::Msg, "oops cfg words here");
  }

  #[test]
  fn b_three_fields_recognized_level() {
    let row = plain(b"10:00:02.500 0.500 crt");
    assert_row(&row, "10:00:02.500", "uncategorized", Level::Critical, "");
  }

  #[test]
  fn b_three_fields_unrecognized_candidate() {
    let row = plain(b"10:00:02.500 0.500 hello");
    assert_row(&row, "10:00:02.500", "uncategorized", Level::Msg, "hello");
  }

  #[test]
  fn b_two_field_line() {
    let row = plain(b"10:00:03.000 leftover");
    assert_row(&row, "10:00:03.000", "uncategorized", Level::Msg, "leftover");
  }

  #[test]
  fn b_single_field_line() {
    let row = plain(b"10:00:04.000");
    assert_row(&row, "10:00:04.000", "uncategorized", Level::Msg, "");
  }

  #[test]
  fn b_empty_line() {
    let row = plain(b"");
    assert_row(&row, "", "uncategorized", Level::Msg, "");
  }

  #[test]
  fn b_time_display_is_time_of_day() {
    let row = plain(b"23:59:59.999 9.999 trc cat t");
    assert_eq!(row.time_display, "23:59:59.999");
    assert_eq!(row.level, Level::Trace);
  }

  #[test]
  fn b_multiple_space_separators() {
    let row = plain(b"10:00:01.000  0.234 dbg app/net  Multi   space message");
    assert_row(&row, "10:00:01.000", "app/net", Level::Debug, "Multi   space message");
  }

  #[test]
  fn b_case_insensitive_level_tag() {
    let row = plain(b"10:00:00.000 0.1 LoG_eRR cat words");
    assert_row(&row, "10:00:00.000", "cat", Level::Error, "words");
  }

  // ------------------------------------------------------------ golden fixtures

  #[test]
  fn golden_ksiva_fixture() {
    let lines = fixture_lines("parsing_ksiva.log");
    assert_eq!(lines.len(), 5);
    // Line 1: full line with a LOG_MSG level tag.
    assert_row(&ksiva(&lines[0]), "10:00:00.000", "app/main", Level::Msg, "Starting application");
    // Line 2: two fields — uncategorized, the second field is the message.
    assert_row(&ksiva(&lines[1]), "10:00:01.000", "uncategorized", Level::Msg, "standalone");
    // Line 3: bare short code as the level tag.
    assert_row(&ksiva(&lines[2]), "10:00:02.500", "a/b/c", Level::Warning, "Something odd");
    // Line 4: unrecognized candidate "Just" joins the message.
    assert_row(&ksiva(&lines[3]), "10:00:03.000", "app", Level::Msg, "Just   words");
    // Line 5: single field — timestamp only.
    assert_row(&ksiva(&lines[4]), "10:00:04.000", "uncategorized", Level::Msg, "");
  }

  #[test]
  fn golden_plain_fixture() {
    let lines = fixture_lines("parsing_plain.log");
    assert_eq!(lines.len(), 3);
    assert_row(&plain(&lines[0]), "10:00:00.000", "cfg", Level::Msg, "Application started");
    assert_row(&plain(&lines[1]), "10:00:01.000", "app/net", Level::Debug, "Multi   space message");
    assert_row(
      &plain(&lines[2]),
      "10:00:02.500",
      "uncategorized",
      Level::Msg,
      "unknown_word  cfg Not a level here",
    );
  }

  #[test]
  fn golden_edge_fixture() {
    let lines = fixture_lines("parsing_edge.log");
    assert_eq!(lines.len(), 4);
    // Line 1 is empty.
    assert_row(&ksiva(&lines[0]), "", "uncategorized", Level::Msg, "");
    // Bracketed level tag.
    assert_row(&ksiva(&lines[1]), "10:00:00.000", "app", Level::Error, "bracketed tag");
    // Long LOG_* form of a level code.
    assert_row(&ksiva(&lines[2]), "10:00:01.000", "app", Level::Trace, "long form");
    // Two fields: the second field is the message.
    assert_row(&ksiva(&lines[3]), "10:00:02.000", "uncategorized", Level::Msg, "app");
  }
}
