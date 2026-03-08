"""Tests for filter engine and related components."""
from __future__ import annotations

import pytest
from beartype import beartype

from src.models.log_entry import LogEntry, LogLevel
from src.models.filter_state import FilterMode, FilterState
from src.core.filter_engine import FilterEngine
from src.core.simple_query_parser import SimpleQueryParser, QueryTokenizer
from src.core.category_tree import CategoryTree, CategoryNode


# Helper function to create test log entries
@beartype
def create_entry(
    message: str,
    category: str = "test",
    level: LogLevel = LogLevel.MSG
) -> LogEntry:
    """Create a test log entry."""
    return LogEntry(
        row_index=0,
        timestamp="2024-01-01 12:00:00",
        category=category,
        raw_message=f"[{level.value}] {message}",
        display_message=message,
        level=level,
        file_offset=0,
        raw_line=f"2024-01-01 12:00:00 [{level.value}] [{category}] {message}"
    )


class TestQueryTokenizer:
    """Tests for QueryTokenizer."""
    
    def test_tokenize_literal(self) -> None:
        """Test tokenizing a simple literal."""
        tokenizer = QueryTokenizer("`error`")
        tokens = tokenizer.tokenize()
        
        assert len(tokens) == 1
        assert tokens[0] == ('LITERAL', 'error')
    
    def test_tokenize_and(self) -> None:
        """Test tokenizing AND expression."""
        tokenizer = QueryTokenizer("`error` and `warning`")
        tokens = tokenizer.tokenize()
        
        assert len(tokens) == 3
        assert tokens[0] == ('LITERAL', 'error')
        assert tokens[1] == ('AND', 'and')
        assert tokens[2] == ('LITERAL', 'warning')
    
    def test_tokenize_or(self) -> None:
        """Test tokenizing OR expression."""
        tokenizer = QueryTokenizer("`error` or `warning`")
        tokens = tokenizer.tokenize()
        
        assert len(tokens) == 3
        assert tokens[0] == ('LITERAL', 'error')
        assert tokens[1] == ('OR', 'or')
        assert tokens[2] == ('LITERAL', 'warning')
    
    def test_tokenize_not(self) -> None:
        """Test tokenizing NOT expression."""
        tokenizer = QueryTokenizer("not `error`")
        tokens = tokenizer.tokenize()
        
        assert len(tokens) == 2
        assert tokens[0] == ('NOT', 'not')
        assert tokens[1] == ('LITERAL', 'error')
    
    def test_tokenize_parentheses(self) -> None:
        """Test tokenizing parentheses."""
        tokenizer = QueryTokenizer("(`error` or `warning`) and `info`")
        tokens = tokenizer.tokenize()
        
        assert len(tokens) == 7
        assert tokens[0] == ('LPAREN', '(')
        assert tokens[1] == ('LITERAL', 'error')
        assert tokens[2] == ('OR', 'or')
        assert tokens[3] == ('LITERAL', 'warning')
        assert tokens[4] == ('RPAREN', ')')
        assert tokens[5] == ('AND', 'and')
        assert tokens[6] == ('LITERAL', 'info')
    
    def test_tokenize_escaped_backtick(self) -> None:
        """Test tokenizing escaped backtick in literal."""
        tokenizer = QueryTokenizer("`test\\`value`")
        tokens = tokenizer.tokenize()
        
        assert len(tokens) == 1
        assert tokens[0] == ('LITERAL', 'test`value')
    
    def test_tokenize_empty_query(self) -> None:
        """Test tokenizing empty query."""
        tokenizer = QueryTokenizer("")
        tokens = tokenizer.tokenize()
        
        assert len(tokens) == 0
    
    def test_tokenize_whitespace_only(self) -> None:
        """Test tokenizing whitespace only."""
        tokenizer = QueryTokenizer("   \t\n  ")
        tokens = tokenizer.tokenize()
        
        assert len(tokens) == 0
    
    def test_tokenize_unterminated_literal(self) -> None:
        """Test error on unterminated literal."""
        tokenizer = QueryTokenizer("`error")
        
        with pytest.raises(ValueError, match="Unterminated literal"):
            tokenizer.tokenize()
    
    def test_tokenize_unexpected_character(self) -> None:
        """Test error on unexpected character."""
        tokenizer = QueryTokenizer("error")
        
        with pytest.raises(ValueError, match="Unexpected character"):
            tokenizer.tokenize()


