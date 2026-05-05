"""
controllers/dashboard_controller.py  —  Phase Chart

Cung cấp thống kê dashboard cho gym management:
  • get_today_stats()           → tổng check-in + số người hôm nay
  • get_month_stats()           → tổng check-in + số người tháng này
  • get_active_members()        → số hội viên đang có gói active
  • get_top_members()           → top N hội viên đi tập nhiều nhất tháng (tính theo ngày)
  • get_member_history()        → lịch sử check-in của 1 hội viên
  • get_checkin_status_stats()  → thống kê valid/expired tháng này (cho Pie Chart)
"""

from __future__ import annotations

from datetime import date

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