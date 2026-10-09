"""Lifecycle regressions for worker teardown, pause recipes, and DAQ positions."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import time
import unittest
from PySide6.QtWidgets import QApplication
from long_core_gui.domain import Action, ActionOpcode, DAQType
from long_core_gui.services.run_engine import RunEngine

APP = QApplication.instance() or QApplication([])


def pump_until(predicate, timeout=4):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        APP.processEvents()
        time.sleep(.005)
    APP.processEvents()
    if not predicate():
        raise AssertionError("Qt worker timed out")


class RunEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = RunEngine()
        self.records = []
        self.actions = []
        self.finishes = []
        self.engine.measurement_ready.connect(self.records.append)
        self.engine.action_started.connect(lambda i, n, a: self.actions.append(a))
        self.engine.finished.connect(self.finishes.append)

    def tearDown(self):
        if self.engine.active:
            self.engine.abort()
            pump_until(lambda: not self.engine.active)

    def test_discrete_positions_and_repeated_readings(self):
        daq = Action(ActionOpcode.SQUID_DAQ, sample_id="core1", daq_type=DAQType.SAMPLE,
                     parameters={"mode": "Discrete", "positions_mm": [0, 10], "readings_per_position": 2})
        self.engine.start((daq, Action(ActionOpcode.DONE)))
        pump_until(lambda: not self.engine.active)
        self.assertEqual(self.finishes, ["Completed"])
        self.assertEqual([r["position_mm"] for r in self.records], [0, 0, 10, 10])
        self.assertEqual([r["reading"] for r in self.records], [1, 2, 1, 2])
        self.assertTrue(all(r["run_id"] == self.engine.run_id for r in self.records))

    def test_continuous_counts(self):
        daq = Action(ActionOpcode.MS_DAQ, daq_type=DAQType.SAMPLE,
                     parameters={"mode": "Continuous", "sample_samples": 3})
        self.engine.start((daq,))
        pump_until(lambda: not self.engine.active)
        self.assertEqual(len(self.records), 3)

    def test_abort_while_paused_never_executes_next_action(self):
        pause = Action(ActionOpcode.PAUSE, value=5)
        self.engine.start((pause, Action(ActionOpcode.DONE)))
        pump_until(lambda: len(self.actions) == 1)
        self.engine.pause()
        self.engine.abort()
        self.assertTrue(self.engine.active)
        with self.assertRaises(RuntimeError): self.engine.start((Action(ActionOpcode.DONE),))
        pump_until(lambda: not self.engine.active)
        self.assertEqual(self.finishes, ["Aborted"])
        self.assertEqual(len(self.actions), 1)

    def test_pause_recipe_observes_duration(self):
        start = time.monotonic()
        self.engine.start((Action(ActionOpcode.PAUSE, value=.2),))
        pump_until(lambda: not self.engine.active)
        self.assertGreaterEqual(time.monotonic()-start, .19)

    def test_can_restart_after_thread_cleanup(self):
        for _ in range(3):
            self.engine.start((Action(ActionOpcode.DONE),))
            pump_until(lambda: not self.engine.active)
        self.assertEqual(self.finishes, ["Completed"]*3)
