"""Recovered legacy error catalog from ``Global/User Error Codes.vi``.

Descriptions are verbatim DFDS strings from the LabVIEW 8.6 VI, including
legacy typos (``swirch``, ``recieved``, ``Furnance``). Codes follow the printed
range table; rows without a visible print anchor are inferred from DFDS order
(see ``reconstructions/ERROR_CODES_REVERSE_ENGINEERING.md``). The catalog is
read-only and performs no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import ClassVar, Mapping


class ErrorSubsystem(str, Enum):
    SQUID = "SQUID"
    MS = "MS"
    IRM = "IRM"
    ARM = "ARM"
    DEGAUSS = "DEGAUSS"
    SAMPLE_HANDLER = "SAMPLE_HANDLER"
    CN76 = "CN76"
    FURNACE = "FURNACE"
    APPLICATION = "APPLICATION"


@dataclass(frozen=True, slots=True)
class LegacyError:
    code: int
    subsystem: ErrorSubsystem
    description: str
    dialog_type: int = 1

    @property
    def short(self) -> str:
        """First line of the description for compact display."""
        return self.description.splitlines()[0]


class LegacyErrorCatalog:
    """Immutable lookup table for the recovered legacy error codes."""

    _ENTRIES: ClassVar[tuple[LegacyError, ...]] = (
        # DC SQUIDs -- 6000 (anchor 6001 printed; 6002 inferred, matches the
        # connection/config codes in SQUID_REVERSE_ENGINEERING.md)
        LegacyError(6001, ErrorSubsystem.SQUID,
                    "SQUID DRIVER ERROR. The SQUIDS did not return the correct ID string when prompted."),
        LegacyError(6002, ErrorSubsystem.SQUID,
                    "SQUID DRIVER ERROR. The SQUIDS failed to configure according to the user's parameters."),
        # MS meter -- 6100 (anchor 6101 printed)
        LegacyError(6101, ErrorSubsystem.MS,
                    "MS DRIVER ERROR. The Magnetic Susceptibility did not return the correct ID string when prompted."),
        # IRM -- 6200 (inferred)
        LegacyError(6201, ErrorSubsystem.IRM,
                    "IRM DRIVER ERROR. The IRM did not return the correct ID string when prompted."),
        LegacyError(6202, ErrorSubsystem.IRM,
                    'IRM TRIGGER TIMEOUT.  The IRM Driver failed to return the "DONE" status with in the time limit'),
        # ARM -- 6300 (anchor 6303 printed)
        LegacyError(6301, ErrorSubsystem.ARM,
                    "ARM DRIVER ERROR.  The ARM did not return the correct ID string when prompted."),
        LegacyError(6302, ErrorSubsystem.ARM, "ARM IS IN MANUAL MODE!"),
        LegacyError(6303, ErrorSubsystem.ARM, "ARM OVER RANGE ERROR!"),
        LegacyError(6304, ErrorSubsystem.ARM,
                    "ARM DRIVER ERROR.  The ARM failed to configure according to the user's parameters."),
        # Degauss -- 6400 (anchor 6411 printed)
        LegacyError(6401, ErrorSubsystem.DEGAUSS, "Degausser failed to ramp up."),
        LegacyError(6402, ErrorSubsystem.DEGAUSS, "Degausser failed to ramp down."),
        LegacyError(6403, ErrorSubsystem.DEGAUSS, "Degausser failed to cycle."),
        LegacyError(6404, ErrorSubsystem.DEGAUSS, "Failed to set axis and AF field!"),
        LegacyError(6405, ErrorSubsystem.DEGAUSS, "Failed to set ramp and dwell!"),
        LegacyError(6406, ErrorSubsystem.DEGAUSS,
                    'Failed to receive "TRACKING" status.'),
        LegacyError(6407, ErrorSubsystem.DEGAUSS,
                    'Failed to receive "ZERO" status.'),
        LegacyError(6408, ErrorSubsystem.DEGAUSS,
                    "DEGAUSSER DRIVER ERROR.  The Degausser did not return the correct ID string!"),
        LegacyError(6409, ErrorSubsystem.DEGAUSS,
                    "DEGAUSSER DRIVER ERROR.  The DEGAUSSER failed to configure according to the user's parameters."),
        LegacyError(6410, ErrorSubsystem.DEGAUSS,
                    "TRACKING ERROR REPORTED BY DEGAUSSER.  "),
        LegacyError(6411, ErrorSubsystem.DEGAUSS,
                    "DEGAUSSER POWER-UP TIME-OUT.\n\nThe Degausser has exceeded the 30 "
                    "second power-up time limit.  There could be a problem with the "
                    "sample handler or the tray is moving to slowly."),
        # Sample Handler -- 6500 (anchor 6507 printed)
        LegacyError(6501, ErrorSubsystem.SAMPLE_HANDLER,
                    "COMMAND ERROR.  Illegal command sent to the 2G Sample Handler.\n\n"
                    "SMC25 error code = 1\n\n"
                    "Contact 2G and provide them with the information in this error message."),
        LegacyError(6502, ErrorSubsystem.SAMPLE_HANDLER,
                    "RANGE ERROR.  An out of range numerical parameter was sent to the "
                    "2G Sample Handler.\n\nSMC25 error code = 2\n\n"
                    "Contact 2G and provide them with the information in this error message."),
        LegacyError(6503, ErrorSubsystem.SAMPLE_HANDLER,
                    "INVALID COMMAND ERROR.  An illegal command was sent to the 2G "
                    "Sample Handler was motion was in progress.\n\nSMC25 error code = 3\n\n"
                    "Contact 2G and provide them with the information in this error message."),
        LegacyError(6504, ErrorSubsystem.SAMPLE_HANDLER,
                    "INVALID COMMAND ERROR.  This command can only issued from an "
                    "EEPROM program.\n\nSMC25 error code = 4\n\n"
                    "Contact 2G and provide them with the information in this error message."),
        LegacyError(6505, ErrorSubsystem.SAMPLE_HANDLER,
                    "TRACK ERROR. Motion stopped before the 2G Sample Handler found the limit switch."),
        LegacyError(6506, ErrorSubsystem.SAMPLE_HANDLER,
                    "TRACK ERROR. Expected to encounter the Right-hand  limit switch but, "
                    "Left-hand limit switch was encountered first!\n\n\nThere can be two "
                    "reasons for this:\n\n1> The limit switch cables are cross connected.  "
                    "Please carefully check that the limit switches are correctly connected "
                    "to the Sample Handler Controller.\n\n2> There is a broken wire or a bad "
                    "switch on the Left-handed limit switch. Use a multimeter to insure that "
                    "there is no breaks in the wire and that the switch is functioning correctly."),
        LegacyError(6507, ErrorSubsystem.SAMPLE_HANDLER,
                    "TRACK ERROR. Expected to encounter the Left-hand  limit switch but, "
                    "Right-hand limit switch was encountered first!\n\n\nThere can be two "
                    "reasons for this:\n\n1> The limit switch cables are cross connected.  "
                    "Please carefully check that the limit switches are correctly connected "
                    "to the Sample Handler Controller.\n\n2> There is a broken wire or a bad "
                    "switch on the Right-handed limit switch. Use a multimeter to insure that "
                    "there is no breaks in the wire and that the switch is functioning correctly."),
        LegacyError(6508, ErrorSubsystem.SAMPLE_HANDLER,
                    "TRACK ERROR. Both limit switches are open!  \n\nMake sure that the "
                    "limit switch cables are connected to the Sample Handler Controller."),
        LegacyError(6509, ErrorSubsystem.SAMPLE_HANDLER,
                    "TRACK ERROR. Motion has stopped but the limit switches have not been "
                    "engaged.\n\n1> A limit switch may have been bumped.\n\n2> The stepping "
                    "motor has failed."),
        LegacyError(6510, ErrorSubsystem.SAMPLE_HANDLER,
                    "TRACK ERROR. A limit swirch was encountered before the Home Switch!\n\n"
                    "Turn off the stepping motor driver, move the boat to the center of the "
                    "track, turn power back on, and try again.  If this doesn't work, the the "
                    "Home Switch may not be connected to the Sample Handler Controller or the "
                    "switch is broken."),
        LegacyError(6511, ErrorSubsystem.SAMPLE_HANDLER,
                    "SAMPLE HANDLER ERROR.  The sampler handler did not return the correct "
                    "ID string when prompted."),
        LegacyError(6512, ErrorSubsystem.SAMPLE_HANDLER,
                    "SAMPLE HANDLER ERROR.  The limit switch was encountered before the end "
                    "of move."),
        # Furnace / CN76000 controller -- 6700 (anchor 6701 printed)
        LegacyError(6701, ErrorSubsystem.FURNACE,
                    "CN76000 ERROR: Undefined command.  Command not within acceptable range."),
        LegacyError(6702, ErrorSubsystem.FURNACE,
                    "CN76000 ERROR: Check sum error on data recieved from host."),
        LegacyError(6703, ErrorSubsystem.FURNACE,
                    "CN76000 ERROR: Command not performed by instrument.  Option may not be "
                    "enabled, restricted read/write menu.  \n\nCheck message on meter."),
        LegacyError(6704, ErrorSubsystem.FURNACE,
                    "CN76000 ERROR: Illegal ASCII characters received in command. "
                    "Instrument only accepts ASCII characters 0-9, A-F and a through f in "
                    "the data field."),
        LegacyError(6705, ErrorSubsystem.FURNACE,
                    "CN76000 ERROR:  Data field error. Not enough, to many, or improper "
                    "positioning of characters in data field."),
        LegacyError(6706, ErrorSubsystem.FURNACE,
                    "CN76000 ERROR: Hardware fault.  Return CN76000 to factory."),
        LegacyError(6707, ErrorSubsystem.FURNACE,
                    "CN76000 ERROR: Check sum error on data recieved from CN7600."),
        LegacyError(6708, ErrorSubsystem.FURNACE,
                    "CN76000 DRIVER ERROR:  The CN7600 did not return the correct ID string "
                    "when prompted."),
        # Application -- 9000 (anchor 9002 printed)
        LegacyError(9001, ErrorSubsystem.APPLICATION,
                    "Serial Port timed out waiting for data.", dialog_type=2),
        LegacyError(9002, ErrorSubsystem.APPLICATION,
                    '"not applicable" state was encountered in the program.  This is a '
                    "programming error.\n\nContact 2G and provide them with the information "
                    "in this error message.", dialog_type=2),
    )

    _BY_CODE: ClassVar[Mapping[int, LegacyError]] = MappingProxyType(
        {e.code: e for e in _ENTRIES}
    )
    _BY_SUBSYSTEM: ClassVar[dict[ErrorSubsystem, tuple[LegacyError, ...]]] = {}
    for _entry in _ENTRIES:
        _BY_SUBSYSTEM.setdefault(_entry.subsystem, []).append(_entry)  # type: ignore[attr-defined]
    for _key in _BY_SUBSYSTEM:
        _BY_SUBSYSTEM[_key] = tuple(sorted(_BY_SUBSYSTEM[_key], key=lambda e: e.code))
    _BY_SUBSYSTEM = MappingProxyType(_BY_SUBSYSTEM)

    @classmethod
    def lookup(cls, code: int) -> LegacyError | None:
        """Return the catalog entry for a code, or None when unknown."""
        if not isinstance(code, int) or isinstance(code, bool):
            return None
        return cls._BY_CODE.get(code)

    @classmethod
    def require(cls, code: int) -> LegacyError:
        entry = cls.lookup(code)
        if entry is None:
            raise KeyError(f"no recovered legacy error with code {code}")
        return entry

    @classmethod
    def subsystem(cls, subsystem: ErrorSubsystem | str) -> tuple[LegacyError, ...]:
        if isinstance(subsystem, str):
            subsystem = ErrorSubsystem(subsystem.upper())
        return cls._BY_SUBSYSTEM.get(subsystem, ())

    @classmethod
    def all(cls) -> tuple[LegacyError, ...]:
        return cls._ENTRIES

    @classmethod
    def ranges(cls) -> Mapping[ErrorSubsystem, tuple[int, int]]:
        """Minimum and maximum catalog code per subsystem."""
        return {
            subsystem: (entries[0].code, entries[-1].code)
            for subsystem, entries in cls._BY_SUBSYSTEM.items()
        }
