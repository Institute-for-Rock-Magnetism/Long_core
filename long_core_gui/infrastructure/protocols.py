"""Pure, validated command builders reconstructed from the LabVIEW sources.

Commands intentionally exclude serial terminators; framing belongs to the
transport. The sample-handler and SQUID word forms mirror the recovered command
enum labels and remain isolated here so verified controller spellings can be
updated without affecting application logic.
"""

from __future__ import annotations

from enum import Enum
import math


class ProtocolValidationError(ValueError):
    """Raised before an unsafe or malformed command can reach a transport."""


class Axis(str, Enum):
    X = "X"
    Y = "Y"
    Z = "Z"
    ALL = "ALL"


class SquidFilter(str, Enum):
    HZ_1 = "1 Hz"
    HZ_10 = "10 Hz"
    HZ_100 = "100 Hz"
    WIDE = "Wide band"


class SquidRange(str, Enum):
    X1 = "1x range"
    X10 = "10x range"
    X100 = "100x range"
    EXTENDED = "Extended range"


class SquidSlew(str, Enum):
    ENABLE_FAST = "Enable fast slew"
    DISABLE_FAST = "Disable fast slew"


class SquidFeedback(str, Enum):
    OPEN = "Open feedback loop"
    CLOSE = "Close feedback loop"
    PULSE_RESET = "Pulse reset the feedback loop"


class SquidStatus(str, Enum):
    ALL = "All status"
    FILTER = "Filter status"
    RANGE = "Range status"
    SLEW = "Slew status"
    FEEDBACK = "Feedback loop status"


def _enum(value: object, enum_type: type[Enum], field: str) -> Enum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value).upper())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ProtocolValidationError(f"{field} must be one of: {allowed}") from exc


