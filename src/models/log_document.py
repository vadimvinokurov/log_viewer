"""Full-loading log document model."""
from __future__ import annotations

from pathlib import Path

from beartype import beartype
from beartype.typing import Callable

from src.models.log_entry import LogEntry


# Ref: docs/specs/features/file-management.md §3.1-§3.4
# Ref: docs/specs/global/memory-model.md §3.2
# Master: docs/SPEC.md §1 (Python 3.12+, PySide6, beartype)
# Memory: All entries loaded into memory, ~200-500 bytes per line
# Thread: Background thread (IndexWorker) - see docs/specs/global/threading.md
class LogDocument:
    """Document model with full file loading.
    
    All log entries are loaded into memory for fast filtering and search.
    File handle is closed immediately after loading.
    """
    
    @beartype
    def __init__(self, filepath: str) -> None:
        """
        Initialize document.
        
        Args:
            filepath: Path to log file
        """
        self.filepath = filepath
        self._entries: list[LogEntry] = []  # All entries loaded into memory
        self._categories: set[str] = set()  # Unique categories
        self._parser = None  # Lazy import to avoid circular dependency
    
    def _get_parser(self):
        """Get parser instance (lazy import to avoid circular dependency)."""
        if self._parser is None:
            from src.core.parser import LogParser
            self._parser = LogParser()
        return self._parser
    
    @beartype
    def load(
        self,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> None:
        """
        Load all lines into memory.
        
        Args:
            progress_callback: Optional callback(bytes_read, total_bytes)
        
        Must be called before get_all_entries().
        File handle is closed immediately after loading.
        """
        # Get file size for progress reporting
        total_bytes = Path(self.filepath).stat().st_size
        
        self._entries = []
        self._categories = set()
        
        # Open file in binary mode for accurate byte offsets
        with open(self.filepath, 'rb') as file_handle:
            bytes_read = 0
            row_index = 0
            
            # Read through file loading all entries
            while True:
                # Record offset of line start
                line_start_offset = file_handle.tell()
                
                # Read a line
                line_bytes = file_handle.readline()
                
                if not line_bytes:
                    break
                
                # Parse line to extract category (decode for parsing)
                try:
                    line_str = line_bytes.decode('utf-8').rstrip('\r\n')
                    if line_str.strip():
                        entry = self._get_parser().parse_line(
                            line_str, row_index, line_start_offset
                        )
                        if entry:
                            self._entries.append(entry)
                            self._categories.add(entry.category)
                            row_index += 1
                except UnicodeDecodeError:
                    # Skip lines that can't be decoded
                    pass
                
                # Update progress
                bytes_read += len(line_bytes)
                if progress_callback and total_bytes > 0:
                    progress_callback(bytes_read, total_bytes)
        
        # File handle is now closed (via context manager)
    
    @beartype
    def get_all_entries(self) -> list[LogEntry]:
        """
        Return all loaded log entries.
        
        Returns:
            List of all LogEntry objects loaded into memory.
        
        Raises:
            beartype.BeartypeCallHintParamViolation: If return type doesn't match.
        """
        return self._entries
    
    @beartype
    def get_line_count(self) -> int:
        """Return total number of lines."""
        return len(self._entries)
    
    @beartype
    def get_categories(self) -> set[str]:
        """Return all unique categories found."""
        return self._categories.copy()
    
    @beartype
    def get_raw_line(self, file_offset: int) -> str:
        """Load raw line from file at given byte offset.
        
        // Ref: docs/specs/features/log-entry-optimization.md §4.3
        // Lazy loading of raw_line for clipboard operations
        
        Args:
            file_offset: Byte offset in file
            
        Returns:
            Raw line string (original log line)
            
        Raises:
            FileNotFoundError: If file no longer exists
            IOError: If seek fails
        """
        with open(self.filepath, 'rb') as f:
            f.seek(file_offset)
            line_bytes = f.readline()
            return line_bytes.decode('utf-8').rstrip('\r\n')