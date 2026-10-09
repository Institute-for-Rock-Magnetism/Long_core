"""Run history, record inspection, filtering, and CSV export."""
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout,
                              QHeaderView, QLabel, QMessageBox, QTableWidget,
                              QTableWidgetItem, QVBoxLayout, QWidget)
from .widgets import button, page_title


class DataPage(QWidget):
    FIELDS = ("sample_id", "daq_type", "instrument", "position_mm", "x", "y", "z",
              "intensity", "inclination", "declination", "run_id", "timestamp", "geographic_inclination", "geographic_declination", "tilt_corrected_inclination", "tilt_corrected_declination")

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.records = []
        self.runs = []
        root = QVBoxLayout(self)
        for widget in page_title("Run data", "Inspect recorded simulations, recover interrupted runs, and export the selected measurements."):
            root.addWidget(widget)
        toolbar = QHBoxLayout()
        self.run = QComboBox(); self.run.setMinimumWidth(260)
        self.sample = QComboBox(); self.sample.setMinimumWidth(150)
        self.run.currentIndexChanged.connect(self.filter_records)
        self.sample.currentIndexChanged.connect(self.filter_records)
        toolbar.addWidget(QLabel("Run")); toolbar.addWidget(self.run, 2)
        toolbar.addWidget(QLabel("Sample")); toolbar.addWidget(self.sample, 1)
        export = button("Export CSV", "primary"); export.clicked.connect(self.export)
        toolbar.addWidget(export); root.addLayout(toolbar)
        self.summary = QLabel(); self.summary.setWordWrap(True)
        root.addWidget(self.summary)
        self.table = QTableWidget(0, len(self.FIELDS))
        self.table.setHorizontalHeaderLabels(["Sample", "DAQ", "Instrument", "Position (mm)", "X", "Y", "Z", "Intensity", "Inclination (°)", "Declination (°)", "Run ID", "Timestamp", "Geo inclination", "Geo declination", "Tilt inclination", "Tilt declination"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setDefaultSectionSize(36)
        root.addWidget(self.table, 1)

    def refresh(self):
        run_id = self.run.currentData(); sample = self.sample.currentData()
        self.runs = self.window.repository.list_runs()
        self.run.blockSignals(True); self.sample.blockSignals(True)
        self.run.clear(); self.run.addItem("All measurements", None)
        for record in self.runs:
            self.run.addItem(f"{record.get('started_at', '')[:19]} · {record.get('state', '')} · {record['run_id'][:8]}", record["run_id"])
        self.run.setCurrentIndex(max(0, self.run.findData(run_id)))
        self.sample.clear(); self.sample.addItem("All samples", None)
        for name in sorted({str(r.get("sample_id", "")) for r in self.window.results}):
            self.sample.addItem(name, name)
        self.sample.setCurrentIndex(max(0, self.sample.findData(sample)))
        self.run.blockSignals(False); self.sample.blockSignals(False)
        self.filter_records()

    def filter_records(self, *args):
        run_id, sample = self.run.currentData(), self.sample.currentData()
        rows = self.window.results
        selected = next((r for r in self.runs if r["run_id"] == run_id), None)
        if selected:
            # A recovered workspace can be older than the durable run snapshot.
            rows = selected.get("results", [])
        self.records = [r for r in rows if (sample is None or r.get("sample_id") == sample)]
        self.summary.setText(f"{len(self.records)} measurements · Simulation data" + (f" · {selected.get('state', '')}" if selected else ""))
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            for col, key in enumerate(self.FIELDS):
                value = record.get(key)
                text = f"{value:.6g}" if isinstance(value, float) else ("" if value is None else str(value))
                self.table.setItem(row, col, QTableWidgetItem(text))

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export measurements", "long-core-measurements.csv", "CSV (*.csv)")
        if path:
            try:
                self.window.repository.export_results(path, self.records)
            except OSError as exc:
                QMessageBox.critical(self, "Export failed", str(exc)); return
            self.window.log_event(f"Exported {len(self.records)} measurements to {path}")
