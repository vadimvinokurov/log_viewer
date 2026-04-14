"""Tests for FilePathSuggester."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from log_viewer.core.suggester import FilePathSuggester


@pytest.fixture
def suggester() -> FilePathSuggester:
    return FilePathSuggester()


@pytest.fixture
def tmp_tree(tmp_path: Path) -> Path:
    """Create a temp directory with files and subdirs for testing."""
    (tmp_path / "alpha.txt").write_text("a")
    (tmp_path / "alpha.log").write_text("b")
    (tmp_path / "beta.txt").write_text("c")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.log").write_text("d")
    return tmp_path


@pytest.mark.asyncio
async def test_returns_none_for_non_open_command(
    suggester: FilePathSuggester,
) -> None:
    result = await suggester.get_suggestion(":q")
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_for_empty_path(
    suggester: FilePathSuggester,
) -> None:
    result = await suggester.get_suggestion(":open ")
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_no_match(
    suggester: FilePathSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/zzz")
    assert result is None


@pytest.mark.asyncio
async def test_completes_single_file_match(
    suggester: FilePathSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/bet")
    assert result == f":open {tmp_tree}/beta.txt"


@pytest.mark.asyncio
async def test_completes_first_match_when_multiple(
    suggester: FilePathSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/alpha")
    # Sorted alphabetically: alpha.log < alpha.txt, so first match is alpha.log
    assert result == f":open {tmp_tree}/alpha.log"


@pytest.mark.asyncio
async def test_completes_directory_with_trailing_slash(
    suggester: FilePathSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/subd")
    assert result == f":open {tmp_tree}/subdir/"


@pytest.mark.asyncio
async def test_completes_inside_existing_directory(
    suggester: FilePathSuggester,
    tmp_tree: Path,
) -> None:
    result = await suggester.get_suggestion(f":open {tmp_tree}/subdir/nest")
    assert result == f":open {tmp_tree}/subdir/nested.log"


@pytest.mark.asyncio
async def test_expands_tilde(
    suggester: FilePathSuggester,
) -> None:
    home = os.path.expanduser("~")
    entries = os.listdir(home)
    if not entries:
        pytest.skip("Home directory is empty")
    first = sorted(entries)[0]
    result = await suggester.get_suggestion(f":open ~/{first[0]}")
    expected_full = os.path.join(home, first)
    if os.path.isdir(expected_full):
        expected_full += "/"
    assert result == f":open {expected_full}"


@pytest.mark.asyncio
async def test_completes_absolute_root_dir(
    suggester: FilePathSuggester,
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
    suggester: FilePathSuggester,
) -> None:
    result = await suggester.get_suggestion(":f pattern")
    assert result is None


@pytest.mark.asyncio
async def test_completes_bare_filename_in_cwd(
    suggester: FilePathSuggester,
    tmp_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_tree)
    result = await suggester.get_suggestion(":open alp")
    assert result == ":open ./alpha.log"
