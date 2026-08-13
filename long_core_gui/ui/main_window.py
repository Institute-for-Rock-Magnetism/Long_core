"""Main application shell and orchestration."""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from ..domain import Action, ActionBuilder, HomingPolicy, QueuePlan, QueueStep
from ..infrastructure import ApplicationConfig
from ..services import RunEngine, WorkspaceRepository
from .commissioning import CommissioningPage
from .pages import InstrumentsPage, LogsPage, OverviewPage, PlotsPage, QueuePage, RunPage


class MainWindow(QMainWindow):
    def __init__(self, config: ApplicationConfig, repository: WorkspaceRepository, logger: logging.Logger) -> None:
        super().__init__()
        self.config, self.repository, self.logger = config, repository, logger
        self.queue_steps: list[QueueStep] = []
        self.results: list[dict[str, object]] = []
        self.homing = HomingPolicy.EVERY_QUEUE
        self.events: list[str] = []
        self.engine = RunEngine(self)
        self.engine.action_started.connect(self._on_action)
        self.engine.measurement_ready.connect(self._on_measurement)
        self.engine.progress_changed.connect(self._on_progress)
        self.engine.state_changed.connect(self._on_state)
        self.engine.failed.connect(self._on_failure)
        self.engine.finished.connect(self._on_finished)
        self.setWindowTitle("Long Core Control")
        icon_path = Path(__file__).resolve().parent / "assets" / "long-core-control.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1440, 900)
        self.setMinimumSize(1080, 700)
        self._build_ui()
        self._restore()
        self.show_page("Overview")

    def _build_ui(self) -> None:
        central = QWidget(); shell = QHBoxLayout(central); shell.setContentsMargins(0, 0, 0, 0); shell.setSpacing(0)
        sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(248)
        nav = QVBoxLayout(sidebar); nav.setContentsMargins(18, 24, 18, 20); nav.setSpacing(7)

        brand_row = QHBoxLayout(); brand_row.setSpacing(12)
        brand_mark = QLabel("LC"); brand_mark.setObjectName("brandMark"); brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_copy = QVBoxLayout(); brand_copy.setSpacing(1)
        brand = QLabel("LONG CORE"); brand.setObjectName("brand")
        caption = QLabel("PALEOMAGNETIC LAB"); caption.setObjectName("brandCaption")
        brand_copy.addWidget(brand); brand_copy.addWidget(caption)
        brand_row.addWidget(brand_mark); brand_row.addLayout(brand_copy, 1)
        nav.addLayout(brand_row); nav.addSpacing(25)

        self.stack = QStackedWidget()
        self.pages = {
            "Overview": OverviewPage(self), "Queue": QueuePage(self), "Run": RunPage(self),
            "Plots": PlotsPage(self), "Instruments": InstrumentsPage(self),
            "Commissioning": CommissioningPage(self), "Logs": LogsPage(self),
        }
        self.nav_buttons: dict[str, QPushButton] = {}
        workspace_label = QLabel("WORKSPACE"); workspace_label.setObjectName("navSection")
        nav.addWidget(workspace_label)
        for name in ("Overview", "Queue", "Run", "Plots"):
            page = self.pages[name]
            control = QPushButton(name); control.setCheckable(True); control.setProperty("kind", "nav")
            control.clicked.connect(lambda checked=False, target=name: self.show_page(target))
            nav.addWidget(control); self.nav_buttons[name] = control; self.stack.addWidget(page)
        nav.addSpacing(17)
        system_label = QLabel("SYSTEM"); system_label.setObjectName("navSection")
        nav.addWidget(system_label)
        for name in ("Instruments", "Commissioning", "Logs"):
            page = self.pages[name]
            control = QPushButton(name); control.setCheckable(True); control.setProperty("kind", "nav")
            control.clicked.connect(lambda checked=False, target=name: self.show_page(target))
            nav.addWidget(control); self.nav_buttons[name] = control; self.stack.addWidget(page)
        nav.addStretch()

        safety_card = QFrame(); safety_card.setObjectName("sidebarSafety")
        safety_layout = QVBoxLayout(safety_card); safety_layout.setSpacing(3)
        safety_title = QLabel("PORT SAFETY LOCK"); safety_title.setObjectName("sidebarSafetyTitle")
        safety = QLabel(
            "Enabled by operator" if self.config.hardware_enabled
            else "Closed by default\nNo physical ports open"
        )
        safety.setObjectName("sidebarSafetyCopy"); safety.setWordWrap(True)
        safety_layout.addWidget(safety_title); safety_layout.addWidget(safety)
        nav.addWidget(safety_card)

        content = QVBoxLayout(); content.setContentsMargins(0, 0, 0, 0); content.setSpacing(0)
        top = QFrame(); top.setObjectName("topbar"); top_layout = QHBoxLayout(top); top_layout.setContentsMargins(34, 14, 34, 14)
        location = QVBoxLayout(); location.setSpacing(0)
        app_label = QLabel("2G U-CHANNEL LONG CORE"); app_label.setObjectName("topEyebrow")
        self.page_location = QLabel("Control center"); self.page_location.setObjectName("topLocation")
        location.addWidget(app_label); location.addWidget(self.page_location)
        top_layout.addLayout(location); top_layout.addStretch()
        self.mode_badge = QLabel("PORT ACCESS ENABLED" if self.config.hardware_enabled else "SIMULATION MODE")
        self.mode_badge.setObjectName("modeBadgeLive" if self.config.hardware_enabled else "modeBadge")
        top_layout.addWidget(self.mode_badge)
        body = QFrame(); body.setObjectName("contentBody")
        body_layout = QVBoxLayout(body); body_layout.setContentsMargins(34, 28, 34, 32); body_layout.addWidget(self.stack)
        content.addWidget(top); content.addWidget(body, 1)
        content_widget = QWidget(); content_widget.setLayout(content)
        shell.addWidget(sidebar); shell.addWidget(content_widget, 1); self.setCentralWidget(central)

    def _restore(self) -> None:
        try:
            self.queue_steps, self.homing, self.results = self.repository.load()
            self.log_event("Workspace restored")
        except RuntimeError as exc:
            self.log_event(str(exc), level=logging.ERROR)
            QMessageBox.warning(self, "Workspace recovery", str(exc))
        self.refresh_all()

    def show_page(self, name: str) -> None:
        self.stack.setCurrentWidget(self.pages[name])
        self.page_location.setText(name)
        for page_name, control in self.nav_buttons.items(): control.setChecked(page_name == name)
        refresh = getattr(self.pages[name], "refresh", None)
        if refresh: refresh()

    def refresh_all(self) -> None:
        for page in self.pages.values():
            refresh = getattr(page, "refresh", None)
            if refresh: refresh()

    def changed(self, message: str) -> None:
        self.log_event(message); self._persist(); self.refresh_all()

    def log_event(self, message: str, level: int = logging.INFO) -> None:
        line = f"{datetime.now().strftime('%H:%M:%S')}  {message}"
        self.events.append(line); self.events = self.events[-500:]
        self.logger.log(level, message)
        for name in ("Overview", "Logs"):
            page = self.pages.get(name)
            if page and hasattr(page, "refresh"): page.refresh()

    def _persist(self) -> None:
        try:
            self.repository.save(self.queue_steps, self.homing, self.results)
        except Exception as exc:
            self.log_event(f"Could not save workspace: {exc}", logging.ERROR)

    def start_run(self) -> None:
        if not self.queue_steps: return
        run_page: RunPage = self.pages["Run"]
        self.homing = HomingPolicy(run_page.homing.currentText())
        try:
            actions = ActionBuilder().build(QueuePlan(tuple(self.queue_steps), self.homing))
        except Exception as exc:
            QMessageBox.warning(self, "Cannot build run", str(exc)); return
        run_page.actions.setPlainText("\n".join(self._format_action(index, action) for index, action in enumerate(actions, 1)))
        self.log_event(f"Built {len(actions)} actions for {len(self.queue_steps)} queue step(s)")
        self.engine.start(actions); self.refresh_all()

    @staticmethod
    def _format_action(index: int, action: Action) -> str:
        details = [action.opcode.value]
        if action.sample_id: details.append(action.sample_id)
        if action.move_target: details.append(action.move_target.value)
        if action.axis: details.append(action.axis.value)
        if action.daq_type: details.append(action.daq_type.value)
        if action.value is not None: details.append(str(action.value))
        return f"{index:03d}  " + "  |  ".join(details)

    def toggle_pause(self) -> None:
        if self.engine.state == "Running": self.engine.pause()
        elif self.engine.state == "Paused": self.engine.resume()

    def abort_run(self) -> None:
        if self.engine.active and QMessageBox.question(self, "Abort run", "Stop at the next safe action boundary?") == QMessageBox.StandardButton.Yes:
            self.engine.abort()

    def _on_action(self, current: int, total: int, action: Action) -> None:
        self.log_event(f"Action {current}/{total}: {action.opcode.value} ({action.sample_id or 'queue'})")

    def _on_measurement(self, record: dict[str, object]) -> None:
        self.results.append(record)
        self.pages["Plots"].refresh()

    def _on_progress(self, current: int, total: int) -> None:
        self.pages["Run"].progress.setValue(round(current * 100 / total))

    def _on_state(self, state: str, message: str) -> None:
        page: RunPage = self.pages["Run"]
        page.state.setText(state); page.detail.setText(message); page.pause.setText("Resume" if state == "Paused" else "Pause")
        self.log_event(message); self.refresh_all()

    def _on_failure(self, message: str) -> None:
        self.log_event(message, logging.ERROR); QMessageBox.critical(self, "Run failed", message)

    def _on_finished(self, state: str) -> None:
        self.pages["Run"].state.setText(state); self.log_event(f"Run {state.lower()}"); self._persist(); self.refresh_all()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.engine.active:
            answer = QMessageBox.question(self, "Run active", "Abort the active simulation and close?")
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore(); return
            self.engine.abort()
        self._persist(); event.accept()
