"""
ui/qr_checkin_page.py  —  Phase 11

Trang QR Check-in.
- KHÔNG mở camera riêng. Nhận frame từ QRService qua signal frame_ready.
- Hiển thị kết quả từ QRService (background scan) qua show_result()
- Bên phải khung camera: QLabel hiển thị ảnh member khi scan thành công
- Hỗ trợ capture mode: chụp ảnh hội viên từ frame hiện tại của QRService
- Nếu opencv/pyzbar chưa cài → hiện hướng dẫn, không crash app
- Giao diện được quản lý hoàn toàn bằng styles.qss

QR format: "member:<id>"   ví dụ: "member:42"
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtCore import QUrl
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
    _DEPS_OK = True
except ImportError as _import_err:
    _DEPS_OK = False
    _IMPORT_ERR_MSG = str(_import_err)

FRAME_W = 560
FRAME_H = 420

MEMBER_IMG_W = FRAME_W
MEMBER_IMG_H = FRAME_H

STATUS_ICONS = {
    "valid":           "✅",
    "expired":         "⚠️",
    "no_subscription": "❌",
    "error":           "❌",
}

# ── Đường dẫn thư mục assets âm thanh ───────────────────────────────────── #
_UI_DIR     = os.path.dirname(os.path.abspath(__file__))
_ASSETS_DIR = os.path.join(_UI_DIR, "..", "assets")
_SFX_SUCCESS = os.path.join(_ASSETS_DIR, "success.wav")
_SFX_ERROR   = os.path.join(_ASSETS_DIR, "error.wav")


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

    def set_qr_service(self, service) -> None:  # noqa: ARG002
        pass

    def show_result(self, result: dict) -> None:  # noqa: ARG002
        pass

    def start_capture_mode(self, member_id: int, member_name: str = "") -> None:  # noqa: ARG002
        pass


# ══════════════════════════════════════════════════════════════════════════ #
#  Trang QR Check-in thực sự                                                 #
# ══════════════════════════════════════════════════════════════════════════ #

class _QRCheckinPageImpl(QWidget):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._qr_service = None          # được inject từ MainWindow
        self._capture_member_id = None
        self._live_preview_active = False
        self._result_timer = QTimer(self)
        self._result_timer.setSingleShot(True)
        self._result_timer.timeout.connect(self._on_result_timeout)
        self._clear_member_timer = QTimer(self)
        self._clear_member_timer.setSingleShot(True)
        self._clear_member_timer.timeout.connect(self._clear_member_photo)
        self._setup_sound_effects()
        self._setup_ui()

    # ── Sound Effects ────────────────────────────────────────────────── #

    def _setup_sound_effects(self) -> None:
        """Khởi tạo QSoundEffect cho success và error."""
        self._sfx_success = QSoundEffect(self)
        self._sfx_success.setSource(QUrl.fromLocalFile(os.path.abspath(_SFX_SUCCESS)))
        self._sfx_success.setVolume(0.8)

        self._sfx_error = QSoundEffect(self)
        self._sfx_error.setSource(QUrl.fromLocalFile(os.path.abspath(_SFX_ERROR)))
        self._sfx_error.setVolume(0.8)

    def _play_sound(self, status: str) -> None:
        """Phát âm thanh tương ứng với trạng thái check-in."""
        if status == "valid":
            self._sfx_success.play()
        else:
            self._sfx_error.play()

    # ── Inject QRService ─────────────────────────────────────────────── #

    def set_qr_service(self, service) -> None:
        """
        Được MainWindow gọi sau khi khởi tạo QRService.
        Kết nối signal frame_ready và camera_status.
        """
        self._qr_service = service
        service.frame_ready.connect(self._on_frame_ready)
        service.camera_status.connect(self._on_camera_status)

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

        sub = QLabel("Camera nền tự động quét — hoặc bật live preview để xem hình ảnh camera")
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
        self._btn_start.clicked.connect(self._on_start_preview)

        self._btn_stop = QPushButton("⏹  Tắt Live Camera")
        self._btn_stop.setObjectName("btnDanger")
        self._btn_stop.setMinimumHeight(38)
        self._btn_stop.setCursor(Qt.PointingHandCursor)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop_preview)

        self._btn_capture = QPushButton("📸  Chụp Ảnh")
        self._btn_capture.setObjectName("btnSecondary")
        self._btn_capture.setMinimumHeight(38)
        self._btn_capture.setCursor(Qt.PointingHandCursor)
        self._btn_capture.setVisible(False)
        self._btn_capture.clicked.connect(self._capture_photo)

        self._cam_status_lbl = QLabel("🟢  Camera nền đang chạy")
        self._cam_status_lbl.setObjectName("appTagline")

        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        btn_row.addWidget(self._btn_capture)
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
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(self._cam_label)
        wrap.addStretch()
        return wrap

    def _build_member_photo_panel(self) -> QVBoxLayout:
        panel = QVBoxLayout()
        panel.setContentsMargins(0, 0, 0, 0)
        panel.setAlignment(Qt.AlignCenter)

        self._member_img_lbl = QLabel()
        self._member_img_lbl.setFixedSize(MEMBER_IMG_W, MEMBER_IMG_H)
        self._member_img_lbl.setAlignment(Qt.AlignCenter)
        self._member_img_lbl.setObjectName("memberImgLabel")
        self._member_img_lbl.setText("Chưa có ảnh")

        overlay_layout = QVBoxLayout(self._member_img_lbl)
        overlay_layout.setAlignment(Qt.AlignCenter)
        overlay_layout.setSpacing(8)

        title = QLabel("👤  Hội Viên")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("memberTitleLabel")

        self._member_name_lbl = QLabel("")
        self._member_name_lbl.setAlignment(Qt.AlignCenter)
        self._member_name_lbl.setWordWrap(True)
        self._member_name_lbl.setObjectName("memberNameLabel")
        self._member_name_lbl.hide()

        overlay_layout.addWidget(title)
        overlay_layout.addWidget(self._member_name_lbl)

        panel.addWidget(self._member_img_lbl)
        return panel

    # ── Public API ───────────────────────────────────────────────────── #

    def show_result(self, result: dict) -> None:
        """
        Được QRService / main_window gọi khi có kết quả check-in.
        Hiển thị message + đổi màu/icon + ảnh member theo result.
        Phát âm thanh tương ứng với trạng thái check-in.
        """
        status  = result.get("status", "error")
        message = result.get("message", "Lỗi không xác định.")
        self._set_result(message, status)
        self._show_member_photo(
            result.get("image_path", ""),
            result.get("member_name", ""),
        )
        # Phát âm thanh thông báo
        self._play_sound(status)

        # Auto clear sau 2 giây
        self._clear_member_timer.start(2000)

        # Tạm ẩn live feed 3 giây để xem kết quả
        if self._live_preview_active:
            self._result_timer.start(3000)

    def _clear_member_photo(self) -> None:
        """Xóa ảnh hội viên sau vài giây."""
        self._member_img_lbl.clear()
        self._member_img_lbl.setText("Chưa có ảnh")

        self._member_name_lbl.clear()
        self._member_name_lbl.hide()

    def start_capture_mode(self, member_id: int, member_name: str = "") -> None:
        """
        Kích hoạt chế độ chụp ảnh cho hội viên cụ thể.
        Được gọi từ MainWindow khi user bấm "📸 Chụp Ảnh" ở MemberPage.
        """
        self._capture_member_id = member_id
        self._btn_capture.setVisible(True)
        # Bật live preview nếu chưa bật
        if not self._live_preview_active:
            self._on_start_preview()
        name_display = f" — {member_name}" if member_name else ""
        self._set_result(
            f"📸  Chế độ chụp ảnh{name_display} — Bấm nút Chụp Ảnh để lưu.",
            "valid",
        )


    # ── Slots từ QRService ────────────────────────────────────────────── #

    @Slot(object)
    def _on_frame_ready(self, frame) -> None:
        """Nhận frame từ QRService và hiển thị lên cam_label (nếu live preview bật)."""
        if not self._live_preview_active:
            return
        self._display_frame(frame)

    @Slot(str)
    def _on_camera_status(self, text: str) -> None:
        """Cập nhật label trạng thái camera trong trang."""
        self._cam_status_lbl.setText(text)

    # ── Live preview controls ─────────────────────────────────────────── #

    @Slot()
    def _on_start_preview(self) -> None:
        """Bật live preview — chỉ hiện frame, không mở camera mới."""
        if self._qr_service and not self._qr_service.is_running():
            self._set_result("❌  Camera nền chưa khởi động.", "error")
            return
        self._live_preview_active = True
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._cam_status_lbl.setText("🟢  Live feed đang chạy")
        self._set_result("🟢  Camera live đang chạy — hướng mã QR vào khung hình.", "valid")

    @Slot()
    def _on_stop_preview(self) -> None:
        """Tắt live preview — camera nền vẫn chạy."""
        self._live_preview_active = False
        self._cam_label.clear()
        self._cam_label.setText("Live feed tắt\n(Camera nền vẫn đang quét QR)")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_capture.setVisible(False)
        self._capture_member_id = None
        self._cam_status_lbl.setText("🟢  Camera nền đang chạy")
        self._set_result("Live feed đã tắt.", "error")

    # ── Capture photo ─────────────────────────────────────────────────── #

    @Slot()
    def _capture_photo(self) -> None:
        """Chụp frame hiện tại từ QRService và lưu làm ảnh hội viên."""
        if not self._qr_service:
            self._set_result("❌  QRService chưa được khởi tạo.", "error")
            return

        frame = self._qr_service.capture_frame()
        if frame is None:
            self._set_result("❌  Lỗi camera: Không thể lấy frame.", "error")
            return

        member_id = self._capture_member_id
        if member_id is None:
            self._set_result("❌  Chưa chọn hội viên để chụp ảnh.", "error")
            return

        save_dir  = os.path.join("images", "members")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"{member_id}.jpg")

        cv2.imwrite(save_path, frame)

        from database import Database
        db = Database()
        db.update_member_image(member_id, save_path)

        member = db.get_member(member_id)
        name = member["name"] if member else "Hội viên"

        self._show_member_photo(save_path, name)
        self._set_result(f"✅  Đã chụp và lưu ảnh cho {name}", "valid")

        # Tự động clear ảnh hội viên trên UI sau 2 giây
        self._clear_member_timer.start(2000)

        # Reset lại dòng thông báo trạng thái bên dưới sau 3 giây (nếu đang bật live)
        if self._live_preview_active:
            self._result_timer.start(3000)

    # ── Internal helpers ──────────────────────────────────────────────── #

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

    @Slot()
    def _on_result_timeout(self) -> None:
        """Sau 3 giây → resume live feed (nếu đang bật)."""
        if self._live_preview_active:
            self._set_result("🟢  Sẵn sàng quét tiếp — hướng mã QR vào khung hình.", "valid")

    def _set_result(self, text: str, status: str) -> None:
        icon = STATUS_ICONS.get(status, "📋")
        self._result_lbl.setText(text)
        self._status_icon_lbl.setText(icon)
        self._result_lbl.setProperty("status", status)
        self._result_lbl.style().unpolish(self._result_lbl)
        self._result_lbl.style().polish(self._result_lbl)

    def _show_member_photo(self, image_path: str, member_name: str) -> None:
        """Load và hiển thị ảnh member lên panel bên phải."""
        if member_name:
            self._member_name_lbl.setText(member_name)
            self._member_name_lbl.show()
        else:
            self._member_name_lbl.hide()

        if image_path and os.path.isfile(image_path):
            pix = QPixmap(image_path).scaled(
                MEMBER_IMG_W,
                MEMBER_IMG_H,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            x = (pix.width()  - MEMBER_IMG_W) // 2
            y = (pix.height() - MEMBER_IMG_H) // 2
            pix = pix.copy(x, y, MEMBER_IMG_W, MEMBER_IMG_H)
            self._member_img_lbl.setPixmap(pix)
        else:
            self._member_img_lbl.clear()
            self._member_img_lbl.setText("Chưa có ảnh")


# ══════════════════════════════════════════════════════════════════════════ #
#  Public export                                                              #
# ══════════════════════════════════════════════════════════════════════════ #

if _DEPS_OK:
    QRCheckinPage = _QRCheckinPageImpl
else:
    class QRCheckinPage(_MissingDepsPage):  # type: ignore[no-redef]
        def __init__(self, parent=None):
            super().__init__(_IMPORT_ERR_MSG, parent)