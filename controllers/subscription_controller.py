"""
controllers/subscription_controller.py  —  Phase 9

Thay đổi so với Phase 7:
  • XÓA method checkin() — đã chuyển sang CheckinController
  • Các method còn lại giữ nguyên
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


class SubscriptionController:

    def __init__(self) -> None:
        self._db = Database()

    # ── Dữ liệu tĩnh cho UI ─────────────────────────────────────────── #

    @staticmethod
    # Lấy danh sách các gói tập để hiển thị trong UI
    def get_plans() -> list[dict]:
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
        cfg           = PLAN_CONFIG[plan_type]
        price_monthly = PRICE_PER_MONTH[customer_type]
        price         = cfg["paid"] * price_monthly
        total_months  = cfg["paid"] + cfg["bonus"]
        start         = date.today()
        end           = start + timedelta(days=total_months * 30)
        return {
            "price":           price,
            "price_per_month": price_monthly,
            "paid_months":     cfg["paid"],
            "bonus_months":    cfg["bonus"],
            "total_months":    total_months,
            "start_date":      start.isoformat(),
            "end_date":        end.isoformat(),
        }

    # ── Helpers nội bộ ──────────────────────────────────────────────── #

    # Lấy plan_id từ database hoặc tạo mới nếu chưa có
    def _get_or_create_plan(self, plan_type: str, customer_type: str) -> int:
        cfg          = PLAN_CONFIG[plan_type] # Lấy cấu hình gói
        ctype_label  = CUSTOMER_TYPE_LABEL[customer_type] # Lấy nhãn loại khách
        plan_name    = f"{cfg['label']} — {ctype_label}"
        price        = cfg["paid"] * PRICE_PER_MONTH[customer_type] # Lấy giá theo tháng
        total_months = cfg["paid"] + cfg["bonus"]
        duration_days = total_months * 30

        existing = self._db.get_plan_by_name(plan_name)
        if existing:
            return existing["id"] # Nếu đã có plan với tên này thì trả về id của nó

        return self._db._execute(
            "INSERT INTO plans (name, duration, price) VALUES (?, ?, ?)",
            (plan_name, duration_days, price),
        )

    def _duration_days(self, plan_type: str) -> int:
        cfg = PLAN_CONFIG[plan_type]
        return (cfg["paid"] + cfg["bonus"]) * 30

    # ── Public API ──────────────────────────────────────────────────── #

    def create_subscription(
        self,
        member_id: int,
        plan_type: str,
        customer_type: str,
    ) -> int:
        """
        Tạo gói mới hoặc gia hạn nếu đã có gói active.
        """
        if plan_type not in PLAN_CONFIG:
            raise ValueError(f"Loại gói không hợp lệ: {plan_type!r}")
        if customer_type not in PRICE_PER_MONTH:
            raise ValueError(f"Loại khách không hợp lệ: {customer_type!r}")
        if not member_id:
            raise ValueError("Chưa chọn hội viên.")

        try:
            active = self._db.get_active_subscription(member_id)
            plan_id = self._get_or_create_plan(plan_type, customer_type)

            if active:
                # FIX LỖI: Thay vì UPDATE bản ghi cũ, tạo hẳn một bản ghi mới để dashboard ghi nhận doanh thu
                extra_days = self._duration_days(plan_type)
                old_end    = date.fromisoformat(active["end_date"])
                new_end    = old_end + timedelta(days=extra_days)
                today_str  = date.today().isoformat()
                
                return self._db.add_subscription(
                    member_id=member_id,
                    plan_id=plan_id,
                    start_date=today_str,
                    end_date=new_end.isoformat(),
                    status="active"
                )
            else:
                return self._db.add_subscription(member_id, plan_id)

        except sqlite3.Error as exc:
            raise RuntimeError(f"Lỗi khi lưu gói đăng ký: {exc}") from exc

    # Gia hạn gói tập hiện tại của hội viên
    def extend_subscription(
        self,
        member_id: int,
        plan_type: str,
        customer_type: str,
    ) -> int:
        """Gia hạn tường minh gói active của hội viên."""
        if plan_type not in PLAN_CONFIG:
            raise ValueError(f"Loại gói không hợp lệ: {plan_type!r}")
        if customer_type not in PRICE_PER_MONTH:
            raise ValueError(f"Loại khách không hợp lệ: {customer_type!r}")

        active = self._db.get_active_subscription(member_id)
        if not active:
            raise ValueError(
                "Hội viên chưa có gói đang hiệu lực.\n"
                "Vui lòng đăng ký gói mới thay vì gia hạn."
            )

        try:
            # FIX LỖI: Tạo một bản ghi gia hạn mới với start_date là ngày hôm nay để ghi nhận tiền vào tháng này
            plan_id = self._get_or_create_plan(plan_type, customer_type)
            extra_days = self._duration_days(plan_type)
            old_end    = date.fromisoformat(active["end_date"])
            new_end    = old_end + timedelta(days=extra_days)
            today_str  = date.today().isoformat()
            
            return self._db.add_subscription(
                member_id=member_id,
                plan_id=plan_id,
                start_date=today_str,
                end_date=new_end.isoformat(),
                status="active"
            )
        except sqlite3.Error as exc:
            raise RuntimeError(f"Lỗi khi gia hạn gói: {exc}") from exc


    # Hủy gói tập hiện tại của hội viên
    def cancel_subscription(self, subscription_id: int) -> bool:
        """Huỷ gói theo subscription_id."""
        try:
            result = self._db.cancel_subscription(subscription_id) # Gọi tới database để huỷ gói
            if not result:
                raise ValueError("Không tìm thấy gói đăng ký.")
            return True
        except sqlite3.Error as exc:
            raise RuntimeError(f"Lỗi khi huỷ gói: {exc}") from exc
        
    # Lấy danh sách gói tập của hội viên
    def get_member_subscriptions(self, member_id: int) -> list[dict]:
        self._db.expire_outdated_subscriptions()
        return self._db.get_subscriptions(member_id)

    def get_all_members(self) -> list[dict]:
        rows = self._db._execute(
            "SELECT id, name, phone FROM members ORDER BY name",
            fetch="all",
        )
        return rows or []