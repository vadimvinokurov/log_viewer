"""Lazy-loading log document model."""
from typing import Optional, Callable, Set, List
from pathlib import Path
from src.models.log_entry import LogEntry


class LogDocument:
    """Document model with lazy loading for large files."""
    
    def __init__(self, filepath: str):
        """
        Initialize document.
        
        Args:
            filepath: Path to log file
        """
        self.filepath = filepath
        self._line_offsets: List[int] = []
        self._line_count: int = 0
        self._categories: Set[str] = set()
        self._parser = None  # Lazy import to avoid circular dependency
        self._file_handle = None
        self._total_bytes: int = 0
    
    def _get_parser(self):
        """Get parser instance (lazy import to avoid circular dependency)."""
        if self._parser is None:
            from src.core.parser import LogParser
            self._parser = LogParser()
        return self._parser
    
    def build_index(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> None:
        """
        Build byte-offset index for all lines.
        
        Args:
            progress_callback: Optional callback(bytes_read, total_bytes)
        """
        # Get file size for progress reporting
        self._total_bytes = Path(self.filepath).stat().st_size
        
        # Open file in binary mode for accurate byte offsets
        self._file_handle = open(self.filepath, 'rb')
        
        self._line_offsets = []
        self._categories = set()
        
        # Track current position
        current_offset = 0
        bytes_read = 0
        
        # Read through file building index
        while True:
            # Record offset of line start
            line_start_offset = self._file_handle.tell()
            
            # Read a line
            line_bytes = self._file_handle.readline()
            
            if not line_bytes:
                break
            
            # Record line offset
            self._line_offsets.append(line_start_offset)
            
            # Parse line to extract category (decode for parsing)
            try:
                line_str = line_bytes.decode('utf-8').rstrip('\r\n')
                if line_str.strip():
                    entry = self._get_parser().parse_line(line_str, len(self._line_offsets) - 1, line_start_offset)
                    if entry:
                        self._categories.add(entry.category)
            except UnicodeDecodeError:
                # Skip lines that can't be decoded
                pass
            
            # Update progress
            bytes_read += len(line_bytes)
            if progress_callback and self._total_bytes > 0:
                progress_callback(bytes_read, self._total_bytes)
        
        self._line_count = len(self._line_offsets)
        
        # Seek back to beginning for future reads
        self._file_handle.seek(0)
    
    def get_line(self, row: int) -> Optional[LogEntry]:
        """
        Get a single log entry by row index.
        
        Args:
            row: Zero-based row index
            
        Returns:
            LogEntry if valid row, None otherwise
        """
        if row < 0 or row >= self._line_count:
            return None
        
        if self._file_handle is None:
            return None
        
        # Seek to line offset
        offset = self._line_offsets[row]
        self._file_handle.seek(offset)
        
        # Read the line
        line_bytes = self._file_handle.readline()
        
        if not line_bytes:
            return None
        
        # Decode and parse
        try:
            line_str = line_bytes.decode('utf-8').rstrip('\r\n')
            return self._get_parser().parse_line(line_str, row, offset)
        except UnicodeDecodeError:
            return None
    
    def get_line_count(self) -> int:
        """Return total number of lines."""
        return self._line_count
    
    def get_categories(self) -> Set[str]:
        """Return all unique categories found."""
        return self._categories.copy()
    
    def close(self) -> None:
        """Close file handle and release resources."""
        if self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False