"""
ui/main_window.py  —  Phase 5
Application shell — sidebar navigation + central stacked area.

Thay đổi so với Phase 4:
  • Thêm nav button "Gói Tập" → SubscriptionPage (index 1)
  • Kết nối data_changed từ MemberPage → SubscriptionPage.refresh_members()
    để dropdown hội viên luôn được đồng bộ sau CRUD
"""

from __future__ import annotations

from PySide6.QtCore import Qt
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
from ui.subscription_page import SubscriptionPage


# ══════════════════════════════════════════════════════════════════════════ #
#  Sidebar nav button                                                        #
# ══════════════════════════════════════════════════════════════════════════ #

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


# ══════════════════════════════════════════════════════════════════════════ #
#  Main Window                                                               #
# ══════════════════════════════════════════════════════════════════════════ #

class MainWindow(QMainWindow):
    """
    Application shell.
    Left : fixed sidebar with navigation.
    Right: QStackedWidget for page switching.

    Pages:
      0 — MemberPage       (Hội Viên)
      1 — SubscriptionPage (Gói Tập)
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GymTK — Hệ Thống Quản Lý Phòng Tập")
        self.setMinimumSize(1100, 660)
        self.resize(1280, 780)
        self._setup_ui()
        self._navigate(0)   # Mặc định → trang Hội Viên

    # ── Layout ───────────────────────────────────────────────────────── #

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content())

        # ── Kết nối tín hiệu liên trang ──
        # Khi thêm/sửa/xóa hội viên → cập nhật dropdown hội viên ở SubscriptionPage
        self._member_page.data_changed.connect(
            self._subscription_page.refresh_members
        )

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

        # ── Danh sách nút nav ──
        self._nav_buttons: list[NavButton] = []

        # Hội Viên (index 0)
        self.nav_members = NavButton("👥", "Hội Viên")
        self.nav_members.clicked.connect(lambda: self._navigate(0))
        self._nav_buttons.append(self.nav_members)
        layout.addWidget(self.nav_members)

        # Gói Tập (index 1)
        self.nav_subscriptions = NavButton("🎫", "Gói Tập")
        self.nav_subscriptions.clicked.connect(lambda: self._navigate(1))
        self._nav_buttons.append(self.nav_subscriptions)
        layout.addWidget(self.nav_subscriptions)

        layout.addStretch()

        # ── Chân trang sidebar ──
        footer = QLabel("Giai Đoạn 5 — Quản Lý Gói Tập")
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

        # ── Pages (thứ tự phải khớp với chỉ số trong _navigate) ──
        self._member_page = MemberPage()           # index 0
        self.stack.addWidget(self._member_page)

        self._subscription_page = SubscriptionPage()  # index 1
        self.stack.addWidget(self._subscription_page)

        return area

    # ── Navigation ───────────────────────────────────────────────────── #

    def _navigate(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.set_active(i == index)