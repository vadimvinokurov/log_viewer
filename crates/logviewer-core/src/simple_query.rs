//! Simple query language (FUNCTIONAL_SPEC §6): boolean expressions over
//! substrings of a log line, with precedence NOT > AND > OR, parentheses for
//! grouping and double-quoted terms. All matching is case-insensitive over the
//! full line text. A syntax error means "matches nothing" and never panics.

/// Grammar / API failure for [`parse`].
///
/// Byte positions refer to the original query `text` passed to [`parse`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SyntaxError {
  /// A quote was opened but never closed before end of input.
  UnclosedQuote { pos: usize },
  /// A `(` was never closed by a `)`.
  UnclosedParen { pos: usize },
  /// A stray symbol / keyword in a position where a term is expected, or
  /// trailing garbage after a complete query.
  UnexpectedToken { pos: usize },
  /// A term with an empty body: `""`.
  EmptyTerm { pos: usize },
}

impl std::fmt::Display for SyntaxError {
  fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
    match self {
      SyntaxError::UnclosedQuote { pos } => write!(f, "unclosed quote at byte {pos}"),
      SyntaxError::UnclosedParen { pos } => write!(f, "unclosed parenthesis at byte {pos}"),
      SyntaxError::UnexpectedToken { pos } => write!(f, "unexpected token at byte {pos}"),
      SyntaxError::EmptyTerm { pos } => write!(f, "empty term (\"\") at byte {pos}"),
    }
  }
}

impl std::error::Error for SyntaxError {}

/// Parsed query tree. Terms are stored lowercased; a `Query` can only be
/// produced by a successful [`parse`].
#[derive(Debug, Clone)]
pub struct Query {
  root: Node,
  /// Distinct lowercased positive (not NOT-negated) terms, for [`positive_spans`].
  positives: Vec<String>,
}

#[derive(Debug, Clone)]
enum Node {
  Term(String),
  And(Box<Node>, Box<Node>),
  Or(Box<Node>, Box<Node>),
  Not(Box<Node>),
}

/// Parses `text` into a [`Query`]. Keywords AND/OR/NOT are case-insensitive.
// spec interpretation: no escape sequences inside terms (the spec does not
// mention them); a backslash or a doubled quote is just a character of the
// term body, which ends only at the next `"` in a raw scan.
pub fn parse(text: &str) -> Result<Query, SyntaxError> {
  let tokens = tokenize(text)?;
  if tokens.is_empty() {
    // An empty (whitespace-only) query is a syntax error: there is no term
    // to evaluate, so the safest reading is "matches nothing".
    return Err(SyntaxError::UnexpectedToken { pos: 0 });
  }
  let mut p = Parser { tokens: &tokens, idx: 0 };
  let root = p.parse_or()?;
  if let Some(tok) = p.peek() {
    return Err(SyntaxError::UnexpectedToken { pos: tok.pos() });
  }
  let mut positives = Vec::new();
  collect_positives(&root, false, &mut positives);
  positives.sort();
  positives.dedup();
  Ok(Query { root, positives })
}

// spec interpretation: only the double quote `"` opens or closes a term and
// only whitespace, `(`, `)` and `"` may separate tokens; any other character
// outside a term is a stray symbol (grammar of §6 admits nothing else).
#[derive(Debug, Clone, PartialEq, Eq)]
enum Tok {
  Term { lower: String, pos: usize },
  And { pos: usize },
  Or { pos: usize },
  Not { pos: usize },
  LParen { pos: usize },
  RParen { pos: usize },
}

impl Tok {
  fn pos(&self) -> usize {
    match self {
      Tok::Term { pos, .. }
      | Tok::And { pos }
      | Tok::Or { pos }
      | Tok::Not { pos }
      | Tok::LParen { pos }
      | Tok::RParen { pos } => *pos,
    }
  }
}

