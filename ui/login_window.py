"""
ui/login_window.py — Login Window for GymTK
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QEvent,QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPixmap
from PySide6.QtWidgets import (
    QLabel, QLineEdit, QMessageBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QFrame,
    QGraphicsDropShadowEffect, QApplication
)

from database import Database


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GymTK — Đăng Nhập")
        self.setFixedSize(400, 520)
        self.setObjectName("loginWindow")
        self._db = Database()
        self._main_window = None
        self._setup_ui()
        self._apply_style()
        self._start_animations()

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

        icon = QLabel()
        pixmap = QPixmap("gym_pic.png")
        icon.setPixmap(pixmap.scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon.setAttribute(Qt.WA_TranslucentBackground)
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("GymTK")
        title.setAttribute(Qt.WA_TranslucentBackground)
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Hệ Thống Quản Lý Phòng Tập")
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
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 5)
        card.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(40, 36, 40, 36)
        c_layout.setSpacing(16)

        # Username Input
        lbl_user = QLabel("Tên Đăng Nhập")
        lbl_user.setObjectName("loginLabel")
        self._username_input = QLineEdit()
        self._username_input.setObjectName("loginInput")
        self._username_input.setPlaceholderText("Nhập tên đăng nhập...")
        self._username_input.setMinimumHeight(42)
        self._username_input.returnPressed.connect(self._password_input_focus)

        # Password Input
        lbl_pass = QLabel("Mật Khẩu")
        lbl_pass.setObjectName("loginLabel")
        
        # Khung chứa password: Đổi thành QFrame để nhận Style CSS tốt nhất
        self._pass_container = QFrame()
        self._pass_container.setObjectName("passContainer") 
        pass_layout = QHBoxLayout(self._pass_container)
        pass_layout.setContentsMargins(0, 0, 0, 0)
        pass_layout.setSpacing(0)

        self._password_input = QLineEdit()
        self._password_input.setObjectName("passwordInput")
        self._password_input.setPlaceholderText("Nhập mật khẩu...")
        self._password_input.setEchoMode(QLineEdit.Password)
        self._password_input.setMinimumHeight(42)
        self._password_input.returnPressed.connect(self._do_login)
        # Gắn bộ lắng nghe sự kiện để đổi màu khung viền khi được click
        self._password_input.installEventFilter(self)

        # Nút ẩn/hiện mật khẩu
        self._toggle_pass_btn = QPushButton("👁️")
        self._toggle_pass_btn.setFixedSize(42, 42)
        self._toggle_pass_btn.setObjectName("togglePassBtn")
        self._toggle_pass_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_pass_btn.setCheckable(True)
        self._toggle_pass_btn.toggled.connect(self._toggle_password_visibility)

        pass_layout.addWidget(self._password_input)
        pass_layout.addWidget(self._toggle_pass_btn)

        # Nút Đăng nhập
        self._login_btn = QPushButton("🔐   Đăng Nhập")
        self._login_btn.setObjectName("loginBtn")
        self._login_btn.setMinimumHeight(46)
        self._login_btn.setCursor(Qt.PointingHandCursor)
        self._login_btn.clicked.connect(self._do_login)

        c_layout.addWidget(lbl_user)
        c_layout.addWidget(self._username_input)
        c_layout.addWidget(lbl_pass)
        c_layout.addWidget(self._pass_container)
        c_layout.addSpacing(12)
        c_layout.addWidget(self._login_btn)

        root.addStretch()
        root.addWidget(card, alignment=Qt.AlignCenter)
        self._card = card
        root.addStretch()

        footer = QLabel("GymTK © 2026")
        footer.setObjectName("loginFooter")
        footer.setAlignment(Qt.AlignCenter)
        root.addWidget(footer)

    def _password_input_focus(self):
        self._password_input.setFocus()

    def _toggle_password_visibility(self, checked):
        if checked:
            self._password_input.setEchoMode(QLineEdit.Normal)
            self._toggle_pass_btn.setText("🙈")
        else:
            self._password_input.setEchoMode(QLineEdit.Password)
            self._toggle_pass_btn.setText("👁️")

    def _apply_style(self):
        try:
            with open("styles.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Không thể tải file styles.qss: {e}")

    def _start_animations(self):
        self._fade_anim = QPropertyAnimation(self._card, b"windowOpacity")
        self._fade_anim.setDuration(500)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._card.setWindowOpacity(0.0)
        self._fade_anim.start()

    # ── Logic ─────────────────────────────────────────────────────────── #

    def _do_login(self):
        username = self._username_input.text().strip()
        password = self._password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")
            return

        # Disable nút để tránh spam click
        self._login_btn.setEnabled(False)
        self._login_btn.setText("Đang đăng nhập...")

        # Disable input
        self._username_input.setEnabled(False)
        self._password_input.setEnabled(False)

        # Refresh UI ngay lập tức
        QApplication.processEvents()

        if self._db.verify_user(username, password):
            self._open_main()
        else:
            QMessageBox.warning(
                self,
                "Đăng Nhập Thất Bại",
                "Tên đăng nhập hoặc mật khẩu không đúng."
            )

            # Enable lại nếu sai
            self._login_btn.setEnabled(True)
            self._login_btn.setText("🔐   Đăng Nhập")

            self._username_input.setEnabled(True)
            self._password_input.setEnabled(True)

            self._password_input.clear()
            self._password_input.setFocus()

    def _open_main(self):
        from ui.main_window import MainWindow
        self._main_window = MainWindow()
        self._main_window.show()
        self.close()

    # Bắt sự kiện người dùng Click (Focus) vào ô Password để viền toàn khối sáng lên
    def eventFilter(self, obj, event):
        if obj == self._password_input:
            if event.type() == QEvent.Type.FocusIn:
                self._pass_container.setProperty("focused", "true")
                self._pass_container.style().unpolish(self._pass_container)
                self._pass_container.style().polish(self._pass_container)
            elif event.type() == QEvent.Type.FocusOut:
                self._pass_container.setProperty("focused", "false")
                self._pass_container.style().unpolish(self._pass_container)
                self._pass_container.style().polish(self._pass_container)
        return super().eventFilter(obj, event)