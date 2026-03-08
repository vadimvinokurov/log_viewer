# Error Handling Specification

**Version:** 1.0  
**Last Updated:** 2026-03-13  
**Project Context:** Python Tooling (Desktop Application)

---

## §1 Overview

This document defines error handling patterns, logging conventions, and recovery strategies for the Log Viewer application.

---

## §2 Error Categories

### §2.1 Error Classification

| Category | Severity | User Impact | Recovery |
|----------|----------|-------------|----------|
| **Critical** | High | Application crash | Log + exit |
| **Error** | Medium | Feature unavailable | Log + user notification |
| **Warning** | Low | Degraded functionality | Log + continue |
| **Info** | None | Status update | Log only |
| **Debug** | None | Development info | Log if debug enabled |

### §2.2 Error Types

```python
# File errors
FileNotFoundError: File not found
PermissionError: Access denied
UnicodeDecodeError: Encoding error

# Parsing errors
ValueError: Malformed log line
IndexError: Missing fields

# Qt errors
RuntimeError: Qt resource error
```

---

## §3 Logging Standards

### §3.1 Logger Configuration

```python
import logging

# Module-level logger
logger = logging.getLogger(__name__)

# Standard format
# %(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### §3.2 Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| `DEBUG` | Development details | `"Processing line {i}"` |
| `INFO` | Normal operations | `"Opened file: {filepath}"` |
| `WARNING` | Recoverable issues | `"Failed to parse line {n}"` |
| `ERROR` | Feature failure | `"Failed to open file: {e}"` |
| `CRITICAL` | Application failure | `"Unrecoverable error: {e}"` |

### §3.3 Logging Patterns

```python
# Good: Structured logging with context
logger.info(f"Opened file: {filepath}")
logger.warning(f"Failed to parse line {n}: {e}")
logger.error(f"Failed to open file {filepath}: {e}")

# Bad: Unstructured logging
logger.info("Opened file")
logger.warning("Parse error")
logger.error("Error")
```

---

## §4 Error Handling Patterns

### §4.1 File Operations

```python
def open_file(self, filepath: str) -> None:
    """Open a log file with error handling."""
    try:
        self._document = LogDocument(filepath)
        self._document.build_index()
        logger.info(f"Opened file: {filepath}")
        
    except FileNotFoundError:
        self._window.show_error(
            "File Not Found",
            f"The file '{filepath}' does not exist."
        )
        logger.error(f"File not found: {filepath}")
        
    except PermissionError:
        self._window.show_error(
            "Access Denied",
            f"Permission denied for '{filepath}'."
        )
        logger.error(f"Permission denied: {filepath}")
        
    except UnicodeDecodeError as e:
        self._window.show_error(
            "Encoding Error",
            f"Failed to decode file: {e}"
        )
        logger.error(f"Unicode decode error: {filepath}: {e}")
        
    except Exception as e:
        self._window.show_error_with_details(
            "Error Opening File",
            f"Failed to open '{filepath}'",
            traceback.format_exc()
        )
        logger.exception(f"Unexpected error opening file: {filepath}")
```

### §4.2 Parsing Operations

```python
def parse_line(self, line: str, row: int, offset: int) -> LogEntry | None:
    """Parse a log line with graceful degradation.
    
    Returns None for malformed lines (logged as warning).
    Never raises exceptions to caller.
    """
    try:
        # Parse logic
        return LogEntry(...)
        
    except (ValueError, IndexError) as e:
        logger.warning(f"Malformed line {row}: {e}")
        return None  # Graceful degradation
```

### §4.3 Filter Operations

```python
def apply_filter(self) -> bool:
    """Apply filter with validation.
    
    Returns:
        True if successful, False if error.
    """
    is_valid, error_msg = self._engine.validate_filter(
        self._state.filter_text,
        self._state.filter_mode
    )
    
    if not is_valid:
        self.filter_error.emit(error_msg)
        logger.warning(f"Invalid filter: {error_msg}")
        return False
    
    try:
        self._compiled_filter = self._engine.compile_filter(self._state)
        self.filter_applied.emit()
        return True
        
    except Exception as e:
        self.filter_error.emit(str(e))
        logger.exception("Filter compilation error")
        return False
```

---

## §5 User Notification

### §5.1 Error Dialog Types

```python
# Critical errors - blocking dialog
QMessageBox.critical(parent, title, message)

# Warnings - blocking dialog
QMessageBox.warning(parent, title, message)

