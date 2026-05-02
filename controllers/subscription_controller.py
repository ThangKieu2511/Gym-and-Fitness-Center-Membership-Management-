"""
controllers/subscription_controller.py  —  Phase 6

Thay đổi so với Phase 5:
  • create_subscription(): nếu có gói active → gia hạn (extend) end_date thay vì tạo mới
  • extend_subscription(): gia hạn gói active hiện tại, trả về sub_id
  • cancel_subscription(): huỷ gói theo subscription_id
  • checkin(): check-in thông minh — valid nếu có gói active, ngược lại expired
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

    def _get_or_create_plan(self, plan_type: str, customer_type: str) -> int:
        cfg          = PLAN_CONFIG[plan_type]
        ctype_label  = CUSTOMER_TYPE_LABEL[customer_type]
        plan_name    = f"{cfg['label']} — {ctype_label}"
        price        = cfg["paid"] * PRICE_PER_MONTH[customer_type]
        total_months = cfg["paid"] + cfg["bonus"]
        duration_days = total_months * 30

        existing = self._db.get_plan_by_name(plan_name)
        if existing:
            return existing["id"]

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

        - Có gói active  → extend end_date, KHÔNG tạo bản ghi mới
        - Chưa có gói    → tạo subscription mới bắt đầu từ hôm nay
        """
        if plan_type not in PLAN_CONFIG:
            raise ValueError(f"Loại gói không hợp lệ: {plan_type!r}")
        if customer_type not in PRICE_PER_MONTH:
            raise ValueError(f"Loại khách không hợp lệ: {customer_type!r}")
        if not member_id:
            raise ValueError("Chưa chọn hội viên.")

        try:
            active = self._db.get_active_subscription(member_id)

            if active:
                # ── Gia hạn: cộng thêm duration vào end_date hiện tại ──
                extra_days = self._duration_days(plan_type)
                old_end    = date.fromisoformat(active["end_date"])
                new_end    = old_end + timedelta(days=extra_days)
                self._db._execute(
                    "UPDATE subscriptions SET end_date = ? WHERE id = ?",
                    (new_end.isoformat(), active["id"]),
                )
                return active["id"]
            else:
                # ── Đăng ký mới ──
                plan_id = self._get_or_create_plan(plan_type, customer_type)
                return self._db.add_subscription(member_id, plan_id)

        except sqlite3.Error as exc:
            raise RuntimeError(f"Lỗi khi lưu gói đăng ký: {exc}") from exc

    def extend_subscription(
        self,
        member_id: int,
        plan_type: str,
        customer_type: str,
    ) -> int:
        """
        Gia hạn tường minh gói active của hội viên.
        Luôn cộng thêm duration vào end_date hiện tại (không tạo bản ghi mới).

        Raises ValueError nếu hội viên không có gói active.
        """
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
            extra_days = self._duration_days(plan_type)
            old_end    = date.fromisoformat(active["end_date"])
            new_end    = old_end + timedelta(days=extra_days)
            self._db._execute(
                "UPDATE subscriptions SET end_date = ? WHERE id = ?",
                (new_end.isoformat(), active["id"]),
            )
            return active["id"]
        except sqlite3.Error as exc:
            raise RuntimeError(f"Lỗi khi gia hạn gói: {exc}") from exc

    def cancel_subscription(self, subscription_id: int) -> bool:
        """
        Huỷ gói theo subscription_id. Trả về True nếu thành công.
        Raises ValueError nếu không tìm thấy sub hoặc gói đã bị huỷ/hết hạn.
        """
        try:
            result = self._db.cancel_subscription(subscription_id)
            if not result:
                raise ValueError("Không tìm thấy gói đăng ký.")
            return True
        except sqlite3.Error as exc:
            raise RuntimeError(f"Lỗi khi huỷ gói: {exc}") from exc

    def checkin(self, member_id: int) -> dict:
        """
        Check-in thông minh.

        Returns
        -------
        dict với keys:
            status  : "valid" | "expired"
            message : Chuỗi thông báo hiển thị cho user
            checkin_id : ID bản ghi check-in vừa tạo
        """
        active = self._db.get_active_subscription(member_id)
        status = "valid" if active else "expired"

        checkin_id = self._db.add_checkin(member_id, status=status)

        if status == "valid":
            message = (
                f"✅  Check-in thành công!\n"
                f"Gói: {active['plan_name']}\n"
                f"Hết hạn: {active['end_date']}"
            )
        else:
            message = "⚠️  Hội viên không có gói đang hiệu lực."

        return {"status": status, "message": message, "checkin_id": checkin_id}

    def get_member_subscriptions(self, member_id: int) -> list[dict]:
        self._db.expire_outdated_subscriptions()
        return self._db.get_subscriptions(member_id)

    def get_all_members(self) -> list[dict]:
        rows = self._db._execute(
            "SELECT id, name, phone FROM members ORDER BY name",
            fetch="all",
        )
        return rows or []