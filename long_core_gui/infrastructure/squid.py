"""Fail-closed SQUID protocol parsing and acquisition math.

This module implements only behavior confirmed in the LabVIEW 8.6 VIs and
their extracted RSRC default-data arrays. It performs no serial I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Mapping

from .protocols import (
    Axis,
    ProtocolValidationError,
    SquidCommands,
    SquidFeedback,
    SquidFilter,
    SquidRange,
    SquidSlew,
    SquidStatus,
)


class SquidReplyError(ValueError):
    """Raised when a fixed-format SQUID reply cannot be decoded safely."""


@dataclass(frozen=True, slots=True)
class SquidStatusReply:
    filter: SquidFilter | None = None
    range: SquidRange | None = None
    slew: SquidSlew | None = None
    feedback: SquidFeedback | None = None


@dataclass(frozen=True, slots=True)
class SquidCommandStep:
    command: str
    expected_reply_bytes: int = 0
    delay_after_s: float = 0.0


@dataclass(frozen=True, slots=True)
class AxisVector:
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        for name in ("x", "y", "z"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ProtocolValidationError(f"{name} must be a finite number")


@dataclass(frozen=True, slots=True)
class SquidMeasurement:
    raw: AxisVector
    adjusted: AxisVector
    moment: AxisVector


_FILTER_DECODE = {
    "1": SquidFilter.HZ_1, "T": SquidFilter.HZ_10,
    "H": SquidFilter.HZ_100, "W": SquidFilter.WIDE,
}
_RANGE_DECODE = {
    "1": SquidRange.X1, "T": SquidRange.X10,
    "H": SquidRange.X100, "E": SquidRange.EXTENDED,
}
_SLEW_DECODE = {"E": SquidSlew.ENABLE_FAST, "D": SquidSlew.DISABLE_FAST}
_FEEDBACK_DECODE = {
    "O": SquidFeedback.OPEN,
    "C": SquidFeedback.CLOSE,
    "P": SquidFeedback.PULSE_RESET,
}
_STATUS_LAYOUT = {
    SquidStatus.FILTER: ("F", _FILTER_DECODE, "filter"),
    SquidStatus.RANGE: ("R", _RANGE_DECODE, "range"),
    SquidStatus.SLEW: ("S", _SLEW_DECODE, "slew"),
    SquidStatus.FEEDBACK: ("L", _FEEDBACK_DECODE, "feedback"),
}


def parse_status_reply(
    reply: str, status: SquidStatus = SquidStatus.ALL
) -> SquidStatusReply:
    """Decode the VI's three-byte segments and reject malformed markers/codes."""

    if not isinstance(reply, str):
        raise SquidReplyError("status reply must be text")
    if status is SquidStatus.ALL:
        if len(reply) != 12:
            raise SquidReplyError("all-status reply must contain exactly 12 characters")
        values: dict[str, object] = {}
        for offset, category in zip(
            (0, 3, 6, 9),
            (SquidStatus.FILTER, SquidStatus.RANGE, SquidStatus.SLEW, SquidStatus.FEEDBACK),
        ):
            marker, table, field = _STATUS_LAYOUT[category]
            if reply[offset] != marker:
                raise SquidReplyError(f"expected {marker!r} marker at offset {offset}")
            try:
                values[field] = table[reply[offset + 1]]
            except KeyError as exc:
                raise SquidReplyError(f"unknown {field} status code {reply[offset + 1]!r}") from exc
        return SquidStatusReply(**values)

    if len(reply) != 3:
        raise SquidReplyError("single-status reply must contain exactly 3 characters")
    marker, table, field = _STATUS_LAYOUT[status]
    if reply[0] != marker:
        raise SquidReplyError(f"expected {marker!r} status marker")
    try:
        value = table[reply[1]]
    except KeyError as exc:
        raise SquidReplyError(f"unknown {field} status code {reply[1]!r}") from exc
    return SquidStatusReply(**{field: value})


