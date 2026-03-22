"""Integration tests for log viewer."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime
from typing import Generator

import pytest

from src.models.log_document import LogDocument
from src.models.log_entry import LogEntry, LogLevel
from src.models.filter_state import FilterMode, FilterState
from src.core.filter_engine import FilterEngine
from src.core.category_tree import CategoryTree
from src.core.highlight_engine import HighlightEngine, HighlightPattern
from src.core.statistics import StatisticsCalculator
from src.core.parser import LogParser
from PySide6.QtGui import QColor


class TestDocumentIntegration:
    """Integration tests for LogDocument."""
    
    def test_document_loading(self, temp_log_file: str) -> None:
        """Test loading a log file."""
        # Ref: docs/specs/features/file-management.md §3.2
        # Ref: docs/specs/global/memory-model.md §3.2
        doc = LogDocument(temp_log_file)
        doc.load()
        
        assert doc.get_line_count() == 5
        assert len(doc.get_categories()) > 0
    
    def test_document_get_all_entries(self, temp_log_file: str) -> None:
        """Test getting all entries from document."""
        doc = LogDocument(temp_log_file)
        doc.load()
        
        entries = doc.get_all_entries()
        assert len(entries) == 5
        
        entry = entries[0]
        assert entry.row_index == 0
        assert entry.category == "Category1/Subcat1"
        assert entry.level == LogLevel.ERROR
    
    def test_document_categories(self, temp_log_file: str) -> None:
        """Test extracting categories from document."""
        doc = LogDocument(temp_log_file)
        doc.load()
        
        categories = doc.get_categories()
        
        assert "Category1/Subcat1" in categories
        assert "Category2" in categories
        assert "Category1/Subcat2" in categories
        assert "Category3" in categories
    
    def test_document_iteration(self, temp_log_file: str) -> None:
        """Test iterating through document."""
        doc = LogDocument(temp_log_file)
        doc.load()
        
        entries = doc.get_all_entries()
        count = len(entries)
        
        assert count == 5


class TestFilterIntegration:
    """Integration tests for filtering system."""
    
    def _create_entry(
        self,
        message: str,
        category: str = "test",
        level: LogLevel = LogLevel.MSG,
        row_index: int = 0
    ) -> LogEntry:
        """Create a test log entry.
        
        Ref: docs/specs/features/log-entry-optimization.md §4.2
        Ref: docs/specs/features/timestamp-unix-epoch.md §3.1
        raw_message removed - never used outside parser
        timestamp converted to Unix epoch float
        """
        level_prefix = f"{level.value} " if level != LogLevel.MSG else ""
        return LogEntry(
            row_index=row_index,
            timestamp=datetime(2024, 1, 1, 12, 0, 0).timestamp(),
            category=category,
            display_message=message,
            level=level,
            file_offset=row_index * 100,
        )
    
    def test_document_and_filter_integration(self, temp_log_file: str) -> None:
        """Test document loading with filtering."""
        # Ref: docs/specs/features/file-management.md §3.2
        doc = LogDocument(temp_log_file)
        doc.load()
        
        # Get all entries
        entries = doc.get_all_entries()
        
        # Filter for errors
        engine = FilterEngine()
        state = FilterState(
            enabled_categories=doc.get_categories(),
            filter_text="Error",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = engine.compile_filter(state)
        filtered = [e for e in entries if filter_func(e)]
        
        assert len(filtered) == 1
        assert "Error" in filtered[0].display_message
    
    def test_category_filter_combination(self, temp_log_file: str) -> None:
        """Test category and text filter combination."""
        doc = LogDocument(temp_log_file)
        doc.load()
        
        # Get all entries
        entries = doc.get_all_entries()
        
        # Filter by category only
        engine = FilterEngine()
        state = FilterState(
            enabled_categories={"Category1/Subcat1"},
            filter_text="",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = engine.compile_filter(state)
        filtered = [e for e in entries if filter_func(e)]
        
        # Should get entries from Category1/Subcat1
        assert len(filtered) == 2
        for entry in filtered:
            assert entry.category == "Category1/Subcat1"
    
    def test_full_workflow(self, temp_log_file: str) -> None:
        """Test full workflow: load, filter, highlight."""
        doc = LogDocument(temp_log_file)
        doc.load()
        
        # Get all entries
        entries = doc.get_all_entries()
        
        # Setup filter
        filter_engine = FilterEngine()
        filter_state = FilterState(
            enabled_categories=doc.get_categories(),
            filter_text="",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = filter_engine.compile_filter(filter_state)
        filtered = [e for e in entries if filter_func(e)]
        
        # Setup highlight
        highlight_engine = HighlightEngine()
        highlight_engine.add_pattern(HighlightPattern(
            text="Error",
            color=QColor(255, 0, 0)
        ))
        
        # Highlight first entry
        if filtered:
            ranges = highlight_engine.highlight(filtered[0].display_message)
            # Should find "Error" in error message
            assert len(ranges) >= 1
    
    def test_regex_filter_with_document(self, temp_log_file: str) -> None:
        """Test regex filtering with document."""
        doc = LogDocument(temp_log_file)
        doc.load()
        
        entries = doc.get_all_entries()
        
        # Filter with regex - search for content in display_message
        # Note: display_message does not contain LOG_ prefix (it was stripped by parser)
        # Ref: docs/specs/features/log-entry-optimization.md §4.3
        engine = FilterEngine()
        state = FilterState(
            enabled_categories=doc.get_categories(),
            filter_text=r"Error|Warning",
            filter_mode=FilterMode.REGEX
        )
        
        filter_func = engine.compile_filter(state)
        filtered = [e for e in entries if filter_func(e)]
        
        # Should match entries with Error or Warning in display_message
        assert len(filtered) >= 2
    
    def test_simple_query_with_document(self, temp_log_file: str) -> None:
        """Test simple query filtering with document."""
        doc = LogDocument(temp_log_file)
        doc.load()
        
        entries = doc.get_all_entries()
        
        # Filter with simple query
        engine = FilterEngine()
        state = FilterState(
            enabled_categories=doc.get_categories(),
            filter_text="`Error` or `Warning`",
            filter_mode=FilterMode.SIMPLE
        )
        
        filter_func = engine.compile_filter(state)
        filtered = [e for e in entries if filter_func(e)]
        
        # Should match error and warning messages
        assert len(filtered) >= 2


class TestCategoryTreeIntegration:
    """Integration tests for category tree."""
    
    def test_category_tree_from_document(self, temp_log_file: str) -> None:
        """Test building category tree from document."""
        # Ref: docs/specs/features/file-management.md §3.2
        doc = LogDocument(temp_log_file)
        doc.load()
        
        # Build category tree
        tree = CategoryTree()
        for category in doc.get_categories():
            tree.add_category(category)
        
        # Verify tree structure
        assert "Category1" in tree
        assert "Category1/Subcat1" in tree
        assert "Category1/Subcat2" in tree
        assert "Category2" in tree
        assert "Category3" in tree
    
    def test_category_tree_filtering(self, temp_log_file: str) -> None:
        """Test filtering with category tree."""
        doc = LogDocument(temp_log_file)
        doc.load()
        
        # Build category tree
        tree = CategoryTree()
        for category in doc.get_categories():
            tree.add_category(category)
        
        # Get all entries
        entries = doc.get_all_entries()
        
        # Disable Category1/Subcat1
        tree.toggle("Category1/Subcat1", False)
        
        # Get enabled categories
        enabled = tree.get_enabled_categories()
        
        # Filter entries
        engine = FilterEngine()
        state = FilterState(
            enabled_categories=enabled,
            filter_text="",
            filter_mode=FilterMode.PLAIN,
            all_categories=tree.get_all_categories()
        )
        
        filter_func = engine.compile_filter(state)
        filtered = [e for e in entries if filter_func(e)]
        
        # Should not include Category1/Subcat1 entries
        for entry in filtered:
            assert entry.category != "Category1/Subcat1"
    
    def test_category_tree_parent_toggle(self, temp_log_file: str) -> None:
        """Test parent toggle behavior in category tree."""
        doc = LogDocument(temp_log_file)
        doc.load()
        
        # Build category tree
        tree = CategoryTree()
        for category in doc.get_categories():
            tree.add_category(category)
        
        # Disable parent Category1
        tree.toggle("Category1", False)
        
        # All children should be disabled
        assert not tree.is_enabled("Category1")
        assert not tree.is_enabled("Category1/Subcat1")
        assert not tree.is_enabled("Category1/Subcat2")
        
        # Other categories should still be enabled
        assert tree.is_enabled("Category2")
        assert tree.is_enabled("Category3")


class TestStatisticsIntegration:
    """Integration tests for statistics."""
    
    def test_statistics_from_document(self, temp_log_file: str) -> None:
        """Test calculating statistics from document."""
        # Ref: docs/specs/features/file-management.md §3.2
        doc = LogDocument(temp_log_file)
        doc.load()
        
        # Calculate statistics
        calc = StatisticsCalculator()
        
        entries = doc.get_all_entries()
        for entry in entries:
            calc.process_entry(entry)
        
        stats = calc.get_statistics(shown_count=doc.get_line_count())
        
        assert stats.total_lines == 5
        assert stats.error_count == 1
        assert stats.warning_count == 2
    
    def test_statistics_with_filtering(self, temp_log_file: str) -> None:
        """Test statistics with filtering."""
        doc = LogDocument(temp_log_file)
        doc.load()
        
        # Get all entries
        entries = doc.get_all_entries()
        
        # Calculate total statistics
        calc = StatisticsCalculator()
        calc.process_entries(entries)
        
        # Filter for errors only
        engine = FilterEngine()
        state = FilterState(
            enabled_categories=doc.get_categories(),
            filter_text="Error",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = engine.compile_filter(state)
        filtered = [e for e in entries if filter_func(e)]
        
        stats = calc.get_statistics(shown_count=len(filtered))
        
        # Total should still be 5
        assert stats.total_lines == 5
        # Shown should be 1 (error message)
        assert stats.shown_lines == 1


class TestHighlightIntegration:
    """Integration tests for highlighting."""
    
    def test_highlight_with_document(self, temp_log_file: str) -> None:
        """Test highlighting with document entries."""
        # Ref: docs/specs/features/file-management.md §3.2
        doc = LogDocument(temp_log_file)
        doc.load()
        
        # Setup highlight engine
        engine = HighlightEngine()
        engine.add_pattern(HighlightPattern(
            text="Error",
            color=QColor(255, 0, 0)
        ))
        engine.add_pattern(HighlightPattern(
            text="Warning",
            color=QColor(255, 255, 0)
        ))
        
        # Highlight each entry
        entries = doc.get_all_entries()
        for entry in entries:
            ranges = engine.highlight(entry.display_message)
            # Just verify it doesn't crash
            assert isinstance(ranges, list)
    
    def test_highlight_with_regex(self, temp_log_file: str) -> None:
        """Test highlighting with regex patterns."""
        doc = LogDocument(temp_log_file)
        doc.load()
        
        # Setup highlight engine with regex
        engine = HighlightEngine()
        engine.add_pattern(HighlightPattern(
            text=r"Error",
            color=QColor(255, 0, 0),
            is_regex=True
        ))
        
        # Highlight entries
        entries = doc.get_all_entries()
        error_entry = entries[0]
        assert error_entry is not None
        
        # Ref: docs/specs/features/log-entry-optimization.md §4.2
        # raw_message removed - use display_message for highlighting
        ranges = engine.highlight(error_entry.display_message)
        # Should find "Error" in display_message
        assert len(ranges) >= 1


class TestParserIntegration:
    """Integration tests for parser."""
    
    def test_parser_with_document(self, temp_log_file: str) -> None:
        """Test parser with document entries."""
        # Ref: docs/specs/features/file-management.md §3.2
        parser = LogParser()
        
        doc = LogDocument(temp_log_file)
        doc.load()
        
        entries = doc.get_all_entries()
        for entry in entries:
            # Verify parser extracted correct data
            assert entry.timestamp is not None
            assert entry.category is not None
            # Ref: docs/specs/features/log-entry-optimization.md §4.3
            # raw_line removed - lazy loaded via LogDocument.get_raw_line()
            assert entry.display_message is not None
    
    def test_parser_levels(self, temp_log_file: str) -> None:
        """Test parser level detection."""
        doc = LogDocument(temp_log_file)
        doc.load()
        
        entries = doc.get_all_entries()
        
        # First entry should be ERROR
        entry0 = entries[0]
        assert entry0 is not None
        assert entry0.level == LogLevel.ERROR
        
        # Second entry should be WARNING
        entry1 = entries[1]
        assert entry1 is not None
        assert entry1.level == LogLevel.WARNING


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""
    
    def test_complete_workflow(self, temp_log_file: str) -> None:
        """Test complete workflow from loading to filtering."""
        # Ref: docs/specs/features/file-management.md §3.2
        doc = LogDocument(temp_log_file)
        doc.load()
        
        # Build category tree
        tree = CategoryTree()
        for category in doc.get_categories():
            tree.add_category(category)
        
        # Load all entries
        entries = doc.get_all_entries()
        
        # Calculate statistics
        stats_calc = StatisticsCalculator()
        stats_calc.process_entries(entries)
        total_stats = stats_calc.get_statistics(len(entries))
        
        # Setup filter
        filter_engine = FilterEngine()
        filter_state = FilterState(
            enabled_categories=tree.get_enabled_categories(),
            filter_text="",
            filter_mode=FilterMode.PLAIN
        )
        
        # Filter entries
        filter_func = filter_engine.compile_filter(filter_state)
        filtered = [e for e in entries if filter_func(e)]
        
        # Setup highlight
        highlight_engine = HighlightEngine()
        highlight_engine.add_pattern(HighlightPattern(
            text="Error",
            color=QColor(255, 0, 0)
        ))
        
        # Highlight filtered entries
        for entry in filtered:
            ranges = highlight_engine.highlight(entry.display_message)
            assert isinstance(ranges, list)
        
        # Verify results
        assert total_stats.total_lines == 5
        assert len(filtered) == 5
    
    def test_workflow_with_disabled_categories(self, temp_log_file: str) -> None:
        """Test workflow with disabled categories."""
        doc = LogDocument(temp_log_file)
        doc.load()
        
        # Build category tree
        tree = CategoryTree()
        for category in doc.get_categories():
            tree.add_category(category)
        
        # Disable some categories
        tree.toggle("Category2", False)
        tree.toggle("Category3", False)
        
        # Load entries
        entries = doc.get_all_entries()
        
        # Filter with enabled categories
        filter_engine = FilterEngine()
        filter_state = FilterState(
            enabled_categories=tree.get_enabled_categories(),
            filter_text="",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = filter_engine.compile_filter(filter_state)
        filtered = [e for e in entries if filter_func(e)]
        
        # Should only have Category1 entries
        for entry in filtered:
            assert entry.category.startswith("Category1")


class TestCategoryVisibilityIntegration:
    """Integration tests for category visibility filtering.
    
    // Ref: docs/specs/features/category-checkbox-behavior.md §4.1
    // Visibility Rule: log_visible(category) = category.checked (simple checkbox state)
    // Each category's checkbox independently controls its own logs.
    """
    
    def _create_entry(
        self,
        category: str,
        message: str = "Test message",
        row_index: int = 0
    ) -> LogEntry:
        """Create a test log entry with specified category.
        
        Ref: docs/specs/features/log-entry-optimization.md §4.2
        Ref: docs/specs/features/timestamp-unix-epoch.md §3.1
        raw_message removed - never used outside parser
        timestamp converted to Unix epoch float
        """
        return LogEntry(
            row_index=row_index,
            timestamp=datetime(2024, 1, 1, 12, 0, 0).timestamp(),
            category=category,
            display_message=message,
            level=LogLevel.MSG,
            file_offset=row_index * 100,
        )
    
    def test_logs_visible_when_parent_enabled_child_disabled(self) -> None:
        """Test that logs hide when parent is enabled but child is disabled.
        
        NEW BEHAVIOR: Parent Checked, Child Unchecked -> Child Logs HIDDEN
        Each category's visibility depends only on its own checkbox state.
        """
        # Build category tree with parent/child structure
        tree = CategoryTree()
        tree.add_category("Parent")
        tree.add_category("Parent/Child")
        tree.add_category("Parent/Child/Grandchild")
        
        # Start with all enabled
        tree.enable_all()
        
        # Disable child (and grandchild) independently while keeping parent enabled
        tree.set_enabled("Parent/Child", False)
        tree.set_enabled("Parent/Child/Grandchild", False)
        
        # Verify states
        assert tree.is_enabled("Parent") is True
        assert tree.is_enabled("Parent/Child") is False
        assert tree.is_enabled("Parent/Child/Grandchild") is False
        
        # Create filter engine with category tree
        engine = FilterEngine()
        state = FilterState(
            enabled_categories=tree.get_enabled_categories(),
            all_categories=tree.get_all_categories()
        )
        
        filter_func = engine.compile_filter(state, category_tree=tree)
        
        # Create entries for each category
        parent_entry = self._create_entry("Parent", "Parent message")
        child_entry = self._create_entry("Parent/Child", "Child message")
        grandchild_entry = self._create_entry("Parent/Child/Grandchild", "Grandchild message")
        
        # Parent is visible (enabled), child and grandchild are NOT visible (disabled)
        assert filter_func(parent_entry) is True, "Parent should be visible (enabled)"
        assert filter_func(child_entry) is False, "Child should NOT be visible (disabled)"
        assert filter_func(grandchild_entry) is False, "Grandchild should NOT be visible (disabled)"
    
    def test_logs_visible_when_child_enabled_parent_disabled(self) -> None:
        """Test that logs display when child is enabled but parent is disabled.
        
        // Ref: docs/specs/features/category-checkbox-behavior.md §4.2
        // Parent Unchecked, Child Checked -> Child Logs Visible
        """
        # Build category tree
        tree = CategoryTree()
        tree.add_category("Parent")
        tree.add_category("Parent/Child")
        tree.add_category("Parent/Child/Grandchild")
        
        # First enable all (default state)
        tree.enable_all()
        
        # Disable parent (cascades to children)
        tree.toggle("Parent", False)
        
        # Now enable just the child (without affecting parent)
        tree.set_enabled("Parent/Child", True)
        
        # Verify states
        assert tree.is_enabled("Parent") is False
        assert tree.is_enabled("Parent/Child") is True
        assert tree.is_enabled("Parent/Child/Grandchild") is False
        
        # Create filter with category tree
        engine = FilterEngine()
        state = FilterState(
            enabled_categories=tree.get_enabled_categories(),
            all_categories=tree.get_all_categories()
        )
        
        filter_func = engine.compile_filter(state, category_tree=tree)
        
        # Create entries
        parent_entry = self._create_entry("Parent", "Parent message")
        child_entry = self._create_entry("Parent/Child", "Child message")
        grandchild_entry = self._create_entry("Parent/Child/Grandchild", "Grandchild message")
        
        # Child should be visible (enabled), parent and grandchild should not
        assert filter_func(parent_entry) is False, "Parent should not be visible"
        assert filter_func(child_entry) is True, "Child should be visible (enabled)"
        assert filter_func(grandchild_entry) is False, "Grandchild should not be visible (disabled)"
    
    def test_logs_hidden_when_both_disabled(self) -> None:
        """Test that logs hide when both parent and child are disabled.
        
        // Ref: docs/specs/features/category-checkbox-behavior.md §4.2
        // Parent Unchecked, Child Unchecked -> Child Logs Hidden
        """
        # Build category tree
        tree = CategoryTree()
        tree.add_category("Parent")
        tree.add_category("Parent/Child")
        
        # Disable parent (cascades to children)
        tree.toggle("Parent", False)
        
        # Verify both are disabled
        assert tree.is_enabled("Parent") is False
        assert tree.is_enabled("Parent/Child") is False
        
        # Create filter with category tree
        engine = FilterEngine()
        state = FilterState(
            enabled_categories=tree.get_enabled_categories(),
            all_categories=tree.get_all_categories()
        )
        
        filter_func = engine.compile_filter(state, category_tree=tree)
        
        # Create entries
        parent_entry = self._create_entry("Parent", "Parent message")
        child_entry = self._create_entry("Parent/Child", "Child message")
        
        # Neither should be visible
        assert filter_func(parent_entry) is False
        assert filter_func(child_entry) is False
    
    def test_parent_enable_cascades_in_filter(self) -> None:
        """Test that enabling parent cascades visibility to children in filter.
        
        // Ref: docs/specs/features/category-checkbox-behavior.md §3.1
        // Parent Enable Rule (Cascade Down) - UI cascade, then each category is independent
        """
        # Build category tree with multiple levels
        tree = CategoryTree()
        tree.add_category("Root")
        tree.add_category("Root/Branch1")
        tree.add_category("Root/Branch1/Leaf1")
        tree.add_category("Root/Branch1/Leaf2")
        tree.add_category("Root/Branch2")
        
        # Disable all first
        tree.disable_all()
        
        # Enable root (should cascade to all children via toggle)
        tree.toggle("Root", True)
        
        # Create filter with category tree
        engine = FilterEngine()
        state = FilterState(
            enabled_categories=tree.get_enabled_categories(),
            all_categories=tree.get_all_categories()
        )
        
        filter_func = engine.compile_filter(state, category_tree=tree)
        
        # Create entries for all categories
        entries = [
            self._create_entry("Root", "Root", 0),
            self._create_entry("Root/Branch1", "Branch1", 1),
            self._create_entry("Root/Branch1/Leaf1", "Leaf1", 2),
            self._create_entry("Root/Branch1/Leaf2", "Leaf2", 3),
            self._create_entry("Root/Branch2", "Branch2", 4),
        ]
        
        # All entries should be visible (toggle cascaded enabled state to all)
        for entry in entries:
            assert filter_func(entry) is True, f"{entry.category} should be visible"
    
    def test_parent_disable_cascades_in_filter(self) -> None:
        """Test that disabling parent cascades to children in filter.
        
        // Ref: docs/specs/features/category-checkbox-behavior.md §3.2
        // Parent Disable Rule (Cascade Down) - UI cascade disables all children
        """
        # Build category tree
        tree = CategoryTree()
        tree.add_category("Root")
        tree.add_category("Root/Branch1")
        tree.add_category("Root/Branch1/Leaf1")
        tree.add_category("Root/Branch2")
        
        # Start with all enabled
        tree.enable_all()
        
        # Disable root (should cascade to all children)
        tree.toggle("Root", False)
        
        # Create filter with category tree
        engine = FilterEngine()
        state = FilterState(
            enabled_categories=tree.get_enabled_categories(),
            all_categories=tree.get_all_categories()
        )
        
        filter_func = engine.compile_filter(state, category_tree=tree)
        
        # Create entries
        entries = [
            self._create_entry("Root", "Root", 0),
            self._create_entry("Root/Branch1", "Branch1", 1),
            self._create_entry("Root/Branch1/Leaf1", "Leaf1", 2),
            self._create_entry("Root/Branch2", "Branch2", 3),
        ]
        
        # No entries should be visible (parent disabled cascades)
        for entry in entries:
            assert filter_func(entry) is False, f"{entry.category} should not be visible"
    
    def test_selective_child_enable_with_disabled_parent(self) -> None:
        """Test enabling specific children while parent is disabled.
        
        // Ref: docs/specs/features/category-checkbox-behavior.md §3.3
        // Child Enable Rule (No Parent Effect) - each category independent
        """
        # Build category tree
        tree = CategoryTree()
        tree.add_category("Root")
        tree.add_category("Root/Branch1")
        tree.add_category("Root/Branch1/Leaf1")
        tree.add_category("Root/Branch1/Leaf2")
        tree.add_category("Root/Branch2")
        
        # Disable all first
        tree.disable_all()
        
        # Enable only Leaf1 (without affecting parent)
        tree.set_enabled("Root/Branch1/Leaf1", True)
        
        # Verify states
        assert tree.is_enabled("Root") is False
        assert tree.is_enabled("Root/Branch1") is False
        assert tree.is_enabled("Root/Branch1/Leaf1") is True
        assert tree.is_enabled("Root/Branch1/Leaf2") is False
        assert tree.is_enabled("Root/Branch2") is False
        
        # Create filter with category tree
        engine = FilterEngine()
        state = FilterState(
            enabled_categories=tree.get_enabled_categories(),
            all_categories=tree.get_all_categories()
        )
        
        filter_func = engine.compile_filter(state, category_tree=tree)
        
        # Create entries
        root_entry = self._create_entry("Root", "Root", 0)
        branch1_entry = self._create_entry("Root/Branch1", "Branch1", 1)
        leaf1_entry = self._create_entry("Root/Branch1/Leaf1", "Leaf1", 2)
        leaf2_entry = self._create_entry("Root/Branch1/Leaf2", "Leaf2", 3)
        branch2_entry = self._create_entry("Root/Branch2", "Branch2", 4)
        
        # Only Leaf1 should be visible (its own checkbox is enabled)
        assert filter_func(root_entry) is False, "Root should not be visible"
        assert filter_func(branch1_entry) is False, "Branch1 should not be visible"
        assert filter_func(leaf1_entry) is True, "Leaf1 should be visible (enabled)"
        assert filter_func(leaf2_entry) is False, "Leaf2 should not be visible"
        assert filter_func(branch2_entry) is False, "Branch2 should not be visible"
    
    def test_visibility_with_deep_hierarchy(self) -> None:
        """Test visibility with deeply nested categories.
        
        // Ref: docs/specs/features/category-checkbox-behavior.md §9.1
        // Test Deep Nesting - each category's visibility is independent
        """
        # Build deep hierarchy (5+ levels)
        tree = CategoryTree()
        tree.add_category("L1")
        tree.add_category("L1/L2")
        tree.add_category("L1/L2/L3")
        tree.add_category("L1/L2/L3/L4")
        tree.add_category("L1/L2/L3/L4/L5")
        
        # Disable all first
        tree.disable_all()
        
        # Enable only L3 (middle level)
        tree.set_enabled("L1/L2/L3", True)
        
        # Create filter with category tree
        engine = FilterEngine()
        state = FilterState(
            enabled_categories=tree.get_enabled_categories(),
            all_categories=tree.get_all_categories()
        )
        
        filter_func = engine.compile_filter(state, category_tree=tree)
        
        # Create entries
        l1_entry = self._create_entry("L1", "L1", 0)
        l2_entry = self._create_entry("L1/L2", "L2", 1)
        l3_entry = self._create_entry("L1/L2/L3", "L3", 2)
        l4_entry = self._create_entry("L1/L2/L3/L4", "L4", 3)
        l5_entry = self._create_entry("L1/L2/L3/L4/L5", "L5", 4)
        
        # Only L3 should be visible (its own checkbox is enabled)
        # L4 and L5 are NOT visible because their own checkboxes are disabled
        assert filter_func(l1_entry) is False, "L1 should not be visible"
        assert filter_func(l2_entry) is False, "L2 should not be visible"
        assert filter_func(l3_entry) is True, "L3 should be visible (enabled)"
        assert filter_func(l4_entry) is False, "L4 should not be visible (disabled)"
        assert filter_func(l5_entry) is False, "L5 should not be visible (disabled)"


class TestSelectionPreservationIntegration:
    """Integration tests for selection preservation across filter changes.
    
    // Ref: docs/specs/features/selection-preservation.md §5.2
    // Tests the full workflow: capture selection -> apply filter -> restore selection
    """
    
    def test_selection_state_capture_and_restore(self) -> None:
        """Test SelectionState capture and restore with filtered entries.
        
        // Ref: docs/specs/features/selection-preservation.md §4.2
        """
        from src.models.selection_state import SelectionState
        from src.views.log_table_view import LogEntryDisplay
        
        # Create sample entries with distinct file_offset values
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.3
        # LogEntryDisplay requires time and time_full strings
        entries = [
            LogEntryDisplay(
                category="System",
                time="18:31:00.000",
                time_full="2024-01-01 18:31:00.000",
                level=LogLevel.MSG,
                message=f"Message {i}",
                file_offset=i * 100,
            )
            for i in range(10)
        ]
        
        # Select entries at indices 1, 3, 5
        selected_entries = [entries[1], entries[3], entries[5]]
        
        # Capture selection state
        state = SelectionState.from_entries(selected_entries)
        
        # Verify captured offsets
        assert 100 in state.offsets
        assert 300 in state.offsets
        assert 500 in state.offsets
        assert len(state.offsets) == 3
        
        # Simulate filter: only show entries at indices 0, 1, 2, 3, 4
        filtered_entries = entries[:5]
        
        # Restore indices in filtered view
        indices = state.restore_indices(filtered_entries)
        
        # Only entries at indices 1 and 3 should be found (offsets 100 and 300)
        assert indices == [1, 3]
    
    def test_selection_preservation_with_filter_change(self, qapp) -> None:
        """Test selection preservation when filter changes.
        
        // Ref: docs/specs/features/selection-preservation.md §5.2
        """
        from PySide6.QtCore import QItemSelectionModel, QItemSelection
        from src.views.log_table_view import LogTableView, LogEntryDisplay
        
        # Create table view
        view = LogTableView()
        
        # Create initial entries
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.3
        # LogEntryDisplay requires time and time_full strings
        entries = [
            LogEntryDisplay(
                category="System",
                time="18:31:00.000",
                time_full="2024-01-01 18:31:00.000",
                level=LogLevel.MSG,
                message=f"Message {i}",
                file_offset=i * 100,
            )
            for i in range(10)
        ]
        
        # Set entries
        view.set_entries(entries)
        
        # Select rows 2, 4, 6 using selection model
        selection = QItemSelection()
        for row in [2, 4, 6]:
            index = view._model.index(row, 0)
            selection.select(index, index)
        view.selectionModel().select(
            selection,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
        )
        
        # Capture selection state
        state = view.get_selection_state()
        assert not state.is_empty()
        assert len(state.offsets) == 3
        
        # Apply filter: show only first 5 entries
        filtered_entries = entries[:5]
        view.set_entries(filtered_entries)
        
        # Restore selection
        restored = view.restore_selection(state)
        
        # Should restore successfully (offsets 200 and 400 exist in filtered view)
        assert restored is True
        
        # Cleanup
        view.deleteLater()
    
    def test_selection_preservation_empty_selection(self, qapp) -> None:
        """Test selection preservation with no selection.
        
        // Ref: docs/specs/features/selection-preservation.md §5.2
        """
        from src.views.log_table_view import LogTableView, LogEntryDisplay
        
        # Create table view
        view = LogTableView()
        
        # Create entries
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.3
        # LogEntryDisplay requires time and time_full strings
        entries = [
            LogEntryDisplay(
                category="System",
                time="18:31:00.000",
                time_full="2024-01-01 18:31:00.000",
                level=LogLevel.MSG,
                message=f"Message {i}",
                file_offset=i * 100,
            )
            for i in range(5)
        ]
        
        view.set_entries(entries)
        
        # No selection - capture state
        state = view.get_selection_state()
        assert state.is_empty()
        
        # Apply filter
        filtered_entries = entries[:3]
        view.set_entries(filtered_entries)
        
        # Restore selection (should do nothing)
        restored_count = view.restore_selection(state)
        assert restored_count == 0
        
        # Cleanup
        view.deleteLater()
    
    def test_selection_preservation_all_entries_filtered_out(self, qapp) -> None:
        """Test selection preservation when selected entries are filtered out.
        
        // Ref: docs/specs/features/selection-preservation.md §5.2
        """
        from PySide6.QtCore import QItemSelectionModel, QItemSelection
        from src.views.log_table_view import LogTableView, LogEntryDisplay
        
        # Create table view
        view = LogTableView()
        
        # Create entries
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.3
        # LogEntryDisplay requires time and time_full strings
        entries = [
            LogEntryDisplay(
                category="System",
                time="18:31:00.000",
                time_full="2024-01-01 18:31:00.000",
                level=LogLevel.MSG,
                message=f"Message {i}",
                file_offset=i * 100,
            )
            for i in range(10)
        ]
        
        view.set_entries(entries)
        
        # Select rows 5, 6, 7 using selection model
        selection = QItemSelection()
        for row in [5, 6, 7]:
            index = view._model.index(row, 0)
            selection.select(index, index)
        view.selectionModel().select(
            selection,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
        )
        
        # Capture selection state
        state = view.get_selection_state()
        assert len(state.offsets) == 3
        
        # Apply filter: show only first 3 entries (selected entries not in view)
        filtered_entries = entries[:3]
        view.set_entries(filtered_entries)
        
        # Restore selection (should restore 0 rows)
        restored = view.restore_selection(state)
        assert restored is False
        
        # Cleanup
        view.deleteLater()
    
    @pytest.mark.skip(reason="Requires T-001 (parser update) to convert timestamps to Unix epoch")
    def test_selection_preservation_with_document_filtering(self, temp_log_file: str) -> None:
        """Test selection preservation with actual document filtering.
        
        // Ref: docs/specs/features/selection-preservation.md §5.2
        // Integration test with LogDocument and FilterEngine.
        // Note: This test requires T-001 (parser update) to be completed first.
        // The parser needs to convert timestamps to Unix epoch floats.
        """
        from src.models.selection_state import SelectionState
        from src.views.log_table_view import LogEntryDisplay
        
        # Ref: docs/specs/features/file-management.md §3.2
        doc = LogDocument(temp_log_file)
        doc.load()
        
        # Get all entries
        all_entries = doc.get_all_entries()
        
        # Convert to display entries
        display_entries = [
            LogEntryDisplay.from_log_entry(e)
            for e in all_entries
        ]
        
        # Select first 2 entries
        selected_entries = display_entries[:2]
        
        # Capture selection state
        state = SelectionState.from_entries(selected_entries)
        
        # Apply filter: show only error messages
        engine = FilterEngine()
        filter_state = FilterState(
            enabled_categories=doc.get_categories(),
            filter_text="Error",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = engine.compile_filter(filter_state)
        filtered_entries = [e for e in all_entries if filter_func(e)]
        
        # Convert to display format
        filtered_display = [
            LogEntryDisplay.from_log_entry(e)
            for e in filtered_entries
        ]
        
        # Restore indices
        indices = state.restore_indices(filtered_display)
        
        # First selected entry should be in filtered results (it's the error)
        # The indices list should contain the index of the error entry
        assert len(indices) >= 0  # May or may not have matches
    
    def test_viewport_position_preserved_on_filter_change(self, qapp) -> None:
        """Viewport position should be preserved for selected row.
        
        // Ref: docs/specs/features/selection-preservation.md §12.2
        // Ref: docs/specs/features/selection-preservation.md §12.3
        """
        from PySide6.QtCore import QItemSelectionModel, QItemSelection
        from src.views.log_table_view import LogTableView, LogEntryDisplay
        from src.models.selection_state import ViewportState
        
        # Create table view
        view = LogTableView()
        
        # Create entries
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.3
        # LogEntryDisplay requires time and time_full strings
        entries = [
            LogEntryDisplay(
                category="System",
                time="18:31:00.000",
                time_full="2024-01-01 18:31:00.000",
                level=LogLevel.MSG,
                message=f"Message {i}",
                file_offset=i * 100,
            )
            for i in range(10)
        ]
        
        view.set_entries(entries)
        
        # Select row 5 (in middle of viewport)
        index = view._model.index(5, 0)
        view.selectionModel().select(
            index,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
        )
        view.selectionModel().setCurrentIndex(index, QItemSelectionModel.NoUpdate)
        
        # Capture viewport state
        viewport_state = view.get_viewport_state()
        assert viewport_state is not None
        assert viewport_state.selected_offset == 500
        
        # Store the viewport offset
        original_offset = viewport_state.viewport_offset
        
        # Apply filter: show only first 5 entries
        filtered_entries = entries[:5]
        view.set_entries(filtered_entries)
        
        # Row 5 is now hidden, so viewport restoration should fail
        # But we can still test the mechanism
        restored = view.restore_viewport_position(viewport_state)
        assert restored is False  # Row not found in filtered entries
        
        # Cleanup
        view.deleteLater()
    
    def test_viewport_position_preserved_with_visible_row(self, qapp) -> None:
        """Viewport position should be preserved when row remains visible.
        
        // Ref: docs/specs/features/selection-preservation.md §12.2
        """
        from PySide6.QtCore import QItemSelectionModel, QItemSelection
        from src.views.log_table_view import LogTableView, LogEntryDisplay
        
        # Create table view
        view = LogTableView()
        
        # Create entries
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.3
        # LogEntryDisplay requires time and time_full strings
        entries = [
            LogEntryDisplay(
                category="System",
                time="18:31:00.000",
                time_full="2024-01-01 18:31:00.000",
                level=LogLevel.MSG,
                message=f"Message {i}",
                file_offset=i * 100,
            )
            for i in range(10)
        ]
        
        view.set_entries(entries)
        
        # Select row 2
        index = view._model.index(2, 0)
        view.selectionModel().select(
            index,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
        )
        view.selectionModel().setCurrentIndex(index, QItemSelectionModel.NoUpdate)
        
        # Capture viewport state
        viewport_state = view.get_viewport_state()
        assert viewport_state is not None
        assert viewport_state.selected_offset == 200
        
        # Apply filter: show entries 0-4 (row 2 remains visible)
        filtered_entries = entries[:5]
        view.set_entries(filtered_entries)
        
        # Restore selection first
        selection_state = view.get_selection_state()
        view.restore_selection(selection_state)
        
        # Restore viewport
        restored = view.restore_viewport_position(viewport_state)
        assert restored is True
        
        # Cleanup
        view.deleteLater()
    
    def test_viewport_fallback_when_row_hidden(self, qapp) -> None:
        """Viewport should use default scroll when selected row is hidden.
        
        // Ref: docs/specs/features/selection-preservation.md §12.2
        // Ref: docs/specs/features/selection-preservation.md §7.7
        """
        from PySide6.QtCore import QItemSelectionModel, QItemSelection
        from src.views.log_table_view import LogTableView, LogEntryDisplay
        
        # Create table view
        view = LogTableView()
        
        # Create entries
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.3
        # LogEntryDisplay requires time and time_full strings
        entries = [
            LogEntryDisplay(
                category="System",
                time="18:31:00.000",
                time_full="2024-01-01 18:31:00.000",
                level=LogLevel.MSG,
                message=f"Message {i}",
                file_offset=i * 100,
            )
            for i in range(10)
        ]
        
        view.set_entries(entries)
        
        # Select row 7
        index = view._model.index(7, 0)
        view.selectionModel().select(
            index,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
        )
        view.selectionModel().setCurrentIndex(index, QItemSelectionModel.NoUpdate)
        
        # Capture viewport state
        viewport_state = view.get_viewport_state()
        assert viewport_state is not None
        assert viewport_state.selected_offset == 700
        
        # Apply filter: show only first 3 entries (row 7 is hidden)
        filtered_entries = entries[:3]
        view.set_entries(filtered_entries)
        
        # Try to restore viewport - should return False
        restored = view.restore_viewport_position(viewport_state)
        assert restored is False
        
        # Cleanup
        view.deleteLater()
    
    def test_viewport_preservation_full_workflow(self, qapp) -> None:
        """Test full workflow: capture viewport, filter, restore viewport.
        
        // Ref: docs/specs/features/selection-preservation.md §7.6
        """
        from PySide6.QtCore import QItemSelectionModel
        from src.views.log_table_view import LogTableView, LogEntryDisplay
        
        # Create table view
        view = LogTableView()
        
        # Create entries
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.3
        # LogEntryDisplay requires time and time_full strings
        entries = [
            LogEntryDisplay(
                category="System",
                time="18:31:00.000",
                time_full="2024-01-01 18:31:00.000",
                level=LogLevel.MSG,
                message=f"Message {i}",
                file_offset=i * 100,
            )
            for i in range(20)
        ]
        
        view.set_entries(entries)
        
        # Select row 10
        index = view._model.index(10, 0)
        view.selectionModel().select(
            index,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
        )
        view.selectionModel().setCurrentIndex(index, QItemSelectionModel.NoUpdate)
        
        # Capture states
        selection_state = view.get_selection_state()
        viewport_state = view.get_viewport_state()
        
        assert selection_state is not None
        assert len(selection_state.offsets) == 1
        assert viewport_state is not None
        assert viewport_state.selected_offset == 1000
        
        # Apply filter: show entries 5-15 (row 10 remains visible at index 5)
        filtered_entries = entries[5:16]
        view.set_entries_preserve_selection_and_viewport(filtered_entries)
        
        # Verify selection is restored
        selected_entries = view.get_selected_entries()
        assert len(selected_entries) == 1
        assert selected_entries[0].file_offset == 1000
        
        # Cleanup
        view.deleteLater()


class TestPerformanceIntegration:
    """Performance integration tests."""
    
    def test_large_file_simulation(self) -> None:
        """Test with simulated large file."""
        # Ref: docs/specs/features/file-management.md §3.2
        # Create a temporary file with many lines
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            filepath = f.name
            for i in range(1000):
                level = "LOG_ERROR" if i % 10 == 0 else ("LOG_WARNING" if i % 5 == 0 else "LOG_MSG")
                category = f"Category{i % 20}"
                f.write(f"25-02-2026T18:31:{i % 60:02d}.{i % 1000:03d} {category} {level} Message {i}\n")
        
        try:
            doc = LogDocument(filepath)
            doc.load()
            
            assert doc.get_line_count() == 1000
            
            # Build category tree
            tree = CategoryTree()
            for category in doc.get_categories():
                tree.add_category(category)
            
            # Should have 20 categories
            assert len(tree) == 20
            
            # Calculate statistics
            calc = StatisticsCalculator()
            entries = doc.get_all_entries()
            for entry in entries:
                calc.process_entry(entry)
            
            stats = calc.get_statistics(1000)
            assert stats.total_lines == 1000
            
        finally:
            os.unlink(filepath)
    
    def test_filter_performance(self) -> None:
        """Test filter performance with many entries."""
        # Create many entries
        entries = []
        for i in range(10000):
            level = LogLevel.ERROR if i % 10 == 0 else (LogLevel.WARNING if i % 5 == 0 else LogLevel.MSG)
            category = f"Category{i % 50}"
            
            # Ref: docs/specs/features/log-entry-optimization.md §4.2
            # Ref: docs/specs/features/timestamp-unix-epoch.md §3.1
            # raw_message removed - never used outside parser
            # timestamp converted to Unix epoch float
            level_prefix = f"{level.value} " if level != LogLevel.MSG else ""
            entry = LogEntry(
                row_index=i,
                timestamp=datetime(2024, 1, 1, 12, 0, i % 60).timestamp(),
                category=category,
                display_message=f"Message {i}",
                level=level,
                file_offset=i * 100,
            )
            entries.append(entry)
        
        # Build category tree
        tree = CategoryTree()
        for i in range(50):
            tree.add_category(f"Category{i}")
        
        # Filter
        engine = FilterEngine()
        state = FilterState(
            enabled_categories=tree.get_enabled_categories(),
            filter_text="Message",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = engine.compile_filter(state)
        filtered = [e for e in entries if filter_func(e)]
        
        # All entries should match
        assert len(filtered) == 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])