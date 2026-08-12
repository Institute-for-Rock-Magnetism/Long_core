"""Side-effect-free serial transport interfaces and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from threading import RLock
from typing import Any, Iterable

from .config import SerialProfile


class TransportError(RuntimeError):
    """Base class for serial transport failures."""


class TransportDisconnectedError(TransportError):
    """Raised when an operation requires a connected transport."""


class SerialTransport(ABC):
    """Minimal synchronous transport boundary used by instrument drivers."""

    def __init__(self, profile: SerialProfile):
        self.profile = profile

    @property
    @abstractmethod
    def is_open(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def write(self, command: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def read_until(self) -> str:
        raise NotImplementedError

    def query(self, command: str) -> str:
        self.write(command)
        return self.read_until()

    def __enter__(self) -> "SerialTransport":
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _frame(self, command: str) -> bytes:
        if not isinstance(command, str) or not command:
            raise ValueError("command must be non-empty text")
        for terminator in {"\r", "\n", self.profile.write_terminator}:
            if terminator and terminator in command:
                raise ValueError("command must not contain framing terminators")
        try:
            return (command + self.profile.write_terminator).encode(self.profile.encoding)
        except UnicodeEncodeError as exc:
            raise ValueError("command cannot be encoded by the serial profile") from exc


class DisconnectedTransport(SerialTransport):
    """Fail-closed transport used when no hardware port is configured."""

    @property
    def is_open(self) -> bool:
        return False

    def open(self) -> None:
        raise TransportDisconnectedError("serial port is not configured")

    def close(self) -> None:
        return None

    def write(self, command: str) -> int:
        raise TransportDisconnectedError("serial transport is disconnected")

    def read_until(self) -> str:
        raise TransportDisconnectedError("serial transport is disconnected")


class SimulatedSerialTransport(SerialTransport):
    """Deterministic in-memory transport that can never perform device I/O."""

    def __init__(self, profile: SerialProfile, responses: Iterable[str] = ()):
        super().__init__(profile)
        self._open = False
        self._responses = deque(responses)
        self._writes: list[bytes] = []
        self._lock = RLock()

    @property
    def is_open(self) -> bool:
        return self._open

    @property
    def writes(self) -> tuple[bytes, ...]:
        return tuple(self._writes)

    def queue_response(self, response: str) -> None:
        if not isinstance(response, str):
            raise TypeError("simulated response must be text")
        with self._lock:
            self._responses.append(response)

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def _require_open(self) -> None:
        if not self._open:
            raise TransportDisconnectedError("simulated transport is closed")

    def write(self, command: str) -> int:
        with self._lock:
            self._require_open()
            frame = self._frame(command)
            self._writes.append(frame)
            return len(frame)

    def read_until(self) -> str:
        with self._lock:
            self._require_open()
            return self._responses.popleft() if self._responses else ""


class PySerialTransport(SerialTransport):
    """pyserial-backed transport; the dependency and port open are both lazy."""

    def __init__(self, profile: SerialProfile):
        if profile.port is None:
            raise ValueError("PySerialTransport requires a configured port")
        super().__init__(profile)
        self._serial: Any | None = None
        self._lock = RLock()

    @property
    def is_open(self) -> bool:
        return bool(self._serial is not None and self._serial.is_open)

    def open(self) -> None:
        with self._lock:
            if self.is_open:
                return
            try:
                import serial
            except ImportError as exc:
                raise TransportError("pyserial is required for hardware transport") from exc
            try:
                self._serial = serial.Serial(
                    port=self.profile.port,
                    baudrate=self.profile.baudrate,
                    bytesize=self.profile.bytesize,
                    parity=self.profile.parity.upper(),
                    stopbits=self.profile.stopbits,
                    timeout=self.profile.read_timeout,
                    write_timeout=self.profile.write_timeout,
                    inter_byte_timeout=self.profile.inter_byte_timeout,
                )
            except Exception as exc:
                self._serial = None
                raise TransportError(f"failed to open serial port {self.profile.port!r}") from exc

    def close(self) -> None:
        with self._lock:
            if self._serial is not None:
                try:
                    self._serial.close()
                finally:
                    self._serial = None

    def _require_open(self) -> Any:
        if not self.is_open:
            raise TransportDisconnectedError("serial transport is closed")
        return self._serial

    def write(self, command: str) -> int:
        with self._lock:
            connection = self._require_open()
            try:
                return int(connection.write(self._frame(command)))
            except Exception as exc:
                raise TransportError("serial write failed") from exc

    def read_until(self) -> str:
        with self._lock:
            connection = self._require_open()
            terminator = self.profile.read_terminator.encode(self.profile.encoding)
            try:
                data = connection.read_until(terminator or b"\n")
                return data.decode(self.profile.encoding).removesuffix(self.profile.read_terminator)
            except Exception as exc:
                raise TransportError("serial read failed") from exc


def create_transport(profile: SerialProfile, *, simulation: bool = True) -> SerialTransport:
    """Create a safe transport without opening it or importing pyserial."""

    if simulation:
        return SimulatedSerialTransport(profile)
    if profile.port is None:
        return DisconnectedTransport(profile)
    return PySerialTransport(profile)
