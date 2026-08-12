"""Versioned, validated application and instrument configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

APPLICATION_CONFIG_VERSION = 1
INSTRUMENT_CONFIG_VERSION = 1


class ConfigValidationError(ValueError):
    """Raised when persisted or user-provided configuration is unsafe."""


class Subsystem(str, Enum):
    TRACK = "TRACK"
    SQUID = "SQUID"
    MS = "MS"
    DG = "DG"
    ARM = "ARM"
    IRM = "IRM"
    FURNACE = "FURNACE"


def _default_profiles() -> dict[Subsystem, "SerialProfile"]:
    return {subsystem: SerialProfile() for subsystem in Subsystem}


@dataclass(frozen=True, slots=True)
class SerialProfile:
    """Serial framing for one subsystem; ``port=None`` means disconnected."""

    port: str | None = None
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = "N"
    stopbits: float = 1.0
    read_timeout: float = 1.0
    write_timeout: float = 1.0
    inter_byte_timeout: float | None = None
    read_terminator: str = "\r\n"
    write_terminator: str = "\r"
    encoding: str = "ascii"

    def __post_init__(self) -> None:
        if self.port is not None and (not isinstance(self.port, str) or not self.port.strip()):
            raise ConfigValidationError("port must be a non-empty string or None")
        if not isinstance(self.baudrate, int) or isinstance(self.baudrate, bool) or self.baudrate <= 0:
            raise ConfigValidationError("baudrate must be a positive integer")
        if self.bytesize not in {5, 6, 7, 8}:
            raise ConfigValidationError("bytesize must be one of 5, 6, 7, or 8")
        if self.parity.upper() not in {"N", "E", "O", "M", "S"}:
            raise ConfigValidationError("parity must be N, E, O, M, or S")
        if self.stopbits not in {1, 1.0, 1.5, 2, 2.0}:
            raise ConfigValidationError("stopbits must be 1, 1.5, or 2")
        for name in ("read_timeout", "write_timeout"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                raise ConfigValidationError(f"{name} must be a non-negative number")
        if self.inter_byte_timeout is not None and (
            not isinstance(self.inter_byte_timeout, (int, float))
            or isinstance(self.inter_byte_timeout, bool)
            or self.inter_byte_timeout < 0
        ):
            raise ConfigValidationError("inter_byte_timeout must be non-negative or None")
        for name in ("read_terminator", "write_terminator"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise ConfigValidationError(f"{name} must be text")
            try:
                value.encode(self.encoding)
            except (LookupError, UnicodeEncodeError) as exc:
                raise ConfigValidationError(f"invalid {name} or encoding") from exc
        try:
            "test".encode(self.encoding)
        except LookupError as exc:
            raise ConfigValidationError(f"unknown encoding: {self.encoding}") from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "bytesize": self.bytesize,
            "parity": self.parity.upper(),
            "stopbits": self.stopbits,
            "read_timeout": self.read_timeout,
            "write_timeout": self.write_timeout,
            "inter_byte_timeout": self.inter_byte_timeout,
            "read_terminator": self.read_terminator,
            "write_terminator": self.write_terminator,
            "encoding": self.encoding,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SerialProfile":
        if not isinstance(data, Mapping):
            raise ConfigValidationError("serial profile must be an object")
        allowed = set(cls.__dataclass_fields__)
        unknown = set(data) - allowed
        if unknown:
            raise ConfigValidationError(f"unknown serial profile fields: {sorted(unknown)}")
        try:
            return cls(**dict(data))
        except TypeError as exc:
            raise ConfigValidationError("invalid serial profile") from exc


@dataclass(frozen=True, slots=True)
class InstrumentConfig:
    """Versioned serial configuration for all recovered LabVIEW subsystems."""

    version: int = INSTRUMENT_CONFIG_VERSION
    profiles: dict[Subsystem, SerialProfile] = field(default_factory=_default_profiles)

    def __post_init__(self) -> None:
        if self.version != INSTRUMENT_CONFIG_VERSION:
            raise ConfigValidationError(
                f"unsupported instrument config version {self.version}; "
                f"expected {INSTRUMENT_CONFIG_VERSION}"
            )
        normalized: dict[Subsystem, SerialProfile] = {}
        try:
            items = self.profiles.items()
        except AttributeError as exc:
            raise ConfigValidationError("profiles must be a mapping") from exc
        for key, profile in items:
            try:
                subsystem = key if isinstance(key, Subsystem) else Subsystem(str(key).upper())
            except ValueError as exc:
                raise ConfigValidationError(f"unknown subsystem: {key}") from exc
            if not isinstance(profile, SerialProfile):
                raise ConfigValidationError(f"profile for {subsystem.value} must be a SerialProfile")
            normalized[subsystem] = profile
        missing = set(Subsystem) - set(normalized)
        if missing:
            names = ", ".join(sorted(item.value for item in missing))
            raise ConfigValidationError(f"missing serial profiles: {names}")
        object.__setattr__(self, "profiles", normalized)

    def profile(self, subsystem: Subsystem | str) -> SerialProfile:
        key = subsystem if isinstance(subsystem, Subsystem) else Subsystem(subsystem.upper())
        return self.profiles[key]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "profiles": {
                subsystem.value: self.profiles[subsystem].to_dict()
                for subsystem in Subsystem
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "InstrumentConfig":
        if not isinstance(data, Mapping):
            raise ConfigValidationError("instrument config must be an object")
        unknown = set(data) - {"version", "profiles"}
        if unknown:
            raise ConfigValidationError(f"unknown instrument config fields: {sorted(unknown)}")
        raw_profiles = data.get("profiles")
        if not isinstance(raw_profiles, Mapping):
            raise ConfigValidationError("instrument profiles must be an object")
        profiles: dict[Subsystem, SerialProfile] = {}
        for name, raw_profile in raw_profiles.items():
            try:
                subsystem = Subsystem(str(name).upper())
            except ValueError as exc:
                raise ConfigValidationError(f"unknown subsystem: {name}") from exc
            profiles[subsystem] = SerialProfile.from_dict(raw_profile)
        return cls(version=data.get("version", 0), profiles=profiles)


@dataclass(frozen=True, slots=True)
class ApplicationConfig:
    """Top-level application configuration with conservative hardware defaults."""

    version: int = APPLICATION_CONFIG_VERSION
    application_name: str = "Long Core Control"
    simulation_mode: bool = True
    data_directory: str = "data"
    log_directory: str = "logs"
    log_level: str = "INFO"
    log_max_bytes: int = 5_000_000
    log_backup_count: int = 5
    instruments: InstrumentConfig = field(default_factory=InstrumentConfig)

    def __post_init__(self) -> None:
        if self.version != APPLICATION_CONFIG_VERSION:
            raise ConfigValidationError(
                f"unsupported application config version {self.version}; "
                f"expected {APPLICATION_CONFIG_VERSION}"
            )
        if not isinstance(self.application_name, str) or not self.application_name.strip():
            raise ConfigValidationError("application_name must be non-empty")
        if not isinstance(self.simulation_mode, bool):
            raise ConfigValidationError("simulation_mode must be boolean")
        for name in ("data_directory", "log_directory"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or "\x00" in value:
                raise ConfigValidationError(f"{name} must be a valid non-empty path")
            Path(value)
        if self.log_level.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigValidationError("unsupported log_level")
        if not isinstance(self.log_max_bytes, int) or self.log_max_bytes <= 0:
            raise ConfigValidationError("log_max_bytes must be a positive integer")
        if not isinstance(self.log_backup_count, int) or self.log_backup_count < 0:
            raise ConfigValidationError("log_backup_count must be a non-negative integer")
        if not isinstance(self.instruments, InstrumentConfig):
            raise ConfigValidationError("instruments must be an InstrumentConfig")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "application_name": self.application_name,
            "simulation_mode": self.simulation_mode,
            "data_directory": self.data_directory,
            "log_directory": self.log_directory,
            "log_level": self.log_level.upper(),
            "log_max_bytes": self.log_max_bytes,
            "log_backup_count": self.log_backup_count,
            "instruments": self.instruments.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ApplicationConfig":
        if not isinstance(data, Mapping):
            raise ConfigValidationError("application config must be an object")
        allowed = set(cls.__dataclass_fields__)
        unknown = set(data) - allowed
        if unknown:
            raise ConfigValidationError(f"unknown application config fields: {sorted(unknown)}")
        values = dict(data)
        if "instruments" in values:
            values["instruments"] = InstrumentConfig.from_dict(values["instruments"])
        try:
            return cls(**values)
        except TypeError as exc:
            raise ConfigValidationError("invalid application config") from exc
