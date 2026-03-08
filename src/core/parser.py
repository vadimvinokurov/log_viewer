"""Log line parser."""
from typing import Optional, Tuple, List
from src.models.log_entry import LogEntry, LogLevel


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
        
        # Split into parts - need at least timestamp and category
        parts = stripped_line.split(' ', 2)  # Split into max 3 parts
        
        if len(parts) < 2:
            # Malformed line - need at least timestamp and category
            return None
        
        timestamp = parts[0]
        category = parts[1]
        
        # Message is everything after the second space (or empty if not present)
        raw_message = parts[2] if len(parts) > 2 else ""
        
        # Detect log level and prepare display message
        level, display_message = self._detect_level_and_message(raw_message)
        
        return LogEntry(
            row_index=row_index,
            timestamp=timestamp,
            category=category,
            raw_message=raw_message,
            display_message=display_message,
            level=level,
            file_offset=file_offset,
            raw_line=line
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