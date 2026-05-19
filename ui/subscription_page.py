"""
ui/subscription_page.py  —  Phase 9

Thay đổi so với Phase 7:
  • _on_checkin() giờ gọi CheckinController.checkin() trực tiếp
    thay vì SubscriptionController.checkin() (đã bị xoá)
  • Import thêm CheckinController
  • Tích hợp âm thanh ăn mừng khi Đăng ký mới / Gia hạn gói thành công bằng os path
"""

from __future__ import annotations
import os
from datetime import date, timedelta

from PySide6.QtCore import Qt, QTimer, Signal, Slot, QUrl
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtGui import QColor
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
from controllers.checkin_controller import CheckinController

# ── Cột bảng ────────────────────────────────────────────────────────────── #
SUB_COLS   = ["#", "Gói Tập", "Giá (đ)", "Ngày Bắt Đầu", "Ngày Kết Thúc", "Trạng Thái", ""]
COL_IDX    = 0
COL_PLAN   = 1
COL_PRICE  = 2
COL_START  = 3
COL_END    = 4
COL_STATUS = 5
COL_ACTION = 6

PLAN_LABELS: dict[str, str] = {
    "1_month":  "1 Tháng",
    "3_month":  "3 Tháng  (+1 tặng → 4 tháng)",
    "6_month":  "6 Tháng  (+2 tặng → 8 tháng)",
    "12_month": "12 Tháng (+3 tặng → 15 tháng)",
}

PLAN_KEYS  = list(PLAN_CONFIG.keys())
CTYPE_KEYS = list(PRICE_PER_MONTH.keys())

# ── Đường dẫn thư mục assets âm thanh chuẩn hóa tuyệt đối bằng os ────────── #
_UI_DIR        = os.path.dirname(os.path.abspath(__file__))
_ASSETS_DIR    = os.path.normpath(os.path.join(_UI_DIR, "..", "assets"))
_SFX_CELEBRATE = os.path.join(_ASSETS_DIR, "celebrate.wav")


# ══════════════════════════════════════════════════════════════════════════ #
#  PreviewCard                                                               #
# ══════════════════════════════════════════════════════════════════════════ #

class PreviewCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("previewCard")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title = QLabel("💰  Thông Tin Gói")
        title.setObjectName("previewTitle")
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("sidebarDivider")
        layout.addWidget(sep)

        self._lbl_price    = self._info_row(layout, "Giá thanh toán:")
        self._lbl_duration = self._info_row(layout, "Thời gian:")
        self._lbl_bonus    = self._info_row(layout, "Tháng tặng:")
        self._lbl_end      = self._info_row(layout, "Ngày kết thúc:")
        self.clear()

    @staticmethod
    def _info_row(parent_layout: QVBoxLayout, label_text: str) -> QLabel:
        row   = QHBoxLayout()
        row.setSpacing(6)
        
        lbl_k = QLabel(label_text)
        lbl_k.setObjectName("previewKey")
        lbl_k.setMinimumWidth(130)
        lbl_k.setMinimumHeight(28) 
        lbl_k.setStyleSheet("padding-bottom: 2px;") 
        lbl_k.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        lbl_v = QLabel("—")
        lbl_v.setObjectName("previewValue")
        lbl_v.setMinimumHeight(28)
        lbl_v.setStyleSheet("padding-bottom: 2px;")
        lbl_v.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        row.addWidget(lbl_k)
        row.addWidget(lbl_v, stretch=1)
        parent_layout.addLayout(row)
        return lbl_v

    def clear(self) -> None:
        for lbl in (self._lbl_price, self._lbl_duration, self._lbl_bonus, self._lbl_end):
            lbl.setText("—")

    def update_preview(self, preview: dict) -> None:
        self._lbl_price.setText(f"{preview['price']:,.0f} đ")
        self._lbl_duration.setText(f"{preview['total_months']} tháng")
        self._lbl_bonus.setText(
            f"{preview['bonus_months']} tháng 🎁" if preview["bonus_months"] else "Không có"
        )
        self._lbl_end.setText(preview["end_date"])


