//! logviewer-core: pure application logic for Log Viewer.
//!
//! Everything that can be tested headless lives here: file scanning, line
//! parsing, match engine, visibility semantics, settings storage. No UI,
//! no threads, no IPC dependencies (see docs/STACK.md).

pub mod categories;
pub mod format;
pub mod highlights;
pub mod matching;
pub mod parser;
pub mod scanner;
pub mod settings;
pub mod simple_query;
pub mod visibility;
pub mod workspace;

pub use format::Format;
pub use scanner::{build_offsets, format_from_reader, Scanner};

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Version string reported to the UI over IPC (scaffold smoke check).
pub fn version() -> String {
  VERSION.to_owned()
}

#[cfg(test)]
mod tests {
  use super::*;

  #[test]
  fn version_is_semver_like() {
    let v = version();
    assert!(!v.is_empty());
    assert!(v.split('.').count() >= 2, "version looks like x.y: {v}");
  }
}
