"""
ui/widgets/chart_widget.py  —  Phase Chart

Cung cấp 2 widget biểu đồ cho Dashboard:
  • PieChartWidget  — tỷ lệ valid / expired check-in tháng này
  • BarChartWidget  — top 5 hội viên đi tập nhiều nhất tháng (số ngày)
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Qt5Agg")  # phải set trước khi import pyplot

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt


# ══════════════════════════════════════════════════════════════════════════ #
#  PieChartWidget                                                             #
# ══════════════════════════════════════════════════════════════════════════ #

class PieChartWidget(QWidget):
    """Biểu đồ tròn: tỷ lệ valid / expired check-in trong tháng hiện tại."""

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
                f"Hợp lệ\n{valid}",
                f"Hết hạn\n{expired}",
            ]
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                autopct="%1.1f%%",
                startangle=90,
            )
            for at in autotexts:
                at.set_fontsize(9)
            ax.set_title("Check-in theo trạng thái", fontsize=10, pad=6)

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
            names  = [r.get("member_name", "") for r in rows]
            days   = [r.get("days_count", 0)   for r in rows]

            bars = ax.bar(names, days)

            ax.set_xlabel("Hội viên",   fontsize=9)
            ax.set_ylabel("Số ngày",    fontsize=9)
            ax.set_title("Top 5 hội viên tháng này", fontsize=10, pad=6)
            ax.tick_params(axis="x", labelsize=8)
            ax.tick_params(axis="y", labelsize=8)

            # Ghi số lên đỉnh cột
            for bar, val in zip(bars, days):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.1,
                    str(val),
                    ha="center", va="bottom", fontsize=9,
                )

        self._canvas.draw()