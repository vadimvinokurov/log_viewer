//! Highlight rules and span computation (FUNCTIONAL_SPEC §9).
//!
//! A highlight never hides rows; it only colors matched spans. Each rule
//! carries an index into the 10-color palette (the hex values live in the
//! UI layer, docs/UI_DESIGN.html — the core only carries 0..10). Spans are
//! byte ranges inside the MESSAGE text of a row; the rendering layer draws
//! a semi-transparent rectangle behind each span in the Message column.

use crate::matching::Matcher;

/// Number of palette colors; `add` assigns them round-robin.
pub const PALETTE_SIZE: usize = 10;

/// One highlight rule (§9: h/hr/hs match by pattern, hn by line number).
pub enum Rule {
  /// Pattern-based highlight (h, hr, hs).
  Pattern {
    matcher: Matcher,
  },
  /// Whole-line highlight by number (hn N): the entire message of the
  /// matching line is colored.
  LineNo {
    line_no: u32,
  },
}

/// A highlight rule plus its assigned palette color and on/off state.
pub struct Highlight {
  pub rule: Rule,
  pub color_index: u8,
  pub enabled: bool,
}

/// Registry of active highlights in rule order (the order rules were added).
// spec interpretation: `Debug`/`Clone` are not derived because `Matcher` does
// not implement them; the engine is owned by the app state and cloned never.
pub struct HighlightEngine {
  rules: Vec<Highlight>,
  next_color: u8,
}

impl Default for HighlightEngine {
  fn default() -> Self {
    Self::new()
  }
}

impl HighlightEngine {
  pub fn new() -> Self {
    HighlightEngine { rules: Vec::new(), next_color: 0 }
  }

  /// Adds a rule, assigning the next palette color round-robin
  /// (`counter % PALETTE_SIZE`), enabled by default.
  pub fn add(&mut self, rule: Rule) {
    let color_index = self.next_color % PALETTE_SIZE as u8;
    self.next_color = self.next_color.wrapping_add(1);
    self.rules.push(Highlight { rule, color_index, enabled: true });
  }

  /// Removes the rule at `idx`; an out-of-range `idx` is ignored (removal is
  /// only ever driven by the UI, which indexes into `rules()`).
  pub fn remove(&mut self, idx: usize) {
    if idx < self.rules.len() {
      self.rules.remove(idx);
    }
  }

  /// Active rules in rule order.
  pub fn rules(&self) -> &[Highlight] {
    &self.rules
  }

  /// Toggles the on/off checkbox of rule `idx`; a disabled one renders nothing.
  /// An out-of-range `idx` is ignored (same policy as `remove`).
  pub fn set_enabled(&mut self, idx: usize, on: bool) -> &mut Self {
    if let Some(h) = self.rules.get_mut(idx) {
      h.enabled = on;
    }
    self
  }

  /// Removes all rules (`rmh`).
  pub fn clear(&mut self) {
    self.rules.clear();
  }
}

/// Spans to render for one row: `(color_index, byte range in the message)`.
/// Overlaps from different rules are kept (no merging); the spans are in
/// rule order. Disabled rules and rules that match nothing contribute nothing.
pub fn row_spans(
  engine: &HighlightEngine,
  row: &crate::parser::Row,
) -> Vec<(u8, std::ops::Range<usize>)> {
  let mut out = Vec::new();
  for h in engine.rules() {
    if !h.enabled {
      continue; // an off checkbox renders nothing (§9)
    }
    match &h.rule {
      // Pattern rules locate their spans inside the message text only
      // (§9: the rectangle is drawn in the Message column).
      Rule::Pattern { matcher } => {
        for (start, end) in matcher.spans(&row.message) {
          out.push((h.color_index, start..end));
        }
      }
      // Line-number rules have no textual span in the matcher (§5); the
      // engine colors the whole message for the matching line instead.
      // spec interpretation: for an empty message this is the empty range
      // `0..0` — a zero-length span renders nothing, which matches the
      // "whole message" semantics (there is nothing to color).
      Rule::LineNo { line_no } => {
        if *line_no == row.line_no {
          out.push((h.color_index, 0..row.message.len()));
        }
      }
    }
  }
  out
}

