"""Category tree widget with checkboxes and search."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from log_viewer.core.models import CategoryNode


class CategoryTreeWidget(QWidget):
    """Tree widget for category filtering with checkboxes and search."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search categories...")
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._tree)

        self._root: CategoryNode | None = None

    def rebuild(self, root: CategoryNode) -> None:
        """Rebuild the tree from the given CategoryNode hierarchy."""
        self._tree.blockSignals(True)
        self._tree.clear()
        self._root = root

        all_item = QTreeWidgetItem(self._tree, ["All"])
        all_item.setCheckState(0, Qt.CheckState.Checked)
        all_item.setData(0, Qt.ItemDataRole.UserRole, "__all__")

        for name in sorted(root.children):
            child_node = root.children[name]
            child_item = QTreeWidgetItem(
                all_item, [f"{child_node.name} ({child_node.line_count})"]
            )
            child_item.setData(0, Qt.ItemDataRole.UserRole, child_node.full_path)
            child_item.setCheckState(
                0,
                Qt.CheckState.Checked if child_node.enabled else Qt.CheckState.Unchecked,
            )
            self._add_children(child_item, child_node)

        all_item.setExpanded(True)
        self._tree.blockSignals(False)

    def _add_children(self, parent_item: QTreeWidgetItem, node: CategoryNode) -> None:
        """Recursively add child items from a CategoryNode."""
        for name in sorted(node.children):
            child_node = node.children[name]
            child_item = QTreeWidgetItem(
                parent_item, [f"{child_node.name} ({child_node.line_count})"]
            )
            child_item.setData(0, Qt.ItemDataRole.UserRole, child_node.full_path)
            child_item.setCheckState(
                0,
                Qt.CheckState.Checked if child_node.enabled else Qt.CheckState.Unchecked,
            )
            self._add_children(child_item, child_node)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle checkbox state changes — propagate to children and parent."""
        if column != 0:
            return

        role_data = item.data(0, Qt.ItemDataRole.UserRole)

        # If "All" item changed, propagate to all children
        if role_data == "__all__":
            state = item.checkState(0)
            self._tree.blockSignals(True)
            self._set_children_checkstate(item, state)
            self._tree.blockSignals(False)
            return

        self._update_parent_check(item)

    def _set_children_checkstate(
        self, parent: QTreeWidgetItem, state: Qt.CheckState
    ) -> None:
        """Recursively set all children to the given check state."""
        for i in range(parent.childCount()):
            child = parent.child(i)
            child.setCheckState(0, state)
            self._set_children_checkstate(child, state)

    def _update_parent_check(self, item: QTreeWidgetItem) -> None:
        """Propagate checkbox state upward — all/partial/none."""
        parent = item.parent()
        if parent is None:
            return

        checked = 0
        partially = 0
        total = parent.childCount()

        for i in range(total):
            state = parent.child(i).checkState(0)
            if state == Qt.CheckState.Checked:
                checked += 1
            elif state == Qt.CheckState.PartiallyChecked:
                partially += 1

        self._tree.blockSignals(True)
        if partially > 0 or (0 < checked < total):
            parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
        elif checked == total:
            parent.setCheckState(0, Qt.CheckState.Checked)
        else:
            parent.setCheckState(0, Qt.CheckState.Unchecked)
        self._tree.blockSignals(False)

        self._update_parent_check(parent)

    def _on_search(self, text: str) -> None:
        """Filter tree items by search text."""
        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            top = root.child(i)
            self._filter_item(top, text.lower())
        self._tree.expandAll()

    def _filter_item(self, item: QTreeWidgetItem, text: str) -> bool:
        """Hide items that don't match. Returns True if item or any descendant matches."""
        matches_self = text in item.text(0).lower()

        any_child_match = False
        for i in range(item.childCount()):
            if self._filter_item(item.child(i), text):
                any_child_match = True

        visible = matches_self or any_child_match or not text
        item.setHidden(not visible)
        return visible

    def set_filter(self, text: str) -> None:
        """Set the search filter text."""
        self._search.setText(text)

    def get_disabled_paths(self) -> list[str]:
        """Return full_path values for all unchecked items."""
        result: list[str] = []
        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            self._collect_disabled(root.child(i), result)
        return result

    def _collect_disabled(
        self, item: QTreeWidgetItem, result: list[str]
    ) -> None:
        """Recursively collect full_path values for unchecked items."""
        role_data = item.data(0, Qt.ItemDataRole.UserRole)
        if (
            item.checkState(0) == Qt.CheckState.Unchecked
            and role_data != "__all__"
        ):
            path = role_data
            if isinstance(path, str) and path:
                result.append(path)

        for i in range(item.childCount()):
            self._collect_disabled(item.child(i), result)
