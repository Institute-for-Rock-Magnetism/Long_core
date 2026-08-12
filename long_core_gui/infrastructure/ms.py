"""Recovered MS (magnetic susceptibility) meter protocol and state enums.

Commands are the exact single characters recovered from the LabVIEW 8.6
``MS Driver.vi`` string table. The module performs no serial I/O; framing
belongs to the transport. The measurement reply is 6 bytes read with the
``Byte Count w/Timeout`` strategy.
"""

from __future__ import annotations

from enum import Enum

from .protocols import ProtocolValidationError


class MsOperation(str, Enum):
    VERIFY_CONNECTION = "Verify Connection"
    MEASURE = "Measure"
    ZERO = "Zero"
    CLEAR = "Clear"


class MsUnits(str, Enum):
    RANGE_0_1 = "0.1"
    RANGE_1_0 = "1.0"
    SI = "S.I."
    CSG = "C.S.G."


class MsDaqType(str, Enum):
    BKGND_1 = "Bkgnd #1"
    BKGND_2 = "Bkgnd #2"
    LEADER = "Leader"
    SAMPLE = "Sample"
    TRAILER = "Trailer"
    MANUAL = "Manual"
    N_A = "N/A"


class MsOrientation(str, Enum):
    NORMAL = "Normal: +X +Y"
    FLIPPED = "Flipped: -X -Y"


class MsCommands:
    """Exact single-character commands recovered from ``MS Driver.vi``."""

    MEASURE_REPLY_BYTES = 6

    @staticmethod
    def _operation(operation: MsOperation | str) -> MsOperation:
        if isinstance(operation, MsOperation):
            return operation
        try:
            return MsOperation(operation)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in MsOperation)
            raise ProtocolValidationError(
                f"MS operation must be one of: {allowed}"
            ) from exc

    @staticmethod
    def command(operation: MsOperation | str) -> str:
        """Return the exact byte command for an MS operation."""
        selected = MsCommands._operation(operation)
        return {
            MsOperation.MEASURE: "M",
            MsOperation.ZERO: "Z",
            MsOperation.CLEAR: "C",
            MsOperation.VERIFY_CONNECTION: "Z",  # best-known legacy behavior
        }[selected]

    @staticmethod
    def measure() -> str:
        return "M"

    @staticmethod
    def zero() -> str:
        return "Z"

    @staticmethod
    def clear() -> str:
        return "C"
