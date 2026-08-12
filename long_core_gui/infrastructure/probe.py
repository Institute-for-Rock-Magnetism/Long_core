"""Operator-gated hardware probing with raw capture.

A probe session opens a transport only when the caller explicitly allows it,
sends only read-only ID/status/poll commands from a per-subsystem allowlist,
and records every byte exchanged (hex + decoded text) for parser verification.

No motion, treatment, or high-power command is ever part of a probe plan.
Commands outside the allowlist raise ``ProbeCommandDenied``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from .config import Subsystem
from .serial_transport import SerialTransport, TransportError


class ProbeError(RuntimeError):
    """Base class for probe-session failures."""


class ProbeCommandDenied(ProbeError):
    """Raised when a command is not on the read-only probe allowlist."""


@dataclass(frozen=True, slots=True)
class ProbeStep:
    """One read-only probe command and its expected reply shape."""

    name: str
    command: str
    description: str = ""
    expected_reply_bytes: int | None = None
    expected_marker: str | None = None


@dataclass(frozen=True, slots=True)
class ProbeStepResult:
    name: str
    command: str
    tx_hex: str
    rx_bytes: int
    rx_hex: str
    rx_text: str
    duration_ms: int
    ok: bool
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "tx_hex": self.tx_hex,
            "rx_bytes": self.rx_bytes,
            "rx_hex": self.rx_hex,
            "rx_text": self.rx_text,
            "duration_ms": self.duration_ms,
            "ok": self.ok,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProbeStepResult":
        return cls(**dict(data))


@dataclass(frozen=True, slots=True)
class ProbeCapture:
    """Full record of one probe session, persisted as JSON."""

    subsystem: str
    profile: dict[str, Any]
    started_at: str
    steps: tuple[ProbeStepResult, ...]
    custom: tuple[ProbeStepResult, ...] = ()
    ok: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "subsystem": self.subsystem,
            "profile": dict(self.profile),
            "started_at": self.started_at,
            "ok": self.ok,
            "steps": [step.to_dict() for step in self.steps],
            "custom": [step.to_dict() for step in self.custom],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProbeCapture":
        return cls(
            subsystem=data["subsystem"],
            profile=dict(data["profile"]),
            started_at=data["started_at"],
            steps=tuple(ProbeStepResult.from_dict(item) for item in data.get("steps", [])),
            custom=tuple(ProbeStepResult.from_dict(item) for item in data.get("custom", [])),
            ok=bool(data.get("ok", True)),
        )


# --------------------------------------------------------------------------
# Read-only probe plans per subsystem. Commands come from the recovered
# command tables (reconstructions/*_REVERSE_ENGINEERING.md); everything here
# is an ID, status, or poll query. MS ``Z``/``M`` are meter operations the
# legacy driver itself uses for verification; they are retained with notes.
# --------------------------------------------------------------------------

PROBE_PLANS: dict[Subsystem, tuple[ProbeStep, ...]] = {
    Subsystem.SQUID: (
        ProbeStep("all-status", "ZSSA", "complete X/Y/Z status; expected 12 bytes",
                  expected_reply_bytes=12, expected_marker="FR SL"),
    ),
    Subsystem.MS: (
        ProbeStep("verify", "Z", "legacy verify/zero command; 6-byte reply expected",
                  expected_reply_bytes=6),
        ProbeStep("measure", "M", "measure; 6-byte reply expected",
                  expected_reply_bytes=6),
    ),
    Subsystem.TRACK: (
        ProbeStep("identify", "?", "SMC25 ID string"),
        ProbeStep("poll", "%", "SMC25 poll reply"),
    ),
    Subsystem.DG: (
        ProbeStep("status", "DSS", "degausser status reply"),
    ),
    Subsystem.ARM: (
        ProbeStep("status", "ARMSS", "ARM status reply; [OF] marker expected",
                  expected_marker="[OF]"),
    ),
    Subsystem.IRM: (
        ProbeStep("status", "PSS", "IRM status reply"),
    ),
    Subsystem.FURNACE: (),
}

_ALLOWED: dict[Subsystem, frozenset[str]] = {
    subsystem: frozenset(step.command for step in steps)
    for subsystem, steps in PROBE_PLANS.items()
}


def allowed_commands(subsystem: Subsystem | str) -> frozenset[str]:
    key = subsystem if isinstance(subsystem, Subsystem) else Subsystem(str(subsystem).upper())
    return _ALLOWED[key]


class ProbeSession:
    """Run a read-only probe plan over one transport and capture everything.

    The transport is created by the caller; this session opens and closes it.
    Every step is recorded even when the read times out, so empty replies are
    visible in the capture.
    """

    def __init__(self, subsystem: Subsystem | str, transport: SerialTransport):
        key = subsystem if isinstance(subsystem, Subsystem) else Subsystem(str(subsystem).upper())
        self.subsystem = key
        self.transport = transport
        self._custom: list[ProbeStepResult] = []

    def run(self, steps: Sequence[ProbeStep] | None = None) -> ProbeCapture:
        plan = tuple(steps) if steps is not None else PROBE_PLANS[self.subsystem]
        results: list[ProbeStepResult] = []
        started = datetime.now(timezone.utc).isoformat()
        try:
            self.transport.open()
            for step in plan:
                results.append(self._execute(step))
        except TransportError as exc:
            results.append(ProbeStepResult(
                name="transport", command="", tx_hex="", rx_bytes=0, rx_hex="",
                rx_text="", duration_ms=0, ok=False, note=str(exc),
            ))
        finally:
            self.transport.close()
        profile = self.transport.profile.to_dict()
        return ProbeCapture(
            subsystem=self.subsystem.value,
            profile=profile,
            started_at=started,
            steps=tuple(results),
            custom=tuple(self._custom),
            ok=all(step.ok for step in results),
        )

    def custom(self, command: str, note: str = "operator-entered raw command") -> ProbeStepResult:
        """Send one operator-entered command (recorded as ``custom``)."""
        if not isinstance(command, str) or not command.strip():
            raise ProbeError("custom probe command must be non-empty text")
        result = self._execute(ProbeStep("custom", command.strip(), note), checked=False)
        self._custom.append(result)
        return result

    def run_custom(self, command: str, note: str = "operator-entered raw command") -> ProbeCapture:
        """Open the transport, send one operator command, capture, close."""
        if not isinstance(command, str) or not command.strip():
            raise ProbeError("custom probe command must be non-empty text")
        started = datetime.now(timezone.utc).isoformat()
        try:
            self.transport.open()
            result = self.custom(command, note=note)
        except TransportError as exc:
            result = ProbeStepResult(
                name="custom", command=command, tx_hex="", rx_bytes=0, rx_hex="",
                rx_text="", duration_ms=0, ok=False, note=str(exc),
            )
            self._custom.append(result)
        finally:
            self.transport.close()
        return ProbeCapture(
            subsystem=self.subsystem.value,
            profile=self.transport.profile.to_dict(),
            started_at=started,
            steps=(),
            custom=tuple(self._custom),
            ok=result.ok,
        )

    def _execute(self, step: ProbeStep, *, checked: bool = True) -> ProbeStepResult:
        if checked:
            allowed = _ALLOWED[self.subsystem]
            if step.command not in allowed:
                raise ProbeCommandDenied(
                    f"{step.command!r} is not on the read-only probe allowlist for "
                    f"{self.subsystem.value}"
                )
        from time import perf_counter

        try:
            tx = self.transport._frame(step.command)  # framing used by the transport
        except (ValueError, AttributeError):
            tx = (step.command + self.transport.profile.write_terminator).encode(
                self.transport.profile.encoding
            )
        started_ms = perf_counter()
        try:
            self.transport.write(step.command)
            reply = self.transport.read_until()
            ok = True
            note = ""
        except TransportError as exc:
            reply, ok, note = "", False, str(exc)
        duration_ms = int(round((perf_counter() - started_ms) * 1000))
        raw = reply.encode(self.transport.profile.encoding, errors="replace")
        problems: list[str] = []
        if step.expected_reply_bytes is not None and len(raw) != step.expected_reply_bytes:
            ok = False
            problems.append(f"expected {step.expected_reply_bytes} reply bytes, got {len(raw)}")
        if step.expected_marker and step.expected_marker not in reply:
            ok = False
            problems.append(f"expected marker {step.expected_marker!r} not found in reply")
        note = "; ".join(problems)
        return ProbeStepResult(
            name=step.name,
            command=step.command,
            tx_hex=tx.hex(" "),
            rx_bytes=len(raw),
            rx_hex=raw.hex(" "),
            rx_text=reply,
            duration_ms=duration_ms,
            ok=ok,
            note=note,
        )


def iter_available_ports() -> Iterable[str]:
    """Yield available serial port names without importing pyserial eagerly."""
    try:
        from serial.tools import list_ports
    except ImportError:
        return
    for info in list_ports.comports():
        yield info.device
