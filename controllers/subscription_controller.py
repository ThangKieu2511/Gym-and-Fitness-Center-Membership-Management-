"""
controllers/subscription_controller.py  —  Phase 5

Business logic cho Quản Lý Gói Tập & Đăng Ký Gói Hội Viên.

Nghiệp vụ:
  - Học sinh/Sinh viên: 180 000 đ/tháng
  - Người lớn:          200 000 đ/tháng

  Gói 1 tháng  → không tặng   (tổng 1 tháng)
  Gói 3 tháng  → tặng 1 tháng (tổng 4 tháng)
  Gói 6 tháng  → tặng 2 tháng (tổng 8 tháng)
  Gói 12 tháng → tặng 3 tháng (tổng 15 tháng)

  Giá = paid_months × đơn_giá_theo_loại_khách
  Thời gian = (paid + bonus) × 30 ngày
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from database import Database

# ── Đơn giá theo tháng ──────────────────────────────────────────────────── #

PRICE_PER_MONTH: dict[str, int] = {
    "student": 180_000,
    "adult":   200_000,
}

# ── Cấu hình gói ────────────────────────────────────────────────────────── #

PLAN_CONFIG: dict[str, dict] = {
    "1_month":  {"paid": 1,  "bonus": 0,  "label": "Gói 1 Tháng"},
    "3_month":  {"paid": 3,  "bonus": 1,  "label": "Gói 3 Tháng"},
    "6_month":  {"paid": 6,  "bonus": 2,  "label": "Gói 6 Tháng"},
    "12_month": {"paid": 12, "bonus": 3,  "label": "Gói 12 Tháng"},
}

CUSTOMER_TYPE_LABEL: dict[str, str] = {
    "student": "Học Sinh/Sinh Viên",
    "adult":   "Người Lớn",
}


# ══════════════════════════════════════════════════════════════════════════ #
#  SubscriptionController                                                    #
# ══════════════════════════════════════════════════════════════════════════ #

class SubscriptionController:
    """
    Cầu nối giữa UI đăng ký gói tập và tầng Database.

    Không viết SQL trực tiếp — sử dụng Database API và _execute() nội bộ
    chỉ cho trường hợp upsert bảng plans (không có sẵn trong public API).
    """

    def __init__(self) -> None:
        self._db = Database()

    # ── Dữ liệu tĩnh cho UI ─────────────────────────────────────────── #

    @staticmethod
    def get_plans() -> list[dict]:
        """
        Trả về danh sách tất cả 8 cấu hình gói (4 loại × 2 loại khách).
        Dùng để hiển thị tuỳ chọn trên UI, không cần truy cập DB.
        """
        result: list[dict] = []
        for plan_type, cfg in PLAN_CONFIG.items():
            total = cfg["paid"] + cfg["bonus"]
            for ctype, price_per_month in PRICE_PER_MONTH.items():
                result.append({
                    "plan_type":     plan_type,
                    "customer_type": ctype,
                    "paid_months":   cfg["paid"],
                    "bonus_months":  cfg["bonus"],
                    "total_months":  total,
                    "price":         cfg["paid"] * price_per_month,
                    "duration_days": total * 30,
                    "label":         cfg["label"],
                })
        return result

    @staticmethod
    def get_plan_preview(plan_type: str, customer_type: str) -> dict:
        """
        Tính xem trước thông tin gói: giá, ngày kết thúc.

        Parameters
        ----------
        plan_type     : "1_month" | "3_month" | "6_month" | "12_month"
        customer_type : "student" | "adult"

        Returns
        -------
        dict với các key:
            price, start_date, end_date, total_months,
            paid_months, bonus_months, price_per_month
        """
        cfg           = PLAN_CONFIG[plan_type]
        price_monthly = PRICE_PER_MONTH[customer_type]
        price         = cfg["paid"] * price_monthly
        total_months  = cfg["paid"] + cfg["bonus"]
        start         = date.today()
        end           = start + timedelta(days=total_months * 30)

        return {
            "price":         price,
            "price_per_month": price_monthly,
            "paid_months":   cfg["paid"],
            "bonus_months":  cfg["bonus"],
            "total_months":  total_months,
            "start_date":    start.isoformat(),
            "end_date":      end.isoformat(),
        }

    # ── Helpers nội bộ ──────────────────────────────────────────────── #

    def _get_or_create_plan(self, plan_type: str, customer_type: str) -> int:
        """
        Tìm hoặc tạo bản ghi plans trong DB theo (plan_type, customer_type).
        Trả về plan_id.
        """
        cfg         = PLAN_CONFIG[plan_type]
        ctype_label = CUSTOMER_TYPE_LABEL[customer_type]
        plan_name   = f"{cfg['label']} — {ctype_label}"
        price       = cfg["paid"] * PRICE_PER_MONTH[customer_type]
        total_months = cfg["paid"] + cfg["bonus"]
        duration_days = total_months * 30

        existing = self._db._execute(
            "SELECT id FROM plans WHERE name = ?",
            (plan_name,),
            fetch="one",
        )
        if existing:
            return existing["id"]

        # Tạo mới nếu chưa có
        return self._db._execute(
            "INSERT INTO plans (name, duration, price) VALUES (?, ?, ?)",
            (plan_name, duration_days, price),
        )

    # ── Public API ──────────────────────────────────────────────────── #

    def create_subscription(
        self,
        member_id: int,
        plan_type: str,
        customer_type: str,
    ) -> int:
        """
        Tạo và lưu gói đăng ký cho hội viên.

        Parameters
        ----------
        member_id     : ID hội viên
        plan_type     : "1_month" | "3_month" | "6_month" | "12_month"
        customer_type : "student" | "adult"

        Returns
        -------
        int — ID subscription vừa tạo

        Raises
        ------
        ValueError       — nếu tham số không hợp lệ
        RuntimeError     — nếu gặp lỗi DB
        """
        if plan_type not in PLAN_CONFIG:
            raise ValueError(f"Loại gói không hợp lệ: {plan_type!r}")
        if customer_type not in PRICE_PER_MONTH:
            raise ValueError(f"Loại khách không hợp lệ: {customer_type!r}")
        if not member_id:
            raise ValueError("Chưa chọn hội viên.")

        try:
            plan_id = self._get_or_create_plan(plan_type, customer_type)
            sub_id  = self._db.add_subscription(member_id, plan_id)
            return sub_id
        except sqlite3.Error as exc:
            raise RuntimeError(f"Lỗi khi lưu gói đăng ký: {exc}") from exc

    def get_member_subscriptions(self, member_id: int) -> list[dict]:
        """
        Trả về tất cả gói đã đăng ký của hội viên.
        Tự động cập nhật trạng thái expired trước khi trả về.
        """
        self._db.expire_outdated_subscriptions()
        return self._db.get_subscriptions(member_id)

    def get_all_members(self) -> list[dict]:
        """Trả về danh sách hội viên để hiển thị trong dropdown."""
        rows = self._db._execute(
            "SELECT id, name, phone FROM members ORDER BY name",
            fetch="all",
        )
        return rows or []