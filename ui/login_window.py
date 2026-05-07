"""
ui/login_window.py — Login Window for GymTK
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QLineEdit, QMessageBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QFrame,
)
from PySide6.QtGui import QFont

from database import Database


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GymTK — Đăng Nhập")
        self.setFixedSize(400, 480)
        self.setObjectName("loginWindow")
        self._db = Database()
        self._main_window = None
        self._setup_ui()
        self._apply_style()

    # ── UI ───────────────────────────────────────────────────────────── #

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("loginHeader")
        header.setFixedHeight(140)
        h_layout = QVBoxLayout(header)
        h_layout.setAlignment(Qt.AlignCenter)
        h_layout.setSpacing(4)

        icon = QLabel("🏋️")
        icon.setAttribute(Qt.WA_TranslucentBackground)
        icon.setAlignment(Qt.AlignCenter)
        icon.setFont(QFont("Segoe UI", 36))

        title = QLabel("GymTK")
        title.setAttribute(Qt.WA_TranslucentBackground)
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Quản Lý Phòng Tập")
        subtitle.setAttribute(Qt.WA_TranslucentBackground)
        subtitle.setObjectName("loginSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        h_layout.addWidget(icon)
        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        root.addWidget(header)

        # Card
        card = QFrame()
        card.setObjectName("loginCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(40, 36, 40, 36)
        c_layout.setSpacing(16)

        lbl_user = QLabel("Tên Đăng Nhập")
        lbl_user.setObjectName("loginLabel")
        self._username_input = QLineEdit()
        self._username_input.setObjectName("loginInput")
        self._username_input.setPlaceholderText("Nhập tên đăng nhập...")
        self._username_input.setMinimumHeight(42)

        lbl_pass = QLabel("Mật Khẩu")
        lbl_pass.setObjectName("loginLabel")
        self._password_input = QLineEdit()
        self._password_input.setObjectName("loginInput")
        self._password_input.setPlaceholderText("Nhập mật khẩu...")
        self._password_input.setEchoMode(QLineEdit.Password)
        self._password_input.setMinimumHeight(42)
        self._password_input.returnPressed.connect(self._do_login)

        self._login_btn = QPushButton("🔐   Đăng Nhập")
        self._login_btn.setObjectName("loginBtn")
        self._login_btn.setMinimumHeight(46)
        self._login_btn.setCursor(Qt.PointingHandCursor)
        self._login_btn.clicked.connect(self._do_login)

        c_layout.addWidget(lbl_user)
        c_layout.addWidget(self._username_input)
        c_layout.addWidget(lbl_pass)
        c_layout.addWidget(self._password_input)
        c_layout.addSpacing(8)
        c_layout.addWidget(self._login_btn)

        root.addStretch()
        root.addWidget(card, alignment=Qt.AlignCenter)
        root.addStretch()

        footer = QLabel("GymTK © 2025")
        footer.setObjectName("loginFooter")
        footer.setAlignment(Qt.AlignCenter)
        root.addWidget(footer)

    def _apply_style(self):
        # Đọc file styles.qss và áp dụng cho LoginWindow
        try:
            with open("styles.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Không thể tải file styles.qss: {e}")

    # ── Logic ─────────────────────────────────────────────────────────── #

    def _do_login(self):
        username = self._username_input.text().strip()
        password = self._password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")
            return

        if self._db.verify_user(username, password):
            self._open_main()
        else:
            QMessageBox.warning(self, "Đăng Nhập Thất Bại", "Tên đăng nhập hoặc mật khẩu không đúng.")
            self._password_input.clear()
            self._password_input.setFocus()

    def _open_main(self):
        from ui.main_window import MainWindow
        self._main_window = MainWindow()
        self._main_window.show()
        self.close()