"""
ui/member_page.py  —  Phase 4

Trang quản lý hội viên — bảng + CRUD dialogs + tìm kiếm realtime.

Thay đổi so với Phase 3:
  • Thanh tìm kiếm với debounce 300ms (QTimer)
  • Nút Làm Mới xóa ô tìm kiếm + reload toàn bộ
  • Empty-state widget khi không có kết quả
  • Truyền join_date khi gọi update_member (giữ nguyên ngày tham gia)
  • Thông báo lỗi chi tiết cho trùng phone/email (IntegrityError)
  • Status bar phân biệt đang tìm kiếm hay hiển thị tất cả
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.member_controller import MemberController

# ── Định nghĩa cột bảng ─────────────────────────────────────────────────── #
COLUMNS   = ["ID", "Họ Tên", "Số Điện Thoại", "Email", "Giới Tính", "Ngày Tham Gia"]
COL_ID     = 0
COL_NAME   = 1
COL_PHONE  = 2
COL_EMAIL  = 3
COL_GENDER = 4
COL_JOIN   = 5

# Thời gian chờ debounce tìm kiếm (ms)
SEARCH_DEBOUNCE_MS = 300


# ══════════════════════════════════════════════════════════════════════════ #
#  MemberDialog — dùng chung cho Thêm và Sửa                               #
# ══════════════════════════════════════════════════════════════════════════ #

class MemberDialog(QDialog):
    """
    Dialog nhập liệu dùng chung cho cả Add lẫn Edit.
    Không emit signal — caller đọc .result() rồi gọi .get_data().
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        member: dict | None = None,
    ) -> None:
        super().__init__(parent)
        self._member = member       # None → chế độ Thêm
        self._setup_ui()
        if member:
            self._populate(member)

    # ── Xây dựng UI ──────────────────────────────────────────────────── #

    def _setup_ui(self) -> None:
        is_edit = self._member is not None
        self.setWindowTitle("Chỉnh Sửa Hội Viên" if is_edit else "Thêm Hội Viên Mới")
        self.setMinimumWidth(440)
        self.setModal(True)

        # Các ô nhập liệu
        self.name_input  = QLineEdit()
        self.name_input.setPlaceholderText("Họ và tên đầy đủ")

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("0xxx xxx xxx")

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("email@example.com")

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["", "Nam", "Nữ"])

        # Form
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(12)
        form.addRow("Họ Tên *",    self.name_input)
        form.addRow("Điện Thoại",  self.phone_input)
        form.addRow("Email",       self.email_input)
        form.addRow("Giới Tính",   self.gender_combo)

        # Nút
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Lưu")
        buttons.button(QDialogButtonBox.Cancel).setText("Hủy")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        # Tiêu đề
        icon      = "✏️" if is_edit else "➕"
        title_txt = "Chỉnh Sửa Hội Viên" if is_edit else "Thêm Hội Viên Mới"
        title_lbl = QLabel(f"{icon}  {title_txt}")
        title_lbl.setObjectName("dialogTitle")

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setObjectName("divider")

        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 20, 24, 20)
        root.addWidget(title_lbl)
        root.addWidget(divider)
        root.addLayout(form)
        root.addWidget(buttons)

    def _populate(self, member: dict) -> None:
        self.name_input.setText(member.get("name", ""))
        self.phone_input.setText(member.get("phone", ""))
        self.email_input.setText(member.get("email", ""))
        idx = self.gender_combo.findText(member.get("gender", ""))
        if idx >= 0:
            self.gender_combo.setCurrentIndex(idx)

    # ── Slots ────────────────────────────────────────────────────────── #

    def _on_accept(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Lỗi Nhập Liệu", "Họ tên không được để trống.")
            self.name_input.setFocus()
            return
        self.accept()

    # ── API công khai ────────────────────────────────────────────────── #

    def get_data(self) -> dict:
        return {
            "name":   self.name_input.text().strip(),
            "phone":  self.phone_input.text().strip(),
            "email":  self.email_input.text().strip(),
            "gender": self.gender_combo.currentText(),
        }


# ══════════════════════════════════════════════════════════════════════════ #
#  MemberPage                                                               #
# ══════════════════════════════════════════════════════════════════════════ #

class MemberPage(QWidget):
    """
    Trang quản lý hội viên đầy đủ.
    Sử dụng MemberController cho mọi thao tác dữ liệu.
    """

    data_changed = Signal()     # emit khi DB thay đổi để sidebar cập nhật

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = MemberController()

        # Timer debounce tìm kiếm — chỉ gọi DB sau khi người dùng dừng gõ
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(SEARCH_DEBOUNCE_MS)
        self._search_timer.timeout.connect(self._do_search)

        self._setup_ui()
        self.load_data()

    # ── Xây dựng UI ──────────────────────────────────────────────────── #

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        root.addLayout(self._build_header())
        root.addLayout(self._build_toolbar())
        root.addLayout(self._build_search_bar())

        # ── Khu vực bảng / trạng thái rỗng ──
        self._table_stack = QStackedWidget()
        self.table        = self._build_table()
        self._empty_lbl   = self._build_empty_label()

        self._table_stack.addWidget(self.table)        # index 0 → có dữ liệu
        self._table_stack.addWidget(self._empty_lbl)   # index 1 → rỗng
        root.addWidget(self._table_stack, stretch=1)

        # ── Thanh trạng thái ──
        self._status_lbl = QLabel("0 hội viên")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)

    # ── Header ───────────────────────────────────────────────────────── #

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()

        icon_lbl = QLabel("🏋️")
        icon_lbl.setObjectName("pageIcon")

        title = QLabel("Quản Lý Hội Viên")
        title.setObjectName("pageTitle")

        sub = QLabel("Xem, thêm, chỉnh sửa và xóa hội viên phòng tập")
        sub.setObjectName("pageSubtitle")

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.addWidget(title)
        text_col.addWidget(sub)

        hdr.addWidget(icon_lbl)
        hdr.addLayout(text_col)
        hdr.addStretch()
        return hdr

    # ── Toolbar (các nút CRUD) ────────────────────────────────────────── #

    def _build_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self.btn_add    = self._make_btn("➕  Thêm Hội Viên", "btnPrimary")
        self.btn_edit   = self._make_btn("✏️  Chỉnh Sửa",     "btnSecondary")
        self.btn_delete = self._make_btn("🗑️  Xóa",           "btnDanger")
        self.btn_refresh = self._make_btn("🔄  Làm Mới",      "btnNeutral")

        self.btn_edit.setEnabled(False)
        self.btn_delete.setEnabled(False)

        bar.addWidget(self.btn_add)
        bar.addWidget(self.btn_edit)
        bar.addWidget(self.btn_delete)
        bar.addStretch()
        bar.addWidget(self.btn_refresh)

        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_edit.clicked.connect(self.open_edit_dialog)
        self.btn_delete.clicked.connect(self.confirm_delete)
        self.btn_refresh.clicked.connect(self._on_refresh)    # ← xóa search rồi reload

        return bar

    # ── Thanh tìm kiếm ───────────────────────────────────────────────── #

    def _build_search_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        # Icon tìm kiếm
        search_icon = QLabel("🔍")
        search_icon.setFixedWidth(24)
        search_icon.setAlignment(Qt.AlignCenter)

        # Ô nhập tìm kiếm
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText(
            "Tìm theo tên, số điện thoại hoặc email..."
        )
        self.search_input.setMinimumHeight(36)
        self.search_input.setClearButtonEnabled(True)   # nút ✕ tích hợp sẵn

        # Khi người dùng gõ → khởi động lại debounce timer
        self.search_input.textChanged.connect(self._on_search_text_changed)

        row.addWidget(search_icon)
        row.addWidget(self.search_input, stretch=1)
        return row

    # ── Bảng dữ liệu ─────────────────────────────────────────────────── #

    def _build_table(self) -> QTableWidget:
        tbl = QTableWidget(0, len(COLUMNS))
        tbl.setHorizontalHeaderLabels(COLUMNS)

        for col in range(len(COLUMNS)):
            tbl.horizontalHeaderItem(col).setTextAlignment(Qt.AlignCenter)
        # Hành vi chọn: toàn hàng, đơn, không sửa trực tiếp
        tbl.setSelectionBehavior(QTableWidget.SelectRows)
        tbl.setSelectionMode(QTableWidget.SingleSelection)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)

        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setSortingEnabled(True)
        tbl.setShowGrid(False)

        
        tbl.horizontalHeaderItem(COL_PHONE).setTextAlignment(Qt.AlignCenter)

        # Giãn cột
        hdr = tbl.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignCenter)
        hdr.setSectionResizeMode(COL_ID,     QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(COL_NAME,   QHeaderView.Stretch)
        hdr.setSectionResizeMode(COL_PHONE,  QHeaderView.Interactive)
        hdr.setSectionResizeMode(COL_EMAIL,  QHeaderView.Stretch)
        hdr.setSectionResizeMode(COL_GENDER, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(COL_JOIN,   QHeaderView.ResizeToContents)
        hdr.setMinimumSectionSize(80)

        tbl.setColumnWidth(COL_PHONE, 150)

        tbl.itemSelectionChanged.connect(self._on_selection_changed)
        tbl.doubleClicked.connect(self.open_edit_dialog)

        return tbl

    # ── Empty-state label ─────────────────────────────────────────────── #

    @staticmethod
    def _build_empty_label() -> QLabel:
        lbl = QLabel()
        lbl.setObjectName("emptyState")
        lbl.setAlignment(Qt.AlignCenter)
        return lbl

    # ── Nút bấm helper ───────────────────────────────────────────────── #

    @staticmethod
    def _make_btn(text: str, obj_name: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(36)
        return btn

    # ══════════════════════════════════════════════════════════════════ #
    #  Tải & hiển thị dữ liệu                                           #
    # ══════════════════════════════════════════════════════════════════ #

    def _populate_table(self, members: list[dict]) -> None:
        """Điền dữ liệu vào bảng và chuyển stack sang trạng thái phù hợp."""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for row_idx, m in enumerate(members):
            self.table.insertRow(row_idx)
            self._set_cell(row_idx, COL_ID, str(row_idx + 1), Qt.AlignCenter, real_id=m.get("id"))
            self._set_cell(row_idx, COL_NAME, m.get("name", ""), Qt.AlignCenter)
            self._set_cell(row_idx, COL_PHONE, m.get("phone", ""), Qt.AlignCenter)
            self._set_cell(row_idx, COL_EMAIL, m.get("email", ""), Qt.AlignCenter)
            self._set_cell(row_idx, COL_GENDER, m.get("gender", ""), Qt.AlignCenter)
            self._set_cell(row_idx, COL_JOIN, m.get("join_date", ""), Qt.AlignCenter)
        self.table.setSortingEnabled(True)

        if members:
            self._table_stack.setCurrentIndex(0)    # hiện bảng
        else:
            # Thông báo phù hợp: đang tìm hay thực sự rỗng?
            query = self.search_input.text().strip()
            if query:
                self._empty_lbl.setText(
                    f'🔍  Không tìm thấy kết quả cho "<b>{query}</b>"'
                )
            else:
                self._empty_lbl.setText("📋  Chưa có hội viên nào.\nHãy bấm ➕ Thêm Hội Viên để bắt đầu.")
            self._table_stack.setCurrentIndex(1)    # hiện empty-state

        self._sync_buttons()

    def _set_cell(
        self,
        row: int,
        col: int,
        text: str,
        align: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter,
        real_id: int | None = None,   # thêm dòng này
    ) -> None:
        item = QTableWidgetItem(text or "")
        item.setTextAlignment(align | Qt.AlignVCenter)
        if real_id is not None : 
            item.setData(Qt.UserRole, real_id) 
        self.table.setItem(row, col, item)

    # ── load_data: tải toàn bộ (dùng khi refresh / sau CRUD) ─────────── #

    @Slot()
    def load_data(self) -> None:
        """Tải toàn bộ danh sách, không tìm kiếm."""
        try:
            members = self._controller.get_members()
        except RuntimeError as exc:
            QMessageBox.critical(self, "Lỗi Cơ Sở Dữ Liệu", str(exc))
            return

        count = len(members)
        self._status_lbl.setText(f"Tổng cộng {count} hội viên")
        self._populate_table(members)

    # ── _do_search: gọi sau khi debounce timer hết giờ ───────────────── #

    @Slot()
    def _do_search(self) -> None:
        query = self.search_input.text().strip()
        try:
            members = self._controller.search_members(query)
        except RuntimeError as exc:
            QMessageBox.critical(self, "Lỗi Tìm Kiếm", str(exc))
            return

        count = len(members)
        if query:
            self._status_lbl.setText(
                f"Tìm thấy {count} kết quả cho \"{query}\""
            )
        else:
            self._status_lbl.setText(f"Tổng cộng {count} hội viên")

        self._populate_table(members)

    # ══════════════════════════════════════════════════════════════════ #
    #  Slot tìm kiếm & refresh                                          #
    # ══════════════════════════════════════════════════════════════════ #

    @Slot(str)
    def _on_search_text_changed(self, _text: str) -> None:
        """Mỗi lần text thay đổi → reset timer debounce."""
        self._search_timer.start()      # restart = debounce

    @Slot()
    def _on_refresh(self) -> None:
        """Làm mới: xóa ô tìm kiếm + tải lại toàn bộ."""
        # blockSignals tránh timer bắn khi clear
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self._search_timer.stop()
        self.load_data()

    # ══════════════════════════════════════════════════════════════════ #
    #  CRUD Dialogs                                                      #
    # ══════════════════════════════════════════════════════════════════ #

    @Slot()
    def open_add_dialog(self) -> None:
        dlg = MemberDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return

        data = dlg.get_data()
        try:
            self._controller.add_member(
                data["name"], data["phone"], data["email"], data["gender"]
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "⚠️  Thêm Hội Viên Thất Bại", str(exc))
            return

        self._status_lbl.setText("✅  Thêm hội viên thành công!")
        self._on_refresh()              # xóa search, reload toàn bộ
        self.data_changed.emit()

    @Slot()
    def open_edit_dialog(self) -> None:
        member = self._selected_member()
        if member is None:
            QMessageBox.information(
                self, "Chưa Chọn",
                "Vui lòng chọn một hội viên trong bảng để chỉnh sửa."
            )
            return

        dlg = MemberDialog(self, member=member)
        if dlg.exec() != QDialog.Accepted:
            return

        data = dlg.get_data()
        try:
            self._controller.update_member(
                member["id"],
                data["name"],
                data["phone"],
                data["email"],
                data["gender"],
                member["join_date"],    # ← giữ nguyên ngày tham gia gốc
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "⚠️  Chỉnh Sửa Thất Bại", str(exc))
            return

        self._status_lbl.setText("✅  Cập nhật hội viên thành công!")
        self._do_search()               # giữ nguyên kết quả tìm kiếm hiện tại
        self.data_changed.emit()

    @Slot()
    def confirm_delete(self) -> None:
        member = self._selected_member()
        if member is None:
            QMessageBox.information(
                self, "Chưa Chọn",
                "Vui lòng chọn một hội viên trong bảng để xóa."
            )
            return

        reply = QMessageBox.question(
            self,
            "Xác Nhận Xóa",
            f"Bạn có chắc chắn muốn xóa hội viên "
            f"<b>{member['name']}</b>?<br>"
            "Hành động này <b>không thể hoàn tác</b>.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self._controller.delete_member(member["id"])
        except RuntimeError as exc:
            QMessageBox.critical(self, "❌  Xóa Thất Bại", str(exc))
            return

        self._status_lbl.setText("🗑️  Đã xóa hội viên.")
        self._do_search()               # giữ nguyên kết quả tìm kiếm hiện tại
        self.data_changed.emit()

    # ══════════════════════════════════════════════════════════════════ #
    #  Helpers                                                           #
    # ══════════════════════════════════════════════════════════════════ #

    def _selected_member(self) -> dict | None:
        """Trả về dict hội viên đang được chọn trong bảng, hoặc None."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        return {
            "id":        self.table.item(row, COL_ID).data(Qt.UserRole),
            "name":      self.table.item(row, COL_NAME).text(),
            "phone":     self.table.item(row, COL_PHONE).text(),
            "email":     self.table.item(row, COL_EMAIL).text(),
            "gender":    self.table.item(row, COL_GENDER).text(),
            "join_date": self.table.item(row, COL_JOIN).text(),
        }

    @Slot()
    def _on_selection_changed(self) -> None:
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        has_sel = bool(self.table.selectionModel().selectedRows())
        self.btn_edit.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)