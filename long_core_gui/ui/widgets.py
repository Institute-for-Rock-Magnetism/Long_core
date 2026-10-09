"""Small reusable interface components."""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget, QGraphicsDropShadowEffect


def page_title(title: str, subtitle: str) -> tuple[QLabel, QLabel]:
    heading = QLabel(title)
    heading.setObjectName("pageTitle")
    caption = QLabel(subtitle)
    caption.setObjectName("pageSubtitle")
    caption.setWordWrap(True)
    return heading, caption


def button(text: str, kind: str = "secondary") -> QPushButton:
    control = QPushButton(text)
    control.setProperty("kind", kind)
    control.setCursor(Qt.CursorShape.PointingHandCursor)
    return control


class MetricCard(QFrame):
    def __init__(self, label: str, value: str = "0", tone: str = "teal") -> None:
        super().__init__()
        self.setObjectName("metricCard")
        self.setProperty("tone", tone)
        glass_shadow(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 17)
        layout.setSpacing(6)
        eyebrow = QLabel(label.upper())
        eyebrow.setObjectName("eyebrow")
        self.value = QLabel(value)
        self.value.setObjectName("metricValue")
        layout.addWidget(eyebrow)
        layout.addWidget(self.value)


class GlassCanvas(QWidget):
    """Diffused, static backdrop: glass stays legible without platform blur APIs."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#F3F0E8"))
        for x, y, radius, color in (
            (0.36, 0.12, 0.55, "#F4A261"),
            (0.95, 0.65, 0.65, "#80B6AF"),
            (0.60, 0.95, 0.45, "#D7BD8A"),
        ):
            gradient = QRadialGradient(QPointF(self.width()*x, self.height()*y), self.width()*radius)
            tint = QColor(color); tint.setAlpha(65)
            gradient.setColorAt(0, tint); tint.setAlpha(0)
            gradient.setColorAt(1, tint)
            painter.fillRect(self.rect(), gradient)


def glass_shadow(widget: QWidget) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(24)
    shadow.setOffset(0, 5)
    shadow.setColor(QColor(16, 42, 54, 24))
    widget.setGraphicsEffect(shadow)
