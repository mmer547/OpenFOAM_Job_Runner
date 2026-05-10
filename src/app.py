from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


def create_app() -> QApplication:
    app = QApplication(sys.argv)
    app.setApplicationName("WSL OpenFOAM Job Runner")
    app.setOrganizationName("WslJobRunner")

    try:
        from PySide6.QtGui import QFontDatabase
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        app.setFont(font)
    except Exception:
        pass

    return app


def run() -> None:
    app = create_app()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
