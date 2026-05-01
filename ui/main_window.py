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


# ── Stylesheet ───────────────────────────────────────────────────────────── #

APP_STYLE = """
/* ── Global ── */
QWidget {
    background-color: #0f1117;
    color: #e2e8f0;
    font-family: "Segoe UI", "SF Pro Display", Cantarell, sans-serif;
    font-size: 13px;
}

/* ── Sidebar ── */
#sidebar {
    background-color: #161b27;
    border-right: 1px solid #1e2535;
    min-width: 220px;
    max-width: 220px;
}

#appName {
    font-size: 15px;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: 0.5px;
}
#appTagline {
    font-size: 11px;
    color: #64748b;
}

#sectionLabel {
    font-size: 10px;
    font-weight: 600;
    color: #475569;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding-left: 4px;
}

/* Nav buttons */
#navBtn {
    background: transparent;
    border: none;
    border-radius: 8px;
    color: #94a3b8;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
    padding: 10px 14px;
}
#navBtn:hover {
    background-color: #1e2535;
    color: #e2e8f0;
}
#navBtn[active="true"] {
    background-color: #1d4ed8;
    color: #ffffff;
}
#navBtn[active="true"]:hover {
    background-color: #2563eb;
}

/* Sidebar divider */
#sidebarDivider {
    border: none;
    border-top: 1px solid #1e2535;
}

/* ── Content area ── */
#contentArea {
    background-color: #0f1117;
}

/* ── Page header ── */
#pageIcon {
    font-size: 28px;
    padding-right: 8px;
}
#pageTitle {
    font-size: 20px;
    font-weight: 700;
    color: #f1f5f9;
}
#pageSubtitle {
    font-size: 12px;
    color: #64748b;
}

/* ── Toolbar buttons ── */
#btnPrimary {
    background-color: #1d4ed8;
    color: #ffffff;
    border: none;
    border-radius: 7px;
    padding: 0 18px;
    font-weight: 600;
}
#btnPrimary:hover  { background-color: #2563eb; }
#btnPrimary:pressed { background-color: #1e40af; }

#btnSecondary {
    background-color: #1e2535;
    color: #94a3b8;
    border: 1px solid #2d3748;
    border-radius: 7px;
    padding: 0 14px;
    font-weight: 500;
}
#btnSecondary:hover   { background-color: #263047; color: #e2e8f0; }
#btnSecondary:disabled { color: #374151; border-color: #1e2535; }

#btnDanger {
    background-color: transparent;
    color: #f87171;
    border: 1px solid #3b1f1f;
    border-radius: 7px;
    padding: 0 14px;
    font-weight: 500;
}
#btnDanger:hover    { background-color: #3b1f1f; color: #fca5a5; }
#btnDanger:disabled { color: #374151; border-color: #1e2535; }

#btnNeutral {
    background-color: transparent;
    color: #64748b;
    border: 1px solid #1e2535;
    border-radius: 7px;
    padding: 0 14px;
}
#btnNeutral:hover { background-color: #1e2535; color: #94a3b8; }

/* ── Table ── */
QTableWidget {
    background-color: #161b27;
    alternate-background-color: #1a2030;
    border: 1px solid #1e2535;
    border-radius: 10px;
    gridline-color: transparent;
    selection-background-color: #1d3a6e;
    selection-color: #e2e8f0;
    outline: none;
}
QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #1e2535;
}
QTableWidget::item:selected {
    background-color: #1d3a6e;
    color: #e2e8f0;
}
QHeaderView::section {
    background-color: #1a2030;
    color: #64748b;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #1e2535;
}
QScrollBar:vertical {
    background: #161b27;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2d3748;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }

/* ── Status label ── */
#statusLabel {
    font-size: 11px;
    color: #475569;
    padding-top: 2px;
}

/* ── Dialog ── */
QDialog {
    background-color: #161b27;
}
#dialogTitle {
    font-size: 16px;
    font-weight: 700;
    color: #f1f5f9;
}
#divider {
    color: #1e2535;
}
QFormLayout QLabel {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 500;
    min-width: 70px;
}
QLineEdit, QComboBox {
    background-color: #0f1117;
    border: 1px solid #2d3748;
    border-radius: 6px;
    color: #e2e8f0;
    padding: 7px 10px;
    selection-background-color: #1d4ed8;
}
QLineEdit:focus, QComboBox:focus {
    border-color: #1d4ed8;
}
QLineEdit::placeholder { color: #374151; }
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #1a2030;
    border: 1px solid #2d3748;
    selection-background-color: #1d4ed8;
    color: #e2e8f0;
}

/* ── Dialog button box ── */
QDialogButtonBox QPushButton {
    border-radius: 6px;
    padding: 7px 20px;
    font-weight: 600;
    min-width: 80px;
}
QDialogButtonBox QPushButton[text="Save"] {
    background-color: #1d4ed8;
    color: #ffffff;
    border: none;
}
QDialogButtonBox QPushButton[text="Save"]:hover { background-color: #2563eb; }
QDialogButtonBox QPushButton[text="Cancel"] {
    background-color: #1e2535;
    color: #94a3b8;
    border: 1px solid #2d3748;
}
QDialogButtonBox QPushButton[text="Cancel"]:hover { background-color: #263047; }

/* ── Message box ── */
QMessageBox {
    background-color: #161b27;
}
QMessageBox QLabel { color: #e2e8f0; }
QMessageBox QPushButton {
    background-color: #1e2535;
    color: #e2e8f0;
    border: 1px solid #2d3748;
    border-radius: 6px;
    padding: 6px 18px;
    min-width: 70px;
}
QMessageBox QPushButton:hover   { background-color: #263047; }
QMessageBox QPushButton[text="&Yes"],
QMessageBox QPushButton[text="Yes"] {
    background-color: #7f1d1d;
    color: #fca5a5;
    border-color: #991b1b;
}
QMessageBox QPushButton[text="&Yes"]:hover,
QMessageBox QPushButton[text="Yes"]:hover { background-color: #991b1b; }
"""


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
        app_name = QLabel("GymQT")
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