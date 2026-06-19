"""
services/qr_service.py  —  Phase 11

Background QR scanning service — singleton camera, chạy bằng QTimer.
Không dùng thread. Không block UI.
QRService là nơi DUY NHẤT giữ cv2.VideoCapture.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

try:
    import cv2
    from controllers.qr_controller import QRController
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False


class QRService(QObject):
   
    scanned       = Signal(dict)
    frame_ready   = Signal(object)   # cv2 BGR frame (numpy ndarray)
    camera_status = Signal(str)      # status text cho footer / cam_status_lbl

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctrl: "QRController | None" = None
        self._timer = QTimer(self)
        self._timer.setInterval(30)          # 30ms ≈ 33fps
        self._timer.timeout.connect(self._tick)
        self._available = _DEPS_OK
        self._last_frame = None              # frame mới nhất để capture

    # ── Public API ──────────────────────────────────────────────────── #

    def is_available(self) -> bool:
        """False nếu opencv / pyzbar chưa cài."""
        return self._available

    def start(self, camera_index: int = 0) -> bool:
        """Mở camera và bắt đầu scan. Trả về True nếu thành công."""
        if not self._available:
            return False
        if self._ctrl and self._ctrl.is_running():
            return True                      # đã chạy rồi

        self._ctrl = QRController(on_result=self._on_result)
        if not self._ctrl.start(camera_index):
            self._ctrl = None
            self.camera_status.emit("🔴  Không thể mở camera")
            return False
        self._timer.start()
        self.camera_status.emit("🟢  Camera đang hoạt động")
        return True

    def stop(self) -> None:
        """Dừng camera và giải phóng tài nguyên."""
        self._timer.stop()
        if self._ctrl:
            self._ctrl.stop()
            self._ctrl = None
        self._last_frame = None
        self.camera_status.emit("🔴  Camera đã tắt")

    def is_running(self) -> bool:
        return self._ctrl is not None and self._ctrl.is_running()

    def capture_frame(self):
        """Trả về frame cuối cùng (BGR numpy array) hoặc None."""
        return self._last_frame

    def resume_scan(self) -> None:
        """Resume sau khi xử lý kết quả QR."""
        if self.is_running():
            if self._ctrl:
                self._ctrl.reset_last()
            if not self._timer.isActive():
                self._timer.start()

    # ── Internal ────────────────────────────────────────────────────── #

    def _tick(self) -> None:
        """Được QTimer gọi mỗi 30ms — đọc frame và decode QR."""
        if not self._ctrl:
            return
        ok, frame = self._ctrl.read_frame()
        if ok and frame is not None:
            self._last_frame = frame
            self.frame_ready.emit(frame)

    def _on_result(self, result: dict) -> None:
        """QRController gọi callback này khi decode được QR."""
        # Tạm dừng scan trong khi xử lý
        self._timer.stop()
        self.scanned.emit(result)