#[cfg(test)]
mod tests {
  use super::*;
  use crate::matching::Matcher;
  use crate::parser::Row;
  use crate::parser::UNCATEGORIZED;

  /// A row with just what the highlight engine looks at (line_no, message).
  fn row(line_no: u32, message: &str) -> Row {
    Row {
      line_no,
      time_display: String::new(),
      category: UNCATEGORIZED.to_string(),
      level: crate::parser::Level::Msg,
      message: message.to_string(),
      raw: Vec::new(),
    }
  }

  fn r(v: &[(u8, usize, usize)]) -> Vec<(u8, std::ops::Range<usize>)> {
    v.iter().map(|&(c, s, e)| (c, s..e)).collect()
  }

  // ------------------------------------------------------------- palette

  #[test]
  fn add_assigns_colors_round_robin() {
    let mut e = HighlightEngine::new();
    for i in 0..PALETTE_SIZE {
      e.add(Rule::LineNo { line_no: (i + 1) as u32 });
      assert_eq!(e.rules()[i].color_index, i as u8, "rule {i}");
      assert!(e.rules()[i].enabled, "added rules are enabled by default");
    }
    // The 11th rule wraps back to color 0.
    e.add(Rule::LineNo { line_no: 99 });
    assert_eq!(e.rules()[10].color_index, 0);
  }

  #[test]
  fn rules_keeps_rule_order() {
    let mut e = HighlightEngine::new();
    e.add(Rule::Pattern { matcher: Matcher::plain("a") });
    e.add(Rule::Pattern { matcher: Matcher::regex("b") });
    e.add(Rule::LineNo { line_no: 1 });
    // Order is as added: plain, regex, line number.
    assert_eq!(e.rules().len(), 3);
    assert!(matches!(e.rules()[0].rule, Rule::Pattern { .. }), "rule 0 is a pattern");
    assert!(matches!(e.rules()[1].rule, Rule::Pattern { .. }), "rule 1 is a pattern");
    assert!(matches!(e.rules()[2].rule, Rule::LineNo { .. }), "rule 2 is hn");
  }

  // ------------------------------------------------------------- row_spans

  #[test]
  fn pattern_rules_locate_spans_in_message() {
    let mut e = HighlightEngine::new();
    e.add(Rule::Pattern { matcher: Matcher::plain("BOOM") });
    // Case-insensitive: both occurrences inside the message get spans.
    assert_eq!(
      row_spans(&e, &row(1, "Big BOOM then boom again")),
      r(&[(0, 4, 8), (0, 14, 18)])
    );
  }

  #[test]
  fn disabled_rule_emits_nothing() {
    let mut e = HighlightEngine::new();
    e.add(Rule::Pattern { matcher: Matcher::plain("boom") });
    e.set_enabled(0, false);
    assert_eq!(row_spans(&e, &row(1, "boom here")), Vec::new());
    // Back on: spans return.
    e.set_enabled(0, true);
    assert_eq!(row_spans(&e, &row(1, "boom here")), r(&[(0, 0, 4)]));
  }

  #[test]
  fn two_rules_overlap_in_rule_order() {
    let mut e = HighlightEngine::new();
    e.add(Rule::Pattern { matcher: Matcher::plain("boom") });
    e.add(Rule::Pattern { matcher: Matcher::regex("o{2}") });
    // Rule 1 spans first (color 0), then rule 2 spans (color 1); overlaps kept.
    assert_eq!(
      row_spans(&e, &row(1, "boom boom")),
      r(&[(0, 0, 4), (0, 5, 9), (1, 1, 3), (1, 6, 8)])
    );
  }