def _integer(value: object, field: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ProtocolValidationError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise ProtocolValidationError(f"{field} must be between {minimum} and {maximum}")
    return value


def _number(value: object, field: str, minimum: float, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ProtocolValidationError(f"{field} must be a finite number")
    result = float(value)
    if not minimum <= result <= maximum:
        raise ProtocolValidationError(f"{field} must be between {minimum} and {maximum}")
    return result


def _format_number(value: float) -> str:
    return format(value, ".9g")


class SampleHandlerCommands:
    """Exact 2G SMC25 command builders recovered from the driver enums.

    The command dictionary is the recovered enum set of
    ``2G Sample Handler Driver.vi``; each label carries the exact byte form,
    e.g. ``Absolute move - Prrrrrr`` means ``P`` followed by six digits.
    Legacy spellings (``Decelaration``, ``Deselct``) are preserved in the
    enum names only; the bytes are spelled exactly.
    """

    MAX_RATE = 9999  # Bddd / Mddd / Azz fields are four/three digits
    MAX_POSITION = 999_999  # Prrrrrr / Nrrrrrr fields are six digits

    @staticmethod
    def _field(value: float, digits: int, field: str) -> str:
        value = _number(value, field, 0.0, 10**digits - 1)
        return f"{value:.0f}".zfill(digits)

    @staticmethod
    def abort() -> str:
        return "."

    @staticmethod
    def absolute_move(position: float) -> str:
        return f"P{SampleHandlerCommands._field(position, 6, 'position')}"

    @staticmethod
    def relative_move(distance: float) -> str:
        return f"N{SampleHandlerCommands._field(distance, 6, 'distance')}"

    @staticmethod
    def acceleration(value: float) -> str:
        return f"A{SampleHandlerCommands._field(value, 2, 'acceleration')}"

    @staticmethod
    def base_rate(value: float) -> str:
        return f"B{SampleHandlerCommands._field(value, 4, 'base_rate')}"

    @staticmethod
    def deceleration(value: float) -> str:
        return f"D{SampleHandlerCommands._field(value, 2, 'deceleration')}"

    @staticmethod
    def maximum_speed(value: float) -> str:
        return f"M{SampleHandlerCommands._field(value, 4, 'maximum_speed')}"

    @staticmethod
    def slow_jog_speed(value: float) -> str:
        return f"J{SampleHandlerCommands._field(value, 2, 'slow_jog_speed')}"

    @staticmethod
    def hold_time(value: int) -> str:
        return f"CH{_integer(value, 'hold_time', 0, 99)}"

    @staticmethod
    def home(position: int = 1) -> str:
        return f"H{_integer(position, 'home_position', 1, 2)}"

    @staticmethod
    def crystal_frequency() -> str:
        return "CX"

    @staticmethod
    def identify() -> str:
        return "?"

    @staticmethod
    def go() -> str:
        return "G"

    @staticmethod
    def go_and_wait() -> str:
        return "GF"

    @staticmethod
    def poll() -> str:
        return "%"

    @staticmethod
    def remaining_steps() -> str:
        return "G"

    @staticmethod
    def select_axis(axis: int) -> str:
        return f"@{_integer(axis, 'axis', 0, 99)}"

    @staticmethod
    def set_position_register(value: int) -> str:
        return f"Z{_integer(value, 'position_register', 0, 999_999)}"

    @staticmethod
    def slew(direction: int) -> str:
        if direction not in {-1, 1}:
            raise ProtocolValidationError("slew direction must be -1 or 1")
        return f"S{direction}"

    @staticmethod
    def stop() -> str:
        return "Q"

    @staticmethod
    def input_pins(pins: int) -> str:
        return f"I{_integer(pins, 'input_pins', 0, 99)},0"

    @staticmethod
    def output_pins(pins: int) -> str:
        return f"O{_integer(pins, 'output_pins', 0, 99)},0"

    @staticmethod
    def wait_period() -> str:
        return "W"

    @staticmethod
    def verify() -> str:
        return "V"


class IrmCommands:
    """Recovered IRM PCA/PET/PSS/PCRH protocol."""

    @staticmethod
    def amplitude(value: int) -> str:
        return f"PCA{_integer(value, 'amplitude', 0, 9999):04d}"

    @staticmethod
    def trigger() -> str:
        return "PET"

    @staticmethod
    def status() -> str:
        return "PSS"

    @staticmethod
    def attention() -> str:
        return "PCRH"


class ArmCommands:
    """Recovered ARM ARMCAA/ARMCAT/ARMCF/ARMSS protocol.

    ``ARMCAA`` and ``ARMCAT`` select the axial and transverse axes, ``ARMCF``
    configures, and ``ARMSS`` requests status. The legacy status scan pattern
    is preserved as ``ARM_STATUS_SCAN``.
    """

    ARM_STATUS_SCAN = "[OF]"

    @staticmethod
    def select_axis(axis: str) -> str:
        if isinstance(axis, str):
            axis = axis.lower()
        if axis in {"axial", "a"}:
            return "ARMCAA"
        if axis in {"transverse", "t"}:
            return "ARMCAT"
        raise ProtocolValidationError("ARM axis must be axial or transverse")

    @staticmethod
    def configure() -> str:
        return "ARMCF"

    @staticmethod
    def status() -> str:
        return "ARMSS"


class DegaussCommands:
    """Recovered DCC/DCA/DCR/DCD/DER*/DSS degausser protocol."""

    @staticmethod
    def coil(coil: int | Axis) -> str:
        if isinstance(coil, Axis):
            if coil is Axis.ALL:
                raise ProtocolValidationError("degauss coil cannot be ALL")
            coil = {Axis.X: 1, Axis.Y: 2, Axis.Z: 3}[coil]
        return f"DCC{_integer(coil, 'coil', 1, 3)}"

    @staticmethod
    def amplitude(value: int) -> str:
        return f"DCA{_integer(value, 'amplitude', 0, 9999):04d}"

    @staticmethod
    def ramp(rate: int) -> str:
        rate = _integer(rate, "ramp", 1, 9)
        if rate not in {1, 3, 5, 7, 9}:
            raise ProtocolValidationError("ramp must be one of 1, 3, 5, 7, or 9")
        return f"DCR{rate}"

    @staticmethod
    def delay(delay: int) -> str:
        return f"DCD{_integer(delay, 'delay', 1, 9)}"

    @staticmethod
    def ramp_up() -> str:
        return "DERU"

    @staticmethod
    def ramp_down() -> str:
        return "DERD"

    @staticmethod
    def cycle() -> str:
        return "DERC"

    @staticmethod
    def status() -> str:
        return "DSS"


class SquidCommands:
    """Exact compact commands recovered from the LabVIEW 8.6 SQUID driver.

    Serial framing is intentionally excluded. The original VI appends ``\r``
    and uses a two-second, string-terminated read in its transport layer.
    """

    _FILTER_CODES = {
        SquidFilter.HZ_1: "1",
        SquidFilter.HZ_10: "T",
        SquidFilter.HZ_100: "H",
        SquidFilter.WIDE: "W",
    }
    _RANGE_CODES = {
        SquidRange.X1: "1",
        SquidRange.X10: "T",
        SquidRange.X100: "H",
        SquidRange.EXTENDED: "E",
    }
    _SLEW_CODES = {
        SquidSlew.ENABLE_FAST: "E",
        SquidSlew.DISABLE_FAST: "D",
    }
    _FEEDBACK_CODES = {
        SquidFeedback.OPEN: "O",
        SquidFeedback.CLOSE: "C",
        SquidFeedback.PULSE_RESET: "P",
    }
    _STATUS_CODES = {
        SquidStatus.ALL: "A",
        SquidStatus.FILTER: "F",
        SquidStatus.RANGE: "R",
        SquidStatus.SLEW: "S",
        SquidStatus.FEEDBACK: "L",
    }

    @staticmethod
    def _axis(axis: Axis | str, *, allow_all: bool = True) -> Axis:
        result = _enum(axis, Axis, "axis")
        assert isinstance(result, Axis)
        if not allow_all and result is Axis.ALL:
            raise ProtocolValidationError("axis must be X, Y, or Z")
        return result

    @staticmethod
    def _choice(value: object, enum_type: type[Enum], aliases: dict[str, Enum]) -> Enum:
        if isinstance(value, enum_type):
            return value
        normalized = str(value).strip().lower().replace("_", " ")
        for member in enum_type:
            if normalized == str(member.value).lower():
                return member
        if normalized in aliases:
            return aliases[normalized]
        allowed = ", ".join(str(member.value) for member in enum_type)
        raise ProtocolValidationError(f"value must be one of: {allowed}")

    @staticmethod
    def _axis_command(axis: Axis | str, all_code: str, x: str, y: str, z: str) -> str:
        selected = SquidCommands._axis(axis)
        return {Axis.ALL: all_code, Axis.X: x, Axis.Y: y, Axis.Z: z}[selected]

    @staticmethod
    def filter(axis: Axis | str, mode: SquidFilter | str) -> str:
        selected = SquidCommands._choice(
            mode, SquidFilter,
            {"1hz": SquidFilter.HZ_1, "10hz": SquidFilter.HZ_10,
             "100hz": SquidFilter.HZ_100, "wide": SquidFilter.WIDE},
        )
        prefix = SquidCommands._axis_command(axis, "ACF", "XCF", "YFC", "ZCF")
        return prefix + SquidCommands._FILTER_CODES[selected]

    @staticmethod
    def range(axis: Axis | str, value: SquidRange | str) -> str:
        selected = SquidCommands._choice(
            value, SquidRange,
            {"1x": SquidRange.X1, "10x": SquidRange.X10,
             "100x": SquidRange.X100, "extended": SquidRange.EXTENDED},
        )
        prefix = SquidCommands._axis_command(axis, "ACR", "XCR", "YCR", "ZCR")
        return prefix + SquidCommands._RANGE_CODES[selected]

    @staticmethod
    def slew(axis: Axis | str, value: SquidSlew | str) -> str:
        selected = SquidCommands._choice(
            value, SquidSlew,
            {"fast": SquidSlew.ENABLE_FAST, "normal": SquidSlew.DISABLE_FAST},
        )
        prefix = SquidCommands._axis_command(axis, "ACS", "XCS", "YCS", "ZCS")
        return prefix + SquidCommands._SLEW_CODES[selected]

    @staticmethod
    def feedback(axis: Axis | str, value: SquidFeedback | str) -> str:
        selected = SquidCommands._choice(
            value, SquidFeedback,
            {"off": SquidFeedback.OPEN, "on": SquidFeedback.CLOSE,
             "pulse": SquidFeedback.PULSE_RESET, "reset": SquidFeedback.PULSE_RESET},
        )
        prefix = SquidCommands._axis_command(axis, "ACL", "XCL", "YCL", "ZCL")
        return prefix + SquidCommands._FEEDBACK_CODES[selected]

    @staticmethod
    def latch_analog(axis: Axis | str = Axis.ALL) -> str:
        return SquidCommands._axis_command(axis, "ALD", "XLD", "YLD", "ZLD")

    @staticmethod
    def read_analog(axis: Axis | str) -> str:
        selected = SquidCommands._axis(axis, allow_all=False)
        return {Axis.X: "XSD", Axis.Y: "YSD", Axis.Z: "ZSD"}[selected]

    @staticmethod
    def latch_counter(axis: Axis | str = Axis.ALL) -> str:
        return SquidCommands._axis_command(axis, "ALC", "XLC", "YLC", "ZLC")

    @staticmethod
    def read_counter(axis: Axis | str) -> str:
        selected = SquidCommands._axis(axis, allow_all=False)
        return {Axis.X: "XSC", Axis.Y: "YSC", Axis.Z: "ZSC"}[selected]

    @staticmethod
    def reset_counter(axis: Axis | str = Axis.ALL) -> str:
        return SquidCommands._axis_command(axis, "ARC", "XRC", "YRC", "ZRC")

    @staticmethod
    def status(axis: Axis | str, status: SquidStatus | str = SquidStatus.ALL) -> str:
        selected_axis = SquidCommands._axis(axis, allow_all=False)
        selected_status = SquidCommands._choice(
            status, SquidStatus,
            {"all": SquidStatus.ALL, "filter": SquidStatus.FILTER,
             "range": SquidStatus.RANGE, "slew": SquidStatus.SLEW,
             "feedback": SquidStatus.FEEDBACK},
        )
        return f"{selected_axis.value}SS{SquidCommands._STATUS_CODES[selected_status]}"

    @staticmethod
    def verify_connection() -> str:
        return "ZSSA"
