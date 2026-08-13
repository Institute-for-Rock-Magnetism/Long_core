"""Navigable pages for queue preparation, execution, plots, and diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..domain import (
    ContinuousMeasurementParameters, DiscreteMeasurementParameters,
    DomainValidationError, HomingPolicy, MeasurementMode, MeasurementType,
    QueuePlan, QueueStep, SampleMetadata, TreatmentOrder, TreatmentType,
)
from ..infrastructure import Subsystem
from ..infrastructure.error_codes import LegacyErrorCatalog
from ..infrastructure.legacy_settings import LegacySettings
from .plot_widget import MeasurementPlots
from .widgets import MetricCard, button, page_title

if TYPE_CHECKING:
    from .main_window import MainWindow


def _heading(layout: QVBoxLayout, title: str, subtitle: str) -> None:
    heading, caption = page_title(title, subtitle)
    layout.addWidget(heading)
    layout.addWidget(caption)
    layout.addSpacing(10)


class OverviewPage(QWidget):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__()
        self.window = window
        root = QVBoxLayout(self)
        _heading(root, "Control center", "A calm view of the queue, run state, instruments, and recent events.")
        row = QHBoxLayout()
        self.cards = {
            "queued": MetricCard("Queued", tone="rust"),
            "results": MetricCard("Measurements", tone="gold"),
            "state": MetricCard("Run state", "Idle", tone="teal"),
            "mode": MetricCard("Operating mode", "SIM", tone="slate"),
        }
        for card in self.cards.values():
            row.addWidget(card)
        root.addLayout(row)
        actions = QHBoxLayout()
        for text, page, kind in (
            ("Prepare queue", "Queue", "secondary"),
            ("Open run console", "Run", "primary"),
            ("Inspect plots", "Plots", "secondary"),
        ):
            control = button(text, kind)
            control.clicked.connect(lambda checked=False, name=page: window.show_page(name))
            actions.addWidget(control)
        actions.addStretch()
        root.addLayout(actions)
        group = QGroupBox("Recent activity")
        box = QVBoxLayout(group)
        self.activity = QPlainTextEdit()
        self.activity.setReadOnly(True)
        self.activity.setProperty("console", True)
        self.activity.setPlaceholderText("Operator activity will appear here.")
        box.addWidget(self.activity)
        root.addWidget(group, 1)

    def refresh(self) -> None:
        self.cards["queued"].value.setText(str(len(self.window.queue_steps)))
        self.cards["results"].value.setText(str(len(self.window.results)))
        self.cards["state"].value.setText(self.window.engine.state)
        self.cards["mode"].value.setText("SIM" if self.window.config.simulation_mode else "LOCKED")
        self.activity.setPlainText("\n".join(self.window.events[-12:][::-1]))


class QueuePage(QWidget):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__()
        self.window = window
        root = QVBoxLayout(self)
        _heading(root, "Measurement queue", "Build validated recipes from the recovered LabVIEW queue and action clusters.")
        form_box = QGroupBox("Add queue step")
        form = QGridLayout(form_box)
        self.sample_id = QLineEdit(); self.sample_id.setPlaceholderText("Sample ID")
        self.measurement = QComboBox(); self.measurement.addItems([item.value for item in MeasurementType])
        self.mode = QComboBox(); self.mode.addItems([item.value for item in MeasurementMode])
        self.treatment = QComboBox(); self.treatment.addItems([item.value for item in TreatmentType])
        self.order = QComboBox(); self.order.addItems([item.value for item in TreatmentOrder])
        self.value = QDoubleSpinBox(); self.value.setRange(0, 100000); self.value.setDecimals(3)
        self.positions = QLineEdit("0, 10, 20"); self.positions.setPlaceholderText("Discrete positions in mm")
        fields = [
            ("Sample ID", self.sample_id), ("Measurement", self.measurement),
            ("Mode", self.mode), ("Treatment", self.treatment),
            ("Treatment order", self.order), ("Amplitude / temperature / pause", self.value),
        ]
        for index, (label, control) in enumerate(fields):
            column, row = index % 3, (index // 3) * 2
            form.addWidget(QLabel(label), row, column)
            form.addWidget(control, row + 1, column)
        form.addWidget(QLabel("Discrete positions"), 4, 0)
        form.addWidget(self.positions, 5, 0, 1, 2)
        add = button("Add step", "primary"); add.clicked.connect(self.add_step)
        form.addWidget(add, 5, 2)
        root.addWidget(form_box)
        toolbar = QHBoxLayout()
        for label, callback in (
            ("Remove selected", self.remove_selected), ("Clear", self.clear),
            ("Import queue", self.import_plan), ("Export queue", self.export_plan),
        ):
            control = button(label); control.clicked.connect(callback); toolbar.addWidget(control)
        toolbar.addStretch(); root.addLayout(toolbar)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["#", "Sample", "Measurement", "Mode", "Treatment", "Order", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(38)
        root.addWidget(self.table, 1)

    def add_step(self) -> None:
        try:
            measurement = MeasurementType(self.measurement.currentText())
            treatment = TreatmentType(self.treatment.currentText())
            mode = None if measurement is MeasurementType.NONE else MeasurementMode(self.mode.currentText())
            continuous = ContinuousMeasurementParameters() if mode is MeasurementMode.CONTINUOUS else None
            discrete = None
            if mode is MeasurementMode.DISCRETE:
                positions = tuple(float(value.strip()) for value in self.positions.text().split(",") if value.strip())
                discrete = DiscreteMeasurementParameters(positions_mm=positions)
            treatment_value = None
            pause_seconds = None
            if treatment is TreatmentType.PAUSE:
                pause_seconds = max(0.1, self.value.value())
            elif treatment is not TreatmentType.NONE:
                treatment_value = self.value.value()
            step = QueueStep(
                sample=SampleMetadata(sample_id=self.sample_id.text().strip()),
                measurement_type=measurement,
                treatment_type=treatment,
                treatment_order=TreatmentOrder(self.order.currentText()),
                measurement_mode=mode,
                treatment_value=treatment_value,
                pause_seconds=pause_seconds,
                continuous=continuous,
                discrete=discrete,
            )
        except (DomainValidationError, ValueError) as exc:
            QMessageBox.warning(self, "Invalid queue step", str(exc))
            return
        self.window.queue_steps.append(step)
        self.sample_id.clear()
        self.window.changed(f"Added {step.sample.sample_id} to the queue")

    def remove_selected(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            del self.window.queue_steps[row]
        if rows:
            self.window.changed(f"Removed {len(rows)} queue step(s)")

    def clear(self) -> None:
        if self.window.queue_steps and QMessageBox.question(self, "Clear queue", "Remove all queue steps?") == QMessageBox.StandardButton.Yes:
            self.window.queue_steps.clear(); self.window.changed("Cleared the queue")

    def import_plan(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import queue", "", "JSON (*.json)")
        if not path: return
        try:
            plan = self.window.repository.import_plan(path)
        except RuntimeError as exc:
            QMessageBox.critical(self, "Import failed", str(exc)); return
        self.window.queue_steps = list(plan.steps)
        self.window.homing = plan.homing
        self.window.changed(f"Imported queue from {path}")

    def export_plan(self) -> None:
        if not self.window.queue_steps:
            QMessageBox.information(self, "Empty queue", "Add at least one queue step first."); return
        path, _ = QFileDialog.getSaveFileName(self, "Export queue", "long-core-queue.json", "JSON (*.json)")
        if path:
            self.window.repository.export_plan(path, QueuePlan(tuple(self.window.queue_steps), self.window.homing))
            self.window.log_event(f"Exported queue to {path}")

    def refresh(self) -> None:
        self.table.setRowCount(len(self.window.queue_steps))
        for row, step in enumerate(self.window.queue_steps):
            values = [row + 1, step.sample.sample_id, step.measurement_type.value,
                      step.measurement_mode.value if step.measurement_mode else "None",
                      step.treatment_type.value, step.treatment_order.value,
                      step.pause_seconds if step.pause_seconds is not None else step.treatment_value]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem("" if value is None else str(value)))


class RunPage(QWidget):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(); self.window = window
        root = QVBoxLayout(self)
        _heading(root, "Run console", "Review the generated action sequence before any execution begins.")
        controls = QHBoxLayout()
        self.homing = QComboBox(); self.homing.addItems([item.value for item in HomingPolicy])
        self.start = button("Start simulation", "primary"); self.start.clicked.connect(window.start_run)
        self.pause = button("Pause"); self.pause.clicked.connect(window.toggle_pause)
        self.abort = button("Abort", "danger"); self.abort.clicked.connect(window.abort_run)
        controls.addWidget(QLabel("Homing policy")); controls.addWidget(self.homing)
        controls.addStretch(); controls.addWidget(self.start); controls.addWidget(self.pause); controls.addWidget(self.abort)
        root.addLayout(controls)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); root.addWidget(self.progress)
        split = QHBoxLayout()
        state_box = QGroupBox("Current state"); state_layout = QVBoxLayout(state_box)
        self.state = QLabel("Idle"); self.state.setObjectName("metricValue")
        self.detail = QLabel("Ready to build a plan"); self.detail.setWordWrap(True)
        state_layout.addWidget(self.state); state_layout.addWidget(self.detail); state_layout.addStretch()
        action_box = QGroupBox("Auditable action plan"); action_layout = QVBoxLayout(action_box)
        self.actions = QPlainTextEdit(); self.actions.setReadOnly(True)
        self.actions.setProperty("console", True)
        self.actions.setPlaceholderText("The validated action sequence will appear here before execution.")
        action_layout.addWidget(self.actions)
        split.addWidget(state_box, 1); split.addWidget(action_box, 3); root.addLayout(split, 1)

    def refresh(self) -> None:
        self.homing.setCurrentText(self.window.homing.value)
        self.start.setEnabled(bool(self.window.queue_steps) and not self.window.engine.active)
        self.pause.setEnabled(self.window.engine.active)
        self.abort.setEnabled(self.window.engine.active)


class PlotsPage(QWidget):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(); self.window = window
        root = QVBoxLayout(self)
        _heading(root, "Measurement plots", "Raw XYZ moment, intensity, inclination, and declination in the original four-plot arrangement.")
        self.plots = MeasurementPlots(); root.addWidget(self.plots, 1)

    def refresh(self) -> None:
        self.plots.set_records(self.window.results)


class InstrumentsPage(QWidget):
    """Recovered instrument topology; scrolls so every table stays reachable."""

    def __init__(self, window: "MainWindow") -> None:
        super().__init__(); self.window = window
        shell = QVBoxLayout(self); shell.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(); root = QVBoxLayout(content)
        shell.addWidget(scroll); scroll.setWidget(content)
        _heading(root, "Instruments", "Recovered serial topology with intentionally unassigned physical ports.")
        warning = QFrame(); warning.setObjectName("safetyCard"); warning_layout = QVBoxLayout(warning)
        warning_layout.setContentsMargins(20, 18, 20, 18)
        title = QLabel("HARDWARE COMMISSIONING LOCK"); title.setObjectName("safetyTitle")
        copy = QLabel("Real I/O is disabled until exact ports, framing, calibration, limits, interlocks, and expected replies are independently verified. Simulation never opens a serial port.")
        copy.setWordWrap(True); warning_layout.addWidget(title); warning_layout.addWidget(copy); root.addWidget(warning)

        self.table = QTableWidget(len(Subsystem), 6)
        self.table.setHorizontalHeaderLabels(["Subsystem", "Port", "Baud", "Data bits", "Parity", "Terminator"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for row, subsystem in enumerate(Subsystem):
            profile = window.config.instruments.profile(subsystem)
            values = [subsystem.value, profile.port or "UNASSIGNED", profile.baudrate, profile.bytesize, profile.parity, repr(profile.write_terminator)]
            for column, value in enumerate(values): self.table.setItem(row, column, QTableWidgetItem(str(value)))
        root.addWidget(self.table)

        recovered = QLabel("Recovered LabVIEW defaults (historical software values - not commissioned)")
        recovered.setObjectName("sectionTitle"); root.addWidget(recovered)
        settings = LegacySettings()
        self.recovered_table = QTableWidget(8, 4)
        self.recovered_table.setHorizontalHeaderLabels(["Subsystem", "Recovered port", "Baud", "Recovered source"])
        self.recovered_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.recovered_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        rows = [
            ("ARM", settings.serial.arm_port, settings.serial.baudrate, "Initializer2.vi diagram constant"),
            ("SQUID", "COM1-COM4 set", settings.serial.baudrate, "Initializer2.vi diagram constants"),
            ("MS", "COM1-COM4 set", settings.serial.baudrate, "Initializer2.vi diagram constants"),
            ("DG", "COM1-COM4 set", settings.serial.baudrate, "Initializer2.vi diagram constants"),
            ("IRM", "COM1-COM4 set", settings.serial.baudrate, "Initializer2.vi diagram constants"),
            ("FURNACE", "COM1-COM4 set", settings.serial.baudrate, "Initializer2.vi diagram constants"),
            ("TRACK", "COM1-COM4 set", settings.serial.baudrate, "Initializer2.vi diagram constants"),
            ("all", "0=COM1 ... 8=COM9", "setup help text", "Full Initialize System.vi help text"),
        ]
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                self.recovered_table.setItem(row, column, QTableWidgetItem(str(value)))
        root.addWidget(self.recovered_table)

        errors_label = QLabel("Recovered legacy error catalog")
        errors_label.setObjectName("sectionTitle"); root.addWidget(errors_label)
        catalog = LegacyErrorCatalog.all()
        self.errors_table = QTableWidget(len(catalog), 3)
        self.errors_table.setHorizontalHeaderLabels(["Code", "Subsystem", "Description"])
        self.errors_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.errors_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.errors_table.setMaximumHeight(300)
        for row, entry in enumerate(catalog):
            self.errors_table.setItem(row, 0, QTableWidgetItem(str(entry.code)))
            self.errors_table.setItem(row, 1, QTableWidgetItem(entry.subsystem.value))
            self.errors_table.setItem(row, 2, QTableWidgetItem(entry.short))
        root.addWidget(self.errors_table)
        root.addStretch()


class LogsPage(QWidget):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(); self.window = window
        root = QVBoxLayout(self)
        _heading(root, "Diagnostics", "Operator-visible events are mirrored to rotating structured JSON logs.")
        self.text = QPlainTextEdit(); self.text.setReadOnly(True)
        self.text.setProperty("console", True)
        self.text.setPlaceholderText("Application diagnostics will appear here.")
        root.addWidget(self.text, 1)

    def refresh(self) -> None:
        self.text.setPlainText("\n".join(self.window.events))
