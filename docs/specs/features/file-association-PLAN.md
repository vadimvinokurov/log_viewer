# File Association Implementation Plan

**Version**: 1.0  
**Created**: 2026-03-21  
**Status**: READY FOR DELEGATION  
**Spec Reference**: [file-association.md](file-association.md)

---

## Overview

This plan breaks down the file association feature into implementation tasks for spec-coder delegation.

**Feature Goal**: Enable users to open log files in Log Viewer using "Open with..." context menu in macOS Finder and Windows Explorer.

**Implementation Approach**: Multi-instance mode (each file opens in separate window)

---

## Task Breakdown

### T-001: Command-Line Argument Parsing

**Priority**: HIGH  
**Estimated Time**: 2 hours  
**Dependencies**: None

#### 📦 TASK DELEGATION
├─ **Task ID**: T-001
├─ **Spec Reference**: §4.1, §4.2 in [file-association.md](file-association.md)
├─ **Master Constraints**: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
├─ **Project Context**: Engine Core / Entry Point
├─ **Scope**: 
│   - `src/main.py` (modify)
├─ **Language**: Python 3.12
├─ **Input/Output**: 
│   - Input: `sys.argv[1:]` (command-line arguments)
│   - Output: List of valid file paths
│   - Memory: Stack allocation for argument list
├─ **Constraints**:
│   - Thread context: Main thread only
│   - Memory: < 1 MB for argument handling
│   - Performance: < 10ms for argument parsing
├─ **Tests Required**: 
│   - Unit: `tests/test_file_association.py::TestParseArguments`
│   - Integration: Manual CLI testing
└─ **Dependencies**: None

#### Implementation Details

1. **Add `parse_arguments()` function**:
   ```python
   @beartype
   def parse_arguments(argv: list[str]) -> list[Path]:
       """Parse command-line arguments.
       
       Args:
           argv: Command-line arguments (sys.argv[1:])
       
       Returns:
           List of valid file paths to open
       """
   ```

2. **Modify `main()` function**:
   - Parse arguments before creating window
   - Open first file in current window
   - Open additional files in new windows via `_open_in_new_window()`

3. **Add `_open_in_new_window()` function**:
   ```python
   def _open_in_new_window(filepath: Path) -> None:
       """Open a file in a new application instance."""
   ```

4. **Error Handling**:
   - Log warning for invalid paths
   - Continue with valid paths only

#### Acceptance Criteria

- [ ] `parse_arguments([])` returns `[]`
- [ ] `parse_arguments(["/valid/file.log"])` returns `[Path("/valid/file.log")]`
- [ ] `parse_arguments(["/nonexistent.log"])` returns `[]` and logs warning
- [ ] `parse_arguments(["--flag", "/file.log"])` skips flag, returns file
- [ ] Multiple files open in separate windows
- [ ] All functions have `@beartype` decorator
- [ ] All functions have complete type annotations

---

### T-002: macOS Info.plist Configuration

**Priority**: HIGH  
**Estimated Time**: 1 hour  
**Dependencies**: T-001

#### 📦 TASK DELEGATION
├─ **Task ID**: T-002
├─ **Spec Reference**: §5.1 in [file-association.md](file-association.md)
├─ **Master Constraints**: docs/SPEC.md §1 (PyInstaller packaging)
├─ **Project Context**: Build System
├─ **Scope**: 
│   - `build/logviewer.spec` (modify)
├─ **Language**: Python (PyInstaller spec)
├─ **Input/Output**: 
│   - Input: None
│   - Output: Info.plist with CFBundleDocumentTypes
├─ **Constraints**:
│   - Platform: macOS only
│   - Build: Must not break existing build
├─ **Tests Required**: 
│   - Manual: Build and verify Info.plist
│   - Integration: Right-click .log file → Open with
└─ **Dependencies**: T-001

#### Implementation Details

1. **Add to `info_plist` dict in `BUNDLE()` call**:
   ```python
   'CFBundleDocumentTypes': [
       {
           'CFBundleTypeName': 'Log File',
           'CFBundleTypeRole': 'Viewer',
           'LSItemContentTypes': [
               'public.log',
               'public.plain-text',
           ],
           'LSHandlerRank': 'Alternate',
           'CFBundleTypeExtensions': [
               'log',
               'txt',
           ],
           'CFBundleTypeIconFile': 'app.icns',
       },
   ],
   'UTExportedTypeDeclarations': [
       {
           'UTTypeIdentifier': 'com.logviewer.log',
           'UTTypeDescription': 'Log File',
           'UTTypeConformsTo': ['public.plain-text'],
           'UTTypeTagSpecification': {
               'public.filename-extension': ['log'],
           },
       },
   ],
   ```

2. **Verify existing entries preserved**:
   - `CFBundleName`, `CFBundleDisplayName`, `CFBundleVersion`
   - `LSMinimumSystemVersion`, `NSHighResolutionCapable`

#### Acceptance Criteria

- [ ] Build succeeds with `pyinstaller build/logviewer.spec`
- [ ] `Log Viewer.app/Contents/Info.plist` contains `CFBundleDocumentTypes`
- [ ] `.log` files show "Log Viewer" in "Open with..." menu
- [ ] `.txt` files show "Log Viewer" in "Open with..." menu
- [ ] App launches when selecting "Open with Log Viewer"

---

### T-003: Unit Tests for File Association

**Priority**: MEDIUM  
**Estimated Time**: 1.5 hours  
**Dependencies**: T-001

