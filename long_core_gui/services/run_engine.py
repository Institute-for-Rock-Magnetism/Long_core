"""Threaded simulation executor with interruptible waits and safe teardown."""
from __future__ import annotations

from hashlib import sha256
import random
import threading
import time
from uuid import uuid4
from datetime import datetime, timezone

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from ..domain import (Action, ActionOpcode, SampleMetadata, VectorMeasurementResult, calculate_coordinate_results, vector_properties)


class _RunWorker(QObject):
    action_started = Signal(int, int, object)
    measurement_ready = Signal(object)
    progress_changed = Signal(int, int)
    state_changed = Signal(str, str)
    checkpoint = Signal()
    failed = Signal(str)
    finished = Signal(str)

    def __init__(self, actions: tuple[Action, ...], run_id: str = "") -> None:
        super().__init__()
        self.actions = actions
        self.run_id = run_id
        self._abort = threading.Event()
        self._pause = threading.Event()
        self._pause.set()

    def _wait(self, seconds: float = 0.0) -> bool:
        """Count only unpaused time; recheck abort after every blocking wait."""
        remaining = seconds
        while True:
            if self._abort.is_set():
                return False
            if not self._pause.wait(0.025):
                continue
            if self._abort.is_set():
                return False
            if remaining <= 0:
                return True
            start = time.monotonic()
            if self._abort.wait(min(remaining, 0.025)):
                return False
            if self._pause.is_set():
                remaining -= time.monotonic() - start

    @Slot()
    def run(self) -> None:
        try:
            total = len(self.actions)
            for index, action in enumerate(self.actions, start=1):
                if not self._wait():
                    self.finished.emit("Aborted")
                    return
                self.action_started.emit(index, total, action)
                if action.opcode in (ActionOpcode.SQUID_DAQ, ActionOpcode.MS_DAQ):
                    params = action.parameters
                    positions = params.get("positions_mm") or (None,)
                    role = action.daq_type.value.lower()
                    count = (params.get("readings_per_position") or 1) if params.get("mode") == "Discrete" else (params.get(f"{role}_samples") or 1)
                    for position in positions:
                        for reading in range(count):
                            if not self._wait(0.015):
                                self.finished.emit("Aborted")
                                return
                            record = self._simulate(action, index, position, reading)
                            record.update(run_id=self.run_id, timestamp=datetime.now(timezone.utc).isoformat())
                            self.measurement_ready.emit(record)
                if action.opcode is ActionOpcode.SAVE:
                    self.checkpoint.emit()
                duration = float(action.value or 0) if action.opcode is ActionOpcode.PAUSE else 0.09
                if not self._wait(duration):
                    self.finished.emit("Aborted")
                    return
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
    def _simulate(action: Action, sequence: int, position=None, reading=0) -> dict[str, object]:
        identity = f"{action.sample_id}:{action.daq_type}:{sequence}:{position}:{reading}".encode()
        rng = random.Random(int.from_bytes(sha256(identity).digest()[:8], "big"))
        scale = 1.0 if action.opcode is ActionOpcode.SQUID_DAQ else 0.08
        x, y, z = (rng.gauss(mean, noise)*scale for mean, noise in ((18, .7), (8, .5), (27, .9)))
        vector = vector_properties(x, y, z)
        record = dict(sample_id=action.sample_id or "background", daq_type=action.daq_type.value,
                    instrument="SQUID" if action.opcode is ActionOpcode.SQUID_DAQ else "MS",
                    x=x, y=y, z=z, intensity=vector.intensity, inclination=vector.inclination_deg,
                    declination=vector.declination_deg, sequence=sequence, position_mm=position, reading=reading+1)
        metadata = action.parameters.get("sample_metadata")
        if metadata and action.opcode is ActionOpcode.SQUID_DAQ:
            coordinates = calculate_coordinate_results(VectorMeasurementResult(x, y, z), SampleMetadata.from_dict(metadata))
            for name in ("geographic", "tilt_corrected"):
                vector = getattr(coordinates, name)
                record[f"{name}_inclination"] = vector.inclination_deg if vector else None
                record[f"{name}_declination"] = vector.declination_deg if vector else None
        return record


class RunEngine(QObject):
    """A run remains active until its worker thread has actually stopped."""
    action_started = Signal(int, int, object)
    measurement_ready = Signal(object)
    progress_changed = Signal(int, int)
    state_changed = Signal(str, str)
    checkpoint = Signal()
    failed = Signal(str)
    finished = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.state = "Idle"
        self.run_id = ""
        self._thread = None
        self._worker = None
        self._terminal_state = "Failed"

    @property
    def active(self) -> bool:
        return self._thread is not None

    def start(self, actions: tuple[Action, ...]) -> None:
        if self.active:
            raise RuntimeError("a run is already active")
        if not actions:
            raise ValueError("action plan is empty")
        self.run_id = uuid4().hex
        self._terminal_state = "Failed"
        thread = QThread(self)
        worker = _RunWorker(actions, self.run_id)
        self._thread, self._worker = thread, worker
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.action_started.connect(self.action_started)
        worker.measurement_ready.connect(self.measurement_ready)
        worker.progress_changed.connect(self.progress_changed)
        worker.checkpoint.connect(self.checkpoint)
        worker.failed.connect(self.failed)
        worker.finished.connect(self._record_completion)
        worker.finished.connect(thread.quit, Qt.ConnectionType.DirectConnection)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._cleanup)
        thread.finished.connect(thread.deleteLater)
        self._set_state("Running", "Executing simulated action plan")
        thread.start()

    def pause(self) -> None:
        if self.state == "Running" and self._worker:
            self._worker.pause()
            self._set_state("Paused", "Run paused by operator")

    def resume(self) -> None:
        if self.state == "Paused" and self._worker:
            self._worker.resume()
            self._set_state("Running", "Run resumed")

    def abort(self) -> None:
        if self.active and self._worker:
            self._worker.abort()
            self._set_state("Stopping", "Stopping simulation at the next action boundary")

    @Slot(str, str)
    def _set_state(self, state: str, message: str) -> None:
        self.state = state
        self.state_changed.emit(state, message)

    @Slot(str)
    def _record_completion(self, state: str) -> None:
        self._terminal_state = state

    @Slot()
    def _cleanup(self) -> None:
        self._worker = None
        self._thread = None
        self.state = self._terminal_state
        self.finished.emit(self.state)
