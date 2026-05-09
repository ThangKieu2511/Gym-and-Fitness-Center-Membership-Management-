"""
ui/widgets/chart_widget.py  —  Phase Chart

Cung cấp 2 widget biểu đồ cho Dashboard:
  • PieChartWidget  — tỷ lệ valid / expired check-in tháng này (Đã nâng cấp Donut Chart)
  • BarChartWidget  — top 5 hội viên đi tập nhiều nhất tháng (số ngày)
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Qt5Agg")  # phải set trước khi import pyplot

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator  # Import thêm để ép trục Y thành số nguyên

from PySide6.QtWidgets import QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt


# ══════════════════════════════════════════════════════════════════════════ #
#  PieChartWidget                                                             #
# ══════════════════════════════════════════════════════════════════════════ #

class PieChartWidget(QWidget):
    """Biểu đồ tròn (Donut): tỷ lệ valid / expired check-in trong tháng hiện tại."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title = QLabel("🥧  Tỷ Lệ Check-in Tháng Này")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self._figure = Figure(figsize=(4, 3), tight_layout=True)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setMinimumHeight(220)
        layout.addWidget(self._canvas)

    def update_chart(self, stats: dict) -> None:
        """
        Parameters
        ----------
        stats : dict
            {"valid": int, "expired": int}
        """
        valid   = stats.get("valid", 0)
        expired = stats.get("expired", 0)

        self._figure.clear()
        ax = self._figure.add_subplot(111)

        total = valid + expired
        if total == 0:
            ax.text(0.5, 0.5, "Không có dữ liệu",
                    ha="center", va="center", transform=ax.transAxes)
            ax.axis("off")
        else:
            sizes  = [valid, expired]
            labels = [
                f"Hợp lệ\n({valid})",
                f"Hết hạn\n({expired})",
            ]
            colors = ['#22c55e', '#f59e0b']

            # Nâng cấp thành Donut Chart hiện đại
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                autopct="%1.1f%%",
                startangle=90,
                colors=colors,
                wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2),
                textprops={'fontsize': 9, 'fontweight': '500'}
            )
            
            ax.set_title("Check-in theo trạng thái", fontsize=10, pad=6, fontweight='bold')

        self._canvas.draw()


# ══════════════════════════════════════════════════════════════════════════ #
#  BarChartWidget                                                             #
# ══════════════════════════════════════════════════════════════════════════ #

class BarChartWidget(QWidget):
    """Biểu đồ cột: top 5 hội viên đi tập nhiều ngày nhất tháng."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title = QLabel("📊  Top 5 Hội Viên — Số Ngày Đi Tập")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self._figure = Figure(figsize=(5, 3), tight_layout=True)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setMinimumHeight(220)
        layout.addWidget(self._canvas)

    def update_chart(self, rows: list[dict]) -> None:
        """
        Parameters
        ----------
        rows : list[dict]
            Mỗi phần tử có key: member_name, days_count
        """
        self._figure.clear()
        ax = self._figure.add_subplot(111)

        if not rows:
            ax.text(0.5, 0.5, "Không có dữ liệu",
                    ha="center", va="center", transform=ax.transAxes)
            ax.axis("off")
        else:
            # Chỉ lấy tên chính (từ cuối cùng)
            names = []
            for r in rows:
                full_name = r.get("member_name", "").strip()
                short_name = full_name.split()[-1] if full_name else ""
                names.append(short_name)
                
            days   = [r.get("days_count", 0)   for r in rows]

            # Vẽ cột với màu hiện đại, độ rộng vừa phải
            bars = ax.bar(names, days, color='#3b82f6', width=0.5, zorder=3)

            ax.set_ylabel("Số ngày", fontsize=9)
            ax.set_title("Top 5 hội viên tháng này", fontsize=10, pad=6, fontweight='bold')
            ax.tick_params(axis="x", labelsize=8)
            ax.tick_params(axis="y", labelsize=8)

            # Ghi số lượng ngay trên đầu cột thay vì dùng loop cồng kềnh
            ax.bar_label(bars, padding=3, fontsize=9, fontweight='bold', color='#475569')

            # --- TỐI ƯU UI/UX ---
            # 1. Bỏ viền thừa xung quanh
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)
            
            # 2. Ép trục Y chỉ hiển thị số nguyên
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            
            # 3. Thêm lưới nền mờ đứt nét
            ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
            ax.set_axisbelow(True)
            
            # 4. Ẩn các gạch đánh dấu ở trục
            ax.tick_params(axis='both', which='both', length=0)

        self._canvas.draw()