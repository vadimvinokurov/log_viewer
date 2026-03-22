"""Log Viewer Application Entry Point."""
from __future__ import annotations
from beartype import beartype
import sys
import logging
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QEvent
from PySide6.QtGui import QFileOpenEvent
from src.views.main_window import MainWindow
from src.controllers.main_controller import MainController

# Configure logging
# Debug level enabled for viewport preservation debugging
# Ref: docs/specs/features/selection-preservation.md §7
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Development flag - auto-open test log file
DEV_AUTO_OPEN_FILE = True
DEV_LOG_FILE = Path(__file__).parent.parent / "test_logs" / "test_log.txt"


class LogViewerApp(QApplication):
    """Custom QApplication to handle macOS file open events.
    
    On macOS, when an app is launched via "Open with..." from Finder,
    the file path is passed via QFileOpenEvent rather than command-line
    arguments. This class handles that event.
    
    Per docs/specs/features/multi-window-instance.md §4.2
    """
    
    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self._controller: MainController | None = None
        self._file_loaded: bool = False  # Track if file loaded in current instance
    
    def set_controller(self, controller: MainController, file_loaded: bool = False) -> None:
        """Set the controller to handle file open events.
        
        Args:
            controller: MainController instance
            file_loaded: Whether a file was loaded from command-line args
        """
        self._controller = controller
        self._file_loaded = file_loaded
    
    def event(self, event: QEvent) -> bool:
        """Handle application events including QFileOpenEvent.
        
        Args:
            event: The event to handle
        
        Returns:
            True if event was handled, False otherwise
        
        Per docs/specs/features/multi-window-instance.md §4.2
        """
        if event.type() == QEvent.Type.FileOpen:
            file_event = event
            if hasattr(file_event, 'file'):
                file_path = file_event.file()
                if file_path:
                    logger.info(f"Received QFileOpenEvent: {file_path}")
                    
                    # Check if current instance is empty (no file loaded)
                    if not self._file_loaded and self._controller:
                        # Open in current instance
                        logger.info(f"Opening file in current instance: {file_path}")
                        QTimer.singleShot(100, lambda: self._controller.open_file(file_path))
                        self._file_loaded = True
                    else:
                        # Launch NEW instance for this file
                        logger.info(f"Launching new instance for: {file_path}")
                        _open_in_new_instance(Path(file_path))
            return True
        return super().event(event)


@beartype
def parse_arguments(argv: list[str]) -> list[Path]:
    """Parse command-line arguments.
    
    Args:
        argv: Command-line arguments (sys.argv[1:])
    
    Returns:
        List of valid file paths to open
    
    Behavior:
        - Returns empty list if no arguments
        - Validates each path exists
        - Returns only valid paths
        - Logs warning for invalid paths
    
    Ref: docs/specs/features/file-association.md §4.1
    """
    valid_paths: list[Path] = []
    
    for arg in argv:
        # Skip flags (future: --version, --help, etc.)
        if arg.startswith('-'):
            continue
        
        path = Path(arg)
        if path.exists() and path.is_file():
            valid_paths.append(path)
        else:
            logger.warning(f"File not found: {arg}")
    
    return valid_paths


def _open_in_new_instance(filepath: Path) -> None:
    """Launch a new instance to open a file.
    
    Args:
        filepath: Path to file to open
    
    Per docs/specs/features/multi-window-instance.md §4.1:
    Each file opens in a separate process instance.
    """
    main_script = Path(sys.argv[0]).absolute()
    
    try:
        if main_script.suffix == '.py':
            # Running as Python script
            subprocess.Popen([sys.executable, str(main_script), str(filepath)])
        else:
            # Running as executable
            subprocess.Popen([str(main_script), str(filepath)])
    except OSError as e:
        logger.error(f"Failed to launch new instance for {filepath}: {e}")
        # Show error dialog
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Instance Launch Failed",
            f"Cannot launch new instance for {filepath}.\n\nError: {e}"
        )


def main() -> None:
    """Application entry point.
    
    Per docs/specs/features/multi-window-instance.md §4.1
    """
    # Debug: Log all arguments received
    logger.debug(f"sys.argv: {sys.argv}")
    logger.debug(f"sys.argv[1:]: {sys.argv[1:]}")
    
    # Use custom QApplication to handle macOS QFileOpenEvent
    app = LogViewerApp(sys.argv)
    app.setApplicationName("Log Viewer")
    app.setApplicationVersion("0.1.0")
    
    # Parse command-line arguments
    file_paths = parse_arguments(sys.argv[1:])
    logger.info(f"Parsed file paths: {file_paths}")
    
    # Create main window and controller
    window = MainWindow()
    controller = MainController(window)
    
    # Determine if a file will be loaded (from args or dev mode)
    # Per docs/specs/features/multi-window-instance.md §4.2
    file_loaded = bool(file_paths) or (DEV_AUTO_OPEN_FILE and DEV_LOG_FILE.exists())
    
    # Set controller on app to handle QFileOpenEvent
    app.set_controller(controller, file_loaded=file_loaded)

    # Show window
    window.show()

    # Open files from command-line arguments
    # Per docs/specs/features/multi-window-instance.md §4.1
    if file_paths:
        # Open first file in current instance
        first_file = str(file_paths[0])
        logger.info(f"Opening file: {first_file}")
        
        if not Path(first_file).exists():
            logger.error(f"File does not exist: {first_file}")
        
        QTimer.singleShot(100, lambda: controller.open_file(first_file))
        
        # Launch additional files in NEW instances
        for path in file_paths[1:]:
            _open_in_new_instance(path)
    else:
        # Development mode: auto-open test file
        if DEV_AUTO_OPEN_FILE and DEV_LOG_FILE.exists():
            QTimer.singleShot(100, lambda: controller.open_file(str(DEV_LOG_FILE)))

    # Run application
    exit_code = app.exec()

    # Clean up
    controller.close()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()