#### 📦 TASK DELEGATION
├─ **Task ID**: T-003
├─ **Spec Reference**: §6.1 in [file-association.md](file-association.md)
├─ **Master Constraints**: docs/SPEC.md §8 (pytest, 80% coverage)
├─ **Project Context**: Tests
├─ **Scope**: 
│   - `tests/test_file_association.py` (create)
├─ **Language**: Python 3.12
├─ **Input/Output**: 
│   - Input: Test arguments
│   - Output: Test results
├─ **Constraints**:
│   - Thread context: Main thread only
│   - Memory: Standard test constraints
│   - Performance: Tests run < 1 second
├─ **Tests Required**: 
│   - pytest: `tests/test_file_association.py`
└─ **Dependencies**: T-001

#### Implementation Details

Create `tests/test_file_association.py` with test cases:

1. **TestParseArguments class**:
   - `test_no_arguments()` - empty list returns empty
   - `test_single_valid_file()` - valid file returns path
   - `test_multiple_valid_files()` - multiple valid files
   - `test_nonexistent_file()` - nonexistent returns empty, logs warning
   - `test_directory_argument()` - directory returns empty
   - `test_mixed_valid_invalid()` - returns only valid paths
   - `test_skip_flags()` - flags are skipped

2. **Test fixtures**:
   - Use `tmp_path` fixture from pytest for temporary files

3. **Test markers**:
   - All tests use `@beartype` decorator
   - All tests have complete type annotations

#### Acceptance Criteria

- [ ] All tests pass with `pytest tests/test_file_association.py`
- [ ] Coverage > 80% for `parse_arguments()` function
- [ ] Tests use pytest fixtures correctly
- [ ] Tests follow project conventions (beartype, type hints)

---

### T-004: User Documentation

**Priority**: LOW  
**Estimated Time**: 1 hour  
**Dependencies**: T-001, T-002, T-003

#### 📦 TASK DELEGATION
├─ **Task ID**: T-004
├─ **Spec Reference**: §10.1 in [file-association.md](file-association.md)
├─ **Master Constraints**: docs/SPEC.md §1
├─ **Project Context**: Documentation
├─ **Scope**: 
│   - `README.md` (modify) - add file association section
│   - `docs/FILE_ASSOCIATION.md` (create) - detailed instructions
├─ **Language**: Markdown
├─ **Input/Output**: N/A
├─ **Constraints**: N/A
├─ **Tests Required**: N/A (documentation)
└─ **Dependencies**: T-001, T-002, T-003

#### Implementation Details

1. **Update README.md**:
   - Add "File Association" section under "Features"
   - Brief description of "Open with..." support

2. **Create docs/FILE_ASSOCIATION.md**:
   - How to associate .log files with Log Viewer
   - Platform-specific instructions (macOS, Windows)
   - Troubleshooting common issues
   - Manual file association steps

#### Acceptance Criteria

- [ ] README.md has file association section
- [ ] docs/FILE_ASSOCIATION.md created with detailed instructions
- [ ] Instructions cover macOS and Windows
- [ ] Troubleshooting section included

---

## Task Execution Order

```
T-001 (Command-Line Parsing)
    ↓
    ├── T-002 (macOS Info.plist) [can run in parallel]
    └── T-003 (Unit Tests) [can run in parallel]
            ↓
        T-004 (Documentation)
```

**Parallelization**: T-002 and T-003 can run in parallel after T-001 completes.

---

## Verification Checklist

### After T-001 Completion
- [ ] `parse_arguments()` function exists in `src/main.py`
- [ ] `_open_in_new_window()` function exists in `src/main.py`
- [ ] `main()` function uses `parse_arguments()`
- [ ] Error handling for invalid files implemented

### After T-002 Completion
- [ ] `build/logviewer.spec` contains `CFBundleDocumentTypes`
- [ ] Build succeeds on macOS
- [ ] Info.plist contains correct entries

### After T-003 Completion
- [ ] `tests/test_file_association.py` exists
- [ ] All tests pass
- [ ] Coverage > 80%

### After T-004 Completion
- [ ] README.md updated
- [ ] docs/FILE_ASSOCIATION.md created
- [ ] Documentation is accurate

---

## Integration Testing

After all tasks complete, perform manual integration tests:

### macOS Tests
1. Build app: `bash build/scripts/build-macos.sh`
2. Install DMG or run app bundle
3. Right-click .log file → Open with → Log Viewer
4. Verify app launches and opens file
5. Test with multiple files (select multiple → Open with)
6. Test with nonexistent file (should show error)

### Windows Tests
1. Build executable: `python build/scripts/build-windows.py`
2. Right-click .log file → Open with → Choose another app → Log Viewer
3. Verify app launches and opens file
4. Test with multiple files
5. Test with nonexistent file

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Build breaks on macOS | Test build after T-002, verify existing functionality |
| Tests fail on CI | Run tests locally before committing |
| File association doesn't work | Verify Info.plist entries, test on clean macOS |
| Windows registry issues | Document manual association steps |

---

## Notes for Spec-Coder

1. **Follow existing code style**: Use `@beartype`, type hints, docstrings
2. **Test locally**: Run `pytest tests/test_file_association.py` before committing
3. **Check build**: Run `pyinstaller build/logviewer.spec` after T-002
4. **Update imports**: Add `from pathlib import Path` if not present
5. **Preserve dev mode**: Keep `DEV_AUTO_OPEN_FILE` logic for development

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Plan Author | Spec Orchestrator | 2026-03-21 | READY |
| Plan Reviewer | [Reviewer] | [Date] | [PENDING] |

---

**End of Implementation Plan**