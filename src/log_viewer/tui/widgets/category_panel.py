"""CategoryPanel — Tree widget showing category hierarchy with enable/disable toggles."""

from __future__ import annotations

from typing import Optional

from textual.widgets import Tree

from log_viewer.core.log_store import LogStore
from log_viewer.core.models import CategoryNode


class CategoryPanel(Tree[str]):
    """Side panel showing the category tree with ✅/❌ icons.

    Click a node name to toggle its enabled/disabled state.
    Click arrows to expand/collapse.
    """

    DEFAULT_CSS = """
    CategoryPanel {
        width: 1fr;
        min-width: 20;
        border-left: solid $primary;
        background: $surface;
    }
    """

    def __init__(self, store: LogStore) -> None:
        super().__init__("Categories")
        self.log_store = store
        self._node_paths: dict[str, object] = {}  # path -> TreeNode id mapping

    def on_mount(self) -> None:
        self._build_tree()

    def _build_tree(self) -> None:
        """Populate tree from LogStore category hierarchy, preserving expansion state."""
        expanded = self._collect_expanded()
        self.root.remove_children()
        self._node_paths.clear()
        # Update root label with icon reflecting all-categories state
        tree = self.log_store.category_tree
        all_enabled = all(c.enabled for c in tree.children.values()) if tree.children else True
        icon = "✅" if all_enabled else "❌"
        self.root.set_label(f"{icon} Categories ({tree.line_count})")
        self.root.allow_expand = False
        self._add_nodes(self.root, self.log_store.category_tree)
        self.root.expand()
        self._restore_expanded(expanded)

    def _collect_expanded(self) -> set[str]:
        """Collect paths of all currently expanded nodes."""
        expanded: set[str] = set()
        for path, node_id in self._node_paths.items():
            try:
                node = self.root.tree.get_node_by_id(node_id)
                if node is not None and node.is_expanded:
                    expanded.add(path)
            except Exception:
                pass
        return expanded

    def _restore_expanded(self, paths: set[str]) -> None:
        """Expand nodes matching the given paths."""
        for path in paths:
            node_id = self._node_paths.get(path)
            if node_id is not None:
                try:
                    node = self.root.tree.get_node_by_id(node_id)
                    if node is not None:
                        node.expand()
                except Exception:
                    pass

    def _add_nodes(self, parent: Tree.Node, cat_node: CategoryNode) -> None:
        """Recursively add tree nodes from category tree."""
        for name, child in sorted(cat_node.children.items()):
            icon = "✅" if child.enabled else "❌"
            label = f"{icon} {name} ({child.line_count})"
            node = parent.add(label, data=child.full_path, allow_expand=True)
            self._node_paths[child.full_path] = node.id
            if child.children:
                self._add_nodes(node, child)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Toggle category enabled state when a node is selected."""
        event.stop()
        path = event.node.data
        if path is None:
            # Root node clicked — toggle all categories
            self._toggle_all()
            self._refresh_app()
            return
        # Find the category node and toggle
        cat_node = self.log_store._find_category_node(path)
        if cat_node is None:
            return
        if cat_node.enabled:
            self.log_store.disable_category(path)
        else:
            self.log_store.enable_category(path)
        self._refresh_app()

    def _toggle_all(self) -> None:
        """Toggle all categories: disable if all enabled, enable otherwise."""
        tree = self.log_store.category_tree
        all_enabled = all(c.enabled for c in tree.children.values())
        if all_enabled:
            self.log_store.disable_all_categories()
        else:
            self.log_store.enable_all_categories()

    def _refresh_app(self) -> None:
        """Trigger full app refresh (LogPanel + CategoryPanel + StatusBar)."""
        try:
            from log_viewer.tui.app import LogViewerApp

            app = self.app
            if isinstance(app, LogViewerApp):
                app.refresh_log_panel()
        except Exception:
            self.rebuild()

    def rebuild(self) -> None:
        """Rebuild the tree from current LogStore state."""
        self._build_tree()
