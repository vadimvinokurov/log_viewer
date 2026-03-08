"""Log Viewer Application Entry Point."""
import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from src.views.main_window import MainWindow
from src.controllers.main_controller import MainController

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(name)s - %(levelname)s - %(message)s'
)

# Development flag - auto-open test log file
DEV_AUTO_OPEN_FILE = True
DEV_LOG_FILE = Path(__file__).parent.parent / "test_logs" / "test_log.txt"


def main() -> None:
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Log Viewer")
    app.setApplicationVersion("0.1.0")

    # Create main window and controller
    window = MainWindow()
    controller = MainController(window)

    # Show window
    window.show()

    # Auto-open test log file in development mode
    if DEV_AUTO_OPEN_FILE and DEV_LOG_FILE.exists():
        # Use QTimer to ensure UI is fully initialized before opening file
        QTimer.singleShot(100, lambda: controller.open_file(str(DEV_LOG_FILE)))

    # Run application
    exit_code = app.exec()

    # Clean up
    controller.close()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()