fn tokenize(text: &str) -> Result<Vec<Tok>, SyntaxError> {
  let bytes = text.as_bytes();
  let mut toks = Vec::new();
  let mut i = 0;
  while i < bytes.len() {
    match bytes[i] {
      b' ' | b'\t' | b'\r' | b'\n' => i += 1,
      b'"' => {
        // Raw scan to the next quote; no escape sequences.
        match text[i + 1..].find('"') {
          Some(rel) => {
            let end = i + 1 + rel;
            let body = &text[i + 1..end];
            if body.is_empty() {
              return Err(SyntaxError::EmptyTerm { pos: i });
            }
            toks.push(Tok::Term { lower: body.to_lowercase(), pos: i });
            i = end + 1;
          }
          None => return Err(SyntaxError::UnclosedQuote { pos: i }),
        }
      }
      b'(' => {
        toks.push(Tok::LParen { pos: i });
        i += 1;
      }
      b')' => {
        toks.push(Tok::RParen { pos: i });
        i += 1;
      }
      b'a'..=b'z' | b'A'..=b'Z' => {
        // Keyword atoms: a run of ASCII letters. Anything else (digits,
        // punctuation, non-ASCII) is a stray symbol.
        let mut j = i;
        while j < bytes.len() && bytes[j].is_ascii_alphabetic() {
          j += 1;
        }
        let word = text[i..j].to_ascii_lowercase();
        match word.as_str() {
          "and" => toks.push(Tok::And { pos: i }),
          "or" => toks.push(Tok::Or { pos: i }),
          "not" => toks.push(Tok::Not { pos: i }),
          // Bare words are not terms per the grammar -> stray symbol.
          _ => return Err(SyntaxError::UnexpectedToken { pos: i }),
        }
        i = j;
      }
      _ => return Err(SyntaxError::UnexpectedToken { pos: i }),
    }
  }
  Ok(toks)
}

/// Recursive-descent parser over the token stream, precedence NOT > AND > OR.
struct Parser<'t> {
  tokens: &'t [Tok],
  idx: usize,
}

impl<'t> Parser<'t> {
  fn peek(&self) -> Option<&Tok> {
    self.tokens.get(self.idx)
  }

  fn parse_or(&mut self) -> Result<Node, SyntaxError> {
    let mut left = self.parse_and()?;
    while let Some(Tok::Or { .. }) = self.peek() {
      self.idx += 1;
      let right = self.parse_and()?;
      left = Node::Or(Box::new(left), Box::new(right));
    }
    Ok(left)
  }

  fn parse_and(&mut self) -> Result<Node, SyntaxError> {
    let mut left = self.parse_not()?;
    while let Some(Tok::And { .. }) = self.peek() {
      self.idx += 1;
      let right = self.parse_not()?;
      left = Node::And(Box::new(left), Box::new(right));
    }
    Ok(left)
  }

  fn parse_not(&mut self) -> Result<Node, SyntaxError> {
    if let Some(Tok::Not { .. }) = self.peek() {
      self.idx += 1;
      return Ok(Node::Not(Box::new(self.parse_not()?)));
    }
    self.parse_primary()
  }

  fn parse_primary(&mut self) -> Result<Node, SyntaxError> {
    // Clone the token out first so advancing `self.idx` is not blocked by
    // an outstanding borrow of the token slice.
    let tok = match self.peek() {
      Some(t) => t.clone(),
      None => return Err(SyntaxError::UnexpectedToken { pos: usize::MAX }),
    };
    match tok {
      Tok::Term { lower, .. } => {
        self.idx += 1;
        Ok(Node::Term(lower))
      }
      Tok::LParen { pos } => {
        self.idx += 1;
        let inner = self.parse_or()?;
        match self.peek() {
          Some(Tok::RParen { .. }) => {
            self.idx += 1;
            Ok(inner)
          }
          _ => Err(SyntaxError::UnclosedParen { pos }),
        }
      }
      _ => Err(SyntaxError::UnexpectedToken { pos: tok.pos() }),
    }
  }
}

/// Terms reachable with an even number of enclosing NOTs are positive.
fn collect_positives(node: &Node, negated: bool, out: &mut Vec<String>) {
  match node {
    Node::Term(lower) => {
      if !negated {
        out.push(lower.clone());
      }
    }
    Node::Not(inner) => collect_positives(inner, !negated, out),
    Node::And(l, r) | Node::Or(l, r) => {
      collect_positives(l, negated, out);
      collect_positives(r, negated, out);
    }
  }
}

/// Evaluates the query against the full text of a log line
/// (case-insensitive substring semantics for every term).
pub fn eval(query: &Query, line_text: &str) -> bool {
  // Terms are stored lowercased, so lowering the line once here is the whole
  // case-insensitivity machinery.
  let line_lower = line_text.to_lowercase();
  eval_node(&query.root, &line_lower)
}

fn eval_node(node: &Node, line_lower: &str) -> bool {
  // Terms are never empty (the tokenizer rejects `""`), so `contains` is the
  // full semantics; an empty line can only satisfy a NOT-ed term.
  match node {
    Node::Term(lower) => line_lower.contains(lower.as_str()),
    Node::And(l, r) => eval_node(l, line_lower) && eval_node(r, line_lower),
    Node::Or(l, r) => eval_node(l, line_lower) || eval_node(r, line_lower),
    Node::Not(inner) => !eval_node(inner, line_lower),
  }
}

/// Convenience gate for callers that receive a query through a fallible path.
// spec interpretation: "validate" keeps the parse-succeeded semantic; since a
// `Query` exists only after a successful `parse`, this is always `true`.
pub fn validate(query: &Query) -> bool {
  // Any constructible Query contains at least one non-empty term (the
  // tokenizer rejects everything else), so it is evaluable.
  let _ = query;
  true
}

