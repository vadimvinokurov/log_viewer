"""Log entry model."""
from dataclasses import dataclass
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration.
    
    Maps log level strings from parsed logs to enum values.
    """
    CRITICAL = "LOG_CRITICAL"
    ERROR = "LOG_ERROR"
    WARNING = "LOG_WARNING"
    MSG = "LOG_MSG"
    DEBUG = "LOG_DEBUG"
    TRACE = "LOG_TRACE"


@dataclass(frozen=True)
class LogEntry:
    """Immutable log entry data."""
    row_index: int
    timestamp: str
    category: str
    raw_message: str
    display_message: str  # With level prefix removed
    level: LogLevel
    file_offset: int  # Byte offset in file for seeking
    raw_line: str  # Original line for copying