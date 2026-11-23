//! Match modes and the text-criterion engine (FUNCTIONAL_SPEC §5).
//!
//! Every text criterion (filter, highlight, pin, search) is a pattern plus a
//! match mode. All modes are case-insensitive. An invalid pattern compiles to
//! a matcher that matches nothing; user input must never cause a panic.

use regex::Regex;

/// Mode tag of a text criterion.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MatchMode {
  /// Case-insensitive substring.
  Plain,
  /// Case-insensitive regular expression (Python-compatible syntax).
  Regex,
  /// Boolean query language over quoted terms (§6).
  Simple,
  /// Exact 1-based line number.
  LineNo,
}

impl Copy for MatchMode {}

/// Sentinel type carried by a matcher that can never match (invalid regex).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NeverMatches;

#[derive(Debug, Clone)]
enum Kind {
  Never(NeverMatches),
  /// `needle` is the case-folded (lowercased) pattern text.
  Plain { needle: String },
  Regex(RegexEng),
  /// Parsed boolean query (§6), kept in the matcher.
  Simple(Box<crate::simple_query::Query>),
  LineNo(u32),
}

/// Regular expression engine, chosen at compile time: the `regex` crate for
/// everything it supports, `fancy_regex` for lookarounds and backreferences.
#[derive(Debug, Clone)]
enum RegexEng {
  Fast(Regex),
  Fancy(fancy_regex::Regex),
}

pub struct Matcher {
  kind: Kind,
}

impl Matcher {
  /// Case-insensitive substring matcher.
  pub fn plain(pattern: &str) -> Matcher {
    Matcher {
      kind: Kind::Plain {
        needle: pattern.to_lowercase(),
      },
    }
  }

  /// Case-insensitive regular-expression matcher. An invalid pattern compiles
  /// to a matcher that matches nothing (never a panic).
  pub fn regex(pattern: &str) -> Matcher {
    // The `(?i)` prefix gives case-insensitivity for both engines.
    let ci = format!("(?i){pattern}");
    let kind = match Regex::new(&ci) {
      Ok(re) => Kind::Regex(RegexEng::Fast(re)),
      Err(_) => match fancy_regex::Regex::new(&ci) {
        Ok(re) => Kind::Regex(RegexEng::Fancy(re)),
        Err(_) => Kind::Never(NeverMatches),
      },
    };
    Matcher { kind }
  }

  /// Matcher on the exact 1-based line number.
  pub fn line_no(n: u32) -> Matcher {
    Matcher {
      kind: Kind::LineNo(n),
    }
  }

  /// Case-insensitive boolean simple query matcher (§6). A syntax error
  /// compiles to a matcher that matches nothing (never a panic).
  pub fn simple(pattern: &str) -> Matcher {
    match crate::simple_query::parse(pattern) {
      Ok(query) => Matcher {
        kind: Kind::Simple(Box::new(query)),
      },
      Err(_) => Matcher {
        kind: Kind::Never(NeverMatches),
      },
    }
  }

  /// A matcher that matches nothing (never used as a user-visible criterion).
  pub fn never() -> Matcher {
    Matcher {
      kind: Kind::Never(NeverMatches),
    }
  }

  /// Does this criterion match `line_text` / the 1-based `line_no`?
  pub fn matches(&self, line_text: &str, line_no: u32) -> bool {
    match &self.kind {
      Kind::Never(_) => false,
      Kind::Plain { needle } => !plain_spans(needle, line_text).is_empty(),
      Kind::Regex(re) => re.is_match(line_text),
      Kind::Simple(query) => crate::simple_query::eval(query, line_text),
      Kind::LineNo(n) => *n == line_no,
    }
  }

  /// Byte spans of the match inside `line_text` (input for highlights).
  /// Empty when not matched or when the mode has no textual span.
  pub fn spans(&self, line_text: &str) -> Vec<(usize, usize)> {
    match &self.kind {
      Kind::Plain { needle } => plain_spans(needle, line_text),
      Kind::Regex(re) => re.spans(line_text),
      Kind::Simple(query) => crate::simple_query::positive_spans(query, line_text),
      Kind::LineNo(_) | Kind::Never(_) => Vec::new(),
    }
  }
}

impl RegexEng {
  fn is_match(&self, text: &str) -> bool {
    match self {
      RegexEng::Fast(re) => re.is_match(text),
      // spec interpretation: a backtracking-limit error counts as "no match",
      // never a panic (§5: an invalid criterion matches nothing).
      RegexEng::Fancy(re) => re.is_match(text).unwrap_or(false),
    }
  }

