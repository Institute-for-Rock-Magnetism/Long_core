"""Threaded, simulation-first execution engine for semantic action plans."""

from __future__ import annotations

from hashlib import sha256
import random
import threading
import time

from PySide6.QtCore import QObject, QThread, Signal, Slot

from ..domain import Action, ActionOpcode, vector_properties


class _RunWorker(QObject):
    action_started = Signal(int, int, object)
    measurement_ready = Signal(object)
    progress_changed = Signal(int, int)
    state_changed = Signal(str, str)
    failed = Signal(str)
    finished = Signal(str)

    def __init__(self, actions: tuple[Action, ...]) -> None:
        super().__init__()
        self.actions = actions
        self._abort = threading.Event()
        self._pause = threading.Event()
        self._pause.set()

    @Slot()
    def run(self) -> None:
        try:
            self.state_changed.emit("Running", "Executing validated action plan")
            total = len(self.actions)
            for index, action in enumerate(self.actions, start=1):
                if self._abort.is_set():
                    self.finished.emit("Aborted")
                    return
                self._pause.wait()
                self.action_started.emit(index, total, action)
                if action.opcode in (ActionOpcode.SQUID_DAQ, ActionOpcode.MS_DAQ):
                    self.measurement_ready.emit(self._simulate(action, index))
                time.sleep(0.09)
                self.progress_changed.emit(index, total)
            self.finished.emit("Completed")
        except Exception as exc:
            self.failed.emit(str(exc))
            self.finished.emit("Failed")

    def pause(self) -> None:
        self._pause.clear()

    def resume(self) -> None:
        self._pause.set()

    def abort(self) -> None:
        self._abort.set()
        self._pause.set()

    @staticmethod
    def _simulate(action: Action, sequence: int) -> dict[str, object]:
        identity = f"{action.sample_id}:{action.daq_type}:{sequence}".encode("utf-8")
        seed = int.from_bytes(sha256(identity).digest()[:8], "big")
        rng = random.Random(seed)
        scale = 1.0 if action.opcode is ActionOpcode.SQUID_DAQ else 0.08
        x = rng.gauss(18.0, 0.7) * scale
        y = rng.gauss(8.0, 0.5) * scale
        z = rng.gauss(27.0, 0.9) * scale
        vector = vector_properties(x, y, z)
        return {
            "sample_id": action.sample_id or "background",
            "daq_type": action.daq_type.value if action.daq_type else "Sample",
            "instrument": "SQUID" if action.opcode is ActionOpcode.SQUID_DAQ else "MS",
            "x": x,
            "y": y,
            "z": z,
            "intensity": vector.intensity,
            "inclination": vector.inclination_deg,
            "declination": vector.declination_deg,
            "sequence": sequence,
        }


class RunEngine(QObject):
    """Owns one worker thread and exposes a small stateful Qt API."""

    action_started = Signal(int, int, object)
    measurement_ready = Signal(object)
    progress_changed = Signal(int, int)
    state_changed = Signal(str, str)
    failed = Signal(str)
    finished = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.state = "Idle"
        self._thread: QThread | None = None
        self._worker: _RunWorker | None = None

    @property
    def active(self) -> bool:
        return self.state in {"Running", "Paused"}

    def start(self, actions: tuple[Action, ...]) -> None:
        if self.active:
            raise RuntimeError("a run is already active")
        if not actions:
            raise ValueError("action plan is empty")
        self._thread = QThread(self)
        self._worker = _RunWorker(actions)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.action_started.connect(self.action_started)
        self._worker.measurement_ready.connect(self.measurement_ready)
        self._worker.progress_changed.connect(self.progress_changed)
        self._worker.state_changed.connect(self._set_state)
        self._worker.failed.connect(self.failed)
        self._worker.finished.connect(self._finish)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self.state = "Running"
        self._thread.start()

    def pause(self) -> None:
        if self.state != "Running" or self._worker is None:
            return
        self._worker.pause()
        self._set_state("Paused", "Run paused by operator")

    def resume(self) -> None:
        if self.state != "Paused" or self._worker is None:
            return
        self._worker.resume()
        self._set_state("Running", "Run resumed")

    def abort(self) -> None:
        if self.active and self._worker is not None:
            self._worker.abort()
            self._set_state("Stopping", "Abort requested; waiting for safe action boundary")

    @Slot(str, str)
    def _set_state(self, state: str, message: str) -> None:
        self.state = state
        self.state_changed.emit(state, message)

    @Slot(str)
    def _finish(self, state: str) -> None:
        self.state = state
        self.finished.emit(state)
        self._worker = None
        self._thread = None
