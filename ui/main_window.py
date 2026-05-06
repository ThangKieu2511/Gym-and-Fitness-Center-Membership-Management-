"""
ui/main_window.py  —  Phase 9  (QR background service)
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from ui.dashboard_page import DashboardPage
from ui.member_page import MemberPage
from ui.subscription_page import SubscriptionPage
from ui.qr_checkin_page import QRCheckinPage
from services.qr_service import QRService


class NavButton(QPushButton):
    def __init__(self, icon: str, label: str, parent: QWidget | None = None):
        super().__init__(f"{icon}   {label}", parent)
        self.setObjectName("navBtn")
        self.setCheckable(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(42)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_active(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GymTK — Hệ Thống Quản Lý Phòng Tập")
        self.setMinimumSize(1100, 660)
        self.resize(1280, 780)
        self._setup_ui()
        self._navigate(0)
        self._init_qr_service()   # ← background QR scan

    # ── Layout ───────────────────────────────────────────────────────── #

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content())
        self._member_page.data_changed.connect(self._subscription_page.refresh_members)
        self._member_page.data_changed.connect(self._dashboard_page.refresh_data)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 20, 14, 20)
        layout.setSpacing(4)

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

        div = QFrame()
        div.setObjectName("sidebarDivider")
        div.setFrameShape(QFrame.HLine)
        layout.addWidget(div)
        layout.addSpacing(12)

        sec = QLabel("MENU CHÍNH")
        sec.setObjectName("sectionLabel")
        layout.addWidget(sec)
        layout.addSpacing(6)

        self._nav_buttons: list[NavButton] = []

        self.nav_members = NavButton("👥", "Hội Viên")
        self.nav_members.clicked.connect(lambda: self._navigate(0))
        self._nav_buttons.append(self.nav_members)
        layout.addWidget(self.nav_members)

        self.nav_subscriptions = NavButton("🎫", "Gói Tập")
        self.nav_subscriptions.clicked.connect(lambda: self._navigate(1))
        self._nav_buttons.append(self.nav_subscriptions)
        layout.addWidget(self.nav_subscriptions)

        self.nav_dashboard = NavButton("📊", "Dashboard")
        self.nav_dashboard.clicked.connect(lambda: self._navigate(2))
        self._nav_buttons.append(self.nav_dashboard)
        layout.addWidget(self.nav_dashboard)

        self.nav_qr = NavButton("📷", "QR Check-in")
        self.nav_qr.clicked.connect(lambda: self._navigate(3))
        self._nav_buttons.append(self.nav_qr)
        layout.addWidget(self.nav_qr)

        layout.addStretch()
        footer = QLabel("Giai Đoạn 9 — QR Check-in")
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

        self._member_page = MemberPage()
        self.stack.addWidget(self._member_page)          # index 0

        self._subscription_page = SubscriptionPage()
        self.stack.addWidget(self._subscription_page)    # index 1

        self._dashboard_page = DashboardPage()
        self.stack.addWidget(self._dashboard_page)       # index 2

        self._qr_page = QRCheckinPage()
        self.stack.addWidget(self._qr_page)              # index 3

        return area

    # ── QR Background Service ─────────────────────────────────────────── #

    def _init_qr_service(self) -> None:
        """Khởi tạo QRService chạy nền và kết nối signal."""
        self._qr_service = QRService(parent=self)

        if not self._qr_service.is_available():
            return  # opencv/pyzbar chưa cài — bỏ qua

        # Debounce 3 giây — tránh spam khi quét liên tục
        self._qr_debounce_timer = QTimer(self)
        self._qr_debounce_timer.setSingleShot(True)
        self._qr_debounce_timer.setInterval(3000)

        self._qr_service.scanned.connect(self._on_qr_scanned)
        self._qr_service.start()

    def _on_qr_scanned(self, result: dict) -> None:
        """Handler khi QRService emit scanned."""
        if self._qr_debounce_timer.isActive():
            # Còn trong thời gian chờ → bỏ qua, resume scan
            self._resume_qr_scan()
            return

        self._qr_debounce_timer.start()

        # Tự chuyển sang trang QR Check-in
        self._navigate(3)

        # Hiển thị kết quả (không mở camera trong page)
        self._qr_page.show_result(result)

        # Resume camera sau 3 giây
        QTimer.singleShot(3000, self._resume_qr_scan)

    def _resume_qr_scan(self) -> None:
        """Cho phép QRService tiếp tục scan."""
        if self._qr_service.is_running():
            if self._qr_service._ctrl:
                self._qr_service._ctrl.reset_last()
            self._qr_service._timer.start()

    # ── Navigation ───────────────────────────────────────────────────── #

    def _navigate(self, index: int):
        # KHÔNG dừng QRService khi chuyển trang — camera chạy nền liên tục
        # (Nút manual trong QRCheckinPage vẫn hoạt động độc lập nếu cần)
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.set_active(i == index)
        if index == 2:
            self._dashboard_page.refresh_data()

    def closeEvent(self, event):  # noqa: N802
        """Dừng camera nền khi đóng app."""
        if hasattr(self, "_qr_service"):
            self._qr_service.stop()
        super().closeEvent(event)