  #[test]
  fn line_no_rule_colors_whole_message_and_nothing_else() {
    let mut e = HighlightEngine::new();
    e.add(Rule::LineNo { line_no: 3 });
    // Line 3: one span over the entire message ("anything at all" = 15 bytes).
    assert_eq!(row_spans(&e, &row(3, "anything at all")), r(&[(0, 0, 15)]));
    // Other lines: nothing, even if the text matches nothing else.
    assert_eq!(row_spans(&e, &row(2, "anything at all")), Vec::new());
    assert_eq!(row_spans(&e, &row(4, "anything at all")), Vec::new());
  }

  #[test]
  fn simple_query_rules_locate_positive_term_spans() {
    let mut e = HighlightEngine::new();
    e.add(Rule::Pattern { matcher: Matcher::simple(r#""timeout""#) });
    assert_eq!(row_spans(&e, &row(1, "Timeout after 1s")), r(&[(0, 0, 7)]));
  }

  #[test]
  fn invalid_pattern_contributes_nothing() {
    let mut e = HighlightEngine::new();
    e.add(Rule::Pattern { matcher: Matcher::regex("(") });
    e.add(Rule::Pattern { matcher: Matcher::simple("error") }); // syntax error
    assert_eq!(row_spans(&e, &row(1, "error line with ( here")), Vec::new());
  }

  #[test]
  fn empty_message_gives_no_pattern_spans() {
    let mut e = HighlightEngine::new();
    e.add(Rule::Pattern { matcher: Matcher::plain("x") });
    assert_eq!(row_spans(&e, &row(1, "")), Vec::new());
  }

  #[test]
  fn line_no_on_empty_message_is_a_zero_length_span() {
    // spec interpretation: a line-number rule colors "the entire message",
    // which is 0..0 for an empty message; a zero-length span renders nothing
    // and the UI is free to skip it.
    let mut e = HighlightEngine::new();
    e.add(Rule::LineNo { line_no: 7 });
    assert_eq!(row_spans(&e, &row(7, "")), r(&[(0, 0, 0)]));
  }

  #[test]
  fn empty_engine_gives_no_spans() {
    let e = HighlightEngine::new();
    assert_eq!(row_spans(&e, &row(1, "anything")), Vec::new());
  }

  // ------------------------------------------------------------- lifecycle

  #[test]
  fn remove_shifts_indices_not_colors() {
    let mut e = HighlightEngine::new();
    e.add(Rule::LineNo { line_no: 1 }); // color 0
    e.add(Rule::LineNo { line_no: 2 }); // color 1
    e.add(Rule::LineNo { line_no: 3 }); // color 2
    e.remove(0);
    assert_eq!(e.rules().len(), 2);
    // The surviving rule keeps its color; its old line_no is now 0-based removed.
    assert!(matches!(e.rules()[0].rule, Rule::LineNo { line_no: 2 }));
    assert_eq!(e.rules()[0].color_index, 1, "surviving rule keeps its color");
    assert_eq!(e.rules()[1].color_index, 2);
    // The color sequence continues after removal: next is still color 3.
    e.add(Rule::LineNo { line_no: 4 });
    assert_eq!(e.rules()[2].color_index, 3);
  }

  #[test]
  fn remove_out_of_range_is_ignored() {
    let mut e = HighlightEngine::new();
    e.add(Rule::LineNo { line_no: 1 });
    e.remove(5); // no panic, no change
    assert_eq!(e.rules().len(), 1);
  }

  #[test]
  fn clear_removes_all_rules() {
    let mut e = HighlightEngine::new();
    for i in 0..4 {
      e.add(Rule::LineNo { line_no: (i + 1) as u32 });
    }
    e.clear();
    assert!(e.rules().is_empty(), "rmh removes all rules");
    assert_eq!(row_spans(&e, &row(1, "boom boom")), Vec::new());
  }

  #[test]
  fn set_enabled_out_of_range_is_ignored() {
    let mut e = HighlightEngine::new();
    e.set_enabled(3, true); // no panic
    assert!(e.rules().is_empty());
  }
}
