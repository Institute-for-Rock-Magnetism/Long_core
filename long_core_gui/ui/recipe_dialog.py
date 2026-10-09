"""Validated recipe editor for all recovered metadata and acquisition fields."""
from __future__ import annotations
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
                              QMessageBox, QScrollArea, QTabWidget, QVBoxLayout, QWidget)
from ..domain import (QueueStep, MeasurementMode, MeasurementType, TreatmentType, TreatmentOrder, ContinuousMeasurementParameters, DiscreteMeasurementParameters)


class RecipeDialog(QDialog):
    def __init__(self, step: QueueStep, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Recipe · {step.sample.sample_id}")
        self.resize(570, 620)
        self.step = step
        self.fields = {}
        root = QVBoxLayout(self)
        tabs = QTabWidget(); root.addWidget(tabs)
        data = step.to_dict()
        recipe = QWidget(); form = QFormLayout(recipe)
        form.setContentsMargins(20, 20, 20, 20); form.setSpacing(14)
        self.choices = {}
        for key, title, enum in (("measurement_type", "Measurement", MeasurementType), ("measurement_mode", "Mode", MeasurementMode), ("treatment_type", "Treatment", TreatmentType), ("treatment_order", "Order", TreatmentOrder)):
            field = QComboBox(); field.addItems([v.value for v in enum])
            if data.get(key): field.setCurrentText(data[key])
            self.choices[key] = field; form.addRow(title, field)
        self.treatment_value = QLineEdit("" if step.treatment_value is None else str(step.treatment_value))
        self.pause_seconds = QLineEdit("" if step.pause_seconds is None else str(step.pause_seconds))
        form.addRow("Amplitude / temperature", self.treatment_value)
        form.addRow("Pause duration (s)", self.pause_seconds)
        tabs.addTab(recipe, "Recipe")
        data["continuous"] = data.get("continuous") or ContinuousMeasurementParameters().to_dict()
        data["discrete"] = data.get("discrete") or DiscreteMeasurementParameters().to_dict()
        for section, title, labels in (
            ("sample", "Sample metadata", {
                "sample_id": "Sample ID", "name": "Name", "site": "Site", "collection": "Collection",
                "volume_cc": "Volume (cc)", "azimuth_deg": "Azimuth (°)", "plunge_deg": "Plunge (°)",
                "bedding_strike_deg": "Bedding strike (°)", "bedding_dip_deg": "Bedding dip (°)", "notes": "Notes"}),
            ("continuous", "Continuous acquisition", {
                "sample_rate_hz": "Sample rate (Hz)", "traverse_speed_mm_s": "Traverse speed (mm/s)",
                "background_samples": "Background readings", "leader_samples": "Leader readings",
                "sample_samples": "Sample readings", "trailer_samples": "Trailer readings"}),
            ("discrete", "Discrete acquisition", {
                "positions_mm": "Positions (mm, comma separated)", "settling_time_s": "Settling time (s)",
                "readings_per_position": "Readings per position", "integration_time_s": "Integration time (s)"}),
        ):
            panel = QWidget(); form = QFormLayout(panel)
            form.setContentsMargins(20, 20, 20, 20); form.setSpacing(14)
            values = data.get(section)
            if section != "sample" and values is None:
                continue
            for key, label in labels.items():
                value = values.get(key)
                text = ", ".join(str(v) for v in value) if isinstance(value, list) else ("" if value is None else str(value))
                field = QLineEdit(text); field.setPlaceholderText("Optional / unspecified")
                self.fields[section, key] = field
                form.addRow(label, field)
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(panel)
            tabs.addTab(scroll, title)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save); buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def save(self) -> None:
        data = self.step.to_dict()
        data["continuous"] = data.get("continuous") or ContinuousMeasurementParameters().to_dict()
        data["discrete"] = data.get("discrete") or DiscreteMeasurementParameters().to_dict()
        for key, field in self.choices.items(): data[key] = field.currentText()
        text_keys = {"sample_id", "name", "site", "collection", "notes"}
        int_keys = {"background_samples", "leader_samples", "sample_samples", "trailer_samples", "readings_per_position"}
        try:
            for (section, key), field in self.fields.items():
                text = field.text().strip()
                if key == "positions_mm":
                    value = [float(v.strip()) for v in text.split(",") if v.strip()]
                elif key in text_keys:
                    value = text or None
                elif not text:
                    value = None
                else:
                    value = int(text) if key in int_keys else float(text)
                data[section][key] = value
            measurement = MeasurementType(data["measurement_type"])
            treatment = TreatmentType(data["treatment_type"])
            data["treatment_value"] = float(self.treatment_value.text()) if treatment not in {TreatmentType.NONE, TreatmentType.PAUSE} else None
            data["pause_seconds"] = float(self.pause_seconds.text()) if treatment is TreatmentType.PAUSE else None
            if measurement is MeasurementType.NONE:
                data["measurement_mode"] = None
                data["continuous"] = data["discrete"] = None
            elif data["measurement_mode"] == MeasurementMode.CONTINUOUS.value:
                data["discrete"] = None
            else:
                data["continuous"] = None
                if not data["discrete"]["positions_mm"]:
                    raise ValueError("Discrete acquisition needs at least one position")
            self.step = QueueStep.from_dict(data)
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self, "Invalid recipe", str(exc)); return
        self.accept()
