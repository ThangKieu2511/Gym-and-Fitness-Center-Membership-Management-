"""
main.py — Gym Management System entry point.

Run with:
    python main.py
"""

import sys
import os
from pathlib import Path
# ── Ensure the project root is on the path so all imports resolve ────────── #
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from ui.login_window import LoginWindow


def load_stylesheet(app):
    qss_path = Path(PROJECT_ROOT) / "styles" / "styles.qss"

    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        print("⚠️ Không tìm thấy styles.qss")


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
    load_stylesheet(app)

    # ── Default font ──
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # ── Show Login trước, MainWindow mở sau khi login thành công ──
    login = LoginWindow()
    login.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())