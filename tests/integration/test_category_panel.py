"""Tests for CategoryPanel widget."""

from __future__ import annotations

from textual.app import App, ComposeResult

from log_viewer.core.log_store import LogStore
from log_viewer.core.models import LogLevel
from log_viewer.tui.widgets.category_panel import CategoryPanel


SAMPLE_LINES = [
    "20-03-2026T12:20:42.258 LEECH/CORE version 5.18",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_ERROR Failed to open",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/st_game_storage LOG_ERROR Read failed",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/folder LOG_WARNING Missing file",
    "20-03-2026T12:20:42.258 PLATFORM win64",
    "20-03-2026T12:20:42.305 HordeMode/game_storage/st_game_storage LOG_DEBUG Debug info",
]


class CategoryPanelApp(App):
    """Test app with CategoryPanel."""

    CSS = """
    Screen {
        layout: horizontal;
    }
    """

    def __init__(self, store: LogStore) -> None:
        super().__init__()
        self.log_store = store

    def compose(self) -> ComposeResult:
        yield CategoryPanel(self.log_store)


def _make_store() -> LogStore:
    store = LogStore()
    store.load_lines(SAMPLE_LINES)
    return store


class TestCategoryPanelRendering:
    def test_category_panel_composes(self) -> None:
        app = CategoryPanelApp(_make_store())
        async def run() -> None:
            async with app.run_test():
                panel = app.query_one(CategoryPanel)
                assert panel is not None
        import asyncio
        asyncio.get_event_loop().run_until_complete(run())

    def test_category_panel_shows_root_label(self) -> None:
        app = CategoryPanelApp(_make_store())
        async def run() -> None:
            async with app.run_test():
                panel = app.query_one(CategoryPanel)
                # Root label should have icon and "Categories"
                label = str(panel.root.label)
                assert "Categories" in label
                assert "✅" in label
        import asyncio
        asyncio.get_event_loop().run_until_complete(run())

    def test_category_panel_has_top_level_nodes(self) -> None:
        app = CategoryPanelApp(_make_store())
        async def run() -> None:
            async with app.run_test():
                panel = app.query_one(CategoryPanel)
                panel.root.expand()
                children = panel.root.children
                names = {str(c.label) for c in children}
                # Should have HordeMode, LEECH, PLATFORM
                assert any("HordeMode" in str(c.label) for c in children)
                assert any("LEECH" in str(c.label) for c in children)
                assert any("PLATFORM" in str(c.label) for c in children)
        import asyncio
        asyncio.get_event_loop().run_until_complete(run())

    def test_category_panel_node_shows_line_count(self) -> None:
        app = CategoryPanelApp(_make_store())
        async def run() -> None:
            async with app.run_test():
                panel = app.query_one(CategoryPanel)
                panel.root.expand()
                children = list(panel.root.children)
                # HordeMode should show count (4 lines)
                horde_nodes = [c for c in children if "HordeMode" in str(c.label)]
                assert len(horde_nodes) == 1
                assert "(4)" in str(horde_nodes[0].label)
        import asyncio
        asyncio.get_event_loop().run_until_complete(run())

    def test_category_panel_enabled_icon(self) -> None:
        """Enabled categories show ✅."""
        app = CategoryPanelApp(_make_store())
        async def run() -> None:
            async with app.run_test():
                panel = app.query_one(CategoryPanel)
                panel.root.expand()
                children = list(panel.root.children)
                # All should be enabled by default → ✅
                for c in children:
                    assert "✅" in str(c.label)
        import asyncio
        asyncio.get_event_loop().run_until_complete(run())

    def test_category_panel_disabled_icon(self) -> None:
        """Disabled categories show ❌."""
        store = _make_store()
        store.disable_category("HordeMode")
        app = CategoryPanelApp(store)
        async def run() -> None:
            async with app.run_test():
                panel = app.query_one(CategoryPanel)
                panel.root.expand()
                children = list(panel.root.children)
                horde_nodes = [c for c in children if "HordeMode" in str(c.label)]
                assert "❌" in str(horde_nodes[0].label)
        import asyncio
        asyncio.get_event_loop().run_until_complete(run())


class TestCategoryPanelToggle:
    def test_select_node_toggles_category(self) -> None:
        """Clicking a node toggles its enabled state."""
        store = _make_store()
        app = CategoryPanelApp(store)
        async def run() -> None:
            async with app.run_test():
                panel = app.query_one(CategoryPanel)
                panel.root.expand()
                children = list(panel.root.children)
                horde_node = [c for c in children if "HordeMode" in str(c.label)][0]
                # Directly simulate the NodeSelected event
                event = CategoryPanel.NodeSelected(horde_node)
                panel.on_tree_node_selected(event)
                # Should be disabled now
                horde_cat = store.category_tree.children["HordeMode"]
                assert horde_cat.enabled is False
        import asyncio
        asyncio.get_event_loop().run_until_complete(run())

    def test_select_disabled_node_re_enables(self) -> None:
        """Clicking a disabled node re-enables it."""
        store = _make_store()
        store.disable_category("HordeMode")
        app = CategoryPanelApp(store)
        async def run() -> None:
            async with app.run_test():
                panel = app.query_one(CategoryPanel)
                panel.root.expand()
                children = list(panel.root.children)
                horde_node = [c for c in children if "HordeMode" in str(c.label)][0]
                event = CategoryPanel.NodeSelected(horde_node)
                panel.on_tree_node_selected(event)
                horde_cat = store.category_tree.children["HordeMode"]
                assert horde_cat.enabled is True
        import asyncio
        asyncio.get_event_loop().run_until_complete(run())