class TestSimpleQueryParser:
    """Tests for SimpleQueryParser."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = SimpleQueryParser()
    
    def test_parse_literal(self) -> None:
        """Test parsing a simple literal."""
        ast = self.parser.parse("`error`")
        
        from src.core.simple_query_parser import Literal
        assert isinstance(ast, Literal)
        assert ast.text == "error"
    
    def test_parse_and(self) -> None:
        """Test parsing AND expression."""
        from src.core.simple_query_parser import AndExpr, Literal
        
        ast = self.parser.parse("`error` and `warning`")
        
        assert isinstance(ast, AndExpr)
        assert len(ast.operands) == 2
        assert isinstance(ast.operands[0], Literal)
        assert isinstance(ast.operands[1], Literal)
        assert ast.operands[0].text == "error"
        assert ast.operands[1].text == "warning"
    
    def test_parse_or(self) -> None:
        """Test parsing OR expression."""
        from src.core.simple_query_parser import OrExpr, Literal
        
        ast = self.parser.parse("`error` or `warning`")
        
        assert isinstance(ast, OrExpr)
        assert len(ast.operands) == 2
    
    def test_parse_not(self) -> None:
        """Test parsing NOT expression."""
        from src.core.simple_query_parser import NotExpr, Literal
        
        ast = self.parser.parse("not `error`")
        
        assert isinstance(ast, NotExpr)
        assert isinstance(ast.operand, Literal)
        assert ast.operand.text == "error"
    
    def test_parse_parentheses(self) -> None:
        """Test parsing parentheses."""
        from src.core.simple_query_parser import AndExpr, OrExpr, Literal
        
        ast = self.parser.parse("(`error` or `warning`) and `info`")
        
        assert isinstance(ast, AndExpr)
        assert isinstance(ast.operands[0], OrExpr)
        assert isinstance(ast.operands[1], Literal)
    
    def test_operator_precedence(self) -> None:
        """Test operator precedence: not > and > or."""
        from src.core.simple_query_parser import OrExpr, AndExpr, NotExpr, Literal
        
        # "not `a` and `b` or `c`" should parse as "((not `a`) and `b`) or `c`"
        ast = self.parser.parse("not `a` and `b` or `c`")
        
        assert isinstance(ast, OrExpr)
        assert isinstance(ast.operands[0], AndExpr)
        assert isinstance(ast.operands[0].operands[0], NotExpr)
    
    def test_evaluate_literal(self) -> None:
        """Test evaluating a literal."""
        ast = self.parser.parse("`error`")
        
        entry_match = create_entry("An error occurred")
        entry_no_match = create_entry("All is fine")
        
        assert self.parser.evaluate(ast, entry_match) is True
        assert self.parser.evaluate(ast, entry_no_match) is False
    
    def test_evaluate_and(self) -> None:
        """Test evaluating AND expression."""
        ast = self.parser.parse("`error` and `failed`")
        
        entry_both = create_entry("error: operation failed")
        entry_one = create_entry("error: operation succeeded")
        entry_none = create_entry("All is fine")
        
        assert self.parser.evaluate(ast, entry_both) is True
        assert self.parser.evaluate(ast, entry_one) is False
        assert self.parser.evaluate(ast, entry_none) is False
    
    def test_evaluate_or(self) -> None:
        """Test evaluating OR expression."""
        ast = self.parser.parse("`error` or `warning`")
        
        entry_error = create_entry("An error occurred")
        entry_warning = create_entry("A warning occurred")
        entry_neither = create_entry("All is fine")
        
        assert self.parser.evaluate(ast, entry_error) is True
        assert self.parser.evaluate(ast, entry_warning) is True
        assert self.parser.evaluate(ast, entry_neither) is False
    
    def test_evaluate_not(self) -> None:
        """Test evaluating NOT expression."""
        ast = self.parser.parse("not `error`")
        
        entry_error = create_entry("An error occurred")
        entry_no_error = create_entry("All is fine")
        
        assert self.parser.evaluate(ast, entry_error) is False
        assert self.parser.evaluate(ast, entry_no_error) is True
    
    def test_evaluate_complex(self) -> None:
        """Test evaluating complex expression."""
        ast = self.parser.parse("(`error` or `warning`) and not `ignored`")
        
        entry_match = create_entry("error: something bad")
        entry_ignored = create_entry("error: but ignored")
        entry_no_match = create_entry("All is fine")
        
        assert self.parser.evaluate(ast, entry_match) is True
        assert self.parser.evaluate(ast, entry_ignored) is False
        assert self.parser.evaluate(ast, entry_no_match) is False
    
    def test_compile(self) -> None:
        """Test compiling a query."""
        matcher = self.parser.compile("`error`")
        
        entry_match = create_entry("An error occurred")
        entry_no_match = create_entry("All is fine")
        
        assert matcher(entry_match) is True
        assert matcher(entry_no_match) is False
    
    def test_empty_query(self) -> None:
        """Test empty query matches everything."""
        ast = self.parser.parse("")
        
        entry = create_entry("Any message")
        assert self.parser.evaluate(ast, entry) is True
    
    def test_case_insensitive(self) -> None:
        """Test case-insensitive matching."""
        ast = self.parser.parse("`ERROR`")
        
        entry = create_entry("An error occurred")
        assert self.parser.evaluate(ast, entry) is True


class TestCategoryTree:
    """Tests for CategoryTree."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.tree = CategoryTree()
    
    def test_add_category(self) -> None:
        """Test adding a category."""
        self.tree.add_category("HordeMode/scripts/app")
        
        assert "HordeMode" in self.tree
        assert "HordeMode/scripts" in self.tree
        assert "HordeMode/scripts/app" in self.tree
    
    def test_add_multiple_categories(self) -> None:
        """Test adding multiple categories."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("app/models")
        self.tree.add_category("app/views")
        
        # Tree contains: app, app/controllers, app/models, app/views (4 nodes)
        assert len(self.tree) == 4
        assert "app" in self.tree
        assert "app/controllers" in self.tree
        assert "app/models" in self.tree
        assert "app/views" in self.tree
    
    def test_toggle_category(self) -> None:
        """Test toggling a category."""
        self.tree.add_category("app/controllers")
        
        # Initially enabled
        assert self.tree.is_enabled("app/controllers")
        
        # Disable
        self.tree.toggle("app/controllers", False)
        assert not self.tree.is_enabled("app/controllers")
        
        # Enable
        self.tree.toggle("app/controllers", True)
        assert self.tree.is_enabled("app/controllers")
    
    def test_toggle_parent_affects_children(self) -> None:
        """Test that toggling parent affects children."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("app/models")
        
        # Disable parent
        self.tree.toggle("app", False)
        
        assert not self.tree.is_enabled("app")
        assert not self.tree.is_enabled("app/controllers")
        assert not self.tree.is_enabled("app/models")
    
    def test_toggle_child_does_not_affect_parent(self) -> None:
        """Test that toggling child does not affect parent."""
        self.tree.add_category("app/controllers")
        
        # Disable child
        self.tree.toggle("app/controllers", False)
        
        assert self.tree.is_enabled("app")
        assert not self.tree.is_enabled("app/controllers")
    
    def test_get_enabled_categories(self) -> None:
        """Test getting enabled categories."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("app/models")
        
        enabled = self.tree.get_enabled_categories()
        assert len(enabled) == 3
        assert "app" in enabled
        assert "app/controllers" in enabled
        assert "app/models" in enabled
    
    def test_get_all_categories(self) -> None:
        """Test getting all categories."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("app/models")
        
        all_cats = self.tree.get_all_categories()
        assert len(all_cats) == 3
    
    def test_enable_all(self) -> None:
        """Test enabling all categories."""
        self.tree.add_category("app/controllers")
        self.tree.toggle("app", False)
        
        self.tree.enable_all()
        
        assert self.tree.is_enabled("app")
        assert self.tree.is_enabled("app/controllers")
    
    def test_disable_all(self) -> None:
        """Test disabling all categories."""
        self.tree.add_category("app/controllers")
        
        self.tree.disable_all()
        
        assert not self.tree.is_enabled("app")
        assert not self.tree.is_enabled("app/controllers")
    
    def test_clear(self) -> None:
        """Test clearing all categories."""
        self.tree.add_category("app/controllers")
        
        self.tree.clear()
        
        assert len(self.tree) == 0
    
    def test_get_node(self) -> None:
        """Test getting a node by path."""
        self.tree.add_category("app/controllers")
        
        node = self.tree.get_node("app/controllers")
        
        assert node is not None
        assert node.name == "controllers"
        assert node.full_path == "app/controllers"
    
    def test_get_children(self) -> None:
        """Test getting children of a category."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("app/models")
        
        children = self.tree.get_children("app")
        
        assert len(children) == 2
        names = {c.name for c in children}
        assert "controllers" in names
        assert "models" in names
    
    def test_get_root_categories(self) -> None:
        """Test getting root categories."""
        self.tree.add_category("app/controllers")
        self.tree.add_category("lib/utils")
        
        roots = self.tree.get_root_categories()
        
        assert len(roots) == 2
        names = {r.name for r in roots}
        assert "app" in names
        assert "lib" in names


class TestFilterEngine:
    """Tests for FilterEngine."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.engine = FilterEngine()
    
    def test_plain_filter(self) -> None:
        """Test plain text filter."""
        state = FilterState(
            enabled_categories={"test"},
            filter_text="error",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = self.engine.compile_filter(state)
        
        entry_match = create_entry("An error occurred")
        entry_no_match = create_entry("All is fine")
        
        assert filter_func(entry_match) is True
        assert filter_func(entry_no_match) is False
    
    def test_plain_filter_case_insensitive(self) -> None:
        """Test plain text filter is case-insensitive."""
        state = FilterState(
            enabled_categories={"test"},
            filter_text="ERROR",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = self.engine.compile_filter(state)
        
        entry = create_entry("An error occurred")
        assert filter_func(entry) is True
    
    def test_regex_filter(self) -> None:
        """Test regex filter."""
        state = FilterState(
            enabled_categories={"test"},
            filter_text=r"error:\s*\d+",
            filter_mode=FilterMode.REGEX
        )
        
        filter_func = self.engine.compile_filter(state)
        
        entry_match = create_entry("error: 404 not found")
        entry_no_match = create_entry("error: not found")
        
        assert filter_func(entry_match) is True
        assert filter_func(entry_no_match) is False
    
    def test_regex_filter_caching(self) -> None:
        """Test that regex patterns are cached."""
        state = FilterState(
            enabled_categories={"test"},
            filter_text=r"\d+",
            filter_mode=FilterMode.REGEX
        )
        
        # Compile twice
        self.engine.compile_filter(state)
        self.engine.compile_filter(state)
        
        # Should be cached
        assert self.engine.get_cache_size() == 1
    
    def test_simple_filter(self) -> None:
        """Test simple query filter."""
        state = FilterState(
            enabled_categories={"test"},
            filter_text="`error` and not `ignored`",
            filter_mode=FilterMode.SIMPLE
        )
        
        filter_func = self.engine.compile_filter(state)
        
        entry_match = create_entry("error: something bad")
        entry_ignored = create_entry("error: but ignored")
        entry_no_match = create_entry("All is fine")
        
        assert filter_func(entry_match) is True
        assert filter_func(entry_ignored) is False
        assert filter_func(entry_no_match) is False
    
    def test_category_filter(self) -> None:
        """Test category filtering."""
        state = FilterState(
            enabled_categories={"app"},
            filter_text="",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = self.engine.compile_filter(state)
        
        entry_app = create_entry("message", category="app")
        entry_lib = create_entry("message", category="lib")
        
        assert filter_func(entry_app) is True
        assert filter_func(entry_lib) is False
    
    def test_category_filter_nested_parent_enabled(self) -> None:
        """Test that enabling parent category matches nested child categories."""
        # When "app" is enabled, entries with "app/controllers" should also match
        state = FilterState(
            enabled_categories={"app"},
            filter_text="",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = self.engine.compile_filter(state)
        
        entry_app = create_entry("message", category="app")
        entry_app_controllers = create_entry("message", category="app/controllers")
        entry_app_models = create_entry("message", category="app/models")
        entry_lib = create_entry("message", category="lib")
        
        assert filter_func(entry_app) is True
        assert filter_func(entry_app_controllers) is True
        assert filter_func(entry_app_models) is True
        assert filter_func(entry_lib) is False
    
    def test_category_filter_nested_middle_enabled(self) -> None:
        """Test that enabling middle category matches deeper nested categories."""
        # When "HordeMode/scripts" is enabled, entries with "HordeMode/scripts/app" should match
        state = FilterState(
            enabled_categories={"HordeMode/scripts"},
            filter_text="",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = self.engine.compile_filter(state)
        
        entry_hordemode = create_entry("message", category="HordeMode")
        entry_hordemode_scripts = create_entry("message", category="HordeMode/scripts")
        entry_hordemode_scripts_app = create_entry("message", category="HordeMode/scripts/app")
        entry_hordemode_scripts_core = create_entry("message", category="HordeMode/scripts/core")
        entry_other = create_entry("message", category="other")
        
        assert filter_func(entry_hordemode) is False  # Parent not enabled
        assert filter_func(entry_hordemode_scripts) is True  # Exact match
        assert filter_func(entry_hordemode_scripts_app) is True  # Child of enabled
        assert filter_func(entry_hordemode_scripts_core) is True  # Child of enabled
        assert filter_func(entry_other) is False
    
    def test_category_filter_nested_specific_enabled(self) -> None:
        """Test that enabling specific category only matches that category and its children."""
        # When "app/controllers" is enabled, only "app/controllers" and its children match
        state = FilterState(
            enabled_categories={"app/controllers"},
            filter_text="",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = self.engine.compile_filter(state)
        
        entry_app = create_entry("message", category="app")
        entry_app_controllers = create_entry("message", category="app/controllers")
        entry_app_controllers_api = create_entry("message", category="app/controllers/api")
        entry_app_models = create_entry("message", category="app/models")
        
        assert filter_func(entry_app) is False  # Parent not enabled
        assert filter_func(entry_app_controllers) is True  # Exact match
        assert filter_func(entry_app_controllers_api) is True  # Child of enabled
        assert filter_func(entry_app_models) is False  # Sibling not enabled
    
    def test_combined_filter(self) -> None:
        """Test combined category and text filter."""
        state = FilterState(
            enabled_categories={"app"},
            filter_text="error",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = self.engine.compile_filter(state)
        
        entry_match = create_entry("error message", category="app")
        entry_wrong_cat = create_entry("error message", category="lib")
        entry_wrong_text = create_entry("info message", category="app")
        
        assert filter_func(entry_match) is True
        assert filter_func(entry_wrong_cat) is False
        assert filter_func(entry_wrong_text) is False
    
    def test_empty_filter(self) -> None:
        """Test empty filter matches everything."""
        state = FilterState(
            enabled_categories=set(),
            filter_text="",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = self.engine.compile_filter(state)
        
        entry = create_entry("Any message")
        assert filter_func(entry) is True
    
    def test_validate_plain_filter(self) -> None:
        """Test validating plain filter."""
        is_valid, error = self.engine.validate_filter("error", FilterMode.PLAIN)
        
        assert is_valid is True
        assert error == ""
    
    def test_validate_regex_filter_valid(self) -> None:
        """Test validating valid regex filter."""
        is_valid, error = self.engine.validate_filter(r"\d+", FilterMode.REGEX)
        
        assert is_valid is True
        assert error == ""
    
    def test_validate_regex_filter_invalid(self) -> None:
        """Test validating invalid regex filter."""
        is_valid, error = self.engine.validate_filter(r"[invalid", FilterMode.REGEX)
        
        assert is_valid is False
        assert "Invalid regex" in error
    
    def test_validate_simple_filter_valid(self) -> None:
        """Test validating valid simple filter."""
        is_valid, error = self.engine.validate_filter("`error` and `warning`", FilterMode.SIMPLE)
        
        assert is_valid is True
        assert error == ""
    
    def test_validate_simple_filter_invalid(self) -> None:
        """Test validating invalid simple filter."""
        is_valid, error = self.engine.validate_filter("`error", FilterMode.SIMPLE)
        
        assert is_valid is False
        assert "Invalid query" in error
    
    def test_clear_cache(self) -> None:
        """Test clearing regex cache."""
        state = FilterState(
            enabled_categories={"test"},
            filter_text=r"\d+",
            filter_mode=FilterMode.REGEX
        )
        
        self.engine.compile_filter(state)
        assert self.engine.get_cache_size() == 1
        
        self.engine.clear_cache()
        assert self.engine.get_cache_size() == 0


class TestFilterIntegration:
    """Integration tests for filtering system."""
    
    def test_full_filtering_workflow(self) -> None:
        """Test complete filtering workflow."""
        # Create entries
        entries = [
            create_entry("Error in app", category="app", level=LogLevel.ERROR),
            create_entry("Warning in app", category="app", level=LogLevel.WARNING),
            create_entry("Info in app", category="app", level=LogLevel.MSG),
            create_entry("Error in lib", category="lib", level=LogLevel.ERROR),
            create_entry("Info in lib", category="lib", level=LogLevel.MSG),
        ]
        
        # Create filter for errors in app
        engine = FilterEngine()
        state = FilterState(
            enabled_categories={"app"},
            filter_text="Error",
            filter_mode=FilterMode.PLAIN
        )
        
        filter_func = engine.compile_filter(state)
        
        # Filter entries
        filtered = [e for e in entries if filter_func(e)]
        
        assert len(filtered) == 1
        assert filtered[0].display_message == "Error in app"
    
    def test_regex_filtering_workflow(self) -> None:
        """Test regex filtering workflow."""
        entries = [
            create_entry("Error 404: Not found"),
            create_entry("Error 500: Server error"),
            create_entry("Warning: Something"),
        ]
        
        engine = FilterEngine()
        state = FilterState(
            enabled_categories={"test"},
            filter_text=r"Error \d+",
            filter_mode=FilterMode.REGEX
        )
        
        filter_func = engine.compile_filter(state)
        filtered = [e for e in entries if filter_func(e)]
        
        assert len(filtered) == 2
    
    def test_simple_query_filtering_workflow(self) -> None:
        """Test simple query filtering workflow."""
        entries = [
            create_entry("Error: critical failure"),
            create_entry("Error: ignored failure"),
            create_entry("Warning: check this"),
            create_entry("Info: all good"),
        ]
        
        engine = FilterEngine()
        state = FilterState(
            enabled_categories={"test"},
            filter_text="`Error` and not `ignored`",
            filter_mode=FilterMode.SIMPLE
        )
        
        filter_func = engine.compile_filter(state)
        filtered = [e for e in entries if filter_func(e)]
        
        assert len(filtered) == 1
        assert "critical" in filtered[0].display_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])