"""Commissioning page: operator-gated hardware probing with raw capture."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..infrastructure.config import ConfigValidationError, Subsystem
from ..infrastructure.probe import (
    ProbeSession,
    allowed_commands, iter_available_ports,
)
from ..infrastructure.serial_transport import (
    PySerialTransport,
)
from .widgets import button, page_title

if TYPE_CHECKING:
    from .main_window import MainWindow


class _ProbeWorker(QThread):
    captured = Signal(object)
    failed = Signal(str)

    def __init__(self, subsystem, profile, command, parent=None):
        super().__init__(parent)
        self.subsystem, self.profile, self.command = subsystem, profile, command

    def run(self):
        try:
            transport = PySerialTransport(self.profile)
            session = ProbeSession(self.subsystem, transport)
            self.captured.emit(session.run_custom(self.command) if self.command is not None else session.run())
        except Exception as exc:
            self.failed.emit(str(exc))


class CommissioningPage(QWidget):
    """Probe each subsystem with read-only commands and capture raw replies."""

    def __init__(self, window: "MainWindow") -> None:
        super().__init__()
        self.window = window
        self._probe_worker = None
        root = QVBoxLayout(self)
        heading, caption = page_title(
            "Commissioning",
            "Probe instruments with allowlisted ID/status commands and capture every byte. "
            "Expert raw commands bypass the allowlist and always require explicit confirmation.",
        )
        root.addWidget(heading); root.addWidget(caption); root.addSpacing(10)

        self.gate = QFrame(); self.gate.setObjectName("safetyCard")
        gate_layout = QHBoxLayout(self.gate)
        self.gate_label = QLabel()
        self.gate_label.setWordWrap(True)
        gate_layout.addWidget(self.gate_label, 1)
        self.detect_button = button("Detect ports")
        self.detect_button.clicked.connect(self.detect_ports)
        gate_layout.addWidget(self.detect_button)
        root.addWidget(self.gate)

        self.table = QTableWidget(len(Subsystem), 5)
        self.table.setHorizontalHeaderLabels(
            ["Subsystem", "Port", "Baud", "Probe commands", "Last result"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self._ports = ["UNASSIGNED", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9"]
        self._port_controls: dict[Subsystem, QComboBox] = {}
        self._baud_controls: dict[Subsystem, QComboBox] = {}
        for row, subsystem in enumerate(Subsystem):
            profile = window.config.instruments.profile(subsystem)
            name_item = QTableWidgetItem(subsystem.value)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)
            port_box = QComboBox(); port_box.setEditable(True); port_box.addItems(self._ports)
            port_box.setCurrentText(profile.port or "UNASSIGNED")
            self._port_controls[subsystem] = port_box
            self.table.setCellWidget(row, 1, port_box)
            baud_choices = ["9600", "19200", "38400", "57600", "115200"]
            baud_box = QComboBox(); baud_box.addItems(baud_choices)
            if str(profile.baudrate) not in baud_choices:
                baud_box.addItem(str(profile.baudrate))
            baud_box.setCurrentText(str(profile.baudrate))
            self._baud_controls[subsystem] = baud_box
            self.table.setCellWidget(row, 2, baud_box)
            commands = ", ".join(sorted(allowed_commands(subsystem))) or "raw only"
            self.table.setItem(row, 3, QTableWidgetItem(commands))
            self.table.setItem(row, 4, QTableWidgetItem("not probed"))
        root.addWidget(self.table)

        controls = QHBoxLayout()
        self.probe_button = button("Run read-only probe", "primary")
        self.probe_button.clicked.connect(self.run_probe)
        controls.addWidget(self.probe_button)
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Raw command for the selected subsystem (recorded as custom)")
        controls.addWidget(self.custom_input, 1)
        self.custom_button = button("Send raw")
        self.custom_button.clicked.connect(self.send_raw)
        controls.addWidget(self.custom_button)
        self.save_button = button("Save configuration")
        self.save_button.clicked.connect(self.save_configuration)
        controls.addWidget(self.save_button)
        root.addLayout(controls)

        self.log = QPlainTextEdit(); self.log.setReadOnly(True)
        self.log.setProperty("console", True)
        self.log.setPlaceholderText("Select a subsystem and run a probe to inspect transmitted and received bytes.")
        root.addWidget(self.log, 1)
        self.refresh()

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        enabled = self.window.config.hardware_enabled
        if enabled:
            self.gate_label.setText(
                "Hardware mode is ENABLED. Probes open real serial ports with "
                "read-only commands only — ID, status, and poll. No motion, "
                "treatment, or high-power commands are included."
            )
        else:
            self.gate_label.setText(
                "Hardware mode is DISABLED — ports never open. To enable, set "
                "LONG_CORE_HARDWARE=1 when starting the application (or set "
                "hardware_enabled=true in the application config), then confirm "
                "each probe session."
            )
        self.probe_button.setEnabled(enabled and not self.busy)
        self.custom_button.setEnabled(enabled and not self.busy)
        self.table.setEnabled(not self.busy)
        self.save_button.setEnabled(not self.busy)
        self.detect_button.setEnabled(not self.busy)

    def detect_ports(self) -> None:
        found = sorted(iter_available_ports())
        if not found:
            QMessageBox.information(self, "Port detection", "No serial ports detected.")
            return
        self._ports = found + [port for port in self._ports if port not in found]
        for box in self._port_controls.values():
            current = box.currentText()
            box.clear(); box.addItems(self._ports); box.setCurrentText(current)
        self.log.appendPlainText(f"Detected ports: {', '.join(found)}")

    def _selected_subsystem(self) -> Subsystem | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Select a subsystem", "Select one row first.")
            return None
        return Subsystem(self.table.item(rows[0].row(), 0).text())

    def _profile_for(self, subsystem: Subsystem):
        from dataclasses import replace
        port = self._port_controls[subsystem].currentText().strip()
        return replace(self.window.config.instruments.profile(subsystem),
                       port=None if port == "UNASSIGNED" or not port else port,
                       baudrate=int(self._baud_controls[subsystem].currentText()))

    def run_probe(self) -> None:
        subsystem = self._selected_subsystem()
        if subsystem is None:
            return
        profile = self._profile_for(subsystem)
        if profile.port is None:
            QMessageBox.warning(self, "Port required", "Assign a verified serial port first.")
            return
        commands = sorted(allowed_commands(subsystem))
        detail = ", ".join(commands) if commands else "no recovered commands — use raw"
        answer = QMessageBox.question(
            self,
            f"Probe {subsystem.value} on {profile.port}?",
            f"Read-only commands: {detail}\n\n"
            f"Port {profile.port} at {profile.baudrate} baud will be opened "
            f"briefly and every reply captured. Continue?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._start_probe(subsystem, profile)

    def send_raw(self) -> None:
        subsystem = self._selected_subsystem()
        if subsystem is None:
            return
        command = self.custom_input.text().strip()
        if not command:
            QMessageBox.information(self, "Raw command", "Enter a command first.")
            return
        profile = self._profile_for(subsystem)
        answer = QMessageBox.question(
            self,
            f"Send raw {command!r} to {subsystem.value}?",
            "This is an unverified command. It will be recorded as 'custom' in "
            "the capture. The probe allowlist will not protect you from typos — "
            "make sure it is a status/ID query, not motion or treatment.\n\n"
            f"Port {profile.port} at {profile.baudrate} baud. Continue?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._start_probe(subsystem, profile, command)

    @property
    def busy(self):
        return self._probe_worker is not None

    def _start_probe(self, subsystem, profile, command=None):
        if self.busy or not self.window.config.hardware_enabled:
            return
        if profile.port is None:
            QMessageBox.warning(self, "Port required", "Assign a verified serial port first.")
            return
        worker = _ProbeWorker(subsystem, profile, command, self)
        self._probe_worker = worker
        worker.captured.connect(self._capture_ready)
        worker.failed.connect(lambda message: QMessageBox.critical(self, "Probe failed", message))
        worker.finished.connect(self._probe_finished)
        worker.finished.connect(worker.deleteLater)
        self.refresh()
        self.log.appendPlainText(f"Probing {subsystem.value} on {profile.port}...")
        worker.start()

    def _capture_ready(self, capture):
        try:
            saved = self.window.repository.save_probe_capture(capture)
        except OSError as exc:
            QMessageBox.critical(self, "Capture save failed", str(exc))
            self._render_capture(capture)
            return
        self._render_capture(capture)
        self.table.item(self._subsystem_row(Subsystem(capture.subsystem)), 4).setText("OK" if capture.ok else "mismatch/timeout")
        self.window.log_event(f"Probe capture saved: {saved.name}")

    def _probe_finished(self):
        self._probe_worker = None
        self.refresh()

    def save_configuration(self) -> None:
        from dataclasses import replace
        from ..infrastructure.config import SerialProfile

        profiles: dict[Subsystem, SerialProfile] = {}
        for subsystem in Subsystem:
            profiles[subsystem] = self._profile_for(subsystem)
        try:
            instruments = type(self.window.config.instruments)(profiles=profiles)
        except ConfigValidationError as exc:
            QMessageBox.critical(self, "Invalid configuration", str(exc))
            return
        self.window.config = replace(self.window.config, instruments=instruments)
        self.window.changed("Saved instrument configuration")

    # ------------------------------------------------------------------

    def _subsystem_row(self, subsystem: Subsystem) -> int:
        return list(Subsystem).index(subsystem)

    def _render_capture(self, capture) -> None:
        self.log.clear()
        self.log.appendPlainText(
            f"{capture.subsystem} on {capture.profile.get('port')} at "
            f"{capture.profile.get('baudrate')} baud — {capture.started_at}"
        )
        for step in (*capture.steps, *capture.custom):
            status = "ok" if step.ok else "FAIL"
            self.log.appendPlainText("")
            self.log.appendPlainText(f"[{status}] {step.name}: {step.command!r}")
            self.log.appendPlainText(f"  TX {step.tx_hex}")
            self.log.appendPlainText(f"  RX {step.rx_hex}  ({step.rx_bytes} bytes)")
            if step.rx_text:
                self.log.appendPlainText(f"  as text: {step.rx_text!r}")
            if step.note:
                self.log.appendPlainText(f"  note: {step.note}")
        self.log.appendPlainText("")
        self.log.appendPlainText("Capture saved to the workspace probes/ folder.")
