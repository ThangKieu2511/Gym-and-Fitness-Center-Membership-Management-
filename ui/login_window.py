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
        self.setStyleSheet("""
            #loginWindow {
                background-color: #1a1d23;
            }
            #loginHeader {
                background-color: #1a1d23;
                background-color: transparent;
            }
            #loginTitle {
                color: #ffffff;
                font-size: 26px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            #loginSubtitle {
                color: #8b95a5;
                font-size: 12px;
                font-family: 'Segoe UI';
            }
            #loginCard {
                background-color: #23262e;
                border-radius: 12px;
                min-width: 320px;
                max-width: 320px;
            }
            #loginTitle, #loginSubtitle, #loginLabel, #loginFooter {
                background: transparent; /* Thêm dòng này để xóa nền đen của chữ */
            }
            #loginLabel {
                color: #c5cdd8;
                font-size: 13px;
                font-family: 'Segoe UI';
                font-weight: 600;
                background: transparent;
            }
            #loginInput {
                background-color: #2c3040;
                color: #e8edf2;
                border: 1.5px solid #3a3f52;
                border-radius: 7px;
                padding: 0 12px;
                font-size: 13px;
                font-family: 'Segoe UI';
            }
            #loginInput:focus {
                border-color: #5b8dee;
                background-color: #2f3447;
            }
            #loginBtn {
                background-color: #5b8dee;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            #loginBtn:hover {
                background-color: #4a7de0;
            }
            #loginBtn:pressed {
                background-color: #3a6dd0;
            }
            #loginFooter {
                color: #4a5060;
                font-size: 11px;
                font-family: 'Segoe UI';
                padding: 10px;
            }
        """)

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