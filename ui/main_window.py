"""
ui/main_window.py
Application shell — sidebar navigation + central stacked area.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.member_page import MemberPage


# ══════════════════════════════════════════════════════════════════════════════ #
#  Sidebar nav button                                                           #
# ══════════════════════════════════════════════════════════════════════════════ #

class NavButton(QPushButton):
    def __init__(self, icon: str, label: str, parent: QWidget | None = None):
        super().__init__(f"{icon}   {label}", parent)
        self.setObjectName("navBtn")
        self.setCheckable(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(42)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._active = False

    def set_active(self, active: bool):
        self._active = active
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


# ══════════════════════════════════════════════════════════════════════════════ #
#  Main Window                                                                  #
# ══════════════════════════════════════════════════════════════════════════════ #

class MainWindow(QMainWindow):
    """
    Application shell.
    Left: fixed sidebar with navigation.
    Right: QStackedWidget for page switching.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GymTK — Hệ Thống Quản Lý Phòng Tập")
        self.setMinimumSize(1000, 640)
        self.resize(1200, 740)
        self._setup_ui()
        self._navigate(0)      # Default to Members page

    # ── Layout ──────────────────────────────────────────────────────────── #

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content())

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 20, 14, 20)
        layout.setSpacing(4)

        # ── Brand ──
        brand_icon = QLabel("🏋️")
        brand_icon.setObjectName("pageIcon")
        app_name = QLabel("GymTK")
        app_name.setObjectName("appName")
        tagline = QLabel("Quản Lý Phòng Tập")
        tagline.setObjectName("appTagline")

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand_text.addWidget(app_name)
        brand_text.addWidget(tagline)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_row.addWidget(brand_icon)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        layout.addLayout(brand_row)

        layout.addSpacing(16)

        # ── Divider ──
        div = QFrame()
        div.setObjectName("sidebarDivider")
        div.setFrameShape(QFrame.HLine)
        layout.addWidget(div)

        layout.addSpacing(12)

        # ── Tiêu đề phần ──
        sec = QLabel("MENU CHÍNH")
        sec.setObjectName("sectionLabel")
        layout.addWidget(sec)
        layout.addSpacing(6)

        # ── Nút điều hướng ──
        self._nav_buttons: list[NavButton] = []
        self._pages: list[QWidget] = []   # filled in _build_content

        self.nav_members = NavButton("👥", "Hội Viên")
        self.nav_members.clicked.connect(lambda: self._navigate(0))
        self._nav_buttons.append(self.nav_members)
        layout.addWidget(self.nav_members)

        layout.addStretch()

        # ── Chân trang sidebar ──
        footer = QLabel("Giai Đoạn 3 — CRUD Hội Viên")
        footer.setObjectName("appTagline")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

        return sidebar

    def _build_content(self) -> QWidget:
        area = QWidget()
        area.setObjectName("contentArea")

        layout = QVBoxLayout(area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # ── Pages ──
        self._member_page = MemberPage()
        self.stack.addWidget(self._member_page)
        self._pages.append(self._member_page)

        return area

    # ── Navigation ──────────────────────────────────────────────────────── #

    def _navigate(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.set_active(i == index)