class TestCategoryPanelRebuild:
    def test_rebuild_updates_tree(self) -> None:
        """Rebuilding the panel reflects new category state."""
        store = _make_store()
        app = CategoryPanelApp(store)
        async def run() -> None:
            async with app.run_test():
                panel = app.query_one(CategoryPanel)
                panel.root.expand()
                # Disable a category externally
                store.disable_category("HordeMode")
                panel.rebuild()
                children = list(panel.root.children)
                horde_nodes = [c for c in children if "HordeMode" in str(c.label)]
                assert "❌" in str(horde_nodes[0].label)
        import asyncio
        asyncio.get_event_loop().run_until_complete(run())


class TestCategoryPanelClickRefreshesLogPanel:
    """Bug fix: clicking CategoryPanel must refresh LogPanel too."""

    def test_click_category_updates_log_panel_rows(self) -> None:
        """Clicking a node in CategoryPanel refreshes LogPanel rows."""
        from log_viewer.tui.app import LogViewerApp
        from log_viewer.tui.widgets.log_panel import LogPanel

        app = LogViewerApp()
        async def run() -> None:
            async with app.run_test():
                store = app.log_store
                store.load_lines(SAMPLE_LINES, file_path="test.log")
                app.refresh_log_panel()
                assert store.category_tree.children["HordeMode"].enabled is True

                cat_panel = app.query_one(CategoryPanel)
                cat_panel.root.expand()
                children = list(cat_panel.root.children)
                horde_node = [c for c in children if "HordeMode" in str(c.label)][0]
                event = CategoryPanel.NodeSelected(horde_node)
                cat_panel.on_tree_node_selected(event)

                # LogPanel should reflect the disabled category
                log_panel = app.query_one(LogPanel)
                assert log_panel.row_count == len(store.filtered_indices)
                # HordeMode has 4 lines, rest have 2 → should be 2 after disable
                assert log_panel.row_count == 2

        import asyncio
        asyncio.get_event_loop().run_until_complete(run())

    def test_toggle_preserves_expansion_state(self) -> None:
        """Clicking a child node preserves expansion of other nodes."""
        from log_viewer.tui.app import LogViewerApp

        app = LogViewerApp()
        async def run() -> None:
            async with app.run_test():
                store = app.log_store
                store.load_lines(SAMPLE_LINES, file_path="test.log")
                app.refresh_log_panel()

                cat_panel = app.query_one(CategoryPanel)
                cat_panel.root.expand()
                # Expand HordeMode to reveal children
                children = list(cat_panel.root.children)
                horde_node = [c for c in children if "HordeMode" in str(c.label)][0]
                horde_node.expand()

                # Toggle game_storage (child of HordeMode)
                horde_children = list(horde_node.children)
                gs_node = [c for c in horde_children if "game_storage" in str(c.label)][0]
                event = CategoryPanel.NodeSelected(gs_node)
                cat_panel.on_tree_node_selected(event)

                # HordeMode should still be expanded after rebuild
                children_after = list(cat_panel.root.children)
                horde_after = [c for c in children_after if "HordeMode" in str(c.label)][0]
                assert horde_after.is_expanded

        import asyncio
        asyncio.get_event_loop().run_until_complete(run())


class TestCategoryPanelRootToggle:
    """Clicking root 'Categories' node toggles all categories."""

    def test_root_click_disables_all(self) -> None:
        """Clicking root when all enabled → disables all, icon becomes ❌."""
        from log_viewer.tui.app import LogViewerApp
        from log_viewer.tui.widgets.log_panel import LogPanel

        app = LogViewerApp()
        async def run() -> None:
            async with app.run_test():
                store = app.log_store
                store.load_lines(SAMPLE_LINES, file_path="test.log")
                app.refresh_log_panel()
                assert len(store.filtered_indices) == 6

                cat_panel = app.query_one(CategoryPanel)
                # Root should show ✅ initially
                assert "✅" in str(cat_panel.root.label)

                event = CategoryPanel.NodeSelected(cat_panel.root)
                cat_panel.on_tree_node_selected(event)

                assert len(store.filtered_indices) == 0
                # Root should now show ❌
                assert "❌" in str(cat_panel.root.label)

        import asyncio
        asyncio.get_event_loop().run_until_complete(run())

    def test_root_click_enables_all(self) -> None:
        """Clicking root when some disabled → enables all."""
        from log_viewer.tui.app import LogViewerApp

        app = LogViewerApp()
        async def run() -> None:
            async with app.run_test():
                store = app.log_store
                store.load_lines(SAMPLE_LINES, file_path="test.log")
                app.refresh_log_panel()
                store.disable_category("HordeMode")
                app.refresh_log_panel()
                assert len(store.filtered_indices) == 2

                cat_panel = app.query_one(CategoryPanel)
                event = CategoryPanel.NodeSelected(cat_panel.root)
                cat_panel.on_tree_node_selected(event)

                assert len(store.filtered_indices) == 6

        import asyncio
        asyncio.get_event_loop().run_until_complete(run())
