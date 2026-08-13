"""Small reusable interface components."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout


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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 17)
        layout.setSpacing(6)
        eyebrow = QLabel(label.upper())
        eyebrow.setObjectName("eyebrow")
        self.value = QLabel(value)
        self.value.setObjectName("metricValue")
        layout.addWidget(eyebrow)
        layout.addWidget(self.value)
