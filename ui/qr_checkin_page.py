"""
ui/qr_checkin_page.py  —  Phase 9

Trang check-in bằng QR camera.
Nếu opencv-python hoặc pyzbar chưa được cài, trang sẽ hiển thị
hướng dẫn cài thay vì crash toàn bộ app.

QR format: "member:<id>"   ví dụ: "member:42"
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# ── Kiểm tra dependency ──────────────────────────────────────────────────── #
try:
    import cv2
    from PySide6.QtGui import QImage, QPixmap
    from pyzbar import pyzbar
    from controllers.qr_controller import QRController
    _DEPS_OK = True
except ImportError as _import_err:
    _DEPS_OK = False
    _IMPORT_ERR_MSG = str(_import_err)

# Kích thước khung camera
FRAME_W = 640
FRAME_H = 480

STATUS_COLORS = {
    "valid":           "#22c55e",
    "expired":         "#f59e0b",
    "no_subscription": "#ef4444",
    "error":           "#ef4444",
}


# ══════════════════════════════════════════════════════════════════════════ #
#  Trang thông báo thiếu dependency                                          #
# ══════════════════════════════════════════════════════════════════════════ #

class _MissingDepsPage(QWidget):
    """Hiển thị khi cv2 hoặc pyzbar chưa được cài đặt."""

    def __init__(self, err_msg: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        icon = QLabel("📦")
        icon.setObjectName("pageIcon")
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("Thiếu thư viện cho QR Check-in")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignCenter)

        desc = QLabel(
            "Tính năng này yêu cầu <b>opencv-python</b> và <b>pyzbar</b>.\n"
            "Chạy lệnh sau trong terminal rồi khởi động lại ứng dụng:"
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)

        cmd = QLabel("pip install opencv-python pyzbar")
        cmd.setAlignment(Qt.AlignCenter)
        cmd.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 13px;"
            "background: #1e293b; color: #38bdf8;"
            "padding: 10px 20px; border-radius: 6px;"
        )

        err_lbl = QLabel(f"Chi tiết lỗi: {err_msg}")
        err_lbl.setAlignment(Qt.AlignCenter)
        err_lbl.setObjectName("appTagline")
        err_lbl.setWordWrap(True)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addWidget(cmd)
        layout.addWidget(err_lbl)

    def _on_stop(self) -> None:
        """Stub — để main_window gọi không bị lỗi."""
        pass


# ══════════════════════════════════════════════════════════════════════════ #
#  Trang QR Check-in thực sự (chỉ dùng khi deps đã cài)                      #
# ══════════════════════════════════════════════════════════════════════════ #

class _QRCheckinPageImpl(QWidget):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._qr_ctrl: "QRController | None" = None
        self._frame_timer  = QTimer(self)
        self._result_timer = QTimer(self)
        self._frame_timer.setInterval(30)
        self._result_timer.setSingleShot(True)
        self._frame_timer.timeout.connect(self._tick)
        self._result_timer.timeout.connect(self._on_result_timeout)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        root.addLayout(self._build_header())

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setObjectName("sidebarDivider")
        root.addWidget(div)

        btn_row = QHBoxLayout()
        self._btn_start = QPushButton("📷  Bắt Đầu Quét QR")
        self._btn_start.setObjectName("btnPrimary")
        self._btn_start.setMinimumHeight(38)
        self._btn_start.setCursor(Qt.PointingHandCursor)
        self._btn_start.clicked.connect(self._on_start)

        self._btn_stop = QPushButton("⏹  Dừng Camera")
        self._btn_stop.setObjectName("btnDanger")
        self._btn_stop.setMinimumHeight(38)
        self._btn_stop.setCursor(Qt.PointingHandCursor)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)

        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self._cam_label = QLabel()
        self._cam_label.setFixedSize(FRAME_W, FRAME_H)
        self._cam_label.setAlignment(Qt.AlignCenter)
        self._cam_label.setStyleSheet(
            "background: #0f172a; border: 2px solid #334155; border-radius: 8px;"
        )
        self._cam_label.setText("Camera chưa được bật")
        self._cam_label.setObjectName("statusLabel")

        cam_wrap = QHBoxLayout()
        cam_wrap.addWidget(self._cam_label)
        cam_wrap.addStretch()
        root.addLayout(cam_wrap)

        self._result_lbl = QLabel("Hướng mã QR vào camera để check-in.")
        self._result_lbl.setObjectName("statusLabel")
        self._result_lbl.setWordWrap(True)
        self._result_lbl.setMinimumHeight(48)
        root.addWidget(self._result_lbl)

        root.addStretch()

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()
        hdr.setSpacing(14)

        icon = QLabel("📷")
        icon.setObjectName("pageIcon")

        title = QLabel("Check-in QR")
        title.setObjectName("pageTitle")

        sub = QLabel("Quét mã QR hội viên để check-in tức thì")
        sub.setObjectName("pageSubtitle")

        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(title)
        col.addWidget(sub)

        hdr.addWidget(icon)
        hdr.addLayout(col)
        hdr.addStretch()
        return hdr

    @Slot()
    def _on_start(self) -> None:
        self._qr_ctrl = QRController(on_result=self._on_checkin_result)
        if not self._qr_ctrl.start():
            self._set_result("❌  Không thể mở camera. Kiểm tra lại thiết bị.", "error")
            return
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._frame_timer.start()
        self._result_lbl.setStyleSheet("")
        self._result_lbl.setText("🟢  Camera đang chạy — hướng mã QR vào khung hình.")

    @Slot()
    def _on_stop(self) -> None:
        self._frame_timer.stop()
        if self._qr_ctrl:
            self._qr_ctrl.stop()
            self._qr_ctrl = None
        self._cam_label.clear()
        self._cam_label.setText("Camera đã dừng")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._result_lbl.setStyleSheet("")
        self._result_lbl.setText("Camera đã dừng.")

    @Slot()
    def _tick(self) -> None:
        if not self._qr_ctrl:
            return
        ok, frame = self._qr_ctrl.read_frame()
        if ok and frame is not None:
            self._display_frame(frame)

    def _display_frame(self, frame) -> None:
        rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        qimg = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
        pix  = QPixmap.fromImage(qimg).scaled(
            FRAME_W, FRAME_H,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._cam_label.setPixmap(pix)

    def _on_checkin_result(self, result: dict) -> None:
        status = result.get("status", "error")
        msg    = result.get("message", "Lỗi không xác định.")
        self._set_result(msg, status)
        self._frame_timer.stop()
        self._result_timer.start(4000)

    @Slot()
    def _on_result_timeout(self) -> None:
        if self._qr_ctrl and self._qr_ctrl.is_running():
            self._qr_ctrl.reset_last()
            self._frame_timer.start()
            self._result_lbl.setStyleSheet("")
            self._result_lbl.setText("🟢  Sẵn sàng quét tiếp — hướng mã QR vào khung hình.")

    def _set_result(self, text: str, status: str) -> None:
        color = STATUS_COLORS.get(status, "#94a3b8")
        self._result_lbl.setText(text)
        self._result_lbl.setStyleSheet(
            f"color: {color}; font-weight: 600; font-size: 14px;"
        )

    def closeEvent(self, event):  # noqa: N802
        self._on_stop()
        super().closeEvent(event)


# ══════════════════════════════════════════════════════════════════════════ #
#  Public export                                                              #
# ══════════════════════════════════════════════════════════════════════════ #

if _DEPS_OK:
    QRCheckinPage = _QRCheckinPageImpl
else:
    class QRCheckinPage(_MissingDepsPage):  # type: ignore[no-redef]
        def __init__(self, parent=None):
            super().__init__(_IMPORT_ERR_MSG, parent)