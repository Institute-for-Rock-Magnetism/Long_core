"""Tests for the recovered MS meter protocol."""

from __future__ import annotations

import pytest

from long_core_gui.infrastructure.ms import (
    MsCommands,
    MsDaqType,
    MsOperation,
    MsOrientation,
    MsUnits,
)
from long_core_gui.infrastructure.protocols import ProtocolValidationError


def test_exact_command_bytes():
    assert MsCommands.measure() == "M"
    assert MsCommands.zero() == "Z"
    assert MsCommands.clear() == "C"
    assert MsCommands.command(MsOperation.MEASURE) == "M"
    assert MsCommands.command("Zero") == "Z"


def test_measurement_reply_size():
    assert MsCommands.MEASURE_REPLY_BYTES == 6


def test_operation_validation():
    with pytest.raises(ProtocolValidationError):
        MsCommands.command("Degauss")


def test_recovered_enums():
    assert [u.value for u in MsUnits] == ["0.1", "1.0", "S.I.", "C.S.G."]
    assert MsDaqType.BKGND_1.value == "Bkgnd #1"
    assert MsOrientation.NORMAL.value == "Normal: +X +Y"
    assert MsOrientation.FLIPPED.value == "Flipped: -X -Y"
