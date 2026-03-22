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
    """Immutable log entry data.
    
    Ref: docs/specs/features/log-entry-optimization.md §4.3
    Ref: docs/specs/features/timestamp-unix-epoch.md §3.1
    Memory: raw_line removed (Phase 3) - lazy loaded via LogDocument.get_raw_line()
    
    Timestamp stored as Unix Epoch (float) for memory efficiency.
    """
    row_index: int
    timestamp: float      # Unix Epoch with milliseconds
    category: str
    display_message: str  # With level prefix removed
    level: LogLevel
    file_offset: int  # Byte offset in file for seeking