# ══════════════════════════════════════════════════════════════════════════ #
#  RegistrationPanel — form bên trái                                         #
# ══════════════════════════════════════════════════════════════════════════ #

class RegistrationPanel(QWidget):
    subscription_created  = Signal(int, str, str)
    subscription_extended = Signal(int)
    checkin_done          = Signal(int, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller         = SubscriptionController()
        self._checkin_controller = CheckinController()
        self._setup_sound_effects()
        self._setup_ui()
        self._refresh_members()

    def _setup_sound_effects(self) -> None:
        """Khởi tạo QSoundEffect cho âm thanh ăn mừng giao dịch."""
        self._sfx_celebrate = QSoundEffect(self)
        self._sfx_celebrate.setSource(QUrl.fromLocalFile(_SFX_CELEBRATE))
        self._sfx_celebrate.setVolume(1.0)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 12, 0)
        root.setSpacing(12)

        pnl_title = QLabel("📋  Đăng Ký / Gia Hạn Gói")
        pnl_title.setObjectName("panelTitle")
        root.addWidget(pnl_title)

        root.addWidget(self._section_label("Hội Viên"))
        self._member_combo = QComboBox()
        self._member_combo.setPlaceholderText("— Chọn hội viên —")
        self._member_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._member_combo.currentIndexChanged.connect(self._on_selection_changed)
        root.addWidget(self._member_combo)

        root.addWidget(self._section_label("Loại Khách"))
        self._ctype_combo = QComboBox()
        for key in CTYPE_KEYS:
            self._ctype_combo.addItem(CUSTOMER_TYPE_LABEL[key], userData=key)
        self._ctype_combo.currentIndexChanged.connect(self._on_selection_changed)
        root.addWidget(self._ctype_combo)

        root.addWidget(self._section_label("Gói Tập"))
        self._plan_combo = QComboBox()
        for key in PLAN_KEYS:
            self._plan_combo.addItem(PLAN_LABELS[key], userData=key)
        self._plan_combo.currentIndexChanged.connect(self._on_selection_changed)
        root.addWidget(self._plan_combo)

        self._preview = PreviewCard()
        root.addWidget(self._preview)

        root.addWidget(self._section_label("Thao Tác"))

        self._btn_register = QPushButton("✅  Đăng Ký Gói Mới")
        self._btn_register.setObjectName("btnPrimary")
        self._btn_register.setMinimumHeight(38)
        self._btn_register.setCursor(Qt.PointingHandCursor)
        self._btn_register.clicked.connect(self._on_register)
        root.addWidget(self._btn_register)

        self._btn_extend = QPushButton("🔁  Gia Hạn Gói Hiện Tại")
        self._btn_extend.setObjectName("btnSecondary")
        self._btn_extend.setMinimumHeight(38)
        self._btn_extend.setCursor(Qt.PointingHandCursor)
        self._btn_extend.clicked.connect(self._on_extend)
        root.addWidget(self._btn_extend)

        self._btn_checkin = QPushButton("🏃  Check-in")
        self._btn_checkin.setObjectName("btnNeutral")
        self._btn_checkin.setMinimumHeight(38)
        self._btn_checkin.setCursor(Qt.PointingHandCursor)
        self._btn_checkin.clicked.connect(self._on_checkin)
        self._btn_checkin.setToolTip(
            "Ghi nhận lượt tập hôm nay.\n"
            "✅  Hợp lệ nếu có gói đang active\n"
            "⚠️  Cảnh báo nếu gói đã hết hạn\n"
            "❌  Từ chối nếu chưa đăng ký gói"
        )
        root.addWidget(self._btn_checkin)

        self._btn_reload = QPushButton("🔄  Làm Mới Danh Sách")
        self._btn_reload.setObjectName("btnNeutral")
        self._btn_reload.setMinimumHeight(34)
        self._btn_reload.setCursor(Qt.PointingHandCursor)
        self._btn_reload.clicked.connect(self._refresh_members)
        root.addWidget(self._btn_reload)

        root.addStretch()

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("formSectionLabel")
        return lbl

    @Slot()
    def _refresh_members(self) -> None:
        prev_id = self._current_member_id()
        self._member_combo.blockSignals(True)
        self._member_combo.clear()
        try:
            members = self._controller.get_all_members()
        except Exception:
            members = []
        for m in members:
            display = m["name"]
            if m.get("phone"):
                display += f"  ({m['phone']})"
            self._member_combo.addItem(display, userData=m["id"])
        if prev_id is not None:
            for i in range(self._member_combo.count()):
                if self._member_combo.itemData(i) == prev_id:
                    self._member_combo.setCurrentIndex(i)
                    break
        self._member_combo.blockSignals(False)
        self._on_selection_changed()

    def _current_member_id(self) -> int | None:
        idx = self._member_combo.currentIndex()
        return self._member_combo.itemData(idx) if idx >= 0 else None

    def _current_plan_type(self) -> str:
        return self._plan_combo.currentData()

    def _current_ctype(self) -> str:
        return self._ctype_combo.currentData()

    def _update_preview(self) -> None:
        plan_type = self._current_plan_type()
        ctype     = self._current_ctype()
        if plan_type and ctype:
            self._preview.update_preview(
                SubscriptionController.get_plan_preview(plan_type, ctype)
            )
        else:
            self._preview.clear()

    @Slot()
    def _on_selection_changed(self) -> None:
        self._update_preview()

    def _require_member(self) -> int | None:
        member_id = self._current_member_id()
        if member_id is None:
            QMessageBox.warning(self, "Thiếu Thông Tin", "Vui lòng chọn hội viên.")
        return member_id

    @Slot()
    def _on_register(self) -> None:
        member_id = self._require_member()
        if member_id is None:
            return

        plan_type   = self._current_plan_type()
        ctype       = self._current_ctype()
        preview     = SubscriptionController.get_plan_preview(plan_type, ctype)
        member_name = self._member_combo.currentText()
        plan_label  = PLAN_LABELS[plan_type]

        active = self._controller._db.get_active_subscription(member_id)
        extra_msg = ""
        if active:
            extra_msg = (
                f"<br><br>⚠️ Hội viên đang có gói active đến <b>{active['end_date']}</b>.<br>"
                f"Thao tác này sẽ <b>gia hạn</b> thêm {preview['total_months']} tháng."
            )

        # ĐÃ ĐƯA RA NGOÀI KHỐI IF ACTIVE: Đảm bảo biến reply luôn được khởi tạo
        reply = QMessageBox.question(
            self,
            "Xác Nhận Đăng Ký",
            f"<b>Hội viên:</b> {member_name}<br>"
            f"<b>Loại khách:</b> {CUSTOMER_TYPE_LABEL[ctype]}<br>"
            f"<b>Gói:</b> {plan_label}<br>"
            f"<b>Giá:</b> {preview['price']:,.0f} đ<br>"
            f"<b>Kết thúc:</b> {preview['end_date']}"
            f"{extra_msg}<br><br>Xác nhận?",
            QMessageBox.Yes | QMessageBox.No,       
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self._controller.create_subscription(member_id, plan_type, ctype)
        except (ValueError, RuntimeError) as exc:
            QMessageBox.critical(self, "❌  Thất Bại", str(exc))
            return

        QMessageBox.information(
            self, "✅  Thành Công",
            f"Đã xử lý gói <b>{plan_label}</b> cho <b>{member_name}</b>!",
        )
        self._sfx_celebrate.play()  # Phát âm thanh ăn mừng thành công
        self.subscription_created.emit(member_id, plan_type, ctype)

    @Slot()
    def _on_extend(self) -> None:
        member_id = self._require_member()
        if member_id is None:
            return

        plan_type   = self._current_plan_type()
        ctype       = self._current_ctype()
        preview     = SubscriptionController.get_plan_preview(plan_type, ctype)
        member_name = self._member_combo.currentText()
        plan_label  = PLAN_LABELS[plan_type]

        active = self._controller._db.get_active_subscription(member_id)
        if not active:
            QMessageBox.warning(
                self, "Không Thể Gia Hạn",
                "Hội viên chưa có gói đang hiệu lực.\n"
                "Vui lòng dùng nút \"Đăng Ký Gói Mới\".",
            )
            return

        new_end = (
            date.fromisoformat(active["end_date"])
            + timedelta(days=preview["total_months"] * 30)
        ).isoformat()

        reply = QMessageBox.question(
            self,
            "Xác Nhận Gia Hạn",
            f"<b>Hội viên:</b> {member_name}<br>"
            f"<b>Gói hiện tại đến:</b> {active['end_date']}<br>"
            f"<b>Gia hạn thêm:</b> {plan_label} ({preview['total_months']} tháng)<br>"
            f"<b>Ngày kết thúc mới:</b> {new_end}<br><br>"
            "Xác nhận gia hạn?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self._controller.extend_subscription(member_id, plan_type, ctype)
        except (ValueError, RuntimeError) as exc:
            QMessageBox.critical(self, "❌  Thất Bại", str(exc))
            return

        QMessageBox.information(
            self, "✅  Gia Hạn Thành Công",
            f"Đã gia hạn gói cho <b>{member_name}</b>.<br>"
            f"Ngày kết thúc mới: <b>{new_end}</b>",
        )
        self._sfx_celebrate.play()  # Phát âm thanh ăn mừng thành công
        self.subscription_extended.emit(member_id)

    @Slot()
    def _on_checkin(self) -> None:
        member_id = self._require_member()
        if member_id is None:
            return

        self._btn_checkin.setEnabled(False)
        QTimer.singleShot(2000, lambda: self._btn_checkin.setEnabled(True))

        try:
            result = self._checkin_controller.checkin(member_id)
        except Exception as exc:
            QMessageBox.critical(self, "❌  Lỗi Check-in", str(exc))
            self._btn_checkin.setEnabled(True)
            return

        status = result["status"]

        if status == "valid":
            QMessageBox.information(self, "✅  Check-in Thành Công", result["message"])
        elif status == "expired":
            QMessageBox.warning(self, "⚠️  Gói Đã Hết Hạn", result["message"])
        else:
            QMessageBox.critical(self, "❌  Chưa Có Gói Tập", result["message"])

        self.checkin_done.emit(member_id, status)

    def refresh_members(self) -> None:
        self._refresh_members()

    def selected_member_id(self) -> int | None:
        return self._current_member_id()


# ══════════════════════════════════════════════════════════════════════════ #
#  SubscriptionTable — bảng bên phải                                         #
# ══════════════════════════════════════════════════════════════════════════ #

class SubscriptionTable(QWidget):
    subscription_cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller  = SubscriptionController()
        self._member_id: int | None = None
        self._member_name: str = ""
        self._sub_ids: list[int] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 0, 0, 0)
        root.setSpacing(10)

        hdr = QHBoxLayout()
        self._title_lbl = QLabel("📄  Gói Đã Đăng Ký")
        self._title_lbl.setObjectName("panelTitle")
        hdr.addWidget(self._title_lbl)
        hdr.addStretch()
        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("statusLabel")
        hdr.addWidget(self._count_lbl)
        root.addLayout(hdr)

        self._table = QTableWidget(0, len(SUB_COLS))
        self._table.setColumnWidth(COL_ACTION, 110)
        self._table.setHorizontalHeaderLabels(SUB_COLS)
        self._table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
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
        hh.setSectionResizeMode(COL_ACTION, QHeaderView.Fixed)

        root.addWidget(self._table, stretch=1)

    def load_for_member(self, member_id: int, member_name: str = "") -> None:
        self._member_id   = member_id
        self._member_name = member_name
        self._title_lbl.setText(
            f"📄  Gói Đã Đăng Ký — {member_name}" if member_name else "📄  Gói Đã Đăng Ký"
        )
        try:
            subs = self._controller.get_member_subscriptions(member_id)
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))
            return
        self._populate(subs)

    def refresh(self) -> None:
        if self._member_id is not None:
            self.load_for_member(self._member_id, self._member_name)

    def clear_table(self) -> None:
        self._member_id   = None
        self._member_name = ""
        self._sub_ids.clear()
        self._table.setRowCount(0)
        self._count_lbl.setText("")
        self._title_lbl.setText("📄  Gói Đã Đăng Ký")

    def _populate(self, subs: list[dict]) -> None:
        self._sub_ids.clear()
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        today = date.today().isoformat()

        for row_idx, s in enumerate(subs):
            self._table.insertRow(row_idx)
            self._sub_ids.append(s["id"])

            self._cell(row_idx, COL_IDX,   str(row_idx + 1), Qt.AlignCenter)
            self._cell(row_idx, COL_PLAN,  s.get("plan_name", ""))
            price = s.get("price", 0) or 0
            self._cell(row_idx, COL_PRICE, f"{price:,.0f}", Qt.AlignCenter)
            self._cell(row_idx, COL_START, s.get("start_date", ""), Qt.AlignCenter)
            self._cell(row_idx, COL_END,   s.get("end_date",   ""), Qt.AlignCenter)
            self._set_status_cell(row_idx, s.get("status", ""), s.get("end_date", ""), today)

            status = s.get("status", "")
            if status == "active":
                btn = QPushButton("🚫 Huỷ")
                btn.setObjectName("btnDanger")
                
                btn.setFixedSize(80, 32)  
                btn.setStyleSheet("padding: 4px 8px;") 
                
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(
                    lambda _, sid=s["id"], rname=s.get("plan_name", ""): self._on_cancel(sid, rname)
                )

                # Container bọc nút
                container = QWidget()
                container.setStyleSheet("background-color: transparent;")
                
                layout = QHBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setAlignment(Qt.AlignCenter)
                layout.addWidget(btn)

                self._table.setCellWidget(row_idx, COL_ACTION, container)
            else:
                self._table.setCellWidget(row_idx, COL_ACTION, None)
            
            self._table.setRowHeight(row_idx, 48)
        self._table.setSortingEnabled(True)
        count = len(subs)
        self._count_lbl.setText(f"{count} gói" if count else "Chưa có gói nào")

    def _cell(self, row, col, text, align=Qt.AlignLeft | Qt.AlignVCenter):
        item = QTableWidgetItem(text or "")
        item.setTextAlignment(align)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self._table.setItem(row, col, item)
        return item

    def _set_status_cell(self, row, status, end_date, today) -> None:
        if status == "active":
            label, color = "✅  Đang Hiệu Lực", QColor("#22c55e")
        elif status == "cancelled":
            label, color = "🚫  Đã Hủy",        QColor("#f87171")
        else:
            label, color = "⏹  Đã Hết Hạn",    QColor("#64748b")

        item = QTableWidgetItem(label)
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(color)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self._table.setItem(row, COL_STATUS, item)

    def _on_cancel(self, sub_id: int, plan_name: str) -> None:
        reply = QMessageBox.question(
            self,
            "Xác Nhận Huỷ Gói",
            f"Bạn chắc chắn muốn huỷ gói <b>{plan_name}</b>?<br>"
            "Thao tác này <b>không thể hoàn tác</b>.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self._controller.cancel_subscription(sub_id)
        except (ValueError, RuntimeError) as exc:
            QMessageBox.critical(self, "❌  Thất Bại", str(exc))
            return

        QMessageBox.information(self, "✅  Đã Huỷ", f"Gói <b>{plan_name}</b> đã được huỷ.")
        self.refresh()
        self.subscription_cancelled.emit()


# ══════════════════════════════════════════════════════════════════════════ #
#  SubscriptionPage                                                          #
# ══════════════════════════════════════════════════════════════════════════ #

class SubscriptionPage(QWidget):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        root.addLayout(self._build_header())

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setObjectName("sidebarDivider")
        root.addWidget(div)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        left_wrap = QWidget()
        left_layout = QVBoxLayout(left_wrap)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._reg_panel = RegistrationPanel()
        left_layout.addWidget(self._reg_panel)
        splitter.addWidget(left_wrap)

        right_wrap = QWidget()
        right_layout = QVBoxLayout(right_wrap)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self._sub_table = SubscriptionTable()
        right_layout.addWidget(self._sub_table)
        splitter.addWidget(right_wrap)

        splitter.setSizes([340, 660])
        root.addWidget(splitter, stretch=1)

        self._status_lbl = QLabel("Chọn hội viên và gói tập để bắt đầu.")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)

        self._reg_panel._member_combo.currentIndexChanged.connect(self._on_member_changed)
        self._reg_panel.subscription_created.connect(self._on_sub_created)
        self._reg_panel.subscription_extended.connect(self._on_sub_extended)
        self._reg_panel.checkin_done.connect(self._on_checkin_done)
        self._sub_table.subscription_cancelled.connect(self._on_sub_cancelled)

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()
        hdr.setSpacing(14)

        icon = QLabel("🎫")
        icon.setObjectName("pageIcon")

        title = QLabel("Quản Lý Gói Tập")
        title.setObjectName("pageTitle")

        sub = QLabel("Đăng ký, gia hạn, huỷ gói và check-in hội viên")
        sub.setObjectName("pageSubtitle")

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.addWidget(title)
        text_col.addWidget(sub)

        hdr.addWidget(icon)
        hdr.addLayout(text_col)
        hdr.addStretch()
        return hdr

    @Slot()
    def _on_member_changed(self) -> None:
        member_id = self._reg_panel.selected_member_id()
        if member_id is None:
            self._sub_table.clear_table()
            return
        member_name = self._reg_panel._member_combo.currentText()
        self._sub_table.load_for_member(member_id, member_name)
        self._status_lbl.setText(f"Đang xem: {member_name}")

    @Slot(int, str, str)
    def _on_sub_created(self, member_id: int, plan_type: str, ctype: str) -> None:
        self._sub_table.load_for_member(member_id, self._reg_panel._member_combo.currentText())
        self._status_lbl.setText("✅  Đăng ký gói thành công.")

    @Slot(int)
    def _on_sub_extended(self, member_id: int) -> None:
        self._sub_table.load_for_member(member_id, self._reg_panel._member_combo.currentText())
        self._status_lbl.setText("🔁  Gia hạn gói thành công.")

    @Slot(int, str)
    def _on_checkin_done(self, member_id: int, status: str) -> None:
        self._sub_table.refresh()
        name  = self._reg_panel._member_combo.currentText()
        today = date.today().strftime("%d/%m/%Y")

        if status == "valid":
            text  = f"✅  Check-in thành công — {name} ({today})"
            color = "#22c55e"
        elif status == "expired":
            text  = f"⚠️  Gói hết hạn — {name}"
            color = "#f59e0b"
        else:
            text  = f"❌  Chưa đăng ký gói — {name}"
            color = "#ef4444"

        self._status_lbl.setText(text)
        self._status_lbl.setStyleSheet(f"color: {color}; font-weight: 600;")

        QTimer.singleShot(
            5000,
            lambda: (
                self._status_lbl.setStyleSheet(""),
                self._status_lbl.setText("Chọn hội viên và gói tập để bắt đầu."),
            ),
        )

    @Slot()
    def _on_sub_cancelled(self) -> None:
        self._status_lbl.setText("🚫  Đã huỷ gói.")

    def refresh_members(self) -> None:
        self._reg_panel.refresh_members()