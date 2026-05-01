"""
controllers/member_controller.py

Tầng trung gian giữa giao diện (UI) và cơ sở dữ liệu.
Sử dụng CLASS Database — không có SQL thô, không gọi sqlite3 trực tiếp ở đây.

Cách dùng (khớp với database.py của bạn):
    from database import Database
    db = Database()
    db.get_members() / db.add_member() / db.update_member() / db.delete_member()
"""

from __future__ import annotations

from database import Database


class MemberController:
    """
    Tầng dịch vụ mỏng bọc ngoài Database, bổ sung kiểm tra dữ liệu đầu vào.

    Một instance Database duy nhất được tạo khi khởi tạo và tái sử dụng
    trong suốt vòng đời của controller (và toàn bộ ứng dụng).
    """

    def __init__(self) -> None:
        # Một instance Database dùng chung — toàn bộ CRUD đều qua self.db
        self.db = Database()

    # ------------------------------------------------------------------ #
    #  Đọc dữ liệu                                                         #
    # ------------------------------------------------------------------ #

    def get_members(self) -> list[dict]:
        """
        Trả về danh sách tất cả hội viên dưới dạng list[dict].

        Mỗi dict chứa: id, name, phone, email, gender, join_date

        Raises:
            RuntimeError: nếu thao tác cơ sở dữ liệu thất bại.
        """
        try:
            return self.db.get_members()
        except Exception as exc:
            raise RuntimeError(f"Không thể tải danh sách hội viên: {exc}") from exc

    def get_member_by_id(self, member_id: int) -> dict | None:
        """
        Trả về dict của một hội viên theo khóa chính, hoặc None nếu không tìm thấy.

        Raises:
            RuntimeError: nếu thao tác cơ sở dữ liệu thất bại.
        """
        try:
            return self.db.get_member_by_id(member_id)
        except Exception as exc:
            raise RuntimeError(f"Không thể tải hội viên #{member_id}: {exc}") from exc

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
        Kiểm tra dữ liệu đầu vào, sau đó gọi db.add_member().

        Returns:
            ID tự động của hội viên vừa tạo.
        Raises:
            ValueError:   khi dữ liệu không hợp lệ (hiển thị cho người dùng qua dialog).
            RuntimeError: khi thao tác cơ sở dữ liệu thất bại.
        """
        name, phone, email, gender = (
            name.strip(), phone.strip(), email.strip(), gender.strip()
        )

        if not name:
            raise ValueError("Họ tên không được để trống.")
        if len(name) > 120:
            raise ValueError("Họ tên không được vượt quá 120 ký tự.")
        if email and "@" not in email:
            raise ValueError("Vui lòng nhập địa chỉ email hợp lệ.")

        try:
            return self.db.add_member(name, phone, email, gender)
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
    ) -> bool:
        """
        Kiểm tra dữ liệu đầu vào, sau đó gọi db.update_member().

        Returns:
            True nếu bản ghi được cập nhật; False nếu không tìm thấy id.
        Raises:
            ValueError:   khi dữ liệu không hợp lệ.
            RuntimeError: khi thao tác cơ sở dữ liệu thất bại.
        """
        name, phone, email, gender = (
            name.strip(), phone.strip(), email.strip(), gender.strip()
        )

        if not name:
            raise ValueError("Họ tên không được để trống.")
        if len(name) > 120:
            raise ValueError("Họ tên không được vượt quá 120 ký tự.")
        if email and "@" not in email:
            raise ValueError("Vui lòng nhập địa chỉ email hợp lệ.")

        try:
            return self.db.update_member(member_id, name, phone, email, gender)
        except Exception as exc:
            raise RuntimeError(f"Không thể cập nhật hội viên #{member_id}: {exc}") from exc

    # ------------------------------------------------------------------ #
    #  Xóa                                                                 #
    # ------------------------------------------------------------------ #

    def delete_member(self, member_id: int) -> bool:
        """
        Gọi db.delete_member() theo khóa chính.

        Returns:
            True nếu bản ghi bị xóa; False nếu không tìm thấy id.
        Raises:
            RuntimeError: khi thao tác cơ sở dữ liệu thất bại.
        """
        try:
            return self.db.delete_member(member_id)
        except Exception as exc:
            raise RuntimeError(f"Không thể xóa hội viên #{member_id}: {exc}") from exc