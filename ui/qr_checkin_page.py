"""
ui/qr_checkin_page.py  —  Phase 10

Trang QR Check-in.
- Hiển thị kết quả từ QRService (background scan) qua show_result()
- Bên phải khung camera: QLabel hiển thị ảnh member khi scan thành công
- Vẫn giữ nút manual để xem live camera feed nếu muốn
- Nếu opencv/pyzbar chưa cài → hiện hướng dẫn, không crash app
- Giao diện được quản lý hoàn toàn bằng styles.qss

QR format: "member:<id>"   ví dụ: "member:42"
"""

from __future__ import annotations

import os

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
    from pyzbar import pyzbar  # noqa: F401
    from controllers.qr_controller import QRController
    _DEPS_OK = True
except ImportError as _import_err:
    _DEPS_OK = False
    _IMPORT_ERR_MSG = str(_import_err)

FRAME_W = 560
FRAME_H = 420

MEMBER_IMG_W = FRAME_W
MEMBER_IMG_H = FRAME_H

# Giữ lại icons để set text động
STATUS_ICONS = {
    "valid":           "✅",
    "expired":         "⚠️",
    "no_subscription": "❌",
    "error":           "❌",
}


# ══════════════════════════════════════════════════════════════════════════ #
#  Trang thiếu dependency                                                    #
# ══════════════════════════════════════════════════════════════════════════ #

class _MissingDepsPage(QWidget):
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
        cmd.setObjectName("missingDepsCmd")

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
        pass

    def show_result(self, result: dict) -> None:  # noqa: ARG002
        pass


