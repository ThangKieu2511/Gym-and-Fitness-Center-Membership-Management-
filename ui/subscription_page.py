"""
ui/subscription_page.py  —  Phase 5

Trang Quản Lý Gói Tập & Đăng Ký Gói.

Bố cục:
  ┌─────────────────────────────────────────────────────────────┐
  │  Header  (icon + tiêu đề)                                   │
  ├─────────────────────┬───────────────────────────────────────┤
  │  Form Đăng Ký       │  Danh Sách Gói Đã Đăng Ký            │
  │  • Chọn hội viên    │  (bảng — tự refresh khi chọn hội viên │
  │  • Loại khách       │   hoặc sau khi đăng ký thành công)    │
  │  • Loại gói         │                                       │
  │  • Preview giá/ngày │                                       │
  │  • Nút Đăng Ký      │                                       │
  └─────────────────────┴───────────────────────────────────────┘
  │  Status bar                                                  │
  └─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.subscription_controller import (
    CUSTOMER_TYPE_LABEL,
    PLAN_CONFIG,
    PRICE_PER_MONTH,
    SubscriptionController,
)

# ── Cột bảng lịch sử gói ──────────────────────────────────────────────── #
SUB_COLS     = ["#", "Gói Tập", "Giá (đ)", "Ngày Bắt Đầu", "Ngày Kết Thúc", "Trạng Thái"]
COL_IDX      = 0
COL_PLAN     = 1
COL_PRICE    = 2
COL_START    = 3
COL_END      = 4
COL_STATUS   = 5

# Nhãn hiển thị loại gói + ưu đãi
PLAN_LABELS: dict[str, str] = {
    "1_month":  "1 Tháng",
    "3_month":  "3 Tháng  (+1 tặng → 4 tháng)",
    "6_month":  "6 Tháng  (+2 tặng → 8 tháng)",
    "12_month": "12 Tháng (+3 tặng → 15 tháng)",
}

PLAN_KEYS   = list(PLAN_CONFIG.keys())      # ["1_month", "3_month", ...]
CTYPE_KEYS  = list(PRICE_PER_MONTH.keys())  # ["student", "adult"]


# ══════════════════════════════════════════════════════════════════════════ #
#  PreviewCard — hiển thị giá + thông tin gói                               #
# ══════════════════════════════════════════════════════════════════════════ #

class PreviewCard(QFrame):
    """Widget nhỏ hiển thị giá + ngày kết thúc theo lựa chọn hiện tại."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("previewCard")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # ── Tiêu đề card ──
        title = QLabel("💰  Thông Tin Gói")
        title.setObjectName("previewTitle")
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("sidebarDivider")
        layout.addWidget(sep)

        # ── Các dòng thông tin ──
        self._lbl_price      = self._info_row(layout, "Giá thanh toán:")
        self._lbl_duration   = self._info_row(layout, "Thời gian:")
        self._lbl_bonus      = self._info_row(layout, "Tháng tặng:")
        self._lbl_end        = self._info_row(layout, "Ngày kết thúc:")

        self.clear()

    @staticmethod
    def _info_row(parent_layout: QVBoxLayout, label_text: str) -> QLabel:
        row    = QHBoxLayout()
        row.setSpacing(6)
        lbl_k  = QLabel(label_text)
        lbl_k.setObjectName("previewKey")
        lbl_k.setMinimumWidth(130)
        lbl_v  = QLabel("—")
        lbl_v.setObjectName("previewValue")
        row.addWidget(lbl_k)
        row.addWidget(lbl_v, stretch=1)
        parent_layout.addLayout(row)
        return lbl_v

    # ── API ──────────────────────────────────────────────────────────── #

    def clear(self) -> None:
        self._lbl_price.setText("—")
        self._lbl_duration.setText("—")
        self._lbl_bonus.setText("—")
        self._lbl_end.setText("—")

    def update_preview(self, preview: dict) -> None:
        price    = preview["price"]
        total    = preview["total_months"]
        bonus    = preview["bonus_months"]
        end_date = preview["end_date"]

        self._lbl_price.setText(f"{price:,.0f} đ")
        self._lbl_duration.setText(f"{total} tháng")
        self._lbl_bonus.setText(
            f"{bonus} tháng 🎁" if bonus else "Không có"
        )
        self._lbl_end.setText(end_date)


# ══════════════════════════════════════════════════════════════════════════ #
#  RegistrationPanel — form đăng ký bên trái                                #
# ══════════════════════════════════════════════════════════════════════════ #