/// Byte spans `(start, end)` in `line_text` of every occurrence of every
/// positive term (NOT-negated terms are excluded; double negation under
/// `NOT NOT` counts as positive). Spans are sorted and overlapping/adjacent
/// ones are merged. Case-insensitive.
// spec interpretation: a term is positive when it appears under an even
// number of NOTs, so `NOT (NOT "x")` still highlights `"x"`.
pub fn positive_spans(query: &Query, line_text: &str) -> Vec<(usize, usize)> {
  let line_lower = line_text.to_lowercase();
  let mut spans = Vec::new();
  for term in &query.positives {
    // Defensive: the tokenizer rejects empty terms, but an empty needle
    // would loop forever here.
    if term.is_empty() {
      continue;
    }
    // Overlapping occurrences included, advancing one byte at a time while
    // staying on UTF-8 character boundaries of the lowered line.
    let mut from = 0;
    while let Some(rel) = line_lower[from..].find(term.as_str()) {
      let start = from + rel;
      let end = start + term.len();
      spans.push((start, end));
      from = start + 1;
      while from <= line_lower.len() && !line_lower.is_char_boundary(from) {
        from += 1;
      }
      if from > line_lower.len() {
        break;
      }
    }
  }
  spans.sort_unstable();
  // Merge overlapping / adjacent spans (next.start <= current.end).
  let mut merged: Vec<(usize, usize)> = Vec::new();
  for (start, end) in spans {
    match merged.last_mut() {
      Some(last) if start <= last.1 => last.1 = last.1.max(end),
      _ => merged.push((start, end)),
    }
  }
  merged
}

#[cfg(test)]
mod tests {
  use super::*;

  fn matches(query_text: &str, line: &str) -> bool {
    match parse(query_text) {
      Ok(q) => eval(&q, line),
      Err(_) => false, // syntax error -> criterion matches nothing
    }
  }

  fn spans(query_text: &str, line: &str) -> Vec<(usize, usize)> {
    positive_spans(&parse(query_text).expect("query must parse"), line)
  }

  fn error_of(query_text: &str) -> SyntaxError {
    parse(query_text).expect_err("query must fail to parse")
  }

  // --- spec examples -------------------------------------------------------

