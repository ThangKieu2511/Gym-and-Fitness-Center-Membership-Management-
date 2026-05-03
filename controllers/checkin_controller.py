"""
controllers/checkin_controller.py  —  Phase 9

Tách toàn bộ logic check-in từ SubscriptionController ra đây.
SubscriptionController.checkin() đã bị xoá — gọi class này thay thế.
"""

from __future__ import annotations

from database import Database


class CheckinController:

    def __init__(self) -> None:
        self._db = Database()

    def checkin(self, member_id: int) -> dict:
        """
        Check-in thông minh — 3 trạng thái:

          • "valid"           → có gói active → lưu check-in vào DB
          • "expired"         → từng có gói nhưng đã hết hạn / bị huỷ
          • "no_subscription" → chưa bao giờ đăng ký gói nào

        Returns
        -------
        dict với keys:
            status     : "valid" | "expired" | "no_subscription"
            message    : Chuỗi thông báo hiển thị cho user
            checkin_id : ID bản ghi check-in vừa tạo (None nếu không valid)
        """
        # Tự expire các gói quá hạn trước khi kiểm tra
        self._db.expire_outdated_subscriptions()

        active = self._db.get_active_subscription(member_id)

        if active:
            checkin_id = self._db.add_checkin(member_id, status="valid")
            message = (
                f"✅  Check-in thành công!\n"
                f"Gói: {active['plan_name']}\n"
                f"Hết hạn: {active['end_date']}"
            )
            return {"status": "valid", "message": message, "checkin_id": checkin_id}

        # Phân biệt: đã từng có gói (expired) hay chưa bao giờ đăng ký
        has_any = self._db._execute(
            "SELECT id FROM subscriptions WHERE member_id = ? LIMIT 1",
            (member_id,),
            fetch="one",
        )

        if has_any:
            checkin_id = self._db.add_checkin(member_id, status="expired")
            message = "⚠️  Gói tập đã hết hạn.\nVui lòng gia hạn để tiếp tục tập."
            return {"status": "expired", "message": message, "checkin_id": checkin_id}
        else:
            checkin_id = self._db.add_checkin(member_id, status="no_subscription")
            message = "❌  Hội viên chưa đăng ký gói tập nào.\nVui lòng đăng ký gói mới."
            return {"status": "no_subscription", "message": message, "checkin_id": checkin_id}