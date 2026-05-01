"""
controllers/member_controller.py  —  Phase 4

Tầng trung gian giữa UI và Database.
Không có SQL thô — chỉ gọi qua self.db.

Thay đổi so với Phase 3:
  • Thêm search_members(query)         — tìm kiếm realtime
  • update_member nhận thêm join_date  — giữ nguyên ngày tham gia khi sửa
  • Bắt sqlite3.IntegrityError         — dịch sang thông báo tiếng Việt thân thiện
"""

from __future__ import annotations

import sqlite3

from database import Database


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
        """
        Trả về một hội viên theo khóa chính, hoặc None nếu không tồn tại.

        Raises:
            RuntimeError: nếu thao tác DB thất bại.
        """
        try:
            return self.db.get_member(member_id)
        except Exception as exc:
            raise RuntimeError(f"Không thể tải hội viên #{member_id}: {exc}") from exc

    def search_members(self, query: str) -> list[dict]:
        """
        Tìm kiếm hội viên theo tên, số điện thoại hoặc email.

        Nếu query rỗng → trả về toàn bộ danh sách (tương đương get_members).

        Args:
            query: Chuỗi tìm kiếm (không phân biệt hoa/thường, hỗ trợ LIKE).
        Returns:
            list[dict] danh sách hội viên khớp.
        Raises:
            RuntimeError: nếu thao tác DB thất bại.
        """
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

    def add_member(
        self,
        name: str,
        phone: str,
        email: str,
        gender: str,
    ) -> int:
        """
        Kiểm tra dữ liệu đầu vào rồi gọi db.add_member().

        Returns:
            ID tự động của hội viên vừa tạo.
        Raises:
            ValueError:   dữ liệu không hợp lệ hoặc trùng phone/email.
            RuntimeError: lỗi DB không xác định.
        """
        name   = name.strip()
        phone  = phone.strip()
        email  = email.strip()
        gender = gender.strip()

        self._validate(name, email)

        try:
            # qr_code=None → NULL trong SQLite, tránh lỗi UNIQUE khi chưa có QR
            return self.db.add_member(name, phone, email, gender, qr_code=None)
        except sqlite3.IntegrityError as exc:
            raise ValueError(self._integrity_msg(exc)) from exc
        except Exception as exc:
            raise RuntimeError(f"Không thể thêm hội viên: {exc}") from exc

    # ------------------------------------------------------------------ #
    #  Cập nhật                                                            #
    # ------------------------------------------------------------------ #

    def update_member(
        self,
        member_id: int,
        name: str,
        phone: str,
        email: str,
        gender: str,
        join_date: str = "",
    ) -> bool:
        """
        Kiểm tra dữ liệu đầu vào rồi gọi db.update_member().

        Tham số join_date được truyền qua để database không ghi đè bằng
        chuỗi rỗng — luôn truyền giá trị gốc từ bản ghi hiện tại.

        Returns:
            True nếu cập nhật thành công; False nếu không tìm thấy id.
        Raises:
            ValueError:   dữ liệu không hợp lệ hoặc trùng phone/email.
            RuntimeError: lỗi DB không xác định.
        """
        name   = name.strip()
        phone  = phone.strip()
        email  = email.strip()
        gender = gender.strip()

        self._validate(name, email)

        try:
            # Lấy qr_code gốc để không vô tình xóa mã QR đã có
            existing = self.db.get_member(member_id)
            qr_code  = existing.get("qr_code") if existing else None

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
        """
        Xóa hội viên theo khóa chính.

        Returns:
            True nếu xóa thành công; False nếu không tìm thấy id.
        Raises:
            RuntimeError: lỗi DB không xác định.
        """
        try:
            return self.db.delete_member(member_id)
        except Exception as exc:
            raise RuntimeError(
                f"Không thể xóa hội viên #{member_id}: {exc}"
            ) from exc