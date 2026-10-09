"""End-to-end desktop workflows using isolated simulated workspaces."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QMessageBox
from long_core_gui.infrastructure import ApplicationConfig, Subsystem, load_application_config
from long_core_gui.services import WorkspaceRepository
from long_core_gui.ui.main_window import MainWindow
from long_core_gui.ui.recipe_dialog import RecipeDialog
from long_core_gui.domain import MeasurementMode, HomingPolicy
from test_run_engine import pump_until

APP = QApplication.instance() or QApplication([])


class DesktopWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = WorkspaceRepository(Path(self.temp.name)/"data")
        self.window = MainWindow(ApplicationConfig(), self.repo, logging.getLogger("test_ui"))
        self.window.config_path = Path(self.temp.name)/"application.json"
        self.window.show()
        APP.processEvents()

    def tearDown(self):
        if self.window.engine.active:
            self.window.engine.abort()
            pump_until(lambda: not self.window.engine.active)
        self.window.close()
        self.temp.cleanup()

    def add_recipe(self):
        queue = self.window.pages["Queue"]
        queue.sample_id.setText("CORE-01")
        queue.mode.setCurrentText(MeasurementMode.DISCRETE.value)
        queue.positions.setText("0, 10, 20")
        queue.add_step()

    def test_queue_preview_execution_history_and_export(self):
        self.add_recipe()
        run = self.window.pages["Run"]
        run.homing.setCurrentText(HomingPolicy.NEVER.value)
        self.assertIn("SQUID DAQ", run.actions.toPlainText())
        self.assertEqual(self.repo.load()[1], HomingPolicy.NEVER)
        self.window.start_run()
        self.assertFalse(self.window.pages["Queue"].isEnabled())
        pump_until(lambda: not self.window.engine.active)
        self.assertEqual(len(self.window.results), 12)
        self.assertEqual(len(self.repo.list_runs()[0]["results"]), 12)
        self.assertEqual(self.repo.list_runs()[0]["state"], "Completed")
        self.assertEqual(run.progress.value(), 100)
        self.assertTrue(self.window.pages["Queue"].isEnabled())
        data = self.window.pages["Run data"]
        data.run.setCurrentIndex(1)
        self.assertEqual(data.table.rowCount(), 12)
        output = Path(self.temp.name)/"export.csv"
        self.repo.export_results(output, data.records)
        self.assertIn("CORE-01", output.read_text())

    def test_recipe_metadata_and_commissioning_configuration_persist(self):
        self.add_recipe()
        editor = RecipeDialog(self.window.queue_steps[0], self.window)
        editor.fields["sample", "site"].setText("IRM")
        editor.fields["sample", "volume_cc"].setText("12.5")
        editor.fields["discrete", "readings_per_position"].setText("2")
        editor.save()
        self.assertEqual(editor.step.sample.site, "IRM")
        self.assertEqual(editor.step.discrete.readings_per_position, 2)
        page = self.window.pages["Commissioning"]
        page._port_controls[Subsystem.SQUID].setCurrentText("COM42")
        page.save_configuration()
        restored = load_application_config(self.window.config_path)
        self.assertEqual(restored.instruments.profile(Subsystem.SQUID).port, "COM42")
        self.assertIsNone(restored.instruments.profile(Subsystem.TRACK).port)

    def test_close_waits_for_worker_and_marks_aborted_run(self):
        self.add_recipe()
        self.window.start_run()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.window.close()
        self.assertTrue(self.window._close_pending)
        pump_until(lambda: not self.window.engine.active)
        self.assertFalse(self.window.isVisible())
        self.assertEqual(self.repo.list_runs()[0]["state"], "Aborted")
    def test_background_probe_uses_capture_and_releases_thread(self):
        from dataclasses import replace
        from long_core_gui.infrastructure import SerialProfile
        from long_core_gui.infrastructure.serial_transport import SimulatedSerialTransport
        self.window.config = replace(self.window.config, hardware_enabled=True)
        page = self.window.pages["Commissioning"]
        profile = SerialProfile(port="COM1")
        transport = SimulatedSerialTransport(profile, responses=["FR SL       "])
        with patch("long_core_gui.ui.commissioning.PySerialTransport", return_value=transport):
            page._start_probe(Subsystem.SQUID, profile)
            self.assertTrue(page.busy)
            pump_until(lambda: not page.busy)
        self.assertEqual(page.table.item(list(Subsystem).index(Subsystem.SQUID), 4).text(), "OK")
        self.assertEqual(len(list((self.repo.directory/"probes").glob("*.json"))), 1)
        self.assertEqual(transport.writes, (b"ZSSA\r",))
