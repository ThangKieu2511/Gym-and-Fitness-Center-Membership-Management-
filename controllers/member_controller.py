"""
controllers/member_controller.py  —  Phase 10

Thay đổi so với Phase 4:
  • Thêm generate_member_qr(member_id) — tạo QR, lưu PNG, cập nhật DB
"""

from __future__ import annotations

import os
import sqlite3

from database import Database
from utils.qr_generator import generate_qr

# Thư mục chứa file QR PNG
QR_DIR = "qr_codes"


class MemberController:
    """
    Bọc ngoài Database, thêm validation và dịch lỗi DB sang thông báo UI.
    Một instance Database duy nhất dùng chung suốt vòng đời ứng dụng.
    """

    def __init__(self) -> None:
        self.db = Database()

    # ------------------------------------------------------------------ #
    #  Validation nội bộ                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate(name: str, email: str) -> None:
        """Ném ValueError nếu dữ liệu không hợp lệ."""
        if not name:
            raise ValueError("Họ tên không được để trống.")
        if len(name) > 120:
            raise ValueError("Họ tên không được vượt quá 120 ký tự.")
        if email and "@" not in email:
            raise ValueError("Địa chỉ email không hợp lệ.")

    @staticmethod
    # Chuyển lỗi trùng lặp của SQLite thành thông báo dễ hiểu cho người dùng
    def _integrity_msg(exc: sqlite3.IntegrityError) -> str:
        """Chuyển IntegrityError thành thông báo tiếng Việt dễ hiểu."""
        msg = str(exc).lower()
        if "phone" in msg:
            return "Số điện thoại này đã được đăng ký cho hội viên khác."
        if "email" in msg:
            return "Email này đã được đăng ký cho hội viên khác."
        if "qr_code" in msg:
            return "Mã QR này đã được sử dụng cho hội viên khác."
        return f"Dữ liệu bị trùng lặp, vui lòng kiểm tra lại. ({exc})"

    # ------------------------------------------------------------------ #
    #  Đọc dữ liệu                                                         #
    # ------------------------------------------------------------------ #

    def get_members(self) -> list[dict]:
        """
        Trả về toàn bộ danh sách hội viên.

        Returns:
            list[dict] — mỗi dict chứa: id, name, phone, email, gender, join_date
        Raises:
            RuntimeError: nếu thao tác DB thất bại.
        """
        try:
            return self.db.get_members()
        except Exception as exc:
            raise RuntimeError(f"Không thể tải danh sách hội viên: {exc}") from exc

    def get_member_by_id(self, member_id: int) -> dict | None:
        # Trả về hội viên theo ID.
        try:
            return self.db.get_member(member_id)
        except Exception as exc:
            raise RuntimeError(f"Không thể tải hội viên #{member_id}: {exc}") from exc

    def search_members(self, query: str) -> list[dict]:
        # Tìm kiếm hội viên theo tên hoặc sđth.
        query = query.strip()
        try:
            if not query:
                return self.db.get_members()
            return self.db.search_members(query)
        except Exception as exc:
            raise RuntimeError(f"Tìm kiếm thất bại: {exc}") from exc

    # ------------------------------------------------------------------ #
    #  Thêm mới                                                            #
    # ------------------------------------------------------------------ #

    # Thêm hội viên mới, tự cho ID tự động.
    def add_member(
        self,
        name: str,
        phone: str,
        email: str,
        gender: str,
    ) -> int:
       
        name   = name.strip()
        phone  = phone.strip()
        email  = email.strip()
        gender = gender.strip()


        # Kiểm tra (Validation) — ném ValueError nếu không hợp lệ
        self._validate(name, email)

        try:
            # Gọi tới Database để thêm hội viên mới, trả về ID tự động
            return self.db.add_member(name, phone, email, gender, qr_code=None)
        except sqlite3.IntegrityError as exc:
            # Chuyển lỗi trùng lặp thành thông báo dễ hiểu
            raise ValueError(self._integrity_msg(exc)) from exc
        except Exception as exc:
            raise RuntimeError(f"Không thể thêm hội viên: {exc}") from exc

    # ------------------------------------------------------------------ #
    #  Cập nhật                                                            #
    # ------------------------------------------------------------------ #

    # Cập nhật thông tin hội viên theo ID.
    def update_member(
        self,
        member_id: int,
        name: str,
        phone: str,
        email: str,
        gender: str,
        join_date: str = "",
    ) -> bool:
        
        name   = name.strip()
        phone  = phone.strip()
        email  = email.strip()
        gender = gender.strip()

        self._validate(name, email)

        try:
            # Lấy qr_code gốc để không vô tình xóa mã QR đã có
            existing = self.db.get_member(member_id) # Kiểm tra hội viên tồn tại trong Database, nếu không sẽ trả về None
            qr_code  = existing.get("qr_code") if existing else None

            # Gọi tới Database để update hội viên, trả về True nếu thành công
            return self.db.update_member( 
                member_id, name, phone, email, gender, join_date, qr_code
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(self._integrity_msg(exc)) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Không thể cập nhật hội viên #{member_id}: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    #  Xóa                                                                 #
    # ------------------------------------------------------------------ #

    def delete_member(self, member_id: int) -> bool:
        
        try:
            return self.db.delete_member(member_id) # Gọi tới Database để xóa hội viên theo ID.
        except Exception as exc:
            raise RuntimeError(
                f"Không thể xóa hội viên #{member_id}: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    #  Tạo QR  (Phase 10)                                                  #
    # ------------------------------------------------------------------ #

    def generate_member_qr(self, member_id: int) -> str:
        
        # ── 1. Kiểm tra hội viên tồn tại ──────────────────────────────── #
        try:
            existing = self.db.get_member(member_id) # Kiểm tra hội viên tồn tại trong Database, nếu không sẽ trả về None
        except Exception as exc:
            raise RuntimeError(f"Không thể truy vấn hội viên #{member_id}: {exc}") from exc

        if existing is None:
            raise ValueError(f"Không tìm thấy hội viên có ID = {member_id}.")

        # ── 2. Chuỗi dữ liệu QR theo format Phase 9 ───────────────────── #
        qr_data = f"member:{member_id}" # Dữ liệu QR sẽ có format "member:{id}" để dễ dàng nhận biết khi quét, có thể mở rộng thêm thông tin khác nếu cần trong tương lai

        # ── 3. Đảm bảo thư mục tồn tại ────────────────────────────────── #
        os.makedirs(QR_DIR, exist_ok=True)
        file_path = os.path.join(QR_DIR, f"member_{member_id}.png")

        # ── 4. Tạo file PNG ────────────────────────────────────────────── #
        try:
            generate_qr(qr_data, file_path) # Gọi hàm ở bên utils/qr_generator.py để tạo file QR PNG
        except Exception as exc:
            raise RuntimeError(f"Không thể tạo file QR: {exc}") from exc

        # ── 5. Cập nhật cột qr_code trong DB ──────────────────────────── #
        try:
            join_date = existing.get("join_date", "")
            self.db.update_member(
                member_id,
                existing.get("name", ""),
                existing.get("phone", ""),
                existing.get("email", ""),
                existing.get("gender", ""),
                join_date,
                qr_code=qr_data,
            )
        except Exception as exc:
            raise RuntimeError(f"Không thể lưu mã QR vào database: {exc}") from exc

        return os.path.abspath(file_path) # Trả về đường dẫn tuyệt đối của file QR PNG vừa tạo