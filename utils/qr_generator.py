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
    qr = qrcode.QRCode(
        version=None,           # tự chọn kích thước nhỏ nhất đủ chứa data
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data) # Đưa chuỗi "member:{id}" vào QR code
    qr.make(fit=True) # Tính toán kích thước QR code

    img = qr.make_image(fill_color="black", back_color="white") #Tạo ảnh QR
    img.save(save_path) #Lưu file PNG vào đường dẫn đã chỉ định