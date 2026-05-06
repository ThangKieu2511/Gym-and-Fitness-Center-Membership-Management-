"""
services/qr_service.py  —  Phase 9

Background QR scanning service — singleton camera, chạy bằng QTimer.
Không dùng thread. Không block UI.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

try:
    from controllers.qr_controller import QRController
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False


class QRService(QObject):
    """
    Singleton-style service quản lý camera nền toàn app.

    Signals
    -------
    scanned(dict) : emit khi decode được QR hợp lệ.
        dict keys: status, message, checkin_id, member_id
    """

    scanned = Signal(dict)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctrl: "QRController | None" = None
        self._timer = QTimer(self)
        self._timer.setInterval(30)          # 30ms ≈ 33fps
        self._timer.timeout.connect(self._tick)
        self._available = _DEPS_OK

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
            return False
        self._timer.start()
        return True

    def stop(self) -> None:
        """Dừng camera và giải phóng tài nguyên."""
        self._timer.stop()
        if self._ctrl:
            self._ctrl.stop()
            self._ctrl = None

    def is_running(self) -> bool:
        return self._ctrl is not None and self._ctrl.is_running()

    # ── Internal ────────────────────────────────────────────────────── #

    def _tick(self) -> None:
        """Được QTimer gọi mỗi 30ms — đọc frame và decode QR."""
        if self._ctrl:
            self._ctrl.read_frame()          # decode + callback xảy ra bên trong

    def _on_result(self, result: dict) -> None:
        """QRController gọi callback này khi decode được QR."""
        # Tạm dừng scan trong khi xử lý — QRController tự reset khi được gọi
        self._timer.stop()
        self.scanned.emit(result)