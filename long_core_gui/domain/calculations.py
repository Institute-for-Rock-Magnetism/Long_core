"""Vector calculations and paleomagnetic coordinate transformations."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, degrees, isfinite, radians, sin, sqrt
from typing import Any, Mapping

from .models import DomainValidationError, SampleMetadata, VectorMeasurementResult


@dataclass(frozen=True)
class DirectionalVector:
    """A vector and its conventional paleomagnetic direction.

    Coordinates use north/east/down after conversion to geographic space.
    Declination is clockwise from north in [0, 360); inclination is positive
    downward in [-90, 90].  The zero vector has no defined direction, so its
    inclination and declination are ``None``.
    """

    x: float
    y: float
    z: float
    intensity: float
    inclination_deg: float | None
    declination_deg: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "intensity": self.intensity,
            "inclination_deg": self.inclination_deg,
            "declination_deg": self.declination_deg,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DirectionalVector":
        allowed = {
            "x",
            "y",
            "z",
            "intensity",
            "inclination_deg",
            "declination_deg",
        }
        unknown = sorted(set(data) - allowed)
        missing = sorted(allowed - set(data))
        errors: dict[str, str] = {}
        errors.update({name: "is not a recognized field" for name in unknown})
        errors.update({name: "is required" for name in missing})
        if errors:
            raise DomainValidationError(errors)
        return cls(**dict(data))


@dataclass(frozen=True)
class CoordinateResults:
    specimen: DirectionalVector
    geographic: DirectionalVector | None
    tilt_corrected: DirectionalVector | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "specimen": self.specimen.to_dict(),
            "geographic": self.geographic.to_dict() if self.geographic else None,
            "tilt_corrected": (
                self.tilt_corrected.to_dict() if self.tilt_corrected else None
            ),
        }


def vector_properties(x: float, y: float, z: float) -> DirectionalVector:
    """Calculate intensity, inclination, and declination for one vector."""

    values = {"x": x, "y": y, "z": z}
    errors = {
        name: "must be a finite number"
        for name, value in values.items()
        if isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
    }
    if errors:
        raise DomainValidationError(errors)
    x, y, z = float(x), float(y), float(z)
    horizontal = sqrt(x * x + y * y)
    intensity = sqrt(horizontal * horizontal + z * z)
    if intensity == 0:
        return DirectionalVector(x, y, z, 0.0, None, None)
    inclination = degrees(atan2(z, horizontal))
    declination = degrees(atan2(y, x)) % 360.0
    return DirectionalVector(x, y, z, intensity, inclination, declination)


def specimen_to_geographic(
    result: VectorMeasurementResult,
    azimuth_deg: float,
    plunge_deg: float,
) -> VectorMeasurementResult:
    """Rotate specimen XYZ into north/east/down geographic coordinates.

    ``azimuth_deg`` and ``plunge_deg`` describe the specimen +X axis.  The +Y
    axis is horizontal and 90 degrees clockwise from +X; +Z completes the
    right-handed frame.  This convention is explicit so instrument-specific
    sign or axis mappings can be applied at the adapter boundary.
    """

    _validate_angle("azimuth_deg", azimuth_deg, 0.0, 360.0, upper_inclusive=False)
    _validate_angle("plunge_deg", plunge_deg, -90.0, 90.0, upper_inclusive=True)
    azimuth = radians(azimuth_deg)
    plunge = radians(plunge_deg)
    ca, sa = cos(azimuth), sin(azimuth)
    cp, sp = cos(plunge), sin(plunge)
    north = result.x * cp * ca - result.y * sa - result.z * sp * ca
    east = result.x * cp * sa + result.y * ca - result.z * sp * sa
    down = result.x * sp + result.z * cp
    return VectorMeasurementResult(north, east, down, result.units, result.sample_id)


def geographic_to_tilt(
    result: VectorMeasurementResult,
    bedding_strike_deg: float,
    bedding_dip_deg: float,
) -> VectorMeasurementResult:
    """Untilts a geographic N/E/down vector with a right-hand-rule strike.

    The correction is a right-handed rotation of ``-bedding_dip_deg`` around
    the horizontal strike axis.  Strike is clockwise from north.
    """

    _validate_angle(
        "bedding_strike_deg",
        bedding_strike_deg,
        0.0,
        360.0,
        upper_inclusive=False,
    )
    _validate_angle(
        "bedding_dip_deg", bedding_dip_deg, 0.0, 90.0, upper_inclusive=True
    )
    strike = radians(bedding_strike_deg)
    angle = radians(-bedding_dip_deg)
    axis = (cos(strike), sin(strike), 0.0)
    rotated = _rodrigues((result.x, result.y, result.z), axis, angle)
    return VectorMeasurementResult(*rotated, result.units, result.sample_id)


def calculate_coordinate_results(
    result: VectorMeasurementResult, metadata: SampleMetadata
) -> CoordinateResults:
    """Calculate available specimen, geographic, and tilt-corrected results."""

    specimen = vector_properties(result.x, result.y, result.z)
    if metadata.azimuth_deg is None or metadata.plunge_deg is None:
        return CoordinateResults(specimen, None, None)
    geographic_result = specimen_to_geographic(
        result, metadata.azimuth_deg, metadata.plunge_deg
    )
    geographic = vector_properties(
        geographic_result.x, geographic_result.y, geographic_result.z
    )
    if metadata.bedding_strike_deg is None or metadata.bedding_dip_deg is None:
        return CoordinateResults(specimen, geographic, None)
    tilt_result = geographic_to_tilt(
        geographic_result,
        metadata.bedding_strike_deg,
        metadata.bedding_dip_deg,
    )
    return CoordinateResults(
        specimen,
        geographic,
        vector_properties(tilt_result.x, tilt_result.y, tilt_result.z),
    )


def _validate_angle(
    name: str,
    value: float,
    lower: float,
    upper: float,
    *,
    upper_inclusive: bool,
) -> None:
    valid_number = (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and isfinite(value)
    )
    in_range = valid_number and lower <= value and (
        value <= upper if upper_inclusive else value < upper
    )
    if not in_range:
        bracket = "]" if upper_inclusive else ")"
        raise DomainValidationError({name: f"must be in [{lower}, {upper}{bracket}"})


def _rodrigues(
    vector: tuple[float, float, float],
    axis: tuple[float, float, float],
    angle: float,
) -> tuple[float, float, float]:
    vx, vy, vz = vector
    kx, ky, kz = axis
    cosine, sine = cos(angle), sin(angle)
    dot = kx * vx + ky * vy + kz * vz
    cross = (ky * vz - kz * vy, kz * vx - kx * vz, kx * vy - ky * vx)
    return (
        vx * cosine + cross[0] * sine + kx * dot * (1 - cosine),
        vy * cosine + cross[1] * sine + ky * dot * (1 - cosine),
        vz * cosine + cross[2] * sine + kz * dot * (1 - cosine),
    )