# Information - blocking dialog
QMessageBox.information(parent, title, message)

# Questions - user decision
reply = QMessageBox.question(
    parent, title, message,
    QMessageBox.Yes | QMessageBox.No
)
```

### §5.2 Status Bar Messages

```python
# Transient status (auto-dismiss)
self._window.show_status("File loaded", 3000)  # 3 seconds

# Persistent status (manual clear)
self._window.show_status("Loading...", 0)  # No timeout
# ... later ...
self._window.clear_status()
```

### §5.3 Error Dialog with Details

```python
class ErrorDialog:
    @staticmethod
    def show_error(
        title: str,
        message: str,
        details: str = "",
        parent: QWidget = None
    ) -> None:
        """Show error with expandable details."""
        dialog = QMessageBox(parent)
        dialog.setIcon(QMessageBox.Critical)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        
        if details:
            dialog.setDetailedText(details)
        
        dialog.exec()
```

---

## §6 Recovery Strategies

### §6.1 File Loading Recovery

```python
def open_file(self, filepath: str) -> None:
    """Open file with recovery on failure."""
    # Close existing document first
    if self._document is not None:
        try:
            self._document.close()
        except Exception as e:
            logger.warning(f"Error closing previous file: {e}")
        finally:
            self._document = None
    
    try:
        self._document = LogDocument(filepath)
        # ... success path
        
    except Exception as e:
        # Recovery: Reset state
        self._all_entries = []
        self._filtered_entries = []
        self._window.get_log_table().clear()
        self._window.get_category_panel().clear()
        
        # Notify user
        self._window.show_error("Error", str(e))
        logger.exception(f"Failed to open file: {filepath}")
```

### §6.2 Filter Recovery

```python
def _on_filter_error(self, error_message: str) -> None:
    """Handle filter error with recovery."""
    # Show error to user
    self._window.show_error("Filter Error", error_message)
    
    # Recovery: Clear invalid filter
    self._filter_controller.clear_filter()
    logger.warning(f"Filter error, cleared: {error_message}")
```

### §6.3 Settings Recovery

```python
def load(self) -> AppSettings:
    """Load settings with recovery on corruption."""
    try:
        with open(self.filepath, "r") as f:
            data = json.load(f)
        return AppSettings.from_dict(data)
        
    except json.JSONDecodeError as e:
        logger.error(f"Corrupt settings file: {e}")
        # Recovery: Return defaults
        return AppSettings()
        
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        # Recovery: Return defaults
        return AppSettings()
```

---

## §7 Exception Handling Rules

### §7.1 Never Crash on Invalid Input

```python
# Good: Graceful handling
def parse_line(self, line: str, row: int, offset: int) -> LogEntry | None:
    if not line.strip():
        return None  # Empty line
    
    parts = line.split(' ', 2)
    if len(parts) < 2:
        logger.warning(f"Malformed line {row}: insufficient fields")
        return None
    
    # ... parse safely

# Bad: Unhandled exception
def parse_line(self, line: str, row: int, offset: int) -> LogEntry:
    parts = line.split(' ', 2)
    return LogEntry(
        timestamp=parts[0],  # IndexError if malformed
        category=parts[1],
        # ...
    )
```

### §7.2 Log and Continue

```python
# Good: Log warning, continue
for i, line in enumerate(lines):
    entry = self.parse_line(line, i, offset)
    if entry:
        entries.append(entry)
    # Continue even if some lines fail

# Bad: Stop on first error
for i, line in enumerate(lines):
    entry = self.parse_line(line, i, offset)  # Raises on error
    entries.append(entry)
```

### §7.3 Context Managers for Resources

```python
# Good: Context manager ensures cleanup
with LogDocument(filepath) as document:
    document.build_index()
    # ... use document
# File handle automatically closed

# Bad: Manual cleanup (error-prone)
document = LogDocument(filepath)
try:
    document.build_index()
    # ... use document
finally:
    document.close()  # Easy to forget
```

---

## §8 Error Propagation

### §8.1 Controller → View

```python
class MainController(QObject):
    # Signal for error notification
    # (No error signal - use direct method call)
    
    def handle_error(self, title: str, message: str, details: str = "") -> None:
        """Handle error with user feedback."""
        logger.error(f"{title}: {message}")
        if details:
            logger.debug(f"Details: {details}")
        self._window.show_error_with_details(title, message, details)
