"""
controllers/dashboard_controller.py  —  Phase Chart

Cung cấp thống kê dashboard cho gym management:
  • get_today_stats()              → tổng check-in + số người hôm nay
  • get_month_stats()              → tổng check-in + số người tháng này
  • get_active_members()           → số hội viên đang có gói active
  • get_top_members()              → top N hội viên đi tập nhiều nhất tháng (tính theo ngày)
  • get_member_history()           → lịch sử check-in của 1 hội viên
  • get_checkin_status_stats()     → thống kê valid/expired tháng này (cho Pie Chart)
  • get_month_revenue_detail()     → chi tiết doanh thu tháng này (cho xuất Excel)
  • get_expiring_members()         → hội viên sắp hết hạn trong N ngày tới (cho xuất Excel)
"""

from __future__ import annotations

from datetime import date, timedelta

from database import Database


class DashboardController:

    def __init__(self) -> None:
        self._db = Database()

    # ── Hôm nay ─────────────────────────────────────────────────────────── #

    def get_today_stats(self) -> dict:
        """
        Trả về thống kê check-in hôm nay (chỉ status='valid').

        Returns
        -------
        dict:
            total_checkins  : int  — tổng số lượt check-in
            unique_members  : int  — số hội viên distinct
            detail          : list[dict]  — mỗi member + số lần check-in
                              keys: member_id, member_name, count
        """
        today = date.today()
        start = f"{today} 00:00:00"
        end   = f"{today} 23:59:59"

        total_row = self._db._execute(
            """
            SELECT COUNT(*) AS cnt
            FROM   checkins
            WHERE  checkin_time BETWEEN ? AND ?
              AND  status = 'valid'
            """,
            (start, end),
            fetch="one",
        )

        unique_row = self._db._execute(
            """
            SELECT COUNT(DISTINCT member_id) AS cnt
            FROM   checkins
            WHERE  checkin_time BETWEEN ? AND ?
              AND  status = 'valid'
            """,
            (start, end),
            fetch="one",
        )

        detail = self._db._execute(
            """
            SELECT c.member_id,
                   m.name   AS member_name,
                   COUNT(*) AS count
            FROM   checkins c
            JOIN   members  m ON m.id = c.member_id
            WHERE  c.checkin_time BETWEEN ? AND ?
              AND  c.status = 'valid'
            GROUP BY c.member_id
            ORDER BY count DESC, m.name
            """,
            (start, end),
            fetch="all",
        )

        return {
            "total_checkins": total_row["cnt"] if total_row else 0,
            "unique_members": unique_row["cnt"] if unique_row else 0,
            "detail":         detail or [],
        }

    # ── Tháng hiện tại ──────────────────────────────────────────────────── #

    def get_month_stats(self) -> dict:
        """
        Trả về thống kê check-in tháng hiện tại (chỉ status='valid').

        Returns
        -------
        dict:
            total_checkins  : int
            unique_members  : int
            detail          : list[dict] — member_id, member_name, count
        """
        today = date.today()
        start = f"{today.year}-{today.month:02d}-01 00:00:00"

        if today.month == 12:
            next_month = f"{today.year + 1}-01-01 00:00:00"
        else:
            next_month = f"{today.year}-{today.month + 1:02d}-01 00:00:00"

        total_row = self._db._execute(
            """
            SELECT COUNT(*) AS cnt
            FROM   checkins
            WHERE  checkin_time >= ? AND checkin_time < ?
              AND  status = 'valid'
            """,
            (start, next_month),
            fetch="one",
        )

        unique_row = self._db._execute(
            """
            SELECT COUNT(DISTINCT member_id) AS cnt
            FROM   checkins
            WHERE  checkin_time BETWEEN ? AND ?
              AND  status = 'valid'
            """,
            (start, next_month),
            fetch="one",
        )

        detail = self._db._execute(
            """
            SELECT c.member_id,
                m.name   AS member_name,
                COUNT(DISTINCT date(c.checkin_time)) AS days_count,
                COUNT(*) AS total_checkins
            FROM   checkins c
            JOIN   members  m ON m.id = c.member_id
            WHERE  c.checkin_time >= ? AND c.checkin_time < ?
              AND  c.status = 'valid'
            GROUP BY c.member_id
            ORDER BY days_count DESC, total_checkins DESC
            """,
            (start, next_month),
            fetch="all",
        )

        return {
            "total_checkins": total_row["cnt"] if total_row else 0,
            "unique_members": unique_row["cnt"] if unique_row else 0,
            "detail":         detail or [],
        }

    # ── Hội viên active ─────────────────────────────────────────────────── #

    def get_active_members(self) -> int:
        """
        Trả về số hội viên đang có gói subscription active (end_date >= hôm nay).
        """
        today = date.today().isoformat()
        row = self._db._execute(
            """
            SELECT COUNT(DISTINCT member_id) AS cnt
            FROM   subscriptions
            WHERE  status   = 'active'
              AND  end_date >= ?
            """,
            (today,),
            fetch="one",
        )
        return row["cnt"] if row else 0

    # ── Top members ─────────────────────────────────────────────────────── #

    def get_top_members(self, limit: int = 5) -> list[dict]:
        """
        Top N hội viên đi tập nhiều nhất trong tháng hiện tại,
        tính theo số NGÀY đi tập distinct (status='valid').

        Returns
        -------
        list[dict]: member_id, member_name, days_count
        """
        today = date.today()
        start = f"{today.year}-{today.month:02d}-01 00:00:00"

        if today.month == 12:
            next_month = f"{today.year + 1}-01-01 00:00:00"
        else:
            next_month = f"{today.year}-{today.month + 1:02d}-01 00:00:00"

        rows = self._db._execute(
            """
            SELECT c.member_id,
                   m.name AS member_name,
                   COUNT(DISTINCT date(c.checkin_time)) AS days_count,
                   COUNT(*) AS total_checkins
            FROM   checkins c
            JOIN   members  m ON m.id = c.member_id
            WHERE  c.checkin_time >= ? AND c.checkin_time < ?
              AND  c.status = 'valid'
            GROUP BY c.member_id
            ORDER BY days_count DESC, total_checkins DESC
            LIMIT  ?
            """,
            (start, next_month, limit),
            fetch="all",
        )
        return rows or []

    # ── Lịch sử check-in của 1 hội viên ────────────────────────────────── #

    def get_member_history(self, member_id: int, limit: int = 200) -> list[dict]:
        """
        Lịch sử check-in của một hội viên, sắp xếp mới nhất trước.

        Returns
        -------
        list[dict]: id, member_id, member_name, checkin_time, status
        """
        rows = self._db._execute(
            """
            SELECT c.id,
                   c.member_id,
                   m.name   AS member_name,
                   c.checkin_time,
                   c.status
            FROM   checkins c
            JOIN   members  m ON m.id = c.member_id
            WHERE  c.member_id = ?
            ORDER BY c.checkin_time DESC
            LIMIT  ?
            """,
            (member_id, limit),
            fetch="all",
        )
        return rows or []

    # ── Danh sách tất cả hội viên (cho combobox) ────────────────────────── #

    def get_all_members(self) -> list[dict]:
        rows = self._db._execute(
            "SELECT id, name, phone FROM members ORDER BY name",
            fetch="all",
        )
        return rows or []

    # ── Doanh thu ───────────────────────────────────────────────────────── #

    def get_month_revenue(self) -> float:
        """Tổng doanh thu tháng hiện tại (tính theo start_date của subscription)."""
        return self._db.get_month_revenue()

    def get_year_revenue(self) -> float:
        """Tổng doanh thu cả năm hiện tại (tính theo start_date của subscription)."""
        return self._db.get_year_revenue()

    # ── Thống kê trạng thái check-in (cho Pie Chart) ───────────────────── #

    def get_checkin_status_stats(self) -> dict:
        """
        Thống kê số lượt check-in theo status trong tháng hiện tại.

        Returns
        -------
        dict:
            valid   : int  — số lượt check-in hợp lệ
            expired : int  — số lượt check-in hết hạn
        """
        today = date.today()
        start = f"{today.year}-{today.month:02d}-01 00:00:00"

        if today.month == 12:
            next_month = f"{today.year + 1}-01-01 00:00:00"
        else:
            next_month = f"{today.year}-{today.month + 1:02d}-01 00:00:00"

        rows = self._db._execute(
            """
            SELECT status, COUNT(*) AS cnt
            FROM   checkins
            WHERE  checkin_time >= ? AND checkin_time < ?
            GROUP BY status
            """,
            (start, next_month),
            fetch="all",
        )

        result = {"valid": 0, "expired": 0}
        for row in (rows or []):
            status = row.get("status", "")
            if status in result:
                result[status] = row["cnt"]

        return result

    # ── Xuất báo cáo Excel ──────────────────────────────────────────────── #

    def get_month_revenue_detail(self) -> list[dict]:
        """
        Chi tiết các gói tập đã đăng ký trong tháng hiện tại.
        Dùng cho Sheet 'Doanh Thu Tháng' khi xuất báo cáo Excel.

        Returns
        -------
        list[dict]:
            member_name  : str   — Họ tên hội viên
            plan_name    : str   — Loại gói tập
            price        : float — Giá tiền
            start_date   : str   — Ngày đăng ký
        """
        today = date.today()
        month_prefix = f"{today.year:04d}-{today.month:02d}"

        rows = self._db._execute(
            """
            SELECT m.name        AS member_name,
                   p.name        AS plan_name,
                   p.price       AS price,
                   s.start_date  AS start_date
            FROM   subscriptions s
            JOIN   members m ON m.id = s.member_id
            JOIN   plans   p ON p.id = s.plan_id
            WHERE  s.start_date LIKE ?
            ORDER BY s.start_date DESC, m.name
            """,
            (f"{month_prefix}%",),
            fetch="all",
        )
        return rows or []

    def get_expiring_members(self, days_ahead: int = 7) -> list[dict]:
        """
        Danh sách hội viên có gói active sắp hết hạn trong vòng N ngày tới.
        Dùng cho Sheet 'Hội Viên Sắp Hết Hạn' khi xuất báo cáo Excel.

        Parameters
        ----------
        days_ahead : int
            Số ngày tới để kiểm tra hết hạn (mặc định: 7).

        Returns
        -------
        list[dict]:
            member_name  : str — Họ tên hội viên
            phone        : str — Số điện thoại
            end_date     : str — Ngày hết hạn gói
            days_left    : int — Số ngày còn lại
        """
        today      = date.today()
        deadline   = today + timedelta(days=days_ahead)

        today_str    = today.isoformat()
        deadline_str = deadline.isoformat()

        rows = self._db._execute(
            """
            SELECT m.name     AS member_name,
                   m.phone    AS phone,
                   s.end_date AS end_date
            FROM   subscriptions s
            JOIN   members m ON m.id = s.member_id
            WHERE  s.status   = 'active'
              AND  s.end_date >= ?
              AND  s.end_date <= ?
            ORDER BY s.end_date ASC, m.name
            """,
            (today_str, deadline_str),
            fetch="all",
        )

        result = []
        for row in (rows or []):
            try:
                end_dt    = date.fromisoformat(row["end_date"])
                days_left = (end_dt - today).days
            except (ValueError, TypeError):
                days_left = 0
            result.append({
                "member_name": row["member_name"],
                "phone":       row["phone"] or "",
                "end_date":    row["end_date"],
                "days_left":   days_left,
            })

        return result