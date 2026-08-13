"""Dependency-free Qt plotting for the four recovered LabVIEW plot families."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
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
        painter.fillRect(self.rect(), QColor("#efede7"))
        margin, gap = 14.0, 12.0
        row_height = (self.height() - margin * 2 - gap * 3) / 4
        plots = [
            ("RAW MOMENT", ("x", "y", "z"), ("#c0521e", "#247078", "#c38b20")),
            ("INTENSITY", ("intensity",), ("#153f47",)),
            ("INCLINATION", ("inclination",), ("#c0521e",)),
            ("DECLINATION", ("declination",), ("#247078",)),
        ]
        for row, (title, keys, colors) in enumerate(plots):
            area = QRectF(margin, margin + row * (row_height + gap), self.width() - 2 * margin, row_height)
            painter.setPen(QPen(QColor("#d8d4ca"), 1))
            painter.setBrush(QColor("#ffffff"))
            painter.drawRoundedRect(area, 13, 13)
            painter.setFont(QFont("Avenir Next", 9, QFont.Weight.DemiBold))
            painter.setPen(QColor("#3b5054"))
            painter.drawText(area.adjusted(14, 9, -14, 0), Qt.AlignmentFlag.AlignTop, title)
            graph = area.adjusted(14, 32, -14, -12)
            for division in range(1, 4):
                y = graph.top() + graph.height() * division / 4
                painter.setPen(QPen(QColor("#ebe8e1"), 1, Qt.PenStyle.DotLine))
                painter.drawLine(graph.left(), y, graph.right(), y)
            if not self.records:
                painter.setFont(QFont("Avenir Next", 10))
                painter.setPen(QColor("#8b9492"))
                painter.drawText(graph, Qt.AlignmentFlag.AlignCenter, "No measurements yet")
                continue

            values_by_key = {
                key: [float(record[key]) for record in self.records if record.get(key) is not None]
                for key in keys
            }
            combined = [value for values in values_by_key.values() for value in values]
            if not combined:
                continue
            low, high = min(combined), max(combined)
            if low == high:
                low, high = low - 1.0, high + 1.0
            padding = max((high - low) * 0.08, 1e-9)
            low -= padding; high += padding

            painter.setFont(QFont("Avenir Next", 8))
            painter.setPen(QColor("#7b8583"))
            painter.drawText(area.adjusted(0, 9, -14, 0), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight, f"{low:.3g} to {high:.3g}")

            legend_x = area.left() + 118
            for key, color in zip(keys, colors):
                painter.setBrush(QColor(color)); painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(legend_x, area.top() + 15), 3, 3)
                painter.setPen(QColor("#657370"))
                painter.drawText(QRectF(legend_x + 7, area.top() + 7, 32, 16), Qt.AlignmentFlag.AlignVCenter, key.upper())
                legend_x += 43

            for key, color in zip(keys, colors):
                values = values_by_key[key]
                if not values:
                    continue
                path = QPainterPath()
                for index, value in enumerate(values):
                    x = graph.left() + graph.width() * index / max(1, len(values) - 1)
                    y = graph.bottom() - graph.height() * (value - low) / (high - low)
                    path.moveTo(QPointF(x, y)) if index == 0 else path.lineTo(QPointF(x, y))
                painter.setPen(QPen(QColor(color), 2.2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)
                last_x = graph.left() + graph.width() * (len(values) - 1) / max(1, len(values) - 1)
                last_y = graph.bottom() - graph.height() * (values[-1] - low) / (high - low)
                painter.setPen(QPen(QColor("#ffffff"), 1.5)); painter.setBrush(QColor(color))
                painter.drawEllipse(QPointF(last_x, last_y), 3.5, 3.5)
