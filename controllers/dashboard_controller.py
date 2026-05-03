"""
controllers/dashboard_controller.py  —  Phase 8

Cung cấp thống kê dashboard cho gym management:
  • get_today_stats()     → tổng check-in + số người hôm nay
  • get_month_stats()     → tổng check-in + số người tháng này
  • get_active_members()  → số hội viên đang có gói active
  • get_top_members()     → top N hội viên đi tập nhiều nhất tháng (tính theo ngày)
  • get_member_history()  → lịch sử check-in của 1 hội viên
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
        today = date.today().isoformat()
        prefix = f"{today}%"

        total_row = self._db._execute(
            """
            SELECT COUNT(*) AS cnt
            FROM   checkins
            WHERE  checkin_time LIKE ?
              AND  status = 'valid'
            """,
            (prefix,),
            fetch="one",
        )

        unique_row = self._db._execute(
            """
            SELECT COUNT(DISTINCT member_id) AS cnt
            FROM   checkins
            WHERE  checkin_time LIKE ?
              AND  status = 'valid'
            """,
            (prefix,),
            fetch="one",
        )

        detail = self._db._execute(
            """
            SELECT c.member_id,
                   m.name   AS member_name,
                   COUNT(*) AS count
            FROM   checkins c
            JOIN   members  m ON m.id = c.member_id
            WHERE  c.checkin_time LIKE ?
              AND  c.status = 'valid'
            GROUP BY c.member_id
            ORDER BY count DESC, m.name
            """,
            (prefix,),
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
        prefix = f"{today.year}-{today.month:02d}%"

        total_row = self._db._execute(
            """
            SELECT COUNT(*) AS cnt
            FROM   checkins
            WHERE  checkin_time LIKE ?
              AND  status = 'valid'
            """,
            (prefix,),
            fetch="one",
        )

        unique_row = self._db._execute(
            """
            SELECT COUNT(DISTINCT member_id) AS cnt
            FROM   checkins
            WHERE  checkin_time LIKE ?
              AND  status = 'valid'
            """,
            (prefix,),
            fetch="one",
        )

        detail = self._db._execute(
            """
            SELECT c.member_id,
                   m.name   AS member_name,
                   COUNT(*) AS count
            FROM   checkins c
            JOIN   members  m ON m.id = c.member_id
            WHERE  c.checkin_time LIKE ?
              AND  c.status = 'valid'
            GROUP BY c.member_id
            ORDER BY count DESC, m.name
            """,
            (prefix,),
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
        prefix = f"{today.year}-{today.month:02d}%"

        rows = self._db._execute(
            """
            SELECT c.member_id,
                   m.name AS member_name,
                   COUNT(DISTINCT date(c.checkin_time)) AS days_count
            FROM   checkins c
            JOIN   members  m ON m.id = c.member_id
            WHERE  c.checkin_time LIKE ?
              AND  c.status = 'valid'
            GROUP BY c.member_id
            ORDER BY days_count DESC, m.name
            LIMIT  ?
            """,
            (prefix, limit),
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