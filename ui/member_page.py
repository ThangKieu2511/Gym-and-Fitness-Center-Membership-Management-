"""
ui/member_page.py
Member management page — table view + CRUD dialogs.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.member_controller import MemberController

# ── Định nghĩa cột bảng ─────────────────────────────────────────────────────── #
COLUMNS = ["ID", "Họ Tên", "Số Điện Thoại", "Email", "Giới Tính", "Ngày Tham Gia"]
COL_ID = 0
COL_NAME = 1
COL_PHONE = 2
COL_EMAIL = 3
COL_GENDER = 4
COL_JOIN = 5


# ══════════════════════════════════════════════════════════════════════════════ #
#  Member Dialog (Add / Edit)                                                   #
# ══════════════════════════════════════════════════════════════════════════════ #

class MemberDialog(QDialog):
    """
    Reusable dialog for both Add and Edit operations.
    Emits no custom signals — the caller reads .result() and .get_data().
    """

    def __init__(self, parent: QWidget | None = None, member: dict | None = None):
        super().__init__(parent)
        self._member = member  # None → Add mode
        self._setup_ui()
        if member:
            self._populate(member)

    # ── UI ──────────────────────────────────────────────────────────────── #

    def _setup_ui(self):
        is_edit = self._member is not None
        self.setWindowTitle("Chỉnh Sửa Hội Viên" if is_edit else "Thêm Hội Viên Mới")
        self.setMinimumWidth(420)
        self.setModal(True)

        # ── Ô nhập liệu ──
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Họ và tên đầy đủ")

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("0xxx xxx xxx")

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("email@example.com")

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["", "Nam", "Nữ", "Khác"])

        # ── Form layout ──
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(12)
        form.addRow("Họ Tên *", self.name_input)
        form.addRow("Điện Thoại", self.phone_input)
        form.addRow("Email", self.email_input)
        form.addRow("Giới Tính", self.gender_combo)

        # ── Nút bấm ──
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Lưu")
        buttons.button(QDialogButtonBox.Cancel).setText("Hủy")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        # ── Tiêu đề dialog ──
        icon = "✏️" if is_edit else "➕"
        title_lbl = QLabel(f"{icon}  {'Chỉnh Sửa Hội Viên' if is_edit else 'Thêm Hội Viên Mới'}")
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

    def _populate(self, member: dict):
        self.name_input.setText(member.get("name", ""))
        self.phone_input.setText(member.get("phone", ""))
        self.email_input.setText(member.get("email", ""))
        gender = member.get("gender", "")
        idx = self.gender_combo.findText(gender)
        if idx >= 0:
            self.gender_combo.setCurrentIndex(idx)

    # ── Slots ───────────────────────────────────────────────────────────── #

    def _on_accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Lỗi Nhập Liệu", "Họ tên không được để trống.")
            self.name_input.setFocus()
            return
        self.accept()

    # ── Public API ──────────────────────────────────────────────────────── #

    def get_data(self) -> dict:
        """Return the form data as a plain dict."""
        return {
            "name":   self.name_input.text().strip(),
            "phone":  self.phone_input.text().strip(),
            "email":  self.email_input.text().strip(),
            "gender": self.gender_combo.currentText(),
        }


# ══════════════════════════════════════════════════════════════════════════════ #
#  Member Page                                                                  #
# ══════════════════════════════════════════════════════════════════════════════ #

class MemberPage(QWidget):
    """
    Full member management page with table + toolbar.
    Uses MemberController for all data operations.
    """

    # Emitted when data changes so the sidebar can update counters, etc.
    data_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = MemberController()
        self._setup_ui()
        self.load_data()

    # ── UI Construction ─────────────────────────────────────────────────── #

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ── Page header ──
        root.addLayout(self._build_header())

        # ── Toolbar ──
        root.addLayout(self._build_toolbar())

        # ── Table ──
        self.table = self._build_table()
        root.addWidget(self.table)

        # ── Thanh trạng thái ──
        self._status_lbl = QLabel("0 hội viên")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)

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

    def _build_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self.btn_add     = self._make_btn("➕  Thêm Hội Viên",  "btnPrimary")
        self.btn_edit    = self._make_btn("✏️  Chỉnh Sửa",      "btnSecondary")
        self.btn_delete  = self._make_btn("🗑️  Xóa",            "btnDanger")
        self.btn_refresh = self._make_btn("🔄  Làm Mới",        "btnNeutral")

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
        self.btn_refresh.clicked.connect(self.load_data)

        return bar

    def _build_table(self) -> QTableWidget:
        tbl = QTableWidget(0, len(COLUMNS))
        tbl.setHorizontalHeaderLabels(COLUMNS)
        tbl.setSelectionBehavior(QTableWidget.SelectRows)
        tbl.setSelectionMode(QTableWidget.SingleSelection)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setSortingEnabled(True)
        tbl.setShowGrid(False)

        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(COL_ID,     QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(COL_NAME,   QHeaderView.Stretch)
        hdr.setSectionResizeMode(COL_PHONE,  QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(COL_EMAIL,  QHeaderView.Stretch)
        hdr.setSectionResizeMode(COL_GENDER, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(COL_JOIN,   QHeaderView.ResizeToContents)

        tbl.itemSelectionChanged.connect(self._on_selection_changed)
        tbl.doubleClicked.connect(self.open_edit_dialog)

        return tbl

    @staticmethod
    def _make_btn(text: str, obj_name: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(36)
        return btn

    # ── Data Operations ─────────────────────────────────────────────────── #

    @Slot()
    def load_data(self):
        """Fetch all members from the controller and populate the table."""
        try:
            members = self._controller.get_members()
        except RuntimeError as exc:
            QMessageBox.critical(self, "Lỗi Cơ Sở Dữ Liệu", str(exc))
            return

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for row_idx, m in enumerate(members):
            self.table.insertRow(row_idx)
            self._set_cell(row_idx, COL_ID,     str(m.get("id", "")),        align=Qt.AlignCenter)
            self._set_cell(row_idx, COL_NAME,   m.get("name", ""))
            self._set_cell(row_idx, COL_PHONE,  m.get("phone", ""))
            self._set_cell(row_idx, COL_EMAIL,  m.get("email", ""))
            self._set_cell(row_idx, COL_GENDER, m.get("gender", ""),         align=Qt.AlignCenter)
            self._set_cell(row_idx, COL_JOIN,   m.get("join_date", ""),      align=Qt.AlignCenter)

        self.table.setSortingEnabled(True)
        count = len(members)
        self._status_lbl.setText(f"Tổng cộng {count} hội viên")
        self._sync_buttons()

    def _set_cell(self, row: int, col: int, text: str, align: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter):
        item = QTableWidgetItem(text)
        item.setTextAlignment(align | Qt.AlignVCenter)
        self.table.setItem(row, col, item)

    # ── CRUD Dialogs ────────────────────────────────────────────────────── #

    @Slot()
    def open_add_dialog(self):
        dlg = MemberDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.get_data()
        try:
            self._controller.add_member(
                data["name"], data["phone"], data["email"], data["gender"]
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Thêm Hội Viên Thất Bại", str(exc))
            return
        self.load_data()
        self.data_changed.emit()
        self._show_toast("Thêm hội viên thành công.")

    @Slot()
    def open_edit_dialog(self):
        member = self._selected_member()
        if member is None:
            QMessageBox.information(self, "Chưa Chọn Hội Viên", "Vui lòng chọn một hội viên để chỉnh sửa.")
            return
        dlg = MemberDialog(self, member=member)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.get_data()
        try:
            self._controller.update_member(
                member["id"], data["name"], data["phone"], data["email"], data["gender"]
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Chỉnh Sửa Thất Bại", str(exc))
            return
        self.load_data()
        self.data_changed.emit()
        self._show_toast("Cập nhật hội viên thành công.")

    @Slot()
    def confirm_delete(self):
        member = self._selected_member()
        if member is None:
            QMessageBox.information(self, "Chưa Chọn Hội Viên", "Vui lòng chọn một hội viên để xóa.")
            return

        reply = QMessageBox.question(
            self,
            "Xác Nhận Xóa",
            f"Bạn có chắc chắn muốn xóa hội viên <b>{member['name']}</b>?<br>"
            "Hành động này không thể hoàn tác.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self._controller.delete_member(member["id"])
        except RuntimeError as exc:
            QMessageBox.critical(self, "Xóa Thất Bại", str(exc))
            return
        self.load_data()
        self.data_changed.emit()
        self._show_toast("Đã xóa hội viên.")

    # ── Helpers ─────────────────────────────────────────────────────────── #

    def _selected_member(self) -> dict | None:
        """Return the currently selected member as a dict, or None."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        return {
            "id":        int(self.table.item(row, COL_ID).text()),
            "name":      self.table.item(row, COL_NAME).text(),
            "phone":     self.table.item(row, COL_PHONE).text(),
            "email":     self.table.item(row, COL_EMAIL).text(),
            "gender":    self.table.item(row, COL_GENDER).text(),
            "join_date": self.table.item(row, COL_JOIN).text(),
        }

    @Slot()
    def _on_selection_changed(self):
        self._sync_buttons()

    def _sync_buttons(self):
        has_sel = bool(self.table.selectionModel().selectedRows())
        self.btn_edit.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)

    @staticmethod
    def _show_toast(msg: str):
        """Simple feedback — could be replaced with a toast widget later."""
        # No-op visual; status bar updated via load_data; keeping it simple.
        pass