class RegistrationPanel(QWidget):
    """Panel trái chứa form đăng ký gói tập."""

    # Emit (member_id, plan_type, customer_type) khi đăng ký thành công
    subscription_created = Signal(int, str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = SubscriptionController()
        self._setup_ui()
        self._refresh_members()

    # ── Xây dựng UI ──────────────────────────────────────────────────── #

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 12, 0)
        root.setSpacing(14)

        # ── Tiêu đề panel ──
        pnl_title = QLabel("📋  Đăng Ký Gói Tập")
        pnl_title.setObjectName("panelTitle")
        root.addWidget(pnl_title)

        # ── Chọn hội viên ──
        root.addWidget(self._section_label("Hội Viên"))
        self._member_combo = QComboBox()
        self._member_combo.setPlaceholderText("— Chọn hội viên —")
        self._member_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._member_combo.currentIndexChanged.connect(self._on_selection_changed)
        root.addWidget(self._member_combo)

        # ── Loại khách ──
        root.addWidget(self._section_label("Loại Khách"))
        self._ctype_combo = QComboBox()
        for key in CTYPE_KEYS:
            self._ctype_combo.addItem(CUSTOMER_TYPE_LABEL[key], userData=key)
        self._ctype_combo.currentIndexChanged.connect(self._on_selection_changed)
        root.addWidget(self._ctype_combo)

        # ── Loại gói ──
        root.addWidget(self._section_label("Gói Tập"))
        self._plan_combo = QComboBox()
        for key in PLAN_KEYS:
            self._plan_combo.addItem(PLAN_LABELS[key], userData=key)
        self._plan_combo.currentIndexChanged.connect(self._on_selection_changed)
        root.addWidget(self._plan_combo)

        # ── Preview card ──
        self._preview = PreviewCard()
        root.addWidget(self._preview)

        # ── Nút đăng ký ──
        self._btn_register = QPushButton("✅  Đăng Ký Gói")
        self._btn_register.setObjectName("btnPrimary")
        self._btn_register.setMinimumHeight(40)
        self._btn_register.setCursor(Qt.PointingHandCursor)
        self._btn_register.clicked.connect(self._on_register)
        root.addWidget(self._btn_register)

        # ── Nút làm mới danh sách hội viên ──
        self._btn_reload = QPushButton("🔄  Làm Mới Danh Sách")
        self._btn_reload.setObjectName("btnNeutral")
        self._btn_reload.setMinimumHeight(34)
        self._btn_reload.setCursor(Qt.PointingHandCursor)
        self._btn_reload.clicked.connect(self._refresh_members)
        root.addWidget(self._btn_reload)

        root.addStretch()

        # Cập nhật preview ngay lập tức
        self._update_preview()

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("formSectionLabel")
        return lbl

    # ── Data helpers ──────────────────────────────────────────────────── #

    @Slot()
    def _refresh_members(self) -> None:
        """Tải lại danh sách hội viên vào combo box."""
        prev_id = self._current_member_id()
        self._member_combo.blockSignals(True)
        self._member_combo.clear()
        try:
            members = self._controller.get_all_members()
        except Exception:
            members = []
        for m in members:
            display = f"{m['name']}"
            if m.get("phone"):
                display += f"  ({m['phone']})"
            self._member_combo.addItem(display, userData=m["id"])

        # Cố gắng khôi phục lại lựa chọn cũ
        if prev_id is not None:
            for i in range(self._member_combo.count()):
                if self._member_combo.itemData(i) == prev_id:
                    self._member_combo.setCurrentIndex(i)
                    break

        self._member_combo.blockSignals(False)
        self._on_selection_changed()

    def _current_member_id(self) -> int | None:
        idx = self._member_combo.currentIndex()
        if idx < 0:
            return None
        return self._member_combo.itemData(idx)

    def _current_plan_type(self) -> str:
        return self._plan_combo.currentData()

    def _current_ctype(self) -> str:
        return self._ctype_combo.currentData()

    # ── Preview update ────────────────────────────────────────────────── #

    def _update_preview(self) -> None:
        plan_type = self._current_plan_type()
        ctype     = self._current_ctype()
        if plan_type and ctype:
            preview = SubscriptionController.get_plan_preview(plan_type, ctype)
            self._preview.update_preview(preview)
        else:
            self._preview.clear()

    @Slot()
    def _on_selection_changed(self) -> None:
        self._update_preview()

    # ── Đăng ký ──────────────────────────────────────────────────────── #

    @Slot()
    def _on_register(self) -> None:
        member_id = self._current_member_id()
        plan_type = self._current_plan_type()
        ctype     = self._current_ctype()

        if member_id is None:
            QMessageBox.warning(self, "Thiếu Thông Tin", "Vui lòng chọn hội viên.")
            return

        # Xác nhận trước khi đăng ký
        preview      = SubscriptionController.get_plan_preview(plan_type, ctype)
        member_name  = self._member_combo.currentText()
        plan_label   = PLAN_LABELS[plan_type]
        ctype_label  = CUSTOMER_TYPE_LABEL[ctype]

        reply = QMessageBox.question(
            self,
            "Xác Nhận Đăng Ký",
            f"<b>Hội viên:</b>  {member_name}<br>"
            f"<b>Loại khách:</b> {ctype_label}<br>"
            f"<b>Gói:</b>        {plan_label}<br>"
            f"<b>Giá:</b>        {preview['price']:,.0f} đ<br>"
            f"<b>Kết thúc:</b>   {preview['end_date']}<br><br>"
            "Xác nhận đăng ký?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self._controller.create_subscription(member_id, plan_type, ctype)
        except (ValueError, RuntimeError) as exc:
            QMessageBox.critical(self, "❌  Đăng Ký Thất Bại", str(exc))
            return

        QMessageBox.information(
            self,
            "✅  Thành Công",
            f"Đã đăng ký gói <b>{plan_label}</b> cho <b>{member_name}</b>!<br>"
            f"Ngày kết thúc: <b>{preview['end_date']}</b>",
        )
        self.subscription_created.emit(member_id, plan_type, ctype)

    # ── Public API ────────────────────────────────────────────────────── #

    def refresh_members(self) -> None:
        """Gọi từ bên ngoài khi danh sách hội viên thay đổi."""
        self._refresh_members()

    def selected_member_id(self) -> int | None:
        return self._current_member_id()


# ══════════════════════════════════════════════════════════════════════════ #
#  SubscriptionTable — bảng lịch sử gói bên phải                            #
# ══════════════════════════════════════════════════════════════════════════ #

class SubscriptionTable(QWidget):
    """Panel phải hiển thị các gói đã đăng ký của hội viên được chọn."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = SubscriptionController()
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 0, 0, 0)
        root.setSpacing(10)

        # ── Tiêu đề ──
        hdr = QHBoxLayout()
        self._title_lbl = QLabel("📄  Gói Đã Đăng Ký")
        self._title_lbl.setObjectName("panelTitle")
        hdr.addWidget(self._title_lbl)
        hdr.addStretch()
        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("statusLabel")
        hdr.addWidget(self._count_lbl)
        root.addLayout(hdr)

        # ── Bảng ──
        self._table = QTableWidget(0, len(SUB_COLS))
        self._table.setHorizontalHeaderLabels(SUB_COLS)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setHighlightSections(False)
        self._table.setShowGrid(False)

        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(COL_IDX,    QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(COL_PLAN,   QHeaderView.Stretch)
        hh.setSectionResizeMode(COL_PRICE,  QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(COL_START,  QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(COL_END,    QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeToContents)

        root.addWidget(self._table, stretch=1)

        # ── Empty state ──
        self._empty_lbl = QLabel(
            "👆  Chọn một hội viên ở bên trái\nđể xem lịch sử gói tập."
        )
        self._empty_lbl.setObjectName("emptyStateLabel")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.hide()

    # ── Populate ──────────────────────────────────────────────────────── #

    def load_for_member(self, member_id: int, member_name: str = "") -> None:
        """Tải danh sách gói của hội viên vào bảng."""
        if member_name:
            self._title_lbl.setText(f"📄  Gói Đã Đăng Ký — {member_name}")
        else:
            self._title_lbl.setText("📄  Gói Đã Đăng Ký")

        try:
            subs = self._controller.get_member_subscriptions(member_id)
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))
            return

        self._populate(subs)

    def clear_table(self) -> None:
        self._table.setRowCount(0)
        self._count_lbl.setText("")
        self._title_lbl.setText("📄  Gói Đã Đăng Ký")

    def _populate(self, subs: list[dict]) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        today = date.today().isoformat()

        for row_idx, s in enumerate(subs):
            self._table.insertRow(row_idx)

            # ── #
            self._cell(row_idx, COL_IDX, str(row_idx + 1), Qt.AlignCenter)

            # ── Tên gói
            self._cell(row_idx, COL_PLAN, s.get("plan_name", ""), Qt.AlignLeft | Qt.AlignVCenter)

            # ── Giá
            price = s.get("price", 0) or 0
            self._cell(row_idx, COL_PRICE, f"{price:,.0f}", Qt.AlignRight | Qt.AlignVCenter)

            # ── Ngày bắt đầu / kết thúc
            self._cell(row_idx, COL_START, s.get("start_date", ""), Qt.AlignCenter)
            self._cell(row_idx, COL_END,   s.get("end_date",   ""), Qt.AlignCenter)

            # ── Trạng thái với màu sắc
            status = s.get("status", "")
            self._set_status_cell(row_idx, status, s.get("end_date", ""), today)

        self._table.setSortingEnabled(True)
        count = len(subs)
        self._count_lbl.setText(f"{count} gói" if count else "Chưa có gói nào")

    def _cell(
        self,
        row: int,
        col: int,
        text: str,
        align: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter,
    ) -> QTableWidgetItem:
        item = QTableWidgetItem(text or "")
        item.setTextAlignment(align)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self._table.setItem(row, col, item)
        return item

    def _set_status_cell(
        self,
        row: int,
        status: str,
        end_date: str,
        today: str,
    ) -> None:
        """Hiển thị trạng thái với màu sắc phù hợp."""
        if status == "active":
            label = "✅  Đang Hiệu Lực"
            color = QColor("#22c55e")   # xanh lá
        elif status == "expired" or (end_date and end_date < today):
            label = "⏹  Đã Hết Hạn"
            color = QColor("#64748b")   # xám
        elif status == "cancelled":
            label = "🚫  Đã Hủy"
            color = QColor("#f87171")   # đỏ nhạt
        else:
            label = status or "—"
            color = QColor("#94a3b8")

        item = QTableWidgetItem(label)
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(color)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self._table.setItem(row, COL_STATUS, item)


# ══════════════════════════════════════════════════════════════════════════ #
#  SubscriptionPage — trang tổng hợp                                        #
# ══════════════════════════════════════════════════════════════════════════ #

class SubscriptionPage(QWidget):
    """
    Trang Quản Lý Gói Tập — tích hợp form đăng ký + lịch sử gói.
    Giao diện chia đôi trái/phải qua QSplitter.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    # ── Xây dựng UI ──────────────────────────────────────────────────── #

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── Header ──
        root.addLayout(self._build_header())

        # ── Divider ──
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setObjectName("sidebarDivider")
        root.addWidget(div)

        # ── Splitter: form trái | bảng phải ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        # Wrap RegistrationPanel trong một container có padding
        left_wrap = QWidget()
        left_layout = QVBoxLayout(left_wrap)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._reg_panel = RegistrationPanel()
        left_layout.addWidget(self._reg_panel)
        splitter.addWidget(left_wrap)

        # Wrap SubscriptionTable
        right_wrap = QWidget()
        right_layout = QVBoxLayout(right_wrap)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self._sub_table = SubscriptionTable()
        right_layout.addWidget(self._sub_table)
        splitter.addWidget(right_wrap)

        splitter.setSizes([340, 660])
        root.addWidget(splitter, stretch=1)

        # ── Status bar ──
        self._status_lbl = QLabel("Chọn hội viên và gói tập để bắt đầu đăng ký.")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)

        # ── Kết nối tín hiệu ──
        # Khi chọn hội viên → tải lịch sử gói
        self._reg_panel._member_combo.currentIndexChanged.connect(
            self._on_member_combo_changed
        )
        # Sau khi đăng ký thành công → refresh bảng
        self._reg_panel.subscription_created.connect(self._on_subscription_created)

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()
        hdr.setSpacing(14)

        icon = QLabel("🎫")
        icon.setObjectName("pageIcon")

        title = QLabel("Quản Lý Gói Tập")
        title.setObjectName("pageTitle")

        sub = QLabel("Đăng ký gói tập và xem lịch sử đăng ký của hội viên")
        sub.setObjectName("pageSubtitle")

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.addWidget(title)
        text_col.addWidget(sub)

        hdr.addWidget(icon)
        hdr.addLayout(text_col)
        hdr.addStretch()
        return hdr

    # ── Slots ─────────────────────────────────────────────────────────── #

    @Slot()
    def _on_member_combo_changed(self) -> None:
        """Khi chọn hội viên khác → tải lại bảng lịch sử."""
        member_id = self._reg_panel.selected_member_id()
        if member_id is None:
            self._sub_table.clear_table()
            return
        member_name = self._reg_panel._member_combo.currentText()
        self._sub_table.load_for_member(member_id, member_name)
        self._status_lbl.setText(f"Đang xem gói tập của: {member_name}")

    @Slot(int, str, str)
    def _on_subscription_created(
        self, member_id: int, plan_type: str, customer_type: str
    ) -> None:
        """Sau khi đăng ký → refresh bảng lịch sử."""
        member_name = self._reg_panel._member_combo.currentText()
        self._sub_table.load_for_member(member_id, member_name)
        self._status_lbl.setText(
            f"✅  Đã đăng ký gói thành công cho {member_name}."
        )

    # ── Public API ────────────────────────────────────────────────────── #

    def refresh_members(self) -> None:
        """
        Gọi từ MainWindow khi danh sách hội viên thay đổi
        (ví dụ sau khi thêm/xóa hội viên ở MemberPage).
        """
        self._reg_panel.refresh_members()