//! Log line format (FUNCTIONAL_SPEC §3).

/// The two supported formats, auto-detected at load time.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Format {
  /// "KSIVA": timestamp category [LOG_LEVEL] message
  Ksiva,
  /// "PLAIN": time elapsed level_short category message
  Plain,
}
