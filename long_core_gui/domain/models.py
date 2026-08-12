"""Validated domain models for the Long Core measurement system.

The domain layer intentionally contains no Qt, serial-port, or instrument-driver
dependencies.  Values that must be established on the real instrument are
optional instead of being populated with unsafe assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, ClassVar, Mapping, Optional, Sequence, Type, TypeVar


class DomainValidationError(ValueError):
    """Validation failure with errors addressable by field name."""

    def __init__(self, errors: Mapping[str, Sequence[str] | str]) -> None:
        normalized = {
            str(name): (value,) if isinstance(value, str) else tuple(value)
            for name, value in errors.items()
        }
        self.errors: dict[str, tuple[str, ...]] = normalized
        detail = "; ".join(
            f"{field_name}: {', '.join(messages)}"
            for field_name, messages in normalized.items()
        )
        super().__init__(detail)


class StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class MeasurementMode(StringEnum):
    CONTINUOUS = "Continuous"
    DISCRETE = "Discrete"


class MeasurementType(StringEnum):
    MAGNETIC_MOMENT = "Magnetic Moment"
    MAGNETIC_SUSCEPTIBILITY = "Magnetic Susceptibility"
    NONE = "None"


class TreatmentType(StringEnum):
    DEGAUSS_XYZ = "Degauss XYZ"
    DEGAUSS_XY = "Degauss XY"
    DEGAUSS_Z = "Degauss Z"
    DEGAUSS_ARM_AXIAL = "Degauss + ARM Axial"
    DEGAUSS_ARM_TRANSVERSE = "Degauss + ARM Transverse"
    ARM_AXIAL = "ARM Axial"
    ARM_TRANSVERSE = "ARM Transverse"
    IRM = "IRM"
    FURNACE = "Furnace"
    PAUSE = "Pause"
    NONE = "None"


class TreatmentOrder(StringEnum):
    BEFORE_MEASUREMENT = "Before Measurement"
    AFTER_MEASUREMENT = "After Measurement"


class HomingPolicy(StringEnum):
    NEVER = "Never"
    EVERY_RUN = "Every Run"
    EVERY_QUEUE = "Every Queue"


class ActionOpcode(StringEnum):
    MOVE = "MOVE"
    SQUID_DAQ = "SQUID DAQ"
    MS_DAQ = "MS DAQ"
    DG = "DG"
    ARM = "ARM"
    IRM = "IRM"
    FURNACE = "FURNACE"
    PAUSE = "PAUSE"
    SAVE = "SAVE"
    DONE = "DONE"


class DAQType(StringEnum):
    BACKGROUND = "Background"
    LEADER = "Leader"
    SAMPLE = "Sample"
    TRAILER = "Trailer"


class Axis(StringEnum):
    X = "X"
    Y = "Y"
    Z = "Z"
    XY = "XY"
    XYZ = "XYZ"
    AXIAL = "Axial"
    TRANSVERSE = "Transverse"


class MoveTarget(StringEnum):
    HOME = "Home"
    LOAD = "Load"
    MEASURE = "Measure"
    UNLOAD = "Unload"


E = TypeVar("E", bound=Enum)


def _enum_value(enum_type: Type[E], value: Any, field_name: str) -> E:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (TypeError, ValueError):
        choices = ", ".join(str(item.value) for item in enum_type)
        raise DomainValidationError({field_name: f"must be one of: {choices}"})


def _check_unknown(data: Mapping[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise DomainValidationError(
            {name: "is not a recognized field" for name in unknown}
        )


def _finite_optional(
    value: Optional[float], field_name: str, errors: dict[str, str]
) -> None:
    if value is not None and (
        isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value)
    ):
        errors[field_name] = "must be a finite number or null"


def _positive_optional(
    value: Optional[float], field_name: str, errors: dict[str, str]
) -> None:
    _finite_optional(value, field_name, errors)
    if field_name not in errors and value is not None and value <= 0:
        errors[field_name] = "must be greater than zero"


def _nonnegative_optional(
    value: Optional[float], field_name: str, errors: dict[str, str]
) -> None:
    _finite_optional(value, field_name, errors)
    if field_name not in errors and value is not None and value < 0:
        errors[field_name] = "must be zero or greater"


@dataclass(frozen=True)
class ContinuousMeasurementParameters:
    sample_rate_hz: Optional[float] = None
    traverse_speed_mm_s: Optional[float] = None
    background_samples: Optional[int] = None
    leader_samples: Optional[int] = None
    sample_samples: Optional[int] = None
    trailer_samples: Optional[int] = None

    _FIELDS: ClassVar[set[str]] = {
        "sample_rate_hz",
        "traverse_speed_mm_s",
        "background_samples",
        "leader_samples",
        "sample_samples",
        "trailer_samples",
    }

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}
        _positive_optional(self.sample_rate_hz, "sample_rate_hz", errors)
        _positive_optional(self.traverse_speed_mm_s, "traverse_speed_mm_s", errors)
        for name in (
            "background_samples",
            "leader_samples",
            "sample_samples",
            "trailer_samples",
        ):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value <= 0
            ):
                errors[name] = "must be a positive integer or null"
        if errors:
            raise DomainValidationError(errors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_rate_hz": self.sample_rate_hz,
            "traverse_speed_mm_s": self.traverse_speed_mm_s,
            "background_samples": self.background_samples,
            "leader_samples": self.leader_samples,
            "sample_samples": self.sample_samples,
            "trailer_samples": self.trailer_samples,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ContinuousMeasurementParameters":
        _check_unknown(data, cls._FIELDS)
        return cls(**dict(data))


@dataclass(frozen=True)
class DiscreteMeasurementParameters:
    positions_mm: tuple[float, ...] = ()
    settling_time_s: Optional[float] = None
    readings_per_position: Optional[int] = None
    integration_time_s: Optional[float] = None

    _FIELDS: ClassVar[set[str]] = {
        "positions_mm",
        "settling_time_s",
        "readings_per_position",
        "integration_time_s",
    }

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}
        if isinstance(self.positions_mm, (str, bytes)):
            errors["positions_mm"] = "must be a sequence of finite numbers"
        else:
            try:
                positions = tuple(self.positions_mm)
            except TypeError:
                errors["positions_mm"] = "must be a sequence of finite numbers"
            else:
                invalid = [
                    value
                    for value in positions
                    if isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not isfinite(value)
                ]
                if invalid:
                    errors["positions_mm"] = "must contain only finite numbers"
                else:
                    object.__setattr__(self, "positions_mm", positions)
        _nonnegative_optional(self.settling_time_s, "settling_time_s", errors)
        _positive_optional(self.integration_time_s, "integration_time_s", errors)
        value = self.readings_per_position
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
        ):
            errors["readings_per_position"] = "must be a positive integer or null"
        if errors:
            raise DomainValidationError(errors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "positions_mm": list(self.positions_mm),
            "settling_time_s": self.settling_time_s,
            "readings_per_position": self.readings_per_position,
            "integration_time_s": self.integration_time_s,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DiscreteMeasurementParameters":
        _check_unknown(data, cls._FIELDS)
        return cls(**dict(data))


@dataclass(frozen=True)
class SampleMetadata:
    sample_id: str
    name: Optional[str] = None
    site: Optional[str] = None
    collection: Optional[str] = None
    volume_cc: Optional[float] = None
    azimuth_deg: Optional[float] = None
    plunge_deg: Optional[float] = None
    bedding_strike_deg: Optional[float] = None
    bedding_dip_deg: Optional[float] = None
    notes: Optional[str] = None

    _FIELDS: ClassVar[set[str]] = {
        "sample_id",
        "name",
        "site",
        "collection",
        "volume_cc",
        "azimuth_deg",
        "plunge_deg",
        "bedding_strike_deg",
        "bedding_dip_deg",
        "notes",
    }

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}
        if not isinstance(self.sample_id, str) or not self.sample_id.strip():
            errors["sample_id"] = "is required"
        for name in ("name", "site", "collection", "notes"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                errors[name] = "must be text or null"
        _positive_optional(self.volume_cc, "volume_cc", errors)
        for name in (
            "azimuth_deg",
            "plunge_deg",
            "bedding_strike_deg",
            "bedding_dip_deg",
        ):
            _finite_optional(getattr(self, name), name, errors)
        if "azimuth_deg" not in errors and self.azimuth_deg is not None:
            if not 0 <= self.azimuth_deg < 360:
                errors["azimuth_deg"] = "must be in [0, 360)"
        if "plunge_deg" not in errors and self.plunge_deg is not None:
            if not -90 <= self.plunge_deg <= 90:
                errors["plunge_deg"] = "must be in [-90, 90]"
        if "bedding_strike_deg" not in errors and self.bedding_strike_deg is not None:
            if not 0 <= self.bedding_strike_deg < 360:
                errors["bedding_strike_deg"] = "must be in [0, 360)"
        if "bedding_dip_deg" not in errors and self.bedding_dip_deg is not None:
            if not 0 <= self.bedding_dip_deg <= 90:
                errors["bedding_dip_deg"] = "must be in [0, 90]"
        paired = (
            ("azimuth_deg", "plunge_deg"),
            ("bedding_strike_deg", "bedding_dip_deg"),
        )
        for first, second in paired:
            if (getattr(self, first) is None) != (getattr(self, second) is None):
                errors[first] = f"must be provided together with {second}"
                errors[second] = f"must be provided together with {first}"
        if errors:
            raise DomainValidationError(errors)

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self._FIELDS}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SampleMetadata":
        _check_unknown(data, cls._FIELDS)
        try:
            return cls(**dict(data))
        except TypeError as exc:
            if "sample_id" not in data:
                raise DomainValidationError({"sample_id": "is required"}) from exc
            raise


@dataclass(frozen=True)
class QueueStep:
    sample: SampleMetadata
    measurement_type: MeasurementType
    treatment_type: TreatmentType
    treatment_order: TreatmentOrder
    measurement_mode: Optional[MeasurementMode] = None
    treatment_value: Optional[float] = None
    pause_seconds: Optional[float] = None
    continuous: Optional[ContinuousMeasurementParameters] = None
    discrete: Optional[DiscreteMeasurementParameters] = None

    _FIELDS: ClassVar[set[str]] = {
        "sample",
        "measurement_type",
        "treatment_type",
        "treatment_order",
        "measurement_mode",
        "treatment_value",
        "pause_seconds",
        "continuous",
        "discrete",
    }

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}
        if not isinstance(self.sample, SampleMetadata):
            errors["sample"] = "must be SampleMetadata"
        for name, enum_type in (
            ("measurement_type", MeasurementType),
            ("treatment_type", TreatmentType),
            ("treatment_order", TreatmentOrder),
        ):
            if not isinstance(getattr(self, name), enum_type):
                errors[name] = f"must be {enum_type.__name__}"
        if self.measurement_mode is not None and not isinstance(
            self.measurement_mode, MeasurementMode
        ):
            errors["measurement_mode"] = "must be MeasurementMode or null"
        _finite_optional(self.treatment_value, "treatment_value", errors)
        _positive_optional(self.pause_seconds, "pause_seconds", errors)
        if self.measurement_type is MeasurementType.NONE:
            if self.measurement_mode is not None:
                errors["measurement_mode"] = "must be null when measurement_type is None"
            if self.continuous is not None or self.discrete is not None:
                errors["measurement_parameters"] = (
                    "must be omitted when measurement_type is None"
                )
        elif self.measurement_mode is None:
            errors["measurement_mode"] = "is required for a measurement"
        if self.measurement_mode is MeasurementMode.CONTINUOUS:
            if not isinstance(self.continuous, ContinuousMeasurementParameters):
                errors["continuous"] = "is required for Continuous measurement"
            if self.discrete is not None:
                errors["discrete"] = "must be null for Continuous measurement"
        if self.measurement_mode is MeasurementMode.DISCRETE:
            if not isinstance(self.discrete, DiscreteMeasurementParameters):
                errors["discrete"] = "is required for Discrete measurement"
            if self.continuous is not None:
                errors["continuous"] = "must be null for Discrete measurement"
        if self.treatment_type is TreatmentType.PAUSE:
            if self.pause_seconds is None:
                errors["pause_seconds"] = "is required for Pause treatment"
            if self.treatment_value is not None:
                errors["treatment_value"] = "must be null for Pause treatment"
        elif self.pause_seconds is not None:
            errors["pause_seconds"] = "is only valid for Pause treatment"
        if self.treatment_type is TreatmentType.NONE and self.treatment_value is not None:
            errors["treatment_value"] = "must be null when treatment_type is None"
        if self.treatment_type not in (TreatmentType.NONE, TreatmentType.PAUSE):
            if self.treatment_value is None:
                errors["treatment_value"] = "is required for this treatment"
            elif self.treatment_value < 0:
                errors["treatment_value"] = "must be zero or greater"
        if errors:
            raise DomainValidationError(errors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample": self.sample.to_dict(),
            "measurement_type": self.measurement_type.value,
            "treatment_type": self.treatment_type.value,
            "treatment_order": self.treatment_order.value,
            "measurement_mode": (
                self.measurement_mode.value if self.measurement_mode else None
            ),
            "treatment_value": self.treatment_value,
            "pause_seconds": self.pause_seconds,
            "continuous": self.continuous.to_dict() if self.continuous else None,
            "discrete": self.discrete.to_dict() if self.discrete else None,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "QueueStep":
        _check_unknown(data, cls._FIELDS)
        errors: dict[str, str] = {}
        required = ("sample", "measurement_type", "treatment_type", "treatment_order")
        for name in required:
            if name not in data:
                errors[name] = "is required"
        if errors:
            raise DomainValidationError(errors)
        sample_data = data["sample"]
        sample = (
            sample_data
            if isinstance(sample_data, SampleMetadata)
            else SampleMetadata.from_dict(sample_data)
        )
        continuous_data = data.get("continuous")
        discrete_data = data.get("discrete")
        mode_data = data.get("measurement_mode")
        return cls(
            sample=sample,
            measurement_type=_enum_value(
                MeasurementType, data["measurement_type"], "measurement_type"
            ),
            treatment_type=_enum_value(
                TreatmentType, data["treatment_type"], "treatment_type"
            ),
            treatment_order=_enum_value(
                TreatmentOrder, data["treatment_order"], "treatment_order"
            ),
            measurement_mode=(
                _enum_value(MeasurementMode, mode_data, "measurement_mode")
                if mode_data is not None
                else None
            ),
            treatment_value=data.get("treatment_value"),
            pause_seconds=data.get("pause_seconds"),
            continuous=(
                continuous_data
                if isinstance(continuous_data, ContinuousMeasurementParameters)
                else ContinuousMeasurementParameters.from_dict(continuous_data)
                if continuous_data is not None
                else None
            ),
            discrete=(
                discrete_data
                if isinstance(discrete_data, DiscreteMeasurementParameters)
                else DiscreteMeasurementParameters.from_dict(discrete_data)
                if discrete_data is not None
                else None
            ),
        )


@dataclass(frozen=True)
class QueuePlan:
    steps: tuple[QueueStep, ...]
    homing: HomingPolicy

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}
        try:
            steps = tuple(self.steps)
        except TypeError:
            errors["steps"] = "must be a sequence of QueueStep values"
        else:
            if not steps:
                errors["steps"] = "must contain at least one step"
            elif not all(isinstance(step, QueueStep) for step in steps):
                errors["steps"] = "must contain only QueueStep values"
            object.__setattr__(self, "steps", steps)
        if not isinstance(self.homing, HomingPolicy):
            errors["homing"] = "must be HomingPolicy"
        if errors:
            raise DomainValidationError(errors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": [step.to_dict() for step in self.steps],
            "homing": self.homing.value,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "QueuePlan":
        _check_unknown(data, {"steps", "homing"})
        errors = {
            name: "is required" for name in ("steps", "homing") if name not in data
        }
        if errors:
            raise DomainValidationError(errors)
        return cls(
            steps=tuple(
                item if isinstance(item, QueueStep) else QueueStep.from_dict(item)
                for item in data["steps"]
            ),
            homing=_enum_value(HomingPolicy, data["homing"], "homing"),
        )


@dataclass(frozen=True)
class VectorMeasurementResult:
    x: float
    y: float
    z: float
    units: Optional[str] = None
    sample_id: Optional[str] = None

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}
        for name in ("x", "y", "z"):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
            ):
                errors[name] = "must be a finite number"
        for name in ("units", "sample_id"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                errors[name] = "must be text or null"
        if errors:
            raise DomainValidationError(errors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "units": self.units,
            "sample_id": self.sample_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "VectorMeasurementResult":
        allowed = {"x", "y", "z", "units", "sample_id"}
        _check_unknown(data, allowed)
        errors = {name: "is required" for name in ("x", "y", "z") if name not in data}
        if errors:
            raise DomainValidationError(errors)
        return cls(**dict(data))
