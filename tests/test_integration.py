"""Integration tests for log viewer."""
from __future__ import annotations

import os
import tempfile
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
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            assert doc.get_line_count() == 5
            assert len(doc.get_categories()) > 0
    
    def test_document_get_line(self, temp_log_file: str) -> None:
        """Test getting lines from document."""
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            entry = doc.get_line(0)
            assert entry is not None
            assert entry.row_index == 0
            assert entry.category == "Category1/Subcat1"
            assert entry.level == LogLevel.ERROR
    
    def test_document_categories(self, temp_log_file: str) -> None:
        """Test extracting categories from document."""
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            categories = doc.get_categories()
            
            assert "Category1/Subcat1" in categories
            assert "Category2" in categories
            assert "Category1/Subcat2" in categories
            assert "Category3" in categories
    
    def test_document_iteration(self, temp_log_file: str) -> None:
        """Test iterating through document."""
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            count = 0
            for i in range(doc.get_line_count()):
                entry = doc.get_line(i)
                if entry:
                    count += 1
            
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
        """Create a test log entry."""
        level_prefix = f"{level.value} " if level != LogLevel.MSG else ""
        return LogEntry(
            row_index=row_index,
            timestamp="2024-01-01 12:00:00",
            category=category,
            raw_message=f"{level_prefix}{message}",
            display_message=message,
            level=level,
            file_offset=row_index * 100,
            raw_line=f"2024-01-01 12:00:00 {category} {level_prefix}{message}"
        )
    
    def test_document_and_filter_integration(self, temp_log_file: str) -> None:
        """Test document loading with filtering."""
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            # Get all entries
            entries = []
            for i in range(doc.get_line_count()):
                entry = doc.get_line(i)
                if entry:
                    entries.append(entry)
            
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
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            # Get all entries
            entries = []
            for i in range(doc.get_line_count()):
                entry = doc.get_line(i)
                if entry:
                    entries.append(entry)
            
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
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            # Get all entries
            entries = []
            for i in range(doc.get_line_count()):
                entry = doc.get_line(i)
                if entry:
                    entries.append(entry)
            
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
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            entries = [
                doc.get_line(i)
                for i in range(doc.get_line_count())
                if doc.get_line(i) is not None
            ]
            
            # Filter with regex
            engine = FilterEngine()
            state = FilterState(
                enabled_categories=doc.get_categories(),
                filter_text=r"LOG_\w+",
                filter_mode=FilterMode.REGEX
            )
            
            filter_func = engine.compile_filter(state)
            filtered = [e for e in entries if filter_func(e)]
            
            # Should match entries with LOG_ERROR, LOG_WARNING, LOG_MSG
            assert len(filtered) >= 3
    
    def test_simple_query_with_document(self, temp_log_file: str) -> None:
        """Test simple query filtering with document."""
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            entries = [
                doc.get_line(i)
                for i in range(doc.get_line_count())
                if doc.get_line(i) is not None
            ]
            
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
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
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
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            # Build category tree
            tree = CategoryTree()
            for category in doc.get_categories():
                tree.add_category(category)
            
            # Get all entries
            entries = []
            for i in range(doc.get_line_count()):
                entry = doc.get_line(i)
                if entry:
                    entries.append(entry)
            
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
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
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
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            # Calculate statistics
            calc = StatisticsCalculator()
            
            for i in range(doc.get_line_count()):
                entry = doc.get_line(i)
                if entry:
                    calc.process_entry(entry)
            
            stats = calc.get_statistics(shown_count=doc.get_line_count())
            
            assert stats.total_lines == 5
            assert stats.error_count == 1
            assert stats.warning_count == 2
    
    def test_statistics_with_filtering(self, temp_log_file: str) -> None:
        """Test statistics with filtering."""
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            # Get all entries
            entries = []
            for i in range(doc.get_line_count()):
                entry = doc.get_line(i)
                if entry:
                    entries.append(entry)
            
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
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
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
            for i in range(doc.get_line_count()):
                entry = doc.get_line(i)
                if entry:
                    ranges = engine.highlight(entry.display_message)
                    # Just verify it doesn't crash
                    assert isinstance(ranges, list)
    
    def test_highlight_with_regex(self, temp_log_file: str) -> None:
        """Test highlighting with regex patterns."""
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            # Setup highlight engine with regex
            engine = HighlightEngine()
            engine.add_pattern(HighlightPattern(
                text=r"LOG_\w+",
                color=QColor(255, 0, 0),
                is_regex=True
            ))
            
            # Highlight entries
            error_entry = doc.get_line(0)
            assert error_entry is not None
            
            ranges = engine.highlight(error_entry.raw_message)
            # Should find LOG_ERROR
            assert len(ranges) >= 1