# ══════════════════════════════════════════════════════════════════════════ #
#  Trang QR Check-in thực sự                                                 #
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

    # ── Build UI ─────────────────────────────────────────────────────── #

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        root.addLayout(self._build_header())

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setObjectName("sidebarDivider")
        root.addWidget(div)

        root.addLayout(self._build_status_card())
        root.addLayout(self._build_camera_controls())
        root.addLayout(self._build_main_area())   # camera + member photo
        root.addStretch()

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()
        hdr.setSpacing(14)

        icon = QLabel("📷")
        icon.setObjectName("pageIcon")

        title = QLabel("Check-in QR")
        title.setObjectName("pageTitle")

        sub = QLabel("Camera nền tự động quét — hoặc dùng nút bên dưới để xem live feed")
        sub.setObjectName("pageSubtitle")

        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(title)
        col.addWidget(sub)

        hdr.addWidget(icon)
        hdr.addLayout(col)
        hdr.addStretch()
        return hdr

    def _build_status_card(self) -> QHBoxLayout:
        """Card hiển thị kết quả check-in gần nhất."""
        row = QHBoxLayout()

        self._status_icon_lbl = QLabel("📋")
        self._status_icon_lbl.setFixedWidth(40)
        self._status_icon_lbl.setAlignment(Qt.AlignCenter)
        self._status_icon_lbl.setObjectName("statusIcon")

        self._result_lbl = QLabel("Hướng mã QR vào camera để check-in tự động.")
        self._result_lbl.setObjectName("statusResultLabel")
        self._result_lbl.setProperty("status", "default")
        self._result_lbl.setWordWrap(True)
        self._result_lbl.setMinimumHeight(56)

        card = QFrame()
        card.setObjectName("statusCard")
        
        card_layout = QHBoxLayout(card)
        card_layout.setSpacing(14)
        card_layout.addWidget(self._status_icon_lbl)
        card_layout.addWidget(self._result_lbl)

        row.addWidget(card)
        return row

    def _build_camera_controls(self) -> QHBoxLayout:
        btn_row = QHBoxLayout()

        self._btn_start = QPushButton("📷  Xem Live Camera")
        self._btn_start.setObjectName("btnPrimary")
        self._btn_start.setMinimumHeight(38)
        self._btn_start.setCursor(Qt.PointingHandCursor)
        self._btn_start.clicked.connect(self._on_start)

        self._btn_stop = QPushButton("⏹  Tắt Live Camera")
        self._btn_stop.setObjectName("btnDanger")
        self._btn_stop.setMinimumHeight(38)
        self._btn_stop.setCursor(Qt.PointingHandCursor)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)

        self._cam_status_lbl = QLabel("🟢  Camera nền đang chạy")
        self._cam_status_lbl.setObjectName("appTagline")

        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        btn_row.addSpacing(16)
        btn_row.addWidget(self._cam_status_lbl)
        btn_row.addStretch()
        return btn_row

    def _build_main_area(self) -> QHBoxLayout:
        area = QHBoxLayout()
        area.setSpacing(16)
        area.setAlignment(Qt.AlignTop)

        # ===== CAMERA =====
        cam_container = QWidget()
        cam_container.setLayout(self._build_camera_view())
        cam_container.setFixedSize(FRAME_W, FRAME_H)

        # ===== MEMBER (CHỈ 1 CONTAINER DUY NHẤT) =====
        member_container = QWidget()
        member_container.setLayout(self._build_member_photo_panel())
        member_container.setFixedSize(MEMBER_IMG_W, MEMBER_IMG_H)

        # ===== ADD =====
        area.addWidget(cam_container)
        area.addWidget(member_container)

        return area

    def _build_camera_view(self) -> QVBoxLayout:
        self._cam_label = QLabel()
        self._cam_label.setFixedSize(FRAME_W, FRAME_H)
        self._cam_label.setAlignment(Qt.AlignCenter)
        self._cam_label.setObjectName("camViewLabel")
        self._cam_label.setText("Live feed tắt\n(Camera nền vẫn đang quét QR)")

        wrap = QVBoxLayout()
        wrap.setContentsMargins(0,0,0,0) 
        wrap.addWidget(self._cam_label)
        wrap.addStretch()   
        return wrap

    def _build_member_photo_panel(self) -> QVBoxLayout:
        panel = QVBoxLayout()
        panel.setContentsMargins(0, 0, 0, 0)
        panel.setAlignment(Qt.AlignCenter)

        # 1. Image Label đóng vai trò là khung chứa (Container)
        self._member_img_lbl = QLabel()
        self._member_img_lbl.setFixedSize(MEMBER_IMG_W, MEMBER_IMG_H)
        self._member_img_lbl.setAlignment(Qt.AlignCenter)
        self._member_img_lbl.setObjectName("memberImgLabel")
        self._member_img_lbl.setText("Chưa có ảnh")

        # 2. Tạo Overlay Layout nằm đè lên trên Image Label
        overlay_layout = QVBoxLayout(self._member_img_lbl)
        overlay_layout.setAlignment(Qt.AlignCenter)
        overlay_layout.setSpacing(8)

        # Title ("Hội Viên")
        title = QLabel("👤  Hội Viên")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("memberTitleLabel")

        # Name
        self._member_name_lbl = QLabel("")
        self._member_name_lbl.setAlignment(Qt.AlignCenter)
        self._member_name_lbl.setWordWrap(True)
        self._member_name_lbl.setObjectName("memberNameLabel")
        self._member_name_lbl.hide()  # Ẩn đi khi chưa có khách hàng check-in

        # Thêm các text vào overlay
        overlay_layout.addWidget(title)
        overlay_layout.addWidget(self._member_name_lbl)

        # Thêm khung ảnh vào panel
        panel.addWidget(self._member_img_lbl)

        return panel

    # ── Public API ───────────────────────────────────────────────────── #

    def show_result(self, result: dict) -> None:
        """
        Được QRService / main_window gọi khi có kết quả check-in.
        Hiển thị message + đổi màu/icon + ảnh member theo result.
        """
        status  = result.get("status", "error")
        message = result.get("message", "Lỗi không xác định.")
        self._set_result(message, status)
        self._show_member_photo(
            result.get("image_path", ""),
            result.get("member_name", ""),
        )

        if self._frame_timer.isActive():
            self._frame_timer.stop()
            self._result_timer.start(3000)

    # ── Manual camera controls ────────────────────────────────────────── #

    @Slot()
    def _on_start(self) -> None:
        self._qr_ctrl = QRController(on_result=self._on_manual_checkin_result)
        if not self._qr_ctrl.start():
            self._set_result("❌  Không thể mở camera.\n(Camera có thể đang được QRService dùng.)", "error")
            self._qr_ctrl = None
            return
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._cam_status_lbl.setText("🔴  Live feed đang chạy")
        self._frame_timer.start()
        self._set_result("🟢  Camera live đang chạy — hướng mã QR vào khung hình.", "valid")

    @Slot()
    def _on_stop(self) -> None:
        self._frame_timer.stop()
        if self._qr_ctrl:
            self._qr_ctrl.stop()
            self._qr_ctrl = None
        self._cam_label.clear()
        self._cam_label.setText("Live feed tắt\n(Camera nền vẫn đang quét QR)")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._cam_status_lbl.setText("🟢  Camera nền đang chạy")
        self._set_result("Live feed đã tắt.", "error")

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
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        self._cam_label.setPixmap(pix)

    def _on_manual_checkin_result(self, result: dict) -> None:
        """Kết quả từ live feed manual."""
        status  = result.get("status", "error")
        message = result.get("message", "Lỗi không xác định.")
        self._set_result(message, status)
        self._show_member_photo(
            result.get("image_path", ""),
            result.get("member_name", ""),
        )
        self._frame_timer.stop()
        self._result_timer.start(3000)

    @Slot()
    def _on_result_timeout(self) -> None:
        """Sau 3 giây → resume live feed (nếu đang bật)."""
        if self._qr_ctrl and self._qr_ctrl.is_running():
            self._qr_ctrl.reset_last()
            self._frame_timer.start()
            self._set_result("🟢  Sẵn sàng quét tiếp — hướng mã QR vào khung hình.", "valid")

    # ── Helpers ──────────────────────────────────────────────────────── #

    def _set_result(self, text: str, status: str) -> None:
        icon = STATUS_ICONS.get(status, "📋")
        self._result_lbl.setText(text)
        self._status_icon_lbl.setText(icon)
        
        # Cập nhật property 'status' để Qt tự động đổi màu theo file QSS
        self._result_lbl.setProperty("status", status)
        
        # Bắt buộc UI render lại style cho widget này
        self._result_lbl.style().unpolish(self._result_lbl)
        self._result_lbl.style().polish(self._result_lbl)

    def _show_member_photo(self, image_path: str, member_name: str) -> None:
        """Load và hiển thị ảnh member lên panel bên phải."""
        # Xử lý hiển thị tên
        if member_name:
            self._member_name_lbl.setText(member_name)
            self._member_name_lbl.show()
        else:
            self._member_name_lbl.hide()

        # Xử lý hiển thị ảnh
        if image_path and os.path.isfile(image_path):
            pix = QPixmap(image_path).scaled(
                MEMBER_IMG_W,
                MEMBER_IMG_H,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
 
            # Cắt ảnh ở giữa (Center Crop) để vừa khít hoàn toàn
            x = (pix.width() - MEMBER_IMG_W) // 2
            y = (pix.height() - MEMBER_IMG_H) // 2
            pix = pix.copy(x, y, MEMBER_IMG_W, MEMBER_IMG_H)
            
            self._member_img_lbl.setPixmap(pix)
        else:
            self._member_img_lbl.clear()
            self._member_img_lbl.setText("Chưa có ảnh")

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