  #[test]
  fn spec_example_and() {
    assert!(matches(r#""error" AND "timeout""#, "10:01 ERROR db timeout"));
    assert!(!matches(r#""error" AND "timeout""#, "10:01 ERROR db ok"));
    assert!(!matches(r#""error" AND "timeout""#, "10:01 warn db timeout"));
  }

  #[test]
  fn spec_example_not() {
    assert!(matches(r#"NOT "info""#, "10:01 warn db start"));
    assert!(!matches(r#"NOT "info""#, "10:01 INFO db start"));
  }

  #[test]
  fn spec_example_group_paren() {
    let q = r#"("auth" OR "login") AND "failed""#;
    assert!(matches(q, "auth failed"));
    assert!(matches(q, "LOGIN failed"));
    assert!(!matches(q, "auth ok"));
    assert!(!matches(q, "login ok"));
  }

  #[test]
  fn precedence_and_binds_tighter_than_or() {
    let q = r#""a" OR "b" AND "c""#;
    // Semantics must be "a" OR ("b" AND "c").
    assert!(matches(q, "a"));
    assert!(matches(q, "b c"));
    assert!(!matches(q, "b"), "if AND bound looser, 'b' alone would match");
    assert!(!matches(q, "c"));
  }

  #[test]
  fn keywords_case_insensitive() {
    assert!(matches(r#""error" and "timeout""#, "ERROR TIMEOUT"));
    assert!(matches(r#""error" And "timeout""#, "ERROR TIMEOUT"));
    assert!(matches(r#"not "info""#, "warn start"));
    assert!(matches(r#"Not "info""#, "warn start"));
    assert!(matches(r#"("auth" oR "login") AnD "failed""#, "auth failed"));
    // Keywords must not be matched inside terms of the same spelling.
    assert!(matches(r#""and""#, "the AND word"));
  }

  #[test]
  fn nested_not_and_paren() {
    assert!(matches(r#"NOT ("a" AND "b")"#, "a only"));
    assert!(!matches(r#"NOT ("a" AND "b")"#, "a and b"));
    assert!(matches(r#"NOT NOT "info""#, "info here"), "double negation");
    assert!(!matches(r#"NOT NOT "info""#, "warn here"));
    assert!(matches(r#"NOT ("a" OR "b") OR "c""#, "c only"));
  }

  #[test]
  fn single_term_plain() {
    let q = parse(r#""x""#).expect("must parse");
    assert!(validate(&q));
    assert!(eval(&q, "has x here"));
    assert!(!eval(&q, "has y here"));
  }

  // --- edge cases ----------------------------------------------------------

  #[test]
  fn empty_line_text() {
    assert!(!matches(r#""x""#, ""));
    assert!(matches(r#"NOT "info""#, "")); // vacuously true
    assert_eq!(spans(r#""x""#, ""), Vec::new());
  }

  #[test]
  fn term_spaces_and_word_boundaries() {
    // Terms may contain spaces and match substrings anywhere in the line.
    assert!(matches(r#""db timeout""#, "ERROR db timeout 10"));
    assert!(matches(r#""abc""#, "xabcx"));
  }

  #[test]
  fn empty_query_text_is_syntax_error() {
    assert_eq!(error_of(""), SyntaxError::UnexpectedToken { pos: 0 });
    assert!(!matches("", "anything"));
  }

  // --- syntax errors -------------------------------------------------------

  #[test]
  fn syntax_error_unclosed_quote() {
    assert_eq!(
      error_of(r#""error"#),
      SyntaxError::UnclosedQuote { pos: 0 }
    );
    assert_eq!(
      error_of(r#" "a" AND "b "#),
      SyntaxError::UnclosedQuote { pos: 9 }
    );
    assert!(
      parse(r#""error"#).is_err()
        && parse(r#""a" AND"#).is_err()
        && parse(r#"("a"#).is_err()
    );
  }

  #[test]
  fn syntax_error_unclosed_paren() {
    assert!(parse(r#"("a" AND "b""#).is_err());
  }

  #[test]
  fn syntax_error_empty_term() {
    // An empty term `""` is a syntax error -> Err (no panic, no match).
    assert!(parse(r#"""#).is_err());
    assert!(parse(r#""a" OR """#).is_err());
  }

  #[test]
  fn syntax_error_stray_symbols() {
    // Bare (unquoted) words are stray symbols per the grammar.
    assert!(parse("error AND timeout").is_err());
    assert!(parse(r#""a" "b""#).is_err());
    assert!(parse(r#"AND "a""#).is_err());
    assert!(parse(r#""a" AND"#).is_err());
    assert!(parse(r#""a" OR "b" )"#).is_err());
    assert!(parse(r#""a" + "b""#).is_err());
    assert!(parse(r#""a" && "b""#).is_err());
    // NOT with nothing to negate.
    assert!(parse(r#"NOT"#).is_err());
    assert!(parse(r#"("a") ("b")"#).is_err());
  }

  #[test]
  fn eval_never_called_on_invalid_query() {
    // The API shape guarantees it: only successful parse() yields a Query,
    // and error paths yield Err which callers map to "matches nothing".
    let bad = [
      r#""error"#,
      r#""""#,
      r#"("a""#,
      "error",
      "NOT",
      "",
    ];
    for q in bad {
      assert!(parse(q).is_err());
    }
  }

  #[test]
  fn validate_reports_parse_succeeded_semantics() {
    let q = parse(r#""a" AND "b""#).expect("must parse");
    assert!(validate(&q));
    assert!(validate(&parse(r#"NOT "info""#).expect("must parse")));
  }

  // --- span API ------------------------------------------------------------

  #[test]
  fn spans_multi_occurrence_case_insensitive() {
    // "AbC x abc ABc": occurrences of "abc" at 0..3, 6..9, 10..13.
    assert_eq!(
      spans(r#""abc""#, "AbC x abc ABc"),
      vec![(0, 3), (6, 9), (10, 13)]
    );
  }

  #[test]
  fn spans_exclude_negated_terms() {
    // Only "abc" is positive; "x" appears in the line but is NOT-negated.
    assert_eq!(
      spans(r#""abc" AND NOT "x""#, "AbC x abc"),
      vec![(0, 3), (6, 9)]
    );
  }

  #[test]
  fn spans_all_positive_terms_and_merge() {
    // "ab" spans (0,2); "bc" spans (1,3); merged into (0,3).
    assert_eq!(spans(r#""ab" OR "bc""#, "abc"), vec![(0, 3)]);
    // Several distinct terms at disjoint positions, sorted.
    assert_eq!(
      spans(r#""c" OR "a""#, "a b c"),
      vec![(0, 1), (4, 5)]
    );
  }

  #[test]
  fn spans_double_negated_term_is_positive() {
    assert_eq!(spans(r#"NOT (NOT "ab")"#, "xx ab yy"), vec![(3, 5)]);
  }

  #[test]
  fn spans_no_match_yields_empty() {
    assert_eq!(spans(r#""zzz""#, "nothing here"), Vec::new());
  }
}
