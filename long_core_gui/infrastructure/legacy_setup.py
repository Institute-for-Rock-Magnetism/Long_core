"""Legacy ``LONG CORE.SET UP`` file handling and machine-config export.

The LabVIEW application persists its full machine configuration (serial
ports, calibrations, positions, subsystem flags) to a file named
``LONG CORE.SET UP`` (verbatim, including the space) via
``File/Write Long Core Set Up.vi``. The file is flattened binary data whose
exact field order lives in the type descriptors that the open extractor does
not parse for LabVIEW 8.6 — so decoding it remains pending a real sample.

This module therefore provides what is useful before that sample exists:

- discovery of the setup file (exact and relaxed names),
- safekeeping of the raw file into the workspace for later analysis,
- the machine-config model and its export to the app's validated
  ``InstrumentConfig`` (ports 0-8 map to COM1-COM9 per the printed help text),
  which the operator fills from the commissioning probes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Any, Mapping

from .config import ConfigValidationError, InstrumentConfig, SerialProfile, Subsystem

SETUP_FILE_NAME = "LONG CORE.SET UP"

#: Subsystem -> legacy port-number semantics (0=COM1 ... 8=COM9).
PORT_NUMBER_TO_COM = {number: f"COM{number + 1}" for number in range(9)}


class SetupFileError(RuntimeError):
    """Raised when a legacy setup file cannot be handled."""


def find_setup_file(folder: str | Path) -> Path | None:
    """Locate the setup file with the exact or any-case name."""
    root = Path(folder)
    if not root.is_dir():
        return None
    exact = root / SETUP_FILE_NAME
    if exact.is_file():
        return exact
    lowered = SETUP_FILE_NAME.lower()
    for candidate in root.iterdir():
        if candidate.is_file() and candidate.name.lower() == lowered:
            return candidate
    return None


def store_setup_file(source: str | Path, destination_folder: str | Path) -> Path:
    """Copy the raw setup file into a workspace folder for analysis."""
    source_path = Path(source)
    if not source_path.is_file():
        raise SetupFileError(f"setup file not found: {source_path}")
    destination = Path(destination_folder) / "legacy"
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / source_path.name
    shutil.copy2(source_path, target)
    return target


@dataclass(frozen=True, slots=True)
class MachineConfig:
    """Operator-verified machine configuration in the app's own models."""

    profiles: Mapping[Subsystem, SerialProfile]

    @classmethod
    def empty(cls) -> "MachineConfig":
        return cls(profiles={subsystem: SerialProfile() for subsystem in Subsystem})

    def with_port(self, subsystem: Subsystem | str, port_number: int, baudrate: int = 9600) -> "MachineConfig":
        key = subsystem if isinstance(subsystem, Subsystem) else Subsystem(str(subsystem).upper())
        if port_number not in PORT_NUMBER_TO_COM:
            raise ConfigValidationError(f"legacy port number must be 0-8, got {port_number}")
        if not isinstance(baudrate, int) or baudrate <= 0:
            raise ConfigValidationError("baudrate must be a positive integer")
        current = self.profiles[key]
        profile = SerialProfile(
            port=PORT_NUMBER_TO_COM[port_number],
            baudrate=baudrate,
            bytesize=current.bytesize,
            parity=current.parity,
            stopbits=current.stopbits,
            read_timeout=current.read_timeout,
            write_timeout=current.write_timeout,
            inter_byte_timeout=current.inter_byte_timeout,
            read_terminator=current.read_terminator,
            write_terminator=current.write_terminator,
            encoding=current.encoding,
        )
        profiles = dict(self.profiles)
        profiles[key] = profile
        return MachineConfig(profiles=profiles)

    def to_instrument_config(self) -> InstrumentConfig:
        return InstrumentConfig(profiles=dict(self.profiles))

    @classmethod
    def from_instrument_config(cls, config: InstrumentConfig) -> "MachineConfig":
        return cls(profiles=dict(config.profiles))

    def to_dict(self) -> dict[str, Any]:
        return {
            subsystem.value: self.profiles[subsystem].to_dict()
            for subsystem in Subsystem
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MachineConfig":
        profiles: dict[Subsystem, SerialProfile] = {}
        for name, raw in data.items():
            try:
                subsystem = Subsystem(str(name).upper())
            except ValueError as exc:
                raise ConfigValidationError(f"unknown subsystem: {name}") from exc
            profiles[subsystem] = SerialProfile.from_dict(raw)
        return cls(profiles=profiles)
