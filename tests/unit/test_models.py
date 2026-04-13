"""Tests for core data models."""

from log_viewer.core.models import (
    CategoryNode,
    Filter,
    Highlight,
    InputMode,
    LogLevel,
    LogLine,
    SearchDirection,
    SearchMode,
    SearchState,
)


class TestLogLevel:
    def test_all_levels_defined(self) -> None:
        expected = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"]
        assert [level.name for level in LogLevel] == expected

    def test_level_values(self) -> None:
        assert LogLevel.CRITICAL.value == "LOG_CRITICAL"
        assert LogLevel.ERROR.value == "LOG_ERROR"
        assert LogLevel.WARNING.value == "LOG_WARNING"
        assert LogLevel.INFO.value == "LOG_INFO"
        assert LogLevel.DEBUG.value == "LOG_DEBUG"
        assert LogLevel.TRACE.value == "LOG_TRACE"

    def test_from_log_prefix_valid(self) -> None:
        assert LogLevel.from_log_prefix("LOG_ERROR") == LogLevel.ERROR
        assert LogLevel.from_log_prefix("LOG_INFO") == LogLevel.INFO
        assert LogLevel.from_log_prefix("LOG_DEBUG") == LogLevel.DEBUG

    def test_from_log_prefix_invalid(self) -> None:
        assert LogLevel.from_log_prefix("something") is None
        assert LogLevel.from_log_prefix("") is None


class TestLogLine:
    def test_create_log_line(self) -> None:
        line = LogLine(
            line_number=1,
            timestamp="20-03-2026T12:20:42.258",
            category="HordeMode/game_storage",
            level=LogLevel.ERROR,
            message="Failed to open file",
            raw="20-03-2026T12:20:42.258 HordeMode/game_storage LOG_ERROR Failed to open file",
        )
        assert line.line_number == 1
        assert line.level == LogLevel.ERROR
        assert line.category == "HordeMode/game_storage"

    def test_log_line_is_dataclass(self) -> None:
        line = LogLine(
            line_number=1,
            timestamp="",
            category="test",
            level=LogLevel.INFO,
            message="msg",
            raw="raw",
        )
        assert hasattr(line, "__dataclass_fields__")

    def test_time_only_from_full_timestamp(self) -> None:
        line = LogLine(
            line_number=1,
            timestamp="20-03-2026T12:20:42.305",
            category="test",
            level=LogLevel.INFO,
            message="msg",
            raw="raw",
        )
        assert line.time_only == "12:20:42.305"

    def test_time_only_empty_timestamp(self) -> None:
        line = LogLine(
            line_number=1,
            timestamp="",
            category="test",
            level=LogLevel.INFO,
            message="msg",
            raw="raw",
        )
        assert line.time_only == ""

    def test_time_only_no_t_separator(self) -> None:
        line = LogLine(
            line_number=1,
            timestamp="12:20:42.305",
            category="test",
            level=LogLevel.INFO,
            message="msg",
            raw="raw",
        )
        assert line.time_only == "12:20:42.305"


class TestSearchEnums:
    def test_search_modes(self) -> None:
        assert SearchMode.PLAIN.value == "plain"
        assert SearchMode.REGEX.value == "regex"
        assert SearchMode.SIMPLE.value == "simple"

    def test_search_directions(self) -> None:
        assert SearchDirection.FORWARD.value == "forward"
        assert SearchDirection.BACKWARD.value == "backward"

    def test_input_modes(self) -> None:
        assert InputMode.NORMAL.value == "normal"
        assert InputMode.COMMAND.value == "command"
        assert InputMode.SEARCH_FORWARD.value == "search_forward"
        assert InputMode.SEARCH_BACKWARD.value == "search_backward"


class TestFilter:
    def test_create_filter(self) -> None:
        f = Filter(pattern="ERROR", mode=SearchMode.PLAIN, case_sensitive=False)
        assert f.pattern == "ERROR"
        assert f.mode == SearchMode.PLAIN
        assert not f.case_sensitive

    def test_filter_defaults(self) -> None:
        f = Filter(pattern="test", mode=SearchMode.PLAIN, case_sensitive=False)
        assert f.case_sensitive is False


class TestHighlight:
    def test_create_highlight(self) -> None:
        h = Highlight(
            pattern="ERROR",
            mode=SearchMode.PLAIN,
            case_sensitive=False,
            color="red",
        )
        assert h.color == "red"


class TestSearchState:
    def test_create_search_state(self) -> None:
        state = SearchState(
            pattern="error",
            mode=SearchMode.PLAIN,
            case_sensitive=False,
            direction=SearchDirection.FORWARD,
            matches=[1, 5, 10],
            current_index=0,
        )
        assert len(state.matches) == 3
        assert state.current_index == 0


class TestCategoryNode:
    def test_create_category_node(self) -> None:
        node = CategoryNode(
            name="network",
            full_path="network",
            enabled=True,
            line_count=100,
            children={},
        )
        assert node.name == "network"
        assert node.enabled is True
        assert node.line_count == 100

    def test_category_node_children(self) -> None:
        child = CategoryNode(
            name="dns",
            full_path="network/dns",
            enabled=True,
            line_count=50,
            children={},
        )
        parent = CategoryNode(
            name="network",
            full_path="network",
            enabled=True,
            line_count=100,
            children={"dns": child},
        )
        assert "dns" in parent.children
        assert parent.children["dns"].full_path == "network/dns"
