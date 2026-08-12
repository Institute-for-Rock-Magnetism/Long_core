"""Recovered LabVIEW system-configuration schema with historical defaults.

Field names and defaults come from the printed global panels and the serial
initializer XML (see ``reconstructions/GLOBALS_REVERSE_ENGINEERING.md``).
Values are software defaults, not commissioned machine values. The module
performs no I/O; it exists so the GUI can render and validate the legacy
settings exactly.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping


class SettingsValidationError(ValueError):
    """Raised when a recovered setting value is unsafe or malformed."""


class MeasurementType(str, Enum):
    CONTINUOUS = "Continuous"
    DISCRETE = "Discrete"


class DriftToleranceType(int, Enum):
    PERCENT_OF_SIGNAL = 0
    ABSOLUTE_VALUE = 1


class SaveOrAbort(int, Enum):
    SAVE_AND_CONTINUE = 0
    ABORT = 1


class TrackKind(str, Enum):
    STANDARD = "Standard"
    HIGH_FIELD = "High Field"


class YesNo(str, Enum):
    YES = "Yes"
    NO = "No"


def _number(value: object, field_name: str, minimum: float, maximum: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
    ):
        raise SettingsValidationError(f"{field_name} must be a finite number")
    result = float(value)
    if not minimum <= result <= maximum:
        raise SettingsValidationError(
            f"{field_name} must be between {minimum} and {maximum}"
        )
    return result


def _enum(value: object, enum_type: type[Enum], field_name: str) -> Enum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except ValueError as exc:
        allowed = ", ".join(str(item.value) for item in enum_type)
        raise SettingsValidationError(
            f"{field_name} must be one of: {allowed}"
        ) from exc


@dataclass(frozen=True, slots=True)
class LegacyFilePaths:
    """Recovered ``File Paths.vi`` global fields and defaults."""

    application_name: str = "Long Core Control"
    local_hard_drive_file_path: str = r"C:\Testing"
    application_folder_file_path: str = ""
    data_file_path: str = ""
    data_file_name: str = ""
    backup_data_file_path: str = ""
    backup_data_file: bool = False
    sample_input_file_path: str = ""
    sample_input_file_name: str = ""
    users_data_file_path: str = ""
    users_data_file_name: str = ""
    use_sample_id: bool = False
    meas_queue_file_path: str = ""
    meas_queue_file_name: str = ""
    datalog_file_names: tuple[str, str, str] = ("", "", "")
    datalog_path: str = ""

    def __post_init__(self) -> None:
        for name in (
            "application_name",
            "local_hard_drive_file_path",
            "application_folder_file_path",
            "data_file_path",
            "data_file_name",
            "backup_data_file_path",
            "sample_input_file_path",
            "sample_input_file_name",
            "users_data_file_path",
            "users_data_file_name",
            "meas_queue_file_path",
            "meas_queue_file_name",
            "datalog_path",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or "\x00" in value:
                raise SettingsValidationError(f"{name} must be text")
        for name in ("backup_data_file", "use_sample_id"):
            if not isinstance(getattr(self, name), bool):
                raise SettingsValidationError(f"{name} must be boolean")
        names = getattr(self, "datalog_file_names")
        if (
            not isinstance(names, tuple)
            or len(names) != 3
            or not all(isinstance(n, str) for n in names)
        ):
            raise SettingsValidationError("datalog_file_names must be three strings")


@dataclass(frozen=True, slots=True)
class SerialPortDefaults:
    """Recovered per-subsystem serial defaults (VISA, 9600 baud)."""

    #: Diagram constants recovered from Serial Port Initializer2.vi.
    recovered_ports: tuple[str, ...] = ("COM1", "COM2", "COM3", "COM4")
    #: The ARM case in the initializer diagram wires COM4.
    arm_port: str = "COM4"
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = "N"
    stopbits: float = 1.0
    #: Subsystem -> legacy port-number semantics from the setup help text.
    legacy_port_numbers: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8)

    def __post_init__(self) -> None:
        for port in self.recovered_ports:
            if not isinstance(port, str) or not port.startswith("COM"):
                raise SettingsValidationError(f"invalid recovered port: {port!r}")
        if not isinstance(self.baudrate, int) or self.baudrate <= 0:
            raise SettingsValidationError("baudrate must be a positive integer")
        if self.bytesize not in {5, 6, 7, 8}:
            raise SettingsValidationError("bytesize must be 5-8")
        if self.parity.upper() not in {"N", "E", "O", "M", "S"}:
            raise SettingsValidationError("parity must be N, E, O, M, or S")
        if self.stopbits not in {1, 1.0, 1.5, 2, 2.0}:
            raise SettingsValidationError("stopbits must be 1, 1.5, or 2")


@dataclass(frozen=True, slots=True)
class TrayParameters:
    """Recovered ``Tray data.vi`` per-system defaults."""

    measurement_type: MeasurementType = MeasurementType.CONTINUOUS
    sample_interval: float = 1.00
    leader_length: float = 9.0
    trailer_length: float = 15.0
    delay_after_move_sec: float = 0.0
    drift_corrected: YesNo = YesNo.NO
    tray_corrected: YesNo = YesNo.NO
    homing: YesNo = YesNo.NO
    valid_tray: bool = False
    tray_1_z: float = 0.0
    tray_2_z: float = 0.0
    tray_3_z: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "measurement_type", _enum(self.measurement_type, MeasurementType, "measurement_type")
        )
        object.__setattr__(self, "sample_interval", _number(self.sample_interval, "sample_interval", 0.0, 1e6))
        object.__setattr__(self, "leader_length", _number(self.leader_length, "leader_length", 0.0, 1e6))
        object.__setattr__(self, "trailer_length", _number(self.trailer_length, "trailer_length", 0.0, 1e6))
        object.__setattr__(self, "delay_after_move_sec", _number(self.delay_after_move_sec, "delay_after_move_sec", 0.0, 1e6))
        object.__setattr__(self, "drift_corrected", _enum(self.drift_corrected, YesNo, "drift_corrected"))
        object.__setattr__(self, "tray_corrected", _enum(self.tray_corrected, YesNo, "tray_corrected"))
        object.__setattr__(self, "homing", _enum(self.homing, YesNo, "homing"))
        if not isinstance(self.valid_tray, bool):
            raise SettingsValidationError("valid_tray must be boolean")
        for name in ("tray_1_z", "tray_2_z", "tray_3_z"):
            object.__setattr__(self, name, _number(getattr(self, name), name, -1e9, 1e9))


@dataclass(frozen=True, slots=True)
class BackgroundParameters:
    """Recovered ``Bkgnd.vi`` autosave/drift defaults."""

    drift_tolerance_type: DriftToleranceType = DriftToleranceType.PERCENT_OF_SIGNAL
    drift_tolerance_percent: float = 0.0
    drift_tolerance_absolute: float = 4.0e-8
    remeasure_count: int = 0
    save_or_abort: SaveOrAbort = SaveOrAbort.SAVE_AND_CONTINUE
    background_1_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    background_2_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    meter_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "drift_tolerance_type",
            _enum(self.drift_tolerance_type, DriftToleranceType, "drift_tolerance_type"),
        )
        object.__setattr__(
            self, "drift_tolerance_percent",
            _number(self.drift_tolerance_percent, "drift_tolerance_percent", 0.0, 100.0),
        )
        object.__setattr__(
            self, "drift_tolerance_absolute",
            _number(self.drift_tolerance_absolute, "drift_tolerance_absolute", 0.0, 1e6),
        )
        if not isinstance(self.remeasure_count, int) or isinstance(self.remeasure_count, bool) or self.remeasure_count < 0:
            raise SettingsValidationError("remeasure_count must be a non-negative integer")
        object.__setattr__(self, "save_or_abort", _enum(self.save_or_abort, SaveOrAbort, "save_or_abort"))
        for name in ("background_1_xyz", "background_2_xyz", "meter_xyz"):
            values = getattr(self, name)
            if not isinstance(values, tuple) or len(values) != 3:
                raise SettingsValidationError(f"{name} must be a three-tuple")
            object.__setattr__(
                self, name,
                tuple(_number(v, name, -1e9, 1e9) for v in values),
            )


@dataclass(frozen=True, slots=True)
class FurnaceParameters:
    """Recovered ``Furnace Globals.vi`` defaults."""

    cooling_temp_degc: float = 30.00
    hold_time_min: float = 0.0
    fan_temp_degc: float = 51.00

    def __post_init__(self) -> None:
        object.__setattr__(self, "cooling_temp_degc", _number(self.cooling_temp_degc, "cooling_temp_degc", -100.0, 2000.0))
        object.__setattr__(self, "hold_time_min", _number(self.hold_time_min, "hold_time_min", 0.0, 1e6))
        object.__setattr__(self, "fan_temp_degc", _number(self.fan_temp_degc, "fan_temp_degc", -100.0, 2000.0))


@dataclass(frozen=True, slots=True)
class SampleHandlerParameters:
    """Recovered ``Sample Handler Globals.vi`` defaults."""

    home_switch_type: str = "Home Switch"
    next_position_steps: int = 0
    positive_direction: bool = False
    homing: bool = False
    home_initialized: bool = False
    furnace_home_initialized: bool = False
    furnace_location: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.home_switch_type, str) or not self.home_switch_type:
            raise SettingsValidationError("home_switch_type must be non-empty text")
        if not isinstance(self.next_position_steps, int) or isinstance(self.next_position_steps, bool) or not 0 <= self.next_position_steps <= 100_000_000:
            raise SettingsValidationError("next_position_steps must be a non-negative step count")
        for name in ("homing", "home_initialized", "furnace_home_initialized", "positive_direction"):
            if not isinstance(getattr(self, name), bool):
                raise SettingsValidationError(f"{name} must be boolean")


@dataclass(frozen=True, slots=True)
class OfflineTreatmentParameters:
    """Recovered ``Offline Treatment.vi`` (queue pause step) defaults."""

    daqs_to_average: int = 1
    units_si: bool = True
    treatment: str = "Degauss X, Y, & Z"
    dg_amplitude: float = 0.0
    arm_amplitude: float = 0.0
    irm_amplitude: float = 0.0
    randomize_dg_axis: bool = False
    temperature: float = 0.0
    field_dec: float = 0.0
    field_inc: float = 90.0

    def __post_init__(self) -> None:
        if not isinstance(self.daqs_to_average, int) or isinstance(self.daqs_to_average, bool) or not 0 <= self.daqs_to_average <= 1:
            raise SettingsValidationError("daqs_to_average must be 0 or 1")
        if not isinstance(self.treatment, str) or not self.treatment:
            raise SettingsValidationError("treatment must be non-empty text")
        for name in ("units_si", "randomize_dg_axis"):
            if not isinstance(getattr(self, name), bool):
                raise SettingsValidationError(f"{name} must be boolean")
        for name in ("dg_amplitude", "arm_amplitude", "irm_amplitude", "temperature", "field_dec", "field_inc"):
            object.__setattr__(self, name, _number(getattr(self, name), name, -1e6, 1e6))


@dataclass(frozen=True, slots=True)
class LegacySettings:
    """The recovered LabVIEW configuration as one validated structure."""

    file_paths: LegacyFilePaths = field(default_factory=LegacyFilePaths)
    serial: SerialPortDefaults = field(default_factory=SerialPortDefaults)
    track_type: TrackKind = TrackKind.STANDARD
    scale: float = 1.00
    tray: TrayParameters = field(default_factory=TrayParameters)
    background: BackgroundParameters = field(default_factory=BackgroundParameters)
    furnace: FurnaceParameters = field(default_factory=FurnaceParameters)
    sample_handler: SampleHandlerParameters = field(default_factory=SampleHandlerParameters)
    offline_treatment: OfflineTreatmentParameters = field(default_factory=OfflineTreatmentParameters)
    degauss_character_delay_ms: int = 50

    def __post_init__(self) -> None:
        object.__setattr__(self, "track_type", _enum(self.track_type, TrackKind, "track_type"))
        object.__setattr__(self, "scale", _number(self.scale, "scale", -1e6, 1e6))
        if not isinstance(self.degauss_character_delay_ms, int) or self.degauss_character_delay_ms < 0:
            raise SettingsValidationError("degauss_character_delay_ms must be a non-negative integer")
        for name in (
            "file_paths",
            "serial",
            "tray",
            "background",
            "furnace",
            "sample_handler",
            "offline_treatment",
        ):
            if not isinstance(getattr(self, name), (LegacyFilePaths, SerialPortDefaults,
                                                    TrayParameters, BackgroundParameters,
                                                    FurnaceParameters, SampleHandlerParameters,
                                                    OfflineTreatmentParameters)):
                raise SettingsValidationError(f"{name} must be a recovered settings object")

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_paths": asdict(self.file_paths),
            "serial": asdict(self.serial),
            "track_type": self.track_type.value,
            "scale": self.scale,
            "tray": asdict(self.tray),
            "background": asdict(self.background),
            "furnace": asdict(self.furnace),
            "sample_handler": asdict(self.sample_handler),
            "offline_treatment": asdict(self.offline_treatment),
            "degauss_character_delay_ms": self.degauss_character_delay_ms,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LegacySettings":
        if not isinstance(data, Mapping):
            raise SettingsValidationError("legacy settings must be an object")
        allowed = set(cls.__dataclass_fields__)
        unknown = set(data) - allowed
        if unknown:
            raise SettingsValidationError(f"unknown legacy settings fields: {sorted(unknown)}")
        values = dict(data)
        for name in (
            "file_paths",
            "serial",
            "tray",
            "background",
            "furnace",
            "sample_handler",
            "offline_treatment",
        ):
            if name in values:
                raw = values[name]
                if not isinstance(raw, Mapping):
                    raise SettingsValidationError(f"{name} must be an object")
                # Enum fields serialize as raw values; rebuild via constructor.
                target = {
                    "file_paths": LegacyFilePaths,
                    "serial": SerialPortDefaults,
                    "tray": TrayParameters,
                    "background": BackgroundParameters,
                    "furnace": FurnaceParameters,
                    "sample_handler": SampleHandlerParameters,
                    "offline_treatment": OfflineTreatmentParameters,
                }[name]
                values[name] = target(**dict(raw))
        try:
            return cls(**values)
        except TypeError as exc:
            raise SettingsValidationError("invalid legacy settings") from exc