class TestParserIntegration:
    """Integration tests for parser."""
    
    def test_parser_with_document(self, temp_log_file: str) -> None:
        """Test parser with document entries."""
        parser = LogParser()
        
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            for i in range(doc.get_line_count()):
                entry = doc.get_line(i)
                if entry:
                    # Verify parser extracted correct data
                    assert entry.timestamp is not None
                    assert entry.category is not None
                    assert entry.raw_line is not None
    
    def test_parser_levels(self, temp_log_file: str) -> None:
        """Test parser level detection."""
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            # First entry should be ERROR
            entry0 = doc.get_line(0)
            assert entry0 is not None
            assert entry0.level == LogLevel.ERROR
            
            # Second entry should be WARNING
            entry1 = doc.get_line(1)
            assert entry1 is not None
            assert entry1.level == LogLevel.WARNING


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""
    
    def test_complete_workflow(self, temp_log_file: str) -> None:
        """Test complete workflow from loading to filtering."""
        with LogDocument(temp_log_file) as doc:
            # Build index
            doc.build_index()
            
            # Build category tree
            tree = CategoryTree()
            for category in doc.get_categories():
                tree.add_category(category)
            
            # Load all entries
            entries = []
            for i in range(doc.get_line_count()):
                entry = doc.get_line(i)
                if entry:
                    entries.append(entry)
            
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
    
    def test_workflow_with_custom_category(self, temp_log_file: str) -> None:
        """Test workflow with custom category."""
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            # Build category tree
            tree = CategoryTree()
            for category in doc.get_categories():
                tree.add_category(category)
            
            # Add custom category
            tree.add_custom_category("errors", pattern=r"LOG_ERROR")
            
            # Verify custom category
            custom = tree.get_custom_categories()
            assert len(custom) == 1
            assert custom[0].name == "errors"
    
    def test_workflow_with_disabled_categories(self, temp_log_file: str) -> None:
        """Test workflow with disabled categories."""
        with LogDocument(temp_log_file) as doc:
            doc.build_index()
            
            # Build category tree
            tree = CategoryTree()
            for category in doc.get_categories():
                tree.add_category(category)
            
            # Disable some categories
            tree.toggle("Category2", False)
            tree.toggle("Category3", False)
            
            # Load entries
            entries = []
            for i in range(doc.get_line_count()):
                entry = doc.get_line(i)
                if entry:
                    entries.append(entry)
            
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
    // Visibility Rule: log_visible(category) = category.checked OR any_ancestor.checked
    """
    
    def _create_entry(
        self,
        category: str,
        message: str = "Test message",
        row_index: int = 0
    ) -> LogEntry:
        """Create a test log entry with specified category."""
        return LogEntry(
            row_index=row_index,
            timestamp="2024-01-01 12:00:00",
            category=category,
            raw_message=f"LOG_MSG {message}",
            display_message=message,
            level=LogLevel.MSG,
            file_offset=row_index * 100,
            raw_line=f"2024-01-01 12:00:00 {category} LOG_MSG {message}"
        )
    
    def test_logs_visible_when_parent_enabled(self) -> None:
        """Test that logs display when parent category is enabled.
        
        // Ref: docs/specs/features/category-checkbox-behavior.md §4.2
        // Parent Checked, Child Unchecked -> Child Logs Visible
        """
        # Build category tree with parent/child structure
        tree = CategoryTree()
        tree.add_category("Parent")
        tree.add_category("Parent/Child")
        tree.add_category("Parent/Child/Grandchild")
        
        # Enable parent only (cascade enables children)
        tree.toggle("Parent", True)
        
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
        
        # All entries should be visible (parent enabled cascades to children)
        assert filter_func(parent_entry) is True
        assert filter_func(child_entry) is True
        assert filter_func(grandchild_entry) is True
    
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
        # Grandchild: child is enabled, so grandchild should be visible via ancestor
        assert filter_func(grandchild_entry) is True, "Grandchild visible via enabled parent"
    
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
        // Parent Enable Rule (Cascade Down)
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
        
        # Enable root (should cascade to all children)
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
        
        # All entries should be visible (parent enabled cascades)
        for entry in entries:
            assert filter_func(entry) is True, f"{entry.category} should be visible"
    
    def test_parent_disable_cascades_in_filter(self) -> None:
        """Test that disabling parent cascades to children in filter.
        
        // Ref: docs/specs/features/category-checkbox-behavior.md §3.2
        // Parent Disable Rule (Cascade Down)
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
        // Child Enable Rule (No Parent Effect)
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
        
        # Only Leaf1 should be visible
        assert filter_func(root_entry) is False, "Root should not be visible"
        assert filter_func(branch1_entry) is False, "Branch1 should not be visible"
        assert filter_func(leaf1_entry) is True, "Leaf1 should be visible (enabled)"
        assert filter_func(leaf2_entry) is False, "Leaf2 should not be visible"
        assert filter_func(branch2_entry) is False, "Branch2 should not be visible"
    
    def test_visibility_with_deep_hierarchy(self) -> None:
        """Test visibility with deeply nested categories.
        
        // Ref: docs/specs/features/category-checkbox-behavior.md §9.1
        // Test Deep Nesting
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
        
        # L3 and its descendants should be visible
        assert filter_func(l1_entry) is False, "L1 should not be visible"
        assert filter_func(l2_entry) is False, "L2 should not be visible"
        assert filter_func(l3_entry) is True, "L3 should be visible (enabled)"
        assert filter_func(l4_entry) is True, "L4 should be visible (ancestor enabled)"
        assert filter_func(l5_entry) is True, "L5 should be visible (ancestor enabled)"


class TestPerformanceIntegration:
    """Performance integration tests."""
    
    def test_large_file_simulation(self) -> None:
        """Test with simulated large file."""
        # Create a temporary file with many lines
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            filepath = f.name
            for i in range(1000):
                level = "LOG_ERROR" if i % 10 == 0 else ("LOG_WARNING" if i % 5 == 0 else "LOG_MSG")
                category = f"Category{i % 20}"
                f.write(f"25-02-2026T18:31:{i % 60:02d}.{i % 1000:03d} {category} {level} Message {i}\n")
        
        try:
            with LogDocument(filepath) as doc:
                doc.build_index()
                
                assert doc.get_line_count() == 1000
                
                # Build category tree
                tree = CategoryTree()
                for category in doc.get_categories():
                    tree.add_category(category)
                
                # Should have 20 categories
                assert len(tree) == 20
                
                # Calculate statistics
                calc = StatisticsCalculator()
                for i in range(doc.get_line_count()):
                    entry = doc.get_line(i)
                    if entry:
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
            
            level_prefix = f"{level.value} " if level != LogLevel.MSG else ""
            entry = LogEntry(
                row_index=i,
                timestamp=f"2024-01-01 12:00:{i % 60:02d}",
                category=category,
                raw_message=f"{level_prefix}Message {i}",
                display_message=f"Message {i}",
                level=level,
                file_offset=i * 100,
                raw_line=f"2024-01-01 12:00:{i % 60:02d} {category} {level_prefix}Message {i}"
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