```

### §8.2 Worker Thread → Main Thread

```python
class IndexWorker(QThread):
    error = Signal(str, str)  # title, message
    
    def run(self) -> None:
        try:
            self._document.build_index()
        except Exception as e:
            self.error.emit("Indexing Error", str(e))

class MainController(QObject):
    def __init__(self):
        self._index_worker.error.connect(self._on_index_error)
    
    def _on_index_error(self, title: str, message: str) -> None:
        # Main thread: Show error
        self._window.show_error(title, message)
```

---

## §9 Validation

### §9.1 Input Validation

```python
@beartype
def validate_filter(self, text: str, mode: FilterMode) -> tuple[bool, str]:
    """Validate filter before compilation.
    
    Returns:
        Tuple of (is_valid, error_message).
    """
    if not text or not text.strip():
        return True, ""  # Empty filter is valid
    
    if mode == FilterMode.REGEX:
        try:
            re.compile(text)
            return True, ""
        except re.error as e:
            return False, f"Invalid regex: {e}"
    
    if mode == FilterMode.SIMPLE:
        try:
            self._simple_parser.parse(text)
            return True, ""
        except ValueError as e:
            return False, f"Invalid query: {e}"
    
    return True, ""  # Plain mode always valid
```

### §9.2 Type Checking with beartype

```python
from beartype import beartype

@beartype
def set_categories(self, categories: set[str]) -> None:
    """Set available categories.
    
    Beartype validates types at runtime.
    """
    self._category_tree.clear()
    for cat in categories:
        self._category_tree.add_category(cat)
```

---

## §10 Error Messages

### §10.1 User-Facing Messages

| Error | User Message | Technical Details |
|-------|--------------|-------------------|
| File not found | "The file '{name}' does not exist." | `FileNotFoundError: {path}` |
| Permission denied | "Permission denied for '{name}'." | `PermissionError: {path}` |
| Encoding error | "Failed to decode file." | `UnicodeDecodeError: {encoding}` |
| Invalid filter | "Invalid filter: {error}" | `re.error: {pattern}` |
| Indexing failed | "Failed to index file." | `Exception: {traceback}` |

### §10.2 Log Messages

```python
# User action
logger.info(f"Opened file: {filepath}")
logger.info(f"Applied filter: {filter_text}")

# Recoverable error
logger.warning(f"Failed to parse line {n}: {e}")
logger.warning(f"Invalid filter pattern: {pattern}")

# Feature failure
logger.error(f"Failed to open file {filepath}: {e}")
logger.error(f"Settings save failed: {e}")

# Unexpected error
logger.exception(f"Unexpected error in {function}")
```

---

## §11 Testing Error Handling

### §11.1 Error Simulation

```python
# Test file not found
def test_open_file_not_found(controller, tmp_path):
    with pytest.raises(FileNotFoundError):
        controller.open_file(str(tmp_path / "nonexistent.log"))
    
    # Verify error shown to user
    controller._window.show_error.assert_called_once()

# Test corrupt settings
def test_load_corrupt_settings(settings_manager, tmp_path):
    corrupt_file = tmp_path / "settings.json"
    corrupt_file.write_text("{ invalid json }")
    
    settings = settings_manager.load()
    
    # Should return defaults
    assert settings == AppSettings()
```

### §11.2 Error Recovery Verification

```python
def test_filter_error_recovery(controller):
    """Test that invalid filter doesn't crash app."""
    # Set invalid regex
    controller._filter_controller.set_filter_text("[invalid")
    controller._filter_controller.set_filter_mode(FilterMode.REGEX)
    
    # Apply should fail gracefully
    result = controller._filter_controller.apply_filter()
    
    assert result is False
    # Should have error signal
    assert controller._filter_controller.filter_error.called
```

---

## §12 Best Practices

### §12.1 Do

✅ Log all errors with context  
✅ Provide user-friendly error messages  
✅ Include technical details in logs  
✅ Use context managers for resources  
✅ Validate input before processing  
✅ Return `None` for parse failures  
✅ Use signals for cross-thread errors  

### §12.2 Don't

❌ Crash on invalid input  
❌ Show raw exceptions to users  
❌ Ignore errors silently  
❌ Use bare `except:` clauses  
❌ Block UI on errors  
❌ Expose internal paths in messages  

---

## §13 Cross-References

- **Memory Model:** [memory-model.md](memory-model.md)
- **Threading Model:** [threading.md](threading.md)
- **File Controller:** [../features/file-management.md](../features/file-management.md)

---

## §14 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-13 | Initial error handling specification |