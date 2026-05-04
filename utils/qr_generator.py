"""
utils/qr_generator.py  —  Phase 10

Tiện ích tạo file QR Code PNG từ chuỗi dữ liệu bất kỳ.
Không phụ thuộc database — chỉ nhận str và đường dẫn lưu.

Yêu cầu:
    pip install qrcode[pil]
"""

from __future__ import annotations

import qrcode
from qrcode.image.styledpil import StyledPilImage


def generate_qr(data: str, save_path: str) -> None:
    """
    Tạo ảnh QR Code từ ``data`` và lưu vào ``save_path`` dưới dạng PNG.

    Parameters
    ----------
    data      : Chuỗi nội dung sẽ được mã hoá vào QR (vd: "member:42").
    save_path : Đường dẫn file đầu ra, bao gồm tên file và đuôi .png.

    Raises
    ------
    OSError   : Nếu không thể ghi file (quyền truy cập, đường dẫn sai, …).
    Exception : Bất kỳ lỗi nào từ thư viện qrcode / Pillow.
    """
    qr = qrcode.QRCode(
        version=None,           # tự chọn kích thước nhỏ nhất đủ chứa data
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(save_path)