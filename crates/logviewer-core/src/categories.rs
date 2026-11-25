//! Category tree (FUNCTIONAL_SPEC §10).
//!
//! Categories are extracted at parse time (§3) and are hierarchical by `/`
//! (§16). This module builds the side-panel tree: a synthetic root whose
//! children are the top-level categories. Owner decision 2026-11-25
//! (log_viewer2-7u9): nodes carry no row counts — the tree is a shape only.
//! Checkbox state lives in the UI task (rhl.2) — this module is a pure tree,
//! no selection semantics.

use std::collections::BTreeMap;

use crate::parser::UNCATEGORIZED;
use crate::workspace::FileModel;

/// One node of the category tree.
pub struct CategoryNode {
  /// Path segment of this node (root has the empty string).
  pub name: String,
  /// Full path `app/main/db` (root: empty).
  pub path: String,
  /// Children sorted by name byte-order, deterministic across rebuilds.
  pub children: Vec<CategoryNode>,
}

/// Build the tree from a loaded model. The synthetic root holds top-level
/// categories (and uncategorized as a child) — the UI renders root children.
// spec interpretation: the uncategorized node is emitted as the FIRST child of
// the root, named `uncategorized` (parser::UNCATEGORIZED), deterministically
// ahead of the alphabetically sorted real categories. It is present when the
// file logs the `uncategorized` path or a deeper `uncategorized/...` category
// exists; an empty model yields no children at all.
pub fn build(model: &FileModel) -> CategoryNode {
  // Intermediate trie keyed by segment in a BTreeMap, so child order falls
  // out byte-sorted and rebuilds are deterministic.
  let mut trie = Trie::default();
  let mut unc_path_seen = false;
  for path in model.categories() {
    if path == UNCATEGORIZED {
      // The parser maps missing categories to this path, so it is the
      // fallback bucket, never a real branch of the tree.
      unc_path_seen = true;
      continue;
    }
    trie.insert(path);
  }
  // spec interpretation: a literal top-level `uncategorized` category is
  // indistinguishable from the fallback bucket from the model's side, so any
  // real `uncategorized/...` branch is folded under the same bucket node.
  let unc_branch = trie.children.remove(UNCATEGORIZED);

  let mut root = CategoryNode {
    name: String::new(),
    path: String::new(),
    children: trie.into_children(""),
  };
  // spec interpretation: the uncategorized node goes first, ahead of the
  // sorted categories, and is omitted when nothing falls into the bucket and
  // no `uncategorized/...` category exists.
  if unc_path_seen || unc_branch.is_some() {
    let bucket = unc_branch.unwrap_or_default();
    let children = bucket.into_children(UNCATEGORIZED);
    root.children.insert(
      0,
      CategoryNode {
        name: UNCATEGORIZED.to_string(),
        path: UNCATEGORIZED.to_string(),
        children,
      },
    );
  }
  root
}

/// Build-time trie keyed by category segment; only the tree shape, no counts
/// (owner decision 2026-11-25: the per-node row counters are gone).
#[derive(Default)]
struct Trie {
  children: BTreeMap<String, Trie>,
}

impl Trie {
  /// Insert one full category path; empty segments are kept verbatim
  /// (spec interpretation: `//` is invalid input, no collapsing is done).
  fn insert(&mut self, path: &str) {
    let mut full = String::new();
    let mut node = self;
    for segment in path.split('/') {
      if !full.is_empty() {
        full.push('/');
      }
      full.push_str(segment);
      node = node.children.entry(segment.to_string()).or_default();
    }
  }

  /// Convert into `CategoryNode`s; `parent_path` is the full path of this
  /// trie level (empty for the root).
  fn into_children(self, parent_path: &str) -> Vec<CategoryNode> {
    self
      .children
      .into_iter()
      .map(|(name, child)| {
        let path = if parent_path.is_empty() {
          name.clone()
        } else {
          format!("{parent_path}/{name}")
        };
        CategoryNode {
          children: child.into_children(&path),
          name,
          path,
        }
      })
      .collect()
  }
}

#[cfg(test)]
mod tests {
  use super::*;

  // ---------------------------------------------------------------- helpers

  /// Load a KSIVA-format log from a temp file (unique name per test).
  fn model_of(name: &str, body: &str) -> FileModel {
    let path = std::env::temp_dir().join(name);
    std::fs::write(&path, body).unwrap();
    FileModel::load_path(&path).unwrap().0
  }

  /// Byte-path of a node, e.g. "app/main": names joined by `/` (root: "").
  fn names(node: &CategoryNode) -> Vec<&str> {
    node.children.iter().map(|c| c.name.as_str()).collect()
  }

