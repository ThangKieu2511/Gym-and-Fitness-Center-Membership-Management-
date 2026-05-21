import sqlite3
import bcrypt
import logging
from datetime import date, datetime
from typing import Optional
import os
import glob
# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("GymDB")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_dict(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain Python dict."""
    return dict(zip([col[0] for col in cursor.description], row))


def _rows_to_dicts(cursor: sqlite3.Cursor, rows: list) -> list[dict]:
    """Convert a list of sqlite3.Row objects to a list of dicts."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


# ---------------------------------------------------------------------------
# Database Class
# ---------------------------------------------------------------------------

class Database:
    """
    Central database manager for the Gym & Fitness Center Management System.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file.
        Defaults to ``"gym.db"`` in the current working directory.
    """

    DEFAULT_ADMIN_USERNAME = "admin"
    DEFAULT_ADMIN_PASSWORD = "123"       # ← đổi thành 123

    def __init__(self, db_path: str = "gym.db") -> None:
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self.connect()
        self.create_tables()
        self._migrate()
        self._seed_default_admin()
        self.backup_database()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open (or re-open) the SQLite connection with WAL journal mode."""
        try:
            self.connection = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False,
            )
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA journal_mode=WAL;")
            self.connection.execute("PRAGMA foreign_keys=ON;")
            logger.info("Connected to database: %s", self.db_path)
        except sqlite3.Error as exc:
            logger.exception("Failed to connect to database: %s", exc)
            raise

    def close(self) -> None:
        """Close the database connection gracefully."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed.")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ------------------------------------------------------------------
    # Schema creation
    # ------------------------------------------------------------------

    def create_tables(self) -> None:
        """Create all required tables if they do not already exist."""
        ddl_statements = [
            # ---- users ------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL
            )
            """,

            # ---- members ----------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS members (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                name      TEXT    NOT NULL,
                phone     TEXT UNIQUE,
                email     TEXT UNIQUE,
                gender    TEXT,
                join_date TEXT,
                qr_code   TEXT UNIQUE
            )
            """,

            # ---- plans ------------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS plans (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     TEXT    NOT NULL,
                duration INTEGER,
                price    REAL
            )
            """,

            # ---- subscriptions ----------------------------------------
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id  INTEGER NOT NULL,
                plan_id    INTEGER NOT NULL,
                start_date TEXT,
                end_date   TEXT,
                status     TEXT CHECK(status IN ('active', 'expired', 'cancelled')),
                FOREIGN KEY (member_id) REFERENCES members(id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (plan_id)   REFERENCES plans(id)
                    ON DELETE RESTRICT  ON UPDATE CASCADE
            )
            """,

            # ---- checkins ---------------------------------------------
            """
            CREATE TABLE IF NOT EXISTS checkins (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id    INTEGER NOT NULL,
                checkin_time TEXT,
                status TEXT CHECK(status IN ('valid', 'expired', 'no_subscription')),
                FOREIGN KEY (member_id) REFERENCES members(id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            )
            """,
        ]

        try:
            with self.connection:
                for stmt in ddl_statements:
                    self.connection.execute(stmt)

            self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_checkins_time ON checkins(checkin_time);"
            )
            logger.info("All tables verified / created successfully.")
        except sqlite3.Error as exc:
            logger.exception("Error creating tables: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Migration — chỉ ALTER TABLE nếu column chưa tồn tại
    # ------------------------------------------------------------------

    def _migrate(self) -> None:
        """Chạy migration tăng dần — an toàn, idempotent."""
        self._add_column_if_missing("members", "image_path", "TEXT")

    def _add_column_if_missing(self, table: str, column: str, col_type: str) -> None:
        """ALTER TABLE … ADD COLUMN nếu column chưa tồn tại."""
        try:
            cursor = self.connection.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cursor.fetchall()]
            if column not in cols:
                self.connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
                )
                self.connection.commit()
                logger.info("Migration: added column '%s' to table '%s'.", column, table)
            else:
                logger.debug("Migration: column '%s.%s' already exists.", table, column)
        except sqlite3.Error as exc:
            logger.exception("Migration error for %s.%s: %s", table, column, exc)
            raise

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    def _execute(
        self,
        sql: str,
        params: tuple = (),
        *,
        fetch: str = "none",
    ):
        try:
            with self.connection:
                cursor = self.connection.execute(sql, params)
                if fetch == "one":
                    row = cursor.fetchone()
                    return _row_to_dict(cursor, row) if row else None
                if fetch == "all":
                    rows = cursor.fetchall()
                    return _rows_to_dicts(cursor, rows)
                return cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            logger.warning("Integrity error: %s | SQL: %s | params: %s", exc, sql, params)
            raise
        except sqlite3.Error as exc:
            logger.exception("Database error: %s | SQL: %s", exc, sql)
            raise

    # ==================================================================
    # USERS
    # ==================================================================

    def create_user(self, username: str, password: str) -> int:
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        row_id = self._execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        logger.info("User created: '%s' (id=%s)", username, row_id)
        return row_id

    def get_user(self, username: str) -> Optional[dict]:
        """Fetch a single user record by username."""
        return self._execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
            fetch="one",
        )

    def verify_user(self, username: str, password: str) -> bool:
        user = self.get_user(username)
        if not user:
            logger.warning("Login attempt for unknown user: '%s'", username)
            return False
        is_valid = bcrypt.checkpw(
            password.encode("utf-8"),
            user["password_hash"].encode("utf-8"),
        )
        logger.info("Login attempt for '%s': %s", username, "OK" if is_valid else "FAILED")
        return is_valid

    def _seed_default_admin(self) -> None:
        """Insert the default admin account if it does not already exist."""
        if not self.get_user(self.DEFAULT_ADMIN_USERNAME):
            self.create_user(self.DEFAULT_ADMIN_USERNAME, self.DEFAULT_ADMIN_PASSWORD)
            logger.info("Default admin account created (username=admin, password=123).")
        else:
            logger.debug("Default admin account already exists — skipping seed.")

    # ==================================================================
    # MEMBERS
    # ==================================================================

    def add_member(
        self,
        name: str,
        phone: str = "",
        email: str = "",
        gender: str = "",
        join_date: str = "",
        qr_code: str = "",
        image_path: str = "",
    ) -> int:
        if not join_date:
            join_date = date.today().isoformat()

        row_id = self._execute(
            """
            INSERT INTO members (name, phone, email, gender, join_date, qr_code, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, phone or None, email or None, gender, join_date, qr_code or None, image_path or None),
        )
        logger.info("Member added: '%s' (id=%s)", name, row_id)
        return row_id

    def get_member(self, member_id: int) -> Optional[dict]:
        return self._execute(
            "SELECT * FROM members WHERE id = ?",
            (member_id,),
            fetch="one",
        )

    def get_member_by_qr(self, qr_code: str) -> Optional[dict]:
        return self._execute(
            "SELECT * FROM members WHERE qr_code = ?",
            (qr_code,),
            fetch="one",
        )

    def get_all_members(self) -> list[dict]:
        return self._execute(
            "SELECT * FROM members ORDER BY name",
            fetch="all",
        )
    
    def get_members(self, query: str = "") -> list[dict]:
        """
        Hàm dự phòng để sửa lỗi UI gọi get_members().
        Nếu có query thì tìm kiếm, không thì trả về tất cả.
        """
        if query:
            return self.search_members(query)
        return self.get_all_members()

    def search_members(self, query: str) -> list[dict]:
        pattern = f"%{query}%"
        return self._execute(
            """
            SELECT * FROM members
            WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?
            ORDER BY name
            """,
            (pattern, pattern, pattern),
            fetch="all",
        )

    def update_member(
        self,
        member_id: int,
        name: str,
        phone: str = "",
        email: str = "",
        gender: str = "",
        join_date: str = "",
        image_path: str = "",
        qr_code: str = "",
    ) -> bool:
        try:
            with self.connection:
                cursor = self.connection.execute(
                    """
                    UPDATE members
                    SET name=?, phone=?, email=?, gender=?, join_date=?, image_path=?, qr_code=?
                    WHERE id=?
                    """,
                    (name, phone or None, email or None, gender, join_date, image_path or None, qr_code or None, member_id),
                )
                updated = cursor.rowcount > 0
            if updated:
                logger.info("Member updated: id=%s name='%s'", member_id, name)
            return updated
        except sqlite3.Error as exc:
            logger.exception("Error updating member id=%s: %s", member_id, exc)
            raise

    def delete_member(self, member_id: int) -> bool:
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "DELETE FROM members WHERE id=?", (member_id,)
                )
                deleted = cursor.rowcount > 0
            if deleted:
                logger.info("Member deleted: id=%s", member_id)
            return deleted
        except sqlite3.Error as exc:
            logger.exception("Error deleting member id=%s: %s", member_id, exc)
            raise

    def update_member_qr(self, member_id: int, qr_code: str) -> bool:
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "UPDATE members SET qr_code=? WHERE id=?",
                    (qr_code, member_id),
                )
                updated = cursor.rowcount > 0
            if updated:
                logger.info("QR code updated for member id=%s", member_id)
            return updated
        except sqlite3.Error as exc:
            logger.exception("Error updating QR for member id=%s: %s", member_id, exc)
            raise

    def update_member_image(self, member_id: int, image_path: str) -> bool:
        """Cập nhật đường dẫn ảnh của hội viên."""
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "UPDATE members SET image_path=? WHERE id=?",
                    (image_path or None, member_id),
                )
                updated = cursor.rowcount > 0
            if updated:
                logger.info("Image path updated for member id=%s -> %s", member_id, image_path)
            return updated
        except sqlite3.Error as exc:
            logger.exception("Error updating image for member id=%s: %s", member_id, exc)
            raise

    # ==================================================================
    # PLANS
    # ==================================================================

    def add_plan(self, name: str, duration: int = 30, price: float = 0.0) -> int:
        row_id = self._execute(
            "INSERT INTO plans (name, duration, price) VALUES (?, ?, ?)",
            (name, duration, price),
        )
        logger.info("Plan added: '%s' duration=%d price=%.2f (id=%s)", name, duration, price, row_id)
        return row_id

    def get_plan(self, plan_id: int) -> Optional[dict]:
        return self._execute(
            "SELECT * FROM plans WHERE id = ?",
            (plan_id,),
            fetch="one",
        )

    def get_all_plans(self) -> list[dict]:
        return self._execute(
            "SELECT * FROM plans ORDER BY name",
            fetch="all",
        )

    def get_plan_by_name(self, name: str) -> Optional[dict]:
        """Lấy plan theo tên (dùng bởi SubscriptionController để tránh trùng lặp)."""
        return self._execute(
            "SELECT * FROM plans WHERE name = ? LIMIT 1",
            (name,),
            fetch="one",
        )

    def update_plan(self, plan_id: int, name: str, duration: int, price: float) -> bool:
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "UPDATE plans SET name=?, duration=?, price=? WHERE id=?",
                    (name, duration, price, plan_id),
                )
                updated = cursor.rowcount > 0
            if updated:
                logger.info("Plan updated: id=%s", plan_id)
            return updated
        except sqlite3.Error as exc:
            logger.exception("Error updating plan id=%s: %s", plan_id, exc)
            raise

    def delete_plan(self, plan_id: int) -> bool:
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "DELETE FROM plans WHERE id=?", (plan_id,)
                )
                deleted = cursor.rowcount > 0
            if deleted:
                logger.info("Plan deleted: id=%s", plan_id)
            return deleted
        except sqlite3.Error as exc:
            logger.exception("Error deleting plan id=%s: %s", plan_id, exc)
            raise

    # ==================================================================
    # SUBSCRIPTIONS
    # ==================================================================

    def add_subscription(
        self,
        member_id: int,
        plan_id: int,
        start_date: str = "",
        end_date: str = "",
        status: str = "active",
    ) -> int:
        from datetime import timedelta

        if not start_date:
            start_date = date.today().isoformat()

        if not end_date:
            plan = self.get_plan(plan_id)
            if plan and plan.get("duration"):
                start_dt = date.fromisoformat(start_date)
                end_date = (start_dt + timedelta(days=plan["duration"])).isoformat()

        row_id = self._execute(
            """
            INSERT INTO subscriptions (member_id, plan_id, start_date, end_date, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (member_id, plan_id, start_date, end_date, status),
        )
        logger.info(
            "Subscription added: member_id=%s plan_id=%s [%s → %s] status=%s (id=%s)",
            member_id, plan_id, start_date, end_date, status, row_id,
        )
        return row_id

    def get_subscriptions(self, member_id: int) -> list[dict]:
        return self._execute(
            """
            SELECT s.*, p.name AS plan_name, p.price, p.duration
            FROM   subscriptions s
            JOIN   plans p ON p.id = s.plan_id
            WHERE  s.member_id = ?
            ORDER BY s.start_date DESC
            """,
            (member_id,),
            fetch="all",
        )

    def get_active_subscription(self, member_id: int) -> Optional[dict]:
        today = date.today().isoformat()
        return self._execute(
            """
            SELECT s.*, p.name AS plan_name, p.price, p.duration
            FROM   subscriptions s
            JOIN   plans p ON p.id = s.plan_id
            WHERE  s.member_id = ?
              AND  s.status    = 'active'
              AND  s.end_date >= ?
            ORDER BY s.end_date DESC
            LIMIT 1
            """,
            (member_id, today),
            fetch="one",
        )

    def expire_outdated_subscriptions(self) -> int:
        today = date.today().isoformat()
        try:
            with self.connection:
                cursor = self.connection.execute(
                    """
                    UPDATE subscriptions
                    SET    status = 'expired'
                    WHERE  status = 'active'
                      AND  end_date < ?
                    """,
                    (today,),
                )
                count = cursor.rowcount
            if count:
                logger.info("Expired %d outdated subscription(s).", count)
            return count
        except sqlite3.Error as exc:
            logger.exception("Error expiring subscriptions: %s", exc)
            raise

    def cancel_subscription(self, subscription_id: int) -> bool:
        """Set a subscription's status to ``'cancelled'``."""
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "UPDATE subscriptions SET status='cancelled' WHERE id=?",
                    (subscription_id,),
                )
                updated = cursor.rowcount > 0
            if updated:
                logger.info("Subscription cancelled: id=%s", subscription_id)
            return updated
        except sqlite3.Error as exc:
            logger.exception("Error cancelling subscription id=%s: %s", subscription_id, exc)
            raise

    # ==================================================================
    # CHECK-INS
    # ==================================================================

    def add_checkin(
        self,
        member_id: int,
        checkin_time: str = "",
        status: str = "valid",
    ) -> int:

        if not checkin_time:
            checkin_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row_id = self._execute(
            "INSERT INTO checkins (member_id, checkin_time, status) VALUES (?, ?, ?)",
            (member_id, checkin_time, status),
        )
        logger.info(
            "Check-in recorded: member_id=%s at %s (id=%s)", member_id, checkin_time, row_id
        )
        return row_id

    def get_checkins(
        self,
        member_id: Optional[int] = None,
        limit: int = 100,
    ) -> list[dict]:
        if member_id is not None:
            return self._execute(
                """
                SELECT c.*, m.name AS member_name
                FROM   checkins c
                JOIN   members  m ON m.id = c.member_id
                WHERE  c.member_id = ?
                ORDER BY c.checkin_time DESC
                LIMIT  ?
                """,
                (member_id, limit),
                fetch="all",
            )
        return self._execute(
            """
            SELECT c.*, m.name AS member_name
            FROM   checkins c
            JOIN   members  m ON m.id = c.member_id
            ORDER BY c.checkin_time DESC
            LIMIT  ?
            """,
            (limit,),
            fetch="all",
        )

    def get_today_checkins(self) -> list[dict]:
        """Return all check-ins that occurred today (local date)."""
        today = date.today().isoformat()
        start = f"{today} 00:00:00"
        end   = f"{today} 23:59:59"
        return self._execute(
            """
            SELECT c.*, m.name AS member_name
            FROM   checkins c
            JOIN   members  m ON m.id = c.member_id
            WHERE  c.checkin_time BETWEEN ? AND ?
            ORDER BY c.checkin_time DESC
            """,
            (start, end),
            fetch="all",
        )

    # ==================================================================
    # DASHBOARD STATISTICS
    # ==================================================================

    def get_stats(self) -> dict:
        today = date.today().isoformat()

        total_members = self._execute(
            "SELECT COUNT(*) AS cnt FROM members", fetch="one"
        )["cnt"]

        active_subs = self._execute(
            """
            SELECT COUNT(*) AS cnt
            FROM   subscriptions
            WHERE  status   = 'active'
              AND  end_date >= ?
            """,
            (today,),
            fetch="one",
        )["cnt"]

        start = f"{today} 00:00:00"
        end   = f"{today} 23:59:59"

        checkins_today = self._execute(
            "SELECT COUNT(*) AS cnt FROM checkins WHERE checkin_time BETWEEN ? AND ?",
            (start, end),
            fetch="one",
        )["cnt"]

        revenue_row = self._execute(
            """
            SELECT COALESCE(SUM(p.price), 0.0) AS total
            FROM   subscriptions s
            JOIN   plans p ON p.id = s.plan_id
            """,
            fetch="one",
        )
        total_revenue = revenue_row["total"] if revenue_row else 0.0

        return {
            "total_members":        total_members,
            "active_subscriptions": active_subs,
            "checkins_today":       checkins_today,
            "total_revenue":        total_revenue,
        }

    def get_month_revenue(self, year: int | None = None, month: int | None = None) -> float:
        """Tổng doanh thu từ các gói đăng ký có start_date trong tháng chỉ định."""
        today = date.today()
        y = year  if year  is not None else today.year
        m = month if month is not None else today.month
        month_prefix = f"{y:04d}-{m:02d}"
        row = self._execute(
            """
            SELECT COALESCE(SUM(p.price), 0.0) AS total
            FROM   subscriptions s
            JOIN   plans p ON p.id = s.plan_id
            WHERE  s.start_date LIKE ?
            """,
            (f"{month_prefix}%",),
            fetch="one",
        )
        return float(row["total"]) if row else 0.0

    def get_year_revenue(self, year: int | None = None) -> float:
        """Tổng doanh thu từ các gói đăng ký có start_date trong năm chỉ định."""
        today = date.today()
        y = year if year is not None else today.year
        year_prefix = f"{y:04d}"
        row = self._execute(
            """
            SELECT COALESCE(SUM(p.price), 0.0) AS total
            FROM   subscriptions s
            JOIN   plans p ON p.id = s.plan_id
            WHERE  s.start_date LIKE ?
            """,
            (f"{year_prefix}%",),
            fetch="one",
        )
        return float(row["total"]) if row else 0.0
    
    # ------------------------------------------------------------------
    # Backup management
    # ------------------------------------------------------------------

    def backup_database(self, backup_dir: str = "backups", keep_last: int = 7) -> None:
        """
        Tự động sao lưu database an toàn sử dụng SQLite Backup API.
        Giữ lại tối đa `keep_last` bản sao lưu gần nhất.
        """
        if not self.connection:
            logger.warning("Không có kết nối DB để backup.")
            return

        try:
            # 1. Đảm bảo thư mục backups tồn tại
            os.makedirs(backup_dir, exist_ok=True)
            
            # 2. Tạo tên file theo thời gian thực (VD: gym_backup_20260521_215508.db)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"gym_backup_{timestamp}.db")

            # 3. Sử dụng API backup chuẩn của SQLite (An toàn, không bị lock DB)
            bck_conn = sqlite3.connect(backup_file)
            with bck_conn:
                self.connection.backup(bck_conn)
            bck_conn.close()

            logger.info("✅ Đã sao lưu database an toàn: %s", backup_file)

            # 4. Dọn dẹp các bản backup cũ (Chỉ giữ lại keep_last bản)
            list_of_files = glob.glob(os.path.join(backup_dir, "gym_backup_*.db"))
            list_of_files.sort(key=os.path.getctime) # Sắp xếp file từ cũ đến mới

            while len(list_of_files) > keep_last:
                oldest_file = list_of_files.pop(0)
                os.remove(oldest_file)
                logger.info("🗑️ Đã xóa bản sao lưu cũ: %s", oldest_file)

        except Exception as exc:
            logger.exception("❌ Lỗi khi sao lưu database: %s", exc)