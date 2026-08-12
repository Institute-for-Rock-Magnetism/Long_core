"""Dependency-free Qt plotting for the four recovered LabVIEW plot families."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class MeasurementPlots(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[dict[str, object]] = []
        self.setMinimumHeight(480)

    def set_records(self, records: list[dict[str, object]]) -> None:
        self.records = records[-400:]
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f5f4f1"))
        margin, gap = 18.0, 10.0
        row_height = (self.height() - margin * 2 - gap * 3) / 4
        plots = [
            ("RAW MOMENT", ("x", "y", "z"), ("#c0521e", "#2d6970", "#d29a32")),
            ("INTENSITY", ("intensity",), ("#173f46",)),
            ("INCLINATION", ("inclination",), ("#c45231",)),
            ("DECLINATION", ("declination",), ("#287a72",)),
        ]
        for row, (title, keys, colors) in enumerate(plots):
            area = QRectF(margin, margin + row * (row_height + gap), self.width() - 2 * margin, row_height)
            painter.setPen(QPen(QColor("#e2e0da"), 1))
            painter.setBrush(QColor("#ffffff"))
            painter.drawRoundedRect(area, 10, 10)
            painter.setPen(QColor("#3f5659"))
            painter.drawText(area.adjusted(12, 8, 0, 0), Qt.AlignmentFlag.AlignTop, title)
            graph = area.adjusted(10, 28, -10, -8)
            painter.setPen(QPen(QColor("#e8e6e0"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(graph.left(), graph.center().y(), graph.right(), graph.center().y())
            if not self.records:
                painter.setPen(QColor("#8b9492"))
                painter.drawText(graph, Qt.AlignmentFlag.AlignCenter, "No measurements yet")
                continue
            for key, color in zip(keys, colors):
                values = [float(record[key]) for record in self.records if record.get(key) is not None]
                if not values:
                    continue
                low, high = min(values), max(values)
                if low == high:
                    low, high = low - 1.0, high + 1.0
                path = QPainterPath()
                for index, value in enumerate(values):
                    x = graph.left() + graph.width() * index / max(1, len(values) - 1)
                    y = graph.bottom() - graph.height() * (value - low) / (high - low)
                    path.moveTo(QPointF(x, y)) if index == 0 else path.lineTo(QPointF(x, y))
                painter.setPen(QPen(QColor(color), 2))
                painter.drawPath(path)
