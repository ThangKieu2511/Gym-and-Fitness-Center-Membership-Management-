"""
ui/dashboard_page.py  —  Phase 8

Dashboard tổng quan cho gym management:
  • StatCard       — card hiển thị 1 chỉ số
  • TodayDetail    — bảng danh sách check-in hôm nay theo member
  • TopMembersTable — bảng top 5 đi tập nhiều nhất tháng
  • MemberHistory  — combobox + bảng lịch sử 1 hội viên
  • DashboardPage  — trang tổng hợp
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.dashboard_controller import DashboardController


# ══════════════════════════════════════════════════════════════════════════ #
#  StatCard                                                                   #
# ══════════════════════════════════════════════════════════════════════════ #

class StatCard(QFrame):
    """Hiển thị 1 chỉ số với icon + label + giá trị lớn."""

    def __init__(
        self,
        icon: str,
        label: str,
        value: str = "—",
        accent: str = "#3b82f6",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self._accent = accent
        self._setup_ui(icon, label, value)

    def _setup_ui(self, icon: str, label: str, value: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(8)

        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("statCardIcon")
        top.addWidget(icon_lbl)

        lbl = QLabel(label)
        lbl.setObjectName("statCardLabel")
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top.addWidget(lbl)
        top.addStretch()

        layout.addLayout(top)

        self._value_lbl = QLabel(value)
        self._value_lbl.setObjectName("statCardValue")
        self._value_lbl.setStyleSheet(f"color: {self._accent};")
        layout.addWidget(self._value_lbl)

    def set_value(self, value: str) -> None:
        self._value_lbl.setText(value)


# ══════════════════════════════════════════════════════════════════════════ #
#  Helpers                                                                    #
# ══════════════════════════════════════════════════════════════════════════ #

def _make_table(headers: list[str]) -> QTableWidget:
    tbl = QTableWidget(0, len(headers))
    tbl.setHorizontalHeaderLabels(headers)
    tbl.setEditTriggers(QTableWidget.NoEditTriggers)
    tbl.setSelectionBehavior(QTableWidget.SelectRows)
    tbl.setAlternatingRowColors(True)
    tbl.verticalHeader().setVisible(False)
    tbl.horizontalHeader().setHighlightSections(False)
    tbl.setShowGrid(False)
    tbl.setSortingEnabled(True)
    return tbl


def _cell(
    tbl: QTableWidget,
    row: int,
    col: int,
    text: str,
    align: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter,
    color: QColor | None = None,
) -> QTableWidgetItem:
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(align)
    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
    if color:
        item.setForeground(color)
    tbl.setItem(row, col, item)
    return item


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("sectionTitle")
    return lbl


# ══════════════════════════════════════════════════════════════════════════ #
#  TodayDetailTable                                                           #
# ══════════════════════════════════════════════════════════════════════════ #

class TodayDetailTable(QWidget):
    HEADERS = ["#", "Tên Hội Viên", "Số Lần Check-in Hôm Nay"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(_section_title("📋  Chi Tiết Check-in Hôm Nay"))
        self._table = _make_table(self.HEADERS)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self._table)

    def load(self, detail: list[dict]) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        for i, row in enumerate(detail):
            r = self._table.rowCount()
            self._table.insertRow(r)
            _cell(self._table, r, 0, str(i + 1), Qt.AlignCenter)
            _cell(self._table, r, 1, row.get("member_name", ""))
            _cell(self._table, r, 2, str(row.get("count", 0)), Qt.AlignCenter)
        self._table.setSortingEnabled(True)


# ══════════════════════════════════════════════════════════════════════════ #
#  TopMembersTable                                                            #
# ══════════════════════════════════════════════════════════════════════════ #

class TopMembersTable(QWidget):
    HEADERS = ["Hạng", "Tên Hội Viên", "Số Ngày Đi Tập (Tháng)"]
    MEDALS  = ["🥇", "🥈", "🥉", "4", "5"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(_section_title("🏆  Top 5 Hội Viên Tháng Này"))
        self._table = _make_table(self.HEADERS)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self._table)

    def load(self, rows: list[dict]) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        medal_colors = [
            QColor("#f59e0b"),   # gold
            QColor("#94a3b8"),   # silver
            QColor("#cd7f32"),   # bronze
        ]
        for i, row in enumerate(rows):
            r = self._table.rowCount()
            self._table.insertRow(r)
            medal = self.MEDALS[i] if i < len(self.MEDALS) else str(i + 1)
            color = medal_colors[i] if i < 3 else None
            _cell(self._table, r, 0, medal, Qt.AlignCenter, color)
            _cell(self._table, r, 1, row.get("member_name", ""), color=color)
            _cell(self._table, r, 2, str(row.get("days_count", 0)), Qt.AlignCenter, color)
        self._table.setSortingEnabled(True)


# ══════════════════════════════════════════════════════════════════════════ #
#  MemberHistoryPanel                                                         #
# ══════════════════════════════════════════════════════════════════════════ #

class MemberHistoryPanel(QWidget):
    HEADERS = ["#", "Thời Gian Check-in", "Trạng Thái"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._members: list[dict] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        layout.addWidget(_section_title("📅  Lịch Sử Check-in Theo Hội Viên"))

        self._combo = QComboBox()
        self._combo.setPlaceholderText("— Chọn hội viên để xem lịch sử —")
        self._combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._combo.currentIndexChanged.connect(self._on_member_changed)
        layout.addWidget(self._combo)

        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("statusLabel")
        layout.addWidget(self._count_lbl)

        self._table = _make_table(self.HEADERS)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self._table)

    def populate_members(self, members: list[dict]) -> None:
        self._members = members
        self._combo.blockSignals(True)
        self._combo.clear()
        for m in members:
            display = f"{m['name']}  ({m.get('phone', '')})"
            self._combo.addItem(display, userData=m["id"])
        self._combo.blockSignals(False)

    def load_history(self, rows: list[dict]) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        for i, row in enumerate(rows):
            r = self._table.rowCount()
            self._table.insertRow(r)
            _cell(self._table, r, 0, str(i + 1), Qt.AlignCenter)
            _cell(self._table, r, 1, row.get("checkin_time", ""), Qt.AlignCenter)

            status = row.get("status", "")
            if status == "valid":
                label, color = "✅  Hợp Lệ",    QColor("#22c55e")
            elif status == "expired":
                label, color = "⚠️  Hết Hạn",   QColor("#f59e0b")
            else:
                label, color = "❌  Chưa Đăng Ký", QColor("#ef4444")
            _cell(self._table, r, 2, label, Qt.AlignCenter, color)

        count = len(rows)
        self._count_lbl.setText(
            f"{count} lượt check-in" if count else "Chưa có lịch sử check-in."
        )
        self._table.setSortingEnabled(True)

    @Slot()
    def _on_member_changed(self) -> None:
        # Emit up to DashboardPage — handled via callback
        pass

    def selected_member_id(self) -> int | None:
        idx = self._combo.currentIndex()
        if idx < 0:
            return None
        return self._combo.itemData(idx)


# ══════════════════════════════════════════════════════════════════════════ #
#  DashboardPage                                                              #
# ══════════════════════════════════════════════════════════════════════════ #

class DashboardPage(QWidget):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctrl = DashboardController()
        self._setup_ui()
        self.refresh_data()

    # ── Build UI ─────────────────────────────────────────────────────── #

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Header
        root.addLayout(self._build_header())

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setObjectName("sidebarDivider")
        root.addWidget(div)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 4, 0)
        body_layout.setSpacing(20)

        # ── Stat cards row ──
        body_layout.addLayout(self._build_stat_cards())

        # ── Today detail + Top members (side by side) ──
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        self._today_table = TodayDetailTable()
        mid_row.addWidget(self._today_table, stretch=1)

        self._top_table = TopMembersTable()
        mid_row.addWidget(self._top_table, stretch=1)

        body_layout.addLayout(mid_row)

        # ── Member history ──
        self._history_panel = MemberHistoryPanel()
        self._history_panel._combo.currentIndexChanged.connect(self._on_history_member_changed)
        body_layout.addWidget(self._history_panel)

        body_layout.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, stretch=1)

        # Status bar
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()
        hdr.setSpacing(14)

        icon = QLabel("📊")
        icon.setObjectName("pageIcon")

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")

        today_str = date.today().strftime("%d/%m/%Y")
        sub = QLabel(f"Tổng quan hoạt động phòng gym  •  {today_str}")
        sub.setObjectName("pageSubtitle")

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.addWidget(title)
        text_col.addWidget(sub)

        hdr.addWidget(icon)
        hdr.addLayout(text_col)
        hdr.addStretch()

        btn_refresh = QPushButton("🔄  Làm Mới")
        btn_refresh.setObjectName("btnNeutral")
        btn_refresh.setMinimumHeight(34)
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh_data)
        hdr.addWidget(btn_refresh)

        return hdr

    def _build_stat_cards(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(12)

        self._card_today_total   = StatCard("🏃", "Tổng Check-in Hôm Nay",    "—", "#3b82f6")
        self._card_today_people  = StatCard("👤", "Số Người Đi Tập Hôm Nay",  "—", "#10b981")
        self._card_month_total   = StatCard("📅", "Tổng Check-in Tháng Này",  "—", "#8b5cf6")
        self._card_month_people  = StatCard("👥", "Số Người Đi Tập Tháng Này","—", "#f59e0b")
        self._card_active        = StatCard("✅", "Hội Viên Đang Active",      "—", "#22c55e")

        grid.addWidget(self._card_today_total,  0, 0)
        grid.addWidget(self._card_today_people, 0, 1)
        grid.addWidget(self._card_month_total,  0, 2)
        grid.addWidget(self._card_month_people, 0, 3)
        grid.addWidget(self._card_active,       0, 4)

        for col in range(5):
            grid.setColumnStretch(col, 1)

        return grid

    # ── Data loading ─────────────────────────────────────────────────── #

    def refresh_data(self) -> None:
        """Load / reload tất cả dữ liệu dashboard."""
        try:
            today_stats  = self._ctrl.get_today_stats()
            month_stats  = self._ctrl.get_month_stats()
            active_count = self._ctrl.get_active_members()
            top_members  = self._ctrl.get_top_members(limit=5)
            all_members  = self._ctrl.get_all_members()

            # Stat cards
            self._card_today_total.set_value(str(today_stats["total_checkins"]))
            self._card_today_people.set_value(str(today_stats["unique_members"]))
            self._card_month_total.set_value(str(month_stats["total_checkins"]))
            self._card_month_people.set_value(str(month_stats["unique_members"]))
            self._card_active.set_value(str(active_count))

            # Tables
            self._today_table.load(today_stats["detail"])
            self._top_table.load(top_members)

            # Member combobox — giữ lại selection nếu có
            current_id = self._history_panel.selected_member_id()
            self._history_panel.populate_members(all_members)

            # Khôi phục selection
            if current_id is not None:
                combo = self._history_panel._combo
                for i in range(combo.count()):
                    if combo.itemData(i) == current_id:
                        combo.setCurrentIndex(i)
                        break

                self._load_member_history()
            elif all_members:
                # Load history cho member đầu tiên mặc định
                self._history_panel._combo.setCurrentIndex(0)
                self._load_member_history()

            now_str = date.today().strftime("%d/%m/%Y")
            self._status_lbl.setText(f"Cập nhật lúc: {now_str}")

        except Exception as exc:  # noqa: BLE001
            self._status_lbl.setText(f"❌  Lỗi tải dữ liệu: {exc}")
            self._status_lbl.setStyleSheet("color: #ef4444;")
            QTimer.singleShot(
                5000,
                lambda: self._status_lbl.setStyleSheet(""),
            )

    def _load_member_history(self) -> None:
        member_id = self._history_panel.selected_member_id()
        if member_id is None:
            self._history_panel.load_history([])
            return
        try:
            rows = self._ctrl.get_member_history(member_id)
            self._history_panel.load_history(rows)
        except Exception as exc:  # noqa: BLE001
            self._history_panel.load_history([])
            self._status_lbl.setText(f"❌  Lỗi tải lịch sử: {exc}")

    # ── Slots ────────────────────────────────────────────────────────── #

    @Slot()
    def _on_history_member_changed(self) -> None:
        self._load_member_history()