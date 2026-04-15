"""Tests for CommandSuggester (file path and category completion)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from log_viewer.core.log_store import LogStore
from log_viewer.core.models import CategoryNode
from log_viewer.core.suggester import CommandSuggester


@pytest.fixture
def suggester() -> CommandSuggester:
    return CommandSuggester()


@pytest.fixture
def tmp_tree(tmp_path: Path) -> Path:
    """Create a temp directory with files and subdirs for testing."""
    (tmp_path / "alpha.txt").write_text("a")
    (tmp_path / "alpha.log").write_text("b")
    (tmp_path / "beta.txt").write_text("c")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.log").write_text("d")
    return tmp_path


# --- File path completion tests ---


@pytest.mark.asyncio
async def test_returns_none_for_non_open_command(
    suggester: CommandSuggester,
) -> None:
    result = await suggester.get_suggestion(":q")
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_for_empty_path(
    suggester: CommandSuggester,
) -> None:
    result = await suggester.get_suggestion(":open ")
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_no_match(
    suggester: CommandSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/zzz")
    assert result is None


@pytest.mark.asyncio
async def test_completes_single_file_match(
    suggester: CommandSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/bet")
    assert result == f":open {tmp_tree}/beta.txt"


@pytest.mark.asyncio
async def test_completes_first_match_when_multiple(
    suggester: CommandSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/alpha")
    # Sorted alphabetically: alpha.log < alpha.txt, so first match is alpha.log
    assert result == f":open {tmp_tree}/alpha.log"


@pytest.mark.asyncio
async def test_completes_directory_with_trailing_slash(
    suggester: CommandSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/subd")
    assert result == f":open {tmp_tree}/subdir/"


@pytest.mark.asyncio
async def test_completes_inside_existing_directory(
    suggester: CommandSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/subdir/nest")
    assert result == f":open {tmp_tree}/subdir/nested.log"


@pytest.mark.asyncio
async def test_preserves_tilde_in_completions(
    suggester: CommandSuggester,
) -> None:
    home = os.path.expanduser("~")
    entries = os.listdir(home)
    if not entries:
        pytest.skip("Home directory is empty")
    first = sorted(entries)[0]
    result = await suggester.get_suggestion(f":open ~/{first[0]}")
    expected = f"~/{first}"
    expected_full = os.path.join(home, first)
    if os.path.isdir(expected_full):
        expected += "/"
    assert result == f":open {expected}"


@pytest.mark.asyncio
async def test_completes_absolute_root_dir(
    suggester: CommandSuggester,
) -> None:
    entries = os.listdir("/")
    if not entries:
        pytest.skip("Root directory is empty")
    first = sorted(entries)[0]
    result = await suggester.get_suggestion(f":open /{first[0]}")
    expected_full = os.path.join("/", first)
    if os.path.isdir(expected_full):
        expected_full += "/"
    assert result == f":open {expected_full}"


@pytest.mark.asyncio
async def test_returns_none_for_non_path_text(
    suggester: CommandSuggester,
) -> None:
    result = await suggester.get_suggestion(":f pattern")
    assert result is None


@pytest.mark.asyncio
async def test_completes_bare_filename_in_cwd(
    suggester: CommandSuggester,
    tmp_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_tree)
    result = await suggester.get_suggestion(":open alp")
    assert result == ":open alpha.log"


# --- Category completion tests ---


def _make_store_with_categories(*paths: str) -> LogStore:
    """Build a LogStore with a category tree from the given paths."""
    store = LogStore()
    tree = store.category_tree
    for path in paths:
        parts = path.split("/")
        built: list[str] = []
        node = tree
        for part in parts:
            built.append(part)
            full = "/".join(built)
            if part not in node.children:
                node.children[part] = CategoryNode(name=part, full_path=full)
            node = node.children[part]
            node.line_count += 1
    return store


@pytest.fixture
def cat_suggester() -> CommandSuggester:
    s = CommandSuggester()
    s.log_store = _make_store_with_categories(
        "HordeMode/game_storage",
        "HordeMode/player_stats",
        "Network/packet_recv",
        "Network/packet_send",
        "System/init",
    )
    return s


@pytest.mark.asyncio
async def test_cate_no_log_store_returns_none() -> None:
    s = CommandSuggester()
    result = await s.get_suggestion(":cate H")
    assert result is None


@pytest.mark.asyncio
async def test_cate_suggests_top_level(
    cat_suggester: CommandSuggester,
) -> None:
    result = await cat_suggester.get_suggestion(":cate ")
    assert result is not None
    # Sorted top-level: HordeMode, Network, System
    assert result == ":cate HordeMode/"


@pytest.mark.asyncio
async def test_cate_suggests_partial_top_level(
    cat_suggester: CommandSuggester,
) -> None:
    result = await cat_suggester.get_suggestion(":cate N")
    assert result == ":cate Network/"


@pytest.mark.asyncio
async def test_cate_suggests_child_node(
    cat_suggester: CommandSuggester,
) -> None:
    result = await cat_suggester.get_suggestion(":cate HordeMode/g")
    assert result == ":cate HordeMode/game_storage"


@pytest.mark.asyncio
async def test_cate_partial_child_match(
    cat_suggester: CommandSuggester,
) -> None:
    result = await cat_suggester.get_suggestion(":cate HordeMode/p")
    assert result == ":cate HordeMode/player_stats"


@pytest.mark.asyncio
async def test_cate_no_match_returns_none(
    cat_suggester: CommandSuggester,
) -> None:
    result = await cat_suggester.get_suggestion(":cate Zzz")
    assert result is None


@pytest.mark.asyncio
async def test_catd_works_same_as_cate(
    cat_suggester: CommandSuggester,
) -> None:
    result = await cat_suggester.get_suggestion(":catd Net")
    assert result == ":catd Network/"


@pytest.mark.asyncio
async def test_cate_leaf_has_no_trailing_slash(
    cat_suggester: CommandSuggester,
) -> None:
    result = await cat_suggester.get_suggestion(":cate System/i")
    assert result == ":cate System/init"


@pytest.mark.asyncio
async def test_cate_empty_tree_returns_none() -> None:
    s = CommandSuggester()
    s.log_store = LogStore()  # empty tree
    result = await s.get_suggestion(":cate ")
    assert result is None


# --- get_all_suggestions tests ---


def test_all_file_suggestions_returns_multiple(
    suggester: CommandSuggester,
    tmp_tree: Path,
) -> None:
    results = suggester.get_all_suggestions(f":open {tmp_tree}/alpha")
    assert results == [
        f":open {tmp_tree}/alpha.log",
        f":open {tmp_tree}/alpha.txt",
    ]


def test_all_file_suggestions_returns_empty_on_no_match(
    suggester: CommandSuggester,
    tmp_tree: Path,
) -> None:
    results = suggester.get_all_suggestions(f":open {tmp_tree}/zzz")
    assert results == []


def test_all_category_suggestions_top_level(
    cat_suggester: CommandSuggester,
) -> None:
    results = cat_suggester.get_all_suggestions(":cate ")
    assert results == [
        ":cate HordeMode/",
        ":cate Network/",
        ":cate System/",
    ]


def test_all_category_suggestions_children(
    cat_suggester: CommandSuggester,
) -> None:
    results = cat_suggester.get_all_suggestions(":cate HordeMode/")
    assert results == [
        ":cate HordeMode/game_storage",
        ":cate HordeMode/player_stats",
    ]


def test_all_category_suggestions_partial(
    cat_suggester: CommandSuggester,
) -> None:
    results = cat_suggester.get_all_suggestions(":cate HordeMode/p")
    assert results == [":cate HordeMode/player_stats"]


def test_all_category_suggestions_network_children(
    cat_suggester: CommandSuggester,
) -> None:
    results = cat_suggester.get_all_suggestions(":cate Network/p")
    assert results == [
        ":cate Network/packet_recv",
        ":cate Network/packet_send",
    ]


def test_all_category_suggestions_empty_on_no_match(
    cat_suggester: CommandSuggester,
) -> None:
    results = cat_suggester.get_all_suggestions(":cate Zzz")
    assert results == []
