"""
controllers/qr_controller.py  —  Phase 9

Scan QR từ camera (OpenCV + pyzbar), decode member_id, gọi CheckinController.

QR format được hỗ trợ: "member:<id>"   ví dụ: "member:42"

Yêu cầu:
    pip install opencv-python pyzbar
"""

from __future__ import annotations

import re
from typing import Callable

import cv2
from pyzbar import pyzbar

from controllers.checkin_controller import CheckinController


class QRController:
    """
    Quản lý vòng lặp camera và xử lý QR check-in.

    Dùng theo cách:
        ctrl = QRController(on_result=my_callback)
        ctrl.start()   # gọi từ thread/timer
        ctrl.stop()
    """

    QR_PATTERN = re.compile(r"^member:(\d+)$")

    def __init__(self, on_result: Callable[[dict], None]) -> None:
        """
        Parameters
        ----------
        on_result : Callable[[dict], None]
            Callback nhận dict kết quả từ CheckinController.checkin()
            Thêm key "member_id" vào dict trước khi gọi callback.
        """
        self._on_result       = on_result
        self._checkin_ctrl    = CheckinController()
        self._cap: cv2.VideoCapture | None = None
        self._running         = False
        self._last_member_id: int | None = None   # tránh scan lặp liên tục

    # ── Public API ──────────────────────────────────────────────────── #

    def start(self, camera_index: int = 0) -> bool:
        """Mở camera. Trả về True nếu thành công."""
        self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            return False
        self._running = True
        self._last_member_id = None
        return True

    def stop(self) -> None:
        """Dừng camera và giải phóng tài nguyên."""
        self._running = False
        if self._cap:
            self._cap.release()
            self._cap = None

    def is_running(self) -> bool:
        return self._running

    def read_frame(self) -> tuple[bool, "cv2.Mat | None"]:
        """
        Đọc 1 frame từ camera, decode QR nếu có, trả về (ok, frame_bgr).
        Gọi method này định kỳ từ QTimer (ví dụ 30ms).
        """
        if not self._running or self._cap is None:
            return False, None

        ok, frame = self._cap.read()
        if not ok:
            return False, None

        member_id = self._decode_qr(frame)
        if member_id is not None and member_id != self._last_member_id:
            self._last_member_id = member_id
            result = self._checkin_ctrl.checkin(member_id)
            result["member_id"] = member_id
            self._on_result(result)

        return True, frame

    def reset_last(self) -> None:
        """Reset cache để cho phép scan lại cùng member sau khi đã xử lý."""
        self._last_member_id = None

    # ── Private ─────────────────────────────────────────────────────── #

    def _decode_qr(self, frame: "cv2.Mat") -> int | None:
        """
        Decode tất cả QR/barcode trong frame.
        Trả về member_id (int) nếu tìm thấy đúng format, ngược lại None.
        """
        codes = pyzbar.decode(frame)
        for code in codes:
            raw = code.data.decode("utf-8", errors="ignore").strip()
            m = self.QR_PATTERN.match(raw)
            if m:
                return int(m.group(1))
        return None