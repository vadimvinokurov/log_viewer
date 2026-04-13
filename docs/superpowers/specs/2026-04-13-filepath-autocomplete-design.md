# File Path Autocomplete for `:open` Command

## Goal

Add tab-completion of file and directory paths when the user types `:open <partial_path>` in the command input, similar to how autocomplete works in a terminal.

## Behavior

- User types `:open ~/Do` in the command bar
- Suggester resolves the partial path against the filesystem
- First matching entry is shown as inline grey text (e.g. `cuments/`)
- User presses **Tab** to accept the suggestion
- Value becomes `:open ~/Documents/`
- Directories get a trailing `/` appended
- If no match, nothing happens (no suggestion shown)
- Only activates for `:open` command — other commands get no suggestions

## Architecture

### FilePathSuggester (`src/log_viewer/core/suggester.py`)

Custom subclass of `textual.suggester.Suggester`:

- `get_suggestion(value: str) -> str | None`
- Parses the input to detect `:open <partial_path>` pattern
- Expands `~` via `os.path.expanduser`
- Resolves parent directory with `os.path.dirname`
- Lists directory contents with `os.listdir`
- Finds first entry that starts with the partial basename
- Returns the full completed value (entire `:open <full_path>`) so Textual can show only the delta as grey text
- Directories get `/` suffix

### CommandInput changes (`src/log_viewer/tui/widgets/command_input.py`)

- Pass `FilePathSuggester()` to `Input.__init__` via `suggester=` parameter
- Add `key_tab` method: if `_suggestion` is non-empty, accept it (set `value = _suggestion`), otherwise pass through

## Key Decisions

- **Tab instead of Right arrow**: Matches terminal muscle memory
- **First match only** (not cycling): Simpler implementation, matches zsh behavior
- **`:open` only**: No autocomplete for command names or other commands
- **No new dependencies**: Uses only stdlib `os.path` and Textual's built-in suggester API

## Testing

- Unit tests for `FilePathSuggester` with mocked filesystem (`tmp_path` fixture)
- Integration test: type `:open <partial>`, press Tab, verify value updated
- Edge cases: no matches, `~` expansion, trailing `/` for directories, paths with spaces
