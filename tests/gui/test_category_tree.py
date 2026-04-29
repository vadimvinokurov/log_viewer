"""Tests for CategoryTreeWidget."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from log_viewer.core.models import CategoryNode
from log_viewer.gui.category_tree import CategoryTreeWidget


def _build_tree() -> CategoryNode:
    root = CategoryNode(name="root", full_path="")
    app = CategoryNode(name="app", full_path="app", enabled=True, line_count=5)
    api = CategoryNode(name="api", full_path="app/api", enabled=True, line_count=2)
    db = CategoryNode(name="db", full_path="app/db", enabled=True, line_count=1)
    err = CategoryNode(name="error", full_path="app/error", enabled=True, line_count=1)
    app.children = {"api": api, "db": db, "error": err}
    sys_node = CategoryNode(name="sys", full_path="sys", enabled=True, line_count=1)
    root.children = {"app": app, "sys": sys_node}
    return root


@pytest.fixture
def cat_tree(qtbot) -> CategoryTreeWidget:
    tree = CategoryTreeWidget()
    qtbot.addWidget(tree)
    return tree


def test_rebuild_populates_tree(cat_tree: CategoryTreeWidget) -> None:
    root = _build_tree()
    cat_tree.rebuild(root)
    assert cat_tree._tree.topLevelItemCount() == 1


def test_all_node_exists(cat_tree: CategoryTreeWidget) -> None:
    root = _build_tree()
    cat_tree.rebuild(root)
    all_item = cat_tree._tree.topLevelItem(0)
    assert all_item is not None
    assert "All" in all_item.text(0)


def test_get_disabled_paths_initially_empty(cat_tree: CategoryTreeWidget) -> None:
    root = _build_tree()
    cat_tree.rebuild(root)
    assert cat_tree.get_disabled_paths() == []


def test_unchecking_all_disables_all_paths(cat_tree: CategoryTreeWidget) -> None:
    root = _build_tree()
    cat_tree.rebuild(root)
    all_item = cat_tree._tree.topLevelItem(0)
    all_item.setCheckState(0, Qt.CheckState.Unchecked)
    disabled = cat_tree.get_disabled_paths()
    assert "app" in disabled
    assert "sys" in disabled


def test_unchecking_child_propagates_to_partial(cat_tree: CategoryTreeWidget) -> None:
    root = _build_tree()
    cat_tree.rebuild(root)
    all_item = cat_tree._tree.topLevelItem(0)

    # Find "sys" child under "All"
    sys_item = None
    for i in range(all_item.childCount()):
        child = all_item.child(i)
        if "sys" in child.text(0).lower():
            sys_item = child
            break

    assert sys_item is not None
    sys_item.setCheckState(0, Qt.CheckState.Unchecked)
    assert all_item.checkState(0) == Qt.CheckState.PartiallyChecked


def test_search_filters_items(cat_tree: CategoryTreeWidget) -> None:
    root = _build_tree()
    cat_tree.rebuild(root)
    cat_tree._on_search("sys")

    all_item = cat_tree._tree.topLevelItem(0)
    assert not all_item.isHidden()

    # "sys" item should be visible, "app" item should be hidden
    # (unless "app" has matching descendants, but "sys" text doesn't match "app")
    found_visible = []
    for i in range(all_item.childCount()):
        child = all_item.child(i)
        if not child.isHidden():
            found_visible.append(child.text(0))

    assert any("sys" in t.lower() for t in found_visible)


def test_set_filter_updates_search(cat_tree: CategoryTreeWidget) -> None:
    root = _build_tree()
    cat_tree.rebuild(root)
    cat_tree.set_filter("api")
    assert cat_tree._search.text() == "api"


def test_rebuild_with_disabled_node(cat_tree: CategoryTreeWidget) -> None:
    root = CategoryNode(name="root", full_path="")
    on = CategoryNode(name="on", full_path="on", enabled=True, line_count=1)
    off = CategoryNode(name="off", full_path="off", enabled=False, line_count=2)
    root.children = {"on": on, "off": off}

    cat_tree.rebuild(root)
    disabled = cat_tree.get_disabled_paths()
    assert "off" in disabled
    assert "on" not in disabled
