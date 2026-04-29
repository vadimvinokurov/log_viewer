"""Log Viewer GUI — PySide6 application."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMainWindow


class MainWindow(QMainWindow):
    """Log Viewer main window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Log Viewer")


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