  fn spans(&self, text: &str) -> Vec<(usize, usize)> {
    match self {
      RegexEng::Fast(re) => re.find_iter(text).map(|m| (m.start(), m.end())).collect(),
      // spec interpretation: non-matching (overrun) attempts inside the fancy
      // iterator are skipped, not propagated as an error.
      RegexEng::Fancy(re) => re.find_iter(text).filter_map(|m| m.ok().map(|m| (m.start(), m.end()))).collect(),
    }
  }
}

/// All case-insensitive occurrences of the (already lowercase-folded) pattern
/// inside `hay`, including overlapping ones; byte offsets refer to the
/// original `hay`.
fn plain_spans(needle: &str, hay: &str) -> Vec<(usize, usize)> {
  if hay.is_empty() {
    return if needle.is_empty() { vec![(0, 0)] } else { Vec::new() };
  }
  if needle.is_ascii() && hay.is_ascii() {
    // Fast path: lowering an ASCII string keeps byte lengths, so offsets
    // found in the lowercase haystack are valid for the original text.
    let lowered = hay.to_ascii_lowercase();
    let finder = memchr::memmem::Finder::new(needle.as_bytes());
    let mut spans = Vec::new();
    let mut from = 0;
    while from <= lowered.len() {
      match finder.find(&lowered.as_bytes()[from..]) {
        Some(rel) => {
          let start = from + rel;
          spans.push((start, start + needle.len()));
          from = start + 1; // overlapping occurrences: advance by one byte
        }
        None => break,
      }
    }
    spans
  } else {
    // Unicode fallback: fold per char so a match always maps back to real
    // byte offsets of the original text (see `fold_match_len`).
    let idx: Vec<(usize, char)> = hay.char_indices().collect();
    let pat: Vec<char> = needle.chars().collect();
    let mut spans = Vec::new();
    for p in 0..idx.len() {
      if let Some(len_chars) = fold_match_len(&idx, &pat, p) {
        let start = idx[p].0;
        let end = if p + len_chars < idx.len() {
          idx[p + len_chars].0
        } else {
          hay.len()
        };
        spans.push((start, end));
      }
    }
    spans
  }
}

/// Length in haystack chars whose folded (lowercase) text matches `pat`
/// starting at position `p`, or `None`. `pat` is already folded; a single
/// haystack char may fold into several pattern chars (rare multi-char
/// lowercase expansions such as `İ` → `i` + U+0307).
fn fold_match_len(idx: &[(usize, char)], pat: &[char], p: usize) -> Option<usize> {
  let mut pi = 0; // index into pat
  let mut hp = p; // index into idx
  while pi < pat.len() {
    if hp >= idx.len() {
      return None; // haystack ran out before the pattern was consumed
    }
    for lc in idx[hp].1.to_lowercase() {
      if pi < pat.len() && pat[pi] == lc {
        pi += 1;
      } else {
        // The folded char diverges from (or overruns) the pattern.
        return None;
      }
    }
    hp += 1;
  }
  Some(hp - p)
}

impl MatchMode {
  /// Build the matcher for this mode. `pattern` is the plain text or regex
  /// source; for `LineNo` it is the line-number literal (e.g. `"5"`).
  ///
  /// // spec interpretation: an unparseable line number matches nothing,
  /// mirroring the invalid-regex policy of §5.
  pub fn matcher(&self, pattern: &str) -> Matcher {
    match self {
      MatchMode::Plain => Matcher::plain(pattern),
      MatchMode::Regex => Matcher::regex(pattern),
      MatchMode::Simple => Matcher::simple(pattern),
      MatchMode::LineNo => match pattern.trim().parse::<u32>() {
        Ok(n) => Matcher::line_no(n),
        Err(_) => Matcher::never(),
      },
    }
  }
}

#[cfg(test)]
mod tests {
  use super::*;

  #[test]
  fn plain_is_case_insensitive_substring() {
    let m = Matcher::plain("err");
    assert!(m.matches("ERROR: disk error", 1));
    assert!(m.spans("ERROR: disk error").contains(&(0, 3)));
    assert!(m.spans("ERROR: disk error").contains(&(12, 15)));
    assert!(!m.matches("warning: fine", 1));
  }

  #[test]
  fn plain_spans_are_overlapping() {
    let m = Matcher::plain("aa");
    assert_eq!(m.spans("aaaa"), vec![(0, 2), (1, 3), (2, 4)]);
    assert!(m.matches("aaaa", 1));
    assert_eq!(m.spans("abab"), Vec::<(usize, usize)>::new());
  }

  #[test]
  fn plain_empty_pattern_matches_every_line() {
    let m = Matcher::plain("");
    assert!(m.matches("anything", 1));
    assert!(m.matches("", 1));
    assert_eq!(m.spans("ab"), vec![(0, 0), (1, 1), (2, 2)]);
  }

  #[test]
  fn plain_is_unicode_case_insensitive() {
    let m = Matcher::plain("слово");
    assert!(m.matches("СЛОВО", 1));
    assert_eq!(m.spans("СЛОВО"), vec![(0, 10)]);
    assert_eq!(m.spans("нет совпадений"), Vec::<(usize, usize)>::new());
  }

  #[test]
  fn line_no_matches_exact_number() {
    let m = Matcher::line_no(5);
    assert!(m.matches("anything at all", 5));
    assert!(!m.matches("anything at all", 4));
    assert!(!m.matches("anything at all", 6));
    // spec interpretation: no textual span for a line-number criterion — the
    // caller decides (e.g. to highlight the whole message text).
    assert_eq!(m.spans("anything at all"), Vec::<(usize, usize)>::new());
  }

  #[test]
  fn regex_is_case_insensitive_and_reports_spans() {
    let m = Matcher::regex("error");
    assert!(m.matches("ERROR and error", 1));
    assert_eq!(m.spans("ERROR and error"), vec![(0, 5), (10, 15)]);
    assert!(!m.matches("all fine", 1));
  }

  #[test]
  fn regex_falls_back_to_fancy_for_lookaround() {
    // Lookahead is unsupported by the `regex` crate; must still work.
    let ahead = Matcher::regex("ERR(?=OR)");
    assert!(ahead.matches("error", 1));
    assert_eq!(ahead.spans("ERROR"), vec![(0, 3)]);
    assert!(!ahead.matches("eror", 1));
    // Lookbehind as well.
    let behind = Matcher::regex("(?<=ERR)OR");
    assert!(behind.matches("error", 1));
    assert_eq!(behind.spans("ERROR"), vec![(3, 5)]);
  }

  #[test]
  fn regex_falls_back_to_fancy_for_backreference() {
    let m = Matcher::regex(r"(\d)\1");
    assert!(m.matches("line 122 and a11b", 1));
    assert_eq!(m.spans("line 122 and a11b"), vec![(6, 8), (14, 16)]);
  }

  #[test]
  fn invalid_regex_matches_nothing_without_panic() {
    for bad in ["(", "(?!", "[a-", "a{2,1}"] {
      let m = Matcher::regex(bad);
      let text = "anything ( [ { 123";
      assert!(!m.matches(text, 1), "pattern {bad:?} must not match");
      assert_eq!(m.spans(text), Vec::<(usize, usize)>::new());
    }
  }

  #[test]
  fn never_matches_nothing() {
    let m = Matcher::never();
    assert!(!m.matches("text", 1));
    assert_eq!(m.spans("text"), Vec::<(usize, usize)>::new());
  }

  #[test]
  fn match_mode_builds_the_right_matcher() {
    assert!(MatchMode::Plain.matcher("Err").matches("ERROR", 1));
    assert!(MatchMode::Regex.matcher("e(r+)").matches("eRR", 1));
    assert!(MatchMode::LineNo.matcher("7").matches("text", 7));
    assert!(!MatchMode::LineNo.matcher("x7").matches("text", 7));
    assert!(!MatchMode::LineNo.matcher("-3").matches("text", 7));
  }

  // --- Simple query mode (§6), wired to simple_query -------------------------

  #[test]
  fn simple_matches_boolean_queries_case_insensitively() {
    let m = MatchMode::Simple.matcher(r#"("db" OR "net") AND "failed""#);
    assert!(m.matches("ERROR db write failed", 1));
    assert!(m.matches("NET request Failed", 1));
    assert!(!m.matches("db write ok", 1));
    assert!(!m.matches("failed but for disk", 1));
  }

  #[test]
  fn simple_invalid_query_matches_nothing() {
    // Stray symbol / bare word is a syntax error (§6) -> no match, no panic.
    let m = MatchMode::Simple.matcher("error");
    assert!(!m.matches("error line", 1));
    assert_eq!(m.spans("error line"), Vec::<(usize, usize)>::new());
  }

  #[test]
  fn simple_spans_cover_positive_terms_only() {
    let m = MatchMode::Simple.matcher(r#""timeout" OR NOT "info""#);
    // Positive term "timeout" gets spans; NOT-term "info" never highlights.
    assert_eq!(m.spans("Timeout after INFO"), vec![(0, 7)]);
    let m2 = MatchMode::Simple.matcher(r#"NOT "x""#);
    assert_eq!(m2.spans("contains x here"), Vec::<(usize, usize)>::new());
  }
}
