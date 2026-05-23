"""
ui/member_page.py  —  Phase 10 + Xem Ảnh

Thay đổi so với Phase 10:
  • Thêm nút "🖼️  Xem Ảnh" nằm giữa "📷 Tạo QR" và "📸 Chụp Ảnh".
  • Thêm ImageViewDialog — dialog tối hiện đại xem ảnh hội viên.
  • _selected_member() trả thêm image_path từ DB.
  • _sync_buttons() đồng bộ thêm btn_view_image.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtCore import QUrl
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
from database import Database

# ── Định nghĩa cột bảng ─────────────────────────────────────────────────── #
COLUMNS   = ["ID", "Họ Tên", "Số Điện Thoại", "Email", "Giới Tính", "Ngày Tham Gia"]
COL_ID     = 0
COL_NAME   = 1
COL_PHONE  = 2
COL_EMAIL  = 3
COL_GENDER = 4
COL_JOIN   = 5

SEARCH_DEBOUNCE_MS = 300

# Thư mục lưu ảnh member
MEMBER_IMAGE_DIR = os.path.join("images", "members")


# ══════════════════════════════════════════════════════════════════════════ #
#  ImageViewDialog — Dialog xem ảnh hội viên                               #
# ══════════════════════════════════════════════════════════════════════════ #

class ImageViewDialog(QDialog):
    """
    Dialog tối hiện đại để xem ảnh hội viên.
    Hiển thị tên hội viên, ảnh giữ tỉ lệ fit trong vùng hiển thị.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        member_name: str = "",
        image_path: str = "",
    ) -> None:
        super().__init__(parent)
        self._member_name = member_name
        self._image_path  = image_path
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Ảnh Hội Viên")
        self.setMinimumSize(520, 560)
        self.setModal(True)
        self.setObjectName("imageViewDialog")

        # Title
        title_lbl = QLabel("🖼️   Ảnh Hội Viên")
        title_lbl.setObjectName("dialogTitle")

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setObjectName("divider")

        # Tên hội viên
        name_lbl = QLabel(self._member_name)
        name_lbl.setObjectName("imageViewMemberName")
        name_lbl.setAlignment(Qt.AlignCenter)

        # Vùng hiển thị ảnh
        self._img_lbl = QLabel()
        self._img_lbl.setObjectName("imageViewLabel")
        self._img_lbl.setAlignment(Qt.AlignCenter)
        self._img_lbl.setMinimumSize(460, 400)
        self._img_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._load_image()

        # Nút đóng
        btn_close = QPushButton("✕   Đóng")
        btn_close.setObjectName("btnCloseImage")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setMinimumHeight(35)
        btn_close.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_close)

        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(24, 20, 24, 20)
        root.addWidget(title_lbl)
        root.addWidget(divider)
        root.addWidget(name_lbl)
        root.addWidget(self._img_lbl, stretch=1)
        root.addLayout(btn_row)

    def _load_image(self) -> None:
        """Tải ảnh an toàn — không crash nếu path không tồn tại."""
        if not self._image_path or not os.path.isfile(self._image_path):
            self._img_lbl.setText("⚠️  Không tìm thấy file ảnh.")
            self._img_lbl.setObjectName("imageViewLabelEmpty")
            return

        pixmap = QPixmap(self._image_path)
        if pixmap.isNull():
            self._img_lbl.setText("⚠️  Không thể đọc file ảnh.")
            self._img_lbl.setObjectName("imageViewLabelEmpty")
            return

        # Scale giữ tỉ lệ, fit vào vùng hiển thị
        scaled = pixmap.scaled(
            460, 400,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._img_lbl.setPixmap(scaled)


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
        self._member = member
        self._setup_ui()
        if member:
            self._populate(member)

    def _setup_ui(self) -> None:
        is_edit = self._member is not None
        self.setWindowTitle("Chỉnh Sửa Hội Viên" if is_edit else "Thêm Hội Viên Mới")
        self.setMinimumWidth(440)
        self.setModal(True)

        self.name_input  = QLineEdit()
        self.name_input.setPlaceholderText("Họ và tên đầy đủ")

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("0xxx xxx xxx")

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("email@example.com")

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["", "Nam", "Nữ"])

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(12)
        form.addRow("Họ Tên *",    self.name_input)
        form.addRow("Điện Thoại",  self.phone_input)
        form.addRow("Email",       self.email_input)
        form.addRow("Giới Tính",   self.gender_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Lưu")
        buttons.button(QDialogButtonBox.Cancel).setText("Hủy")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

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

    def _on_accept(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Lỗi Nhập Liệu", "Họ tên không được để trống.")
            self.name_input.setFocus()
            return
        self.accept()

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

    data_changed = Signal()
    # signal truyền thêm member_name để QRCheckinPage hiển thị
    capture_photo_requested = Signal(int, str)  # (member_id, member_name)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = MemberController()
        self._db         = Database()

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
        root.setSpacing(18)

        root.addLayout(self._build_header())
        root.addLayout(self._build_toolbar())
        root.addLayout(self._build_search_bar())

        self._table_stack = QStackedWidget()
        self.table        = self._build_table()
        self._empty_lbl   = self._build_empty_label()

        self._table_stack.addWidget(self.table)
        self._table_stack.addWidget(self._empty_lbl)

        # ── Table Card Wrapper ──
        table_card = QFrame()
        table_card.setObjectName("tableCard")

        card_layout = QVBoxLayout(table_card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(0)

        card_layout.addWidget(self._table_stack)

        root.addWidget(table_card, stretch=1)
        self._status_lbl = QLabel("0 hội viên")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()

        hdr.setSpacing(2)
        icon_lbl = QLabel()
        pixmap = QPixmap("gym_pic.png")
        icon_lbl.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
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

        self.btn_add        = self._make_btn("➕  Thêm Hội Viên", "btnPrimary")
        self.btn_edit       = self._make_btn("✏️  Chỉnh Sửa",     "btnSecondary")
        self.btn_delete     = self._make_btn("🗑️  Xóa",           "btnDanger")
        self.btn_qr         = self._make_btn("📷  Tạo QR",        "btnSecondary")
        self.btn_view_image = self._make_btn("🖼️  Xem Ảnh",       "btnViewImage")   # ← NEW
        self.btn_photo      = self._make_btn("📸  Chụp Ảnh",      "btnSecondary")
        self.btn_refresh    = self._make_btn("🔄  Làm Mới",       "btnNeutral")

        self.btn_edit.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.btn_qr.setEnabled(False)
        self.btn_view_image.setEnabled(False)   # ← NEW: tắt khi chưa chọn hàng
        self.btn_photo.setEnabled(False)

        bar.addWidget(self.btn_add)
        bar.addWidget(self.btn_edit)
        bar.addWidget(self.btn_delete)
        bar.addWidget(self.btn_qr)
        bar.addWidget(self.btn_view_image)      # ← NEW: nằm giữa Tạo QR và Chụp Ảnh
        bar.addWidget(self.btn_photo)
        bar.addStretch()
        bar.addWidget(self.btn_refresh)

        self.btn_add.clicked.connect(self.open_add_dialog)  # Kết nối nút bấm với slot mở dialog thêm hội viên

        self.btn_edit.clicked.connect(self.open_edit_dialog)

        self.btn_delete.clicked.connect(self.confirm_delete)

        self.btn_qr.clicked.connect(self._on_generate_qr) # Kết nối nút bấm với slot tạo QR cho hội viên đã chọn

        self.btn_view_image.clicked.connect(self._on_view_image)   # ← NEW

        self.btn_photo.clicked.connect(self._on_capture_photo)

        self.btn_refresh.clicked.connect(self._on_refresh)

        return bar

    def _build_search_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        search_icon = QLabel("🔍")
        search_icon.setFixedWidth(24)
        search_icon.setAlignment(Qt.AlignCenter)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText(
            "Tìm theo tên, số điện thoại hoặc email..."
        )
        self.search_input.setMinimumHeight(36)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_text_changed)

        row.addWidget(search_icon)
        row.addWidget(self.search_input, stretch=1)
        return row

    def _build_table(self) -> QTableWidget:
        tbl = QTableWidget(0, len(COLUMNS))
        tbl.setHorizontalHeaderLabels(COLUMNS)

        for col in range(len(COLUMNS)):
            tbl.horizontalHeaderItem(col).setTextAlignment(Qt.AlignCenter)

        tbl.setSelectionBehavior(QTableWidget.SelectRows)
        tbl.setSelectionMode(QTableWidget.SingleSelection)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setAlternatingRowColors(True)

        tbl.verticalHeader().setVisible(False)
        tbl.verticalHeader().setDefaultSectionSize(50)  # Premium row height
        tbl.setSortingEnabled(True)
        tbl.setShowGrid(False)

        tbl.horizontalHeaderItem(COL_PHONE).setTextAlignment(Qt.AlignCenter)

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

    @staticmethod
    def _build_empty_label() -> QLabel:
        lbl = QLabel()
        lbl.setObjectName("emptyStateLabel")
        lbl.setAlignment(Qt.AlignCenter)
        return lbl

    @staticmethod
    def _make_btn(text: str, obj_name: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(40)
        return btn

    # ══════════════════════════════════════════════════════════════════ #
    #  Tải & hiển thị dữ liệu                                           #
    # ══════════════════════════════════════════════════════════════════ #

    def _populate_table(self, members: list[dict]) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for row_idx, m in enumerate(members):
            self.table.insertRow(row_idx)

            real_id = m.get("id")
            display_id = str(real_id).zfill(3) if real_id else ""

            self._set_cell(row_idx, COL_ID, display_id, Qt.AlignCenter, real_id=real_id)
            self._set_cell(row_idx, COL_NAME, m.get("name", ""), Qt.AlignCenter)
            self._set_cell(row_idx, COL_PHONE, m.get("phone", ""), Qt.AlignCenter)
            self._set_cell(row_idx, COL_EMAIL, m.get("email", ""), Qt.AlignCenter)
            self._set_cell(row_idx, COL_GENDER, m.get("gender", ""), Qt.AlignCenter)
            self._set_cell(row_idx, COL_JOIN, m.get("join_date", ""), Qt.AlignCenter)
        self.table.setSortingEnabled(True)

        if members:
            self._table_stack.setCurrentIndex(0)
        else:
            query = self.search_input.text().strip()
            if query:
                self._empty_lbl.setText(
                    f'🔍  Không tìm thấy kết quả cho "<b>{query}</b>"'
                )
            else:
                self._empty_lbl.setText("📋  Chưa có hội viên nào.\nHãy bấm ➕ Thêm Hội Viên để bắt đầu.")
            self._table_stack.setCurrentIndex(1)

        self._sync_buttons()

    def _set_cell(
        self,
        row: int,
        col: int,
        text: str,
        align: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter,
        real_id: int | None = None,
    ) -> None:
        item = QTableWidgetItem(text or "")
        item.setTextAlignment(align | Qt.AlignVCenter)
        if real_id is not None:
            item.setData(Qt.UserRole, real_id)
        self.table.setItem(row, col, item)

    @Slot()
    def load_data(self) -> None:
        try:
            members = self._controller.get_members()
        except RuntimeError as exc:
            QMessageBox.critical(self, "Lỗi Cơ Sở Dữ Liệu", str(exc))
            return

        count = len(members)
        self._status_lbl.setText(f"Tổng cộng {count} hội viên")
        self._populate_table(members)

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
            self._status_lbl.setText(f"Tìm thấy {count} kết quả cho \"{query}\"")
        else:
            self._status_lbl.setText(f"Tổng cộng {count} hội viên")

        self._populate_table(members)

    # ══════════════════════════════════════════════════════════════════ #
    #  Slot tìm kiếm & refresh                                          #
    # ══════════════════════════════════════════════════════════════════ #

    @Slot(str)
    def _on_search_text_changed(self, _text: str) -> None:
        self._search_timer.start()

    @Slot()
    def _on_refresh(self) -> None:
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self._search_timer.stop()
        self.load_data()

    # ══════════════════════════════════════════════════════════════════ #
    #  CRUD Dialogs                                                      #
    # ══════════════════════════════════════════════════════════════════ #

    
    @Slot()
    # Mở dialog thêm hội viên mới, sau khi thêm thành công sẽ refresh lại bảng và emit data_changed
    def open_add_dialog(self) -> None:
        dlg = MemberDialog(self) # dialog trống để nhập thông tin hội viên mới  
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.get_data() # lấy dữ liệu từ ô input 
        try:
            # Gọi MemberController để thêm hội viên mới vào DB, nếu có lỗi sẽ hiển thị QMessageBox
            self._controller.add_member(
                data["name"], data["phone"], data["email"], data["gender"]
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "⚠️  Thêm Hội Viên Thất Bại", str(exc))
            return

        self._status_lbl.setText("✅  Thêm hội viên thành công!")
        self._on_refresh()
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
                member["join_date"],
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "⚠️  Chỉnh Sửa Thất Bại", str(exc))
            return

        self._status_lbl.setText("✅  Cập nhật hội viên thành công!")
        self._do_search()
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
        self._do_search()
        self.data_changed.emit()

    # ══════════════════════════════════════════════════════════════════ #
    #  Tạo QR  (Phase 10)                                               #
    # ══════════════════════════════════════════════════════════════════ #

    @Slot()
    def _on_generate_qr(self) -> None:
        member = self._selected_member() # Lấy hội viên đã chọn để tạo QR
        if member is None:
            QMessageBox.information(
                self, "Chưa Chọn",
                "Vui lòng chọn một hội viên trong bảng để tạo QR."
            )
            return

        member_id   = member["id"]
        member_name = member["name"]

        try:
            qr_path = self._controller.generate_member_qr(member_id) # Gọi tới MemberController để tạo QR, trả về đường dẫn file QR đã tạo
        except (ValueError, RuntimeError) as exc:
            QMessageBox.critical(self, "❌  Tạo QR Thất Bại", str(exc))
            return

        self._status_lbl.setText(f"✅  Đã tạo QR cho hội viên {member_name} → {qr_path}")

        reply = QMessageBox.question(
            self,
            "✅  Tạo QR Thành Công",
            f"Đã tạo QR cho hội viên <b>{member_name}</b>.<br><br>"
            f"📁 File: <code>{qr_path}</code><br><br>"
            "Bạn có muốn mở file QR ngay bây giờ không?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )

        if reply == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(qr_path)) # Mở file QR bằng ứng dụng mặc định của hệ điều hành

    # ══════════════════════════════════════════════════════════════════ #
    #  Xem Ảnh  ← NEW                                                   #
    # ══════════════════════════════════════════════════════════════════ #

    @Slot()
    def _on_view_image(self) -> None:
        """
        Slot xử lý nút "🖼️  Xem Ảnh":
          - Nếu hội viên có image_path hợp lệ → mở ImageViewDialog.
          - Nếu chưa có ảnh → thông báo QMessageBox.
        """
        member = self._selected_member()
        if member is None:
            QMessageBox.information(
                self, "Chưa Chọn",
                "Vui lòng chọn một hội viên trong bảng để xem ảnh."
            )
            return

        image_path  = member.get("image_path", "") or ""
        member_name = member["name"]

        # Kiểm tra có ảnh không
        if not image_path or not os.path.isfile(image_path):
            QMessageBox.information(
                self, "Không Có Ảnh",
                "Hội viên này chưa có ảnh."
            )
            return

        dlg = ImageViewDialog(self, member_name=member_name, image_path=image_path)
        dlg.exec()

    # ══════════════════════════════════════════════════════════════════ #
    #  Chụp Ảnh  (Phase 10 — emit signal thay vì chụp trực tiếp)       #
    # ══════════════════════════════════════════════════════════════════ #

    @Slot()
    def _on_capture_photo(self) -> None:
        """
        Slot xử lý nút "📸 Chụp Ảnh":
          Emit capture_photo_requested(member_id, member_name) để MainWindow
          chuyển sang QRCheckinPage và kích hoạt chế độ chụp ảnh.
        """
        member = self._selected_member()
        if member is None:
            QMessageBox.information(
                self, "Chưa Chọn",
                "Vui lòng chọn một hội viên trong bảng để chụp ảnh."
            )
            return

        self.capture_photo_requested.emit(member["id"], member["name"])

    # ══════════════════════════════════════════════════════════════════ #
    #  Helpers                                                           #
    # ══════════════════════════════════════════════════════════════════ #

    def _selected_member(self) -> dict | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()

        member_id = self.table.item(row, COL_ID).data(Qt.UserRole)

        # Lấy image_path từ DB để phục vụ tính năng Xem Ảnh
        image_path = ""
        try:
            db_member = self._db.get_member(member_id) # <-- SỬA THÀNH get_member
            if db_member:
                image_path = db_member.get("image_path", "") or ""
        except Exception as e:
            # Bạn nên in lỗi ra console để sau này có lỗi khác thì dễ phát hiện hơn
            print(f"Lỗi khi lấy ảnh từ DB: {e}")
            image_path = ""

        return {
            "id":         member_id,
            "name":       self.table.item(row, COL_NAME).text(),
            "phone":      self.table.item(row, COL_PHONE).text(),
            "email":      self.table.item(row, COL_EMAIL).text(),
            "gender":     self.table.item(row, COL_GENDER).text(),
            "join_date":  self.table.item(row, COL_JOIN).text(),
            "image_path": image_path,
        }

    @Slot()
    def _on_selection_changed(self) -> None:
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        has_sel = bool(self.table.selectionModel().selectedRows())

        self.btn_edit.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)
        self.btn_qr.setEnabled(has_sel)
        self.btn_view_image.setEnabled(has_sel)   # ← NEW
        self.btn_photo.setEnabled(has_sel)