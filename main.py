"""
main.py — Gym Management System entry point.

Run with:
    python main.py
"""

import sys
import os

# ── Ensure the project root is on the path so all imports resolve ────────── #
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from ui.main_window import MainWindow, APP_STYLE


def main() -> int:
    # ── High-DPI support ──
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("GymTK")
    app.setOrganizationName("GymTK")
    app.setApplicationDisplayName("GymTK — Gym Management System")

    # ── Global stylesheet ──
    app.setStyleSheet(APP_STYLE)

    # ── Default font ──
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # ── Launch window ──
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())