def verify_connection_reply(reply: str) -> SquidStatusReply:
    """Validate the 12-byte reply required by the hard-coded ``ZSSA`` probe."""

    return parse_status_reply(reply, SquidStatus.ALL)


def parse_counter_reply(reply: str) -> int:
    text = reply.strip()
    if not re.fullmatch(r"[+-]?\d+", text):
        raise SquidReplyError("counter reply is not a signed decimal integer")
    value = int(text)
    if not -(2**31) <= value < 2**31:
        raise SquidReplyError("counter reply is outside signed 32-bit range")
    return value


def normalize_x_analog_reply(reply: str) -> str:
    """Reproduce ``SQUID AC PARSE.vi`` without guessing numeric semantics."""

    if not reply.startswith("P"):
        return reply
    if len(reply) < 14:
        raise SquidReplyError("P-prefixed X analog reply is shorter than 14 characters")
    return " ".join((reply[10:12], reply[8:10], reply[4:6], reply[12:14]))


def parse_analog_reply(reply: str, axis: Axis | str) -> float:
    selected = axis if isinstance(axis, Axis) else Axis(str(axis).upper())
    if selected is Axis.ALL:
        raise SquidReplyError("analog replies are axis-specific")
    text = normalize_x_analog_reply(reply) if selected is Axis.X else reply
    try:
        value = float(text.strip())
    except ValueError as exc:
        raise SquidReplyError(
            "analog reply is not directly numeric; a real P-format trace is required"
        ) from exc
    if not math.isfinite(value):
        raise SquidReplyError("analog reply is not finite")
    return value


def acquisition_plan(ranges: Mapping[Axis, SquidRange]) -> tuple[SquidCommandStep, ...]:
    """Build the connected-mode DAQ sequence recovered from ``SQUID DAQ.vi``."""

    missing = {Axis.X, Axis.Y, Axis.Z} - set(ranges)
    if missing:
        raise ProtocolValidationError("ranges must contain X, Y, and Z")
    steps = [
        SquidCommandStep(SquidCommands.latch_analog()),
        SquidCommandStep(SquidCommands.latch_counter(), delay_after_s=0.3),
    ]
    for axis in (Axis.X, Axis.Y, Axis.Z):
        if ranges[axis] is SquidRange.X1:
            steps.append(SquidCommandStep(SquidCommands.read_counter(axis), 7, 0.05))
    for axis in (Axis.Z, Axis.Y, Axis.X):
        delay = 0.05 if axis is not Axis.X else 0.0
        steps.append(SquidCommandStep(SquidCommands.read_analog(axis), 9, delay))
    return tuple(steps)


def calculate_measurement(
    counters: AxisVector,
    analog: AxisVector,
    background: AxisVector,
    calibration: AxisVector,
    ranges: Mapping[Axis, SquidRange],
    *,
    background_capture: bool = False,
) -> SquidMeasurement:
    """Combine counter/analog values, background-correct, then calibrate."""

    missing = {Axis.X, Axis.Y, Axis.Z} - set(ranges)
    if missing:
        raise ProtocolValidationError("ranges must contain X, Y, and Z")
    raw_values = {}
    for axis, name in ((Axis.X, "x"), (Axis.Y, "y"), (Axis.Z, "z")):
        counter = getattr(counters, name) if ranges[axis] is SquidRange.X1 else 0.0
        raw_values[name] = counter + getattr(analog, name)
    raw = AxisVector(**raw_values)
    adjusted = AxisVector(**{
        name: getattr(raw, name) if background_capture else getattr(raw, name) - getattr(background, name)
        for name in ("x", "y", "z")
    })
    moment = AxisVector(**{
        name: getattr(adjusted, name) * getattr(calibration, name)
        for name in ("x", "y", "z")
    })
    return SquidMeasurement(raw, adjusted, moment)