  fn child<'a>(node: &'a CategoryNode, name: &str) -> &'a CategoryNode {
    node
      .children
      .iter()
      .find(|c| c.name == name)
      .unwrap_or_else(|| panic!("no child {name:?} under {:?}", node.path))
  }

  // ------------------------------------------------------------- tests

  #[test]
  fn category_tree_nested_chain_shapes() {
    let model = model_of(
      "lv_cat_chain.log",
      concat!(
        "2024-01-01T10:00:00.000 app/main LOG_MSG a\n",
        "2024-01-01T10:00:01.000 app/main/db LOG_ERR b\n",
        "2024-01-01T10:00:02.000 app LOG_TRC c\n",
        "2024-01-01T10:00:03.000 app/main/db LOG_MSG d\n",
        "2024-01-01T10:00:04.000 solo\n",
        "2024-01-01T10:00:05.000 another\n",
      ),
    );
    let root = build(&model);
    assert_eq!(root.name, "");
    assert_eq!(root.path, "");
    // Uncategorized node first, then top-level categories byte-sorted.
    assert_eq!(names(&root), vec!["uncategorized", "app"]);
    assert_eq!(child(&root, "uncategorized").path, "uncategorized");
    assert!(child(&root, "uncategorized").children.is_empty());
    // Chain app -> main -> db.
    let app = child(&root, "app");
    assert_eq!(app.path, "app");
    let main = child(app, "main");
    assert_eq!(main.path, "app/main");
    let db = child(main, "db");
    assert_eq!(db.path, "app/main/db");
    assert!(db.children.is_empty());
  }

  #[test]
  fn category_tree_ordering_is_byte_order() {
    let model = model_of(
      "lv_cat_order.log",
      concat!(
        "2024-01-01T10:00:00.000 B LOG_MSG x\n",
        "2024-01-01T10:00:01.000 a LOG_MSG y\n",
        "2024-01-01T10:00:02.000 B/x LOG_MSG z\n",
        "2024-01-01T10:00:03.000 a/m LOG_MSG w\n",
      ),
    );
    let root = build(&model);
    // "B" (0x42) sorts before "a" (0x61) in byte order; no uncategorized row.
    assert_eq!(names(&root), vec!["B", "a"]);
    assert_eq!(names(child(&root, "B")), vec!["x"]);
    assert_eq!(names(child(&root, "a")), vec!["m"]);
  }

  #[test]
  fn category_tree_interior_nodes() {
    let model = model_of(
      "lv_cat_interior.log",
      concat!(
        "2024-01-01T10:00:00.000 x/y LOG_MSG a\n",
        "2024-01-01T10:00:01.000 x/z LOG_MSG b\n",
        "2024-01-01T10:00:02.000 x/z LOG_MSG c\n",
      ),
    );
    let root = build(&model);
    let x = child(&root, "x");
    // "x" has no rows of its own path; the node exists as an interior node.
    assert_eq!(names(x), vec!["y", "z"]);
  }

  #[test]
  fn category_tree_empty_model() {
    let model = model_of("lv_cat_empty.log", "");
    assert_eq!(model.line_count(), 0);
    let root = build(&model);
    assert_eq!(root.name, "");
    assert_eq!(root.path, "");
    assert!(root.children.is_empty());
  }

  #[test]
  fn category_tree_only_uncategorized() {
    let model = model_of(
      "lv_cat_unc_only.log",
      concat!(
        "2024-01-01T10:00:00.000 solo\n",
        "2024-01-01T10:00:01.000\n", // single field: uncategorized, empty msg
      ),
    );
    let root = build(&model);
    assert_eq!(names(&root), vec!["uncategorized"]);
    assert!(child(&root, "uncategorized").children.is_empty());
  }

  #[test]
  fn category_tree_empty_segments_kept_verbatim() {
    // spec interpretation: `//` is invalid input; each `/`-segment is kept
    // as-is with no collapsing, so `app//main` nests app -> "" -> main.
    let model = model_of(
      "lv_cat_empty_seg.log",
      "2024-01-01T10:00:00.000 app//main LOG_MSG x\n",
    );
    let root = build(&model);
    let app = child(&root, "app");
    let empty = child(app, "");
    let main = child(empty, "main");
    assert_eq!(main.path, "app//main");
  }

  #[test]
  fn category_tree_uncategorized_sub_category_merge() {
    // spec interpretation: literal top-level `uncategorized` rows are the
    // fallback bucket (parser maps missing categories there), so a deeper
    // `uncategorized/...` branch hangs under the same bucket node.
    let model = model_of(
      "lv_cat_unc_sub.log",
      concat!(
        "2024-01-01T10:00:00.000 uncategorized/sub LOG_MSG a\n",
        "2024-01-01T10:00:01.000 plainrow\n",
      ),
    );
    let root = build(&model);
    assert_eq!(names(&root), vec!["uncategorized"]); // bucket first, no dup
    let bucket = child(&root, "uncategorized");
    assert_eq!(names(bucket), vec!["sub"]);
  }
}
