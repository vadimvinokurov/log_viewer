"""Log line parser."""
import re
import sys
from datetime import datetime
from typing import Optional, Tuple, List
from src.models.log_entry import LogEntry, LogLevel


def _parse_timestamp(ts_str: str) -> float:
    """Parse timestamp string to Unix Epoch.
    
    Supported formats:
    - DD-MM-YYYYTHH:MM:SS.MS (e.g., "10-03-2026T15:30:45.123")
    - YYYY-MM-DDTHH:MM:SS (e.g., "2024-01-01T10:00:00")
    - YYYY-MM-DD HH:MM:SS (e.g., "2024-01-01 12:00:00")
    - YYYY-MM-DD (e.g., "2024-01-01") - uses midnight
    - HH:MM:SS (e.g., "00:00:00") - uses current date
    
    Args:
        ts_str: Timestamp string from log
        
    Returns:
        Unix timestamp (seconds since epoch with milliseconds)
        
    Raises:
        ValueError: If timestamp format is unrecognized
    """
    # Try DD-MM-YYYYTHH:MM:SS.MS format (with milliseconds)
    if 'T' in ts_str:
        try:
            dt = datetime.strptime(ts_str, "%d-%m-%YT%H:%M:%S.%f")
            return dt.timestamp()
        except ValueError:
            pass
        # Try YYYY-MM-DDTHH:MM:SS format (ISO-like, no milliseconds)
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
            return dt.timestamp()
        except ValueError:
            pass
    
    # Try YYYY-MM-DD HH:MM:SS format
    if ' ' in ts_str:
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            return dt.timestamp()
        except ValueError:
            pass
    
    # Try YYYY-MM-DD format (date only, use midnight)
    try:
        dt = datetime.strptime(ts_str, "%Y-%m-%d")
        return dt.timestamp()
    except ValueError:
        pass
    
    # Try HH:MM:SS format (use current date)
    try:
        time_part = datetime.strptime(ts_str, "%H:%M:%S")
        today = datetime.now().replace(
            hour=time_part.hour,
            minute=time_part.minute,
            second=time_part.second
        )
        return today.timestamp()
    except ValueError:
        pass
    
    raise ValueError(f"Unrecognized timestamp format: {ts_str}")


class LogParser:
    """Parser for log lines."""
    
    def parse_line(self, line: str, row_index: int, file_offset: int) -> Optional[LogEntry]:
        """
        Parse a single log line.
        
        Args:
            line: Raw log line
            row_index: Zero-based row index
            file_offset: Byte offset in file
            
        Returns:
            LogEntry if parsing successful, None if line is malformed
        """
        # Strip the line for processing but keep original
        stripped_line = line.strip()
        
        # Handle empty lines
        if not stripped_line:
            return None
        
        # Split into parts
        parts = stripped_line.split(' ')
        
        if len(parts) < 2:
            # Malformed line - need at least timestamp and category
            return None
        
        # Detect timestamp format and extract components
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.2
        # Format 1: DD-MM-YYYYTHH:MM:SS.MS (no space in timestamp)
        # Format 2: YYYY-MM-DD HH:MM:SS (space between date and time)
        # Format 3: HH:MM:SS (no space in timestamp)
        
        first_part = parts[0]
        
        # Check for YYYY-MM-DD format (needs next part for time)
        if re.match(r'^\d{4}-\d{2}-\d{2}$', first_part):
            # YYYY-MM-DD HH:MM:SS format
            if len(parts) < 3:
                return None
            timestamp_str = f"{parts[0]} {parts[1]}"
            category = sys.intern(parts[2])
            raw_message = ' '.join(parts[3:]) if len(parts) > 3 else ""
        else:
            # DD-MM-YYYYTHH:MM:SS.MS or HH:MM:SS format
            timestamp_str = parts[0]
            category = sys.intern(parts[1])
            raw_message = ' '.join(parts[2:]) if len(parts) > 2 else ""
        
        # Convert timestamp string to Unix Epoch float
        # Ref: docs/specs/features/timestamp-unix-epoch.md §3.2
        timestamp = _parse_timestamp(timestamp_str)
        
        # Detect log level and prepare display message
        # Ref: docs/specs/features/log-entry-optimization.md §4.2
        # raw_message removed - never used outside parser
        level, display_message = self._detect_level_and_message(raw_message)
        
        return LogEntry(
            row_index=row_index,
            timestamp=timestamp,
            category=category,
            display_message=display_message,
            level=level,
            file_offset=file_offset
        )
    
    def _detect_level_and_message(self, message: str) -> Tuple[LogLevel, str]:
        """
        Detect log level from message and return level with display message.
        
        Args:
            message: Raw message text
            
        Returns:
            Tuple of (LogLevel, display_message with prefix removed if applicable)
        """
        if not message:
            return LogLevel.MSG, message
        
        # Check for level markers at the start of the message
        if message.startswith("LOG_CRITICAL "):
            return LogLevel.CRITICAL, message[len("LOG_CRITICAL "):]
        elif message.startswith("LOG_ERROR "):
            return LogLevel.ERROR, message[len("LOG_ERROR "):]
        elif message.startswith("LOG_WARNING "):
            return LogLevel.WARNING, message[len("LOG_WARNING "):]
        elif message.startswith("LOG_MSG "):
            return LogLevel.MSG, message[len("LOG_MSG "):]
        elif message.startswith("LOG_DEBUG "):
            return LogLevel.DEBUG, message[len("LOG_DEBUG "):]
        elif message.startswith("LOG_TRACE "):
            return LogLevel.TRACE, message[len("LOG_TRACE "):]
        
        # No level marker - default to MSG
        return LogLevel.MSG, message
    
    def extract_category(self, category_str: str) -> Tuple[str, List[str]]:
        """
        Extract category path from category string.
        
        Args:
            category_str: Category like "HordeMode/scripts/app"
            
        Returns:
            Tuple of (full_path, path_components)
        """
        if not category_str:
            return "", []
        
        # Split by / to get path components
        components = category_str.split('/')
        
        return category_str, components