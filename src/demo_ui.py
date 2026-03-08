#!/usr/bin/env python
"""Demo script to test the new UI design.

Run this script to see the redesigned Log Viewer interface:
    uv run python src/demo_ui.py
"""
from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.views.main_window import MainWindow
from src.controllers.main_controller import MainController
from src.styles.stylesheet import get_application_stylesheet


def main() -> int:
    """Run the demo application."""
    # Create application
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Apply stylesheet
    app.setStyleSheet(get_application_stylesheet())
    
    # Create main window
    window = MainWindow()
    window.setWindowTitle("Log Viewer - Demo")
    window.resize(1400, 900)
    
    # Create controller and connect to window
    controller = MainController(window)
    
    # Show window
    window.show()
    
    # Run event loop
    result = app.exec()
    
    # Clean up
    controller.close()
    
    return result


if __name__ == "__main__":
    sys.exit(main())