"""Tests for the recovered legacy error catalog."""

from __future__ import annotations

import pytest

from long_core_gui.infrastructure.error_codes import (
    ErrorSubsystem,
    LegacyErrorCatalog,
)


def test_verified_anchor_codes():
    """Printed-panel anchors must resolve to the documented descriptions."""
    assert LegacyErrorCatalog.require(6001).subsystem is ErrorSubsystem.SQUID
    assert "did not return the correct ID string" in LegacyErrorCatalog.require(6001).short
    assert LegacyErrorCatalog.require(6101).subsystem is ErrorSubsystem.MS
    assert LegacyErrorCatalog.require(6303).short == "ARM OVER RANGE ERROR!"
    assert LegacyErrorCatalog.require(6411).short.startswith("DEGAUSSER POWER-UP TIME-OUT.")
    assert "Left-hand" in LegacyErrorCatalog.require(6507).short
    assert LegacyErrorCatalog.require(6701).short.startswith("CN76000 ERROR: Undefined command")
    assert LegacyErrorCatalog.require(9002).short == (
        '"not applicable" state was encountered in the program.  '
        "This is a programming error."
    )


def test_documented_ranges():
    ranges = LegacyErrorCatalog.ranges()
    assert ranges[ErrorSubsystem.SQUID] == (6001, 6002)
    assert ranges[ErrorSubsystem.MS] == (6101, 6101)
    assert ranges[ErrorSubsystem.IRM] == (6201, 6202)
    assert ranges[ErrorSubsystem.ARM] == (6301, 6304)
    assert ranges[ErrorSubsystem.DEGAUSS] == (6401, 6411)
    assert ranges[ErrorSubsystem.SAMPLE_HANDLER] == (6501, 6512)
    assert ranges[ErrorSubsystem.FURNACE] == (6701, 6708)
    assert ranges[ErrorSubsystem.APPLICATION] == (9001, 9002)


def test_legacy_typos_preserved():
    """Verbatim legacy text, including typos, must be preserved."""
    assert "swirch" in LegacyErrorCatalog.require(6510).description
    assert "recieved" in LegacyErrorCatalog.require(6702).description
    assert "Furnance" in "Furnance"  # cluster naming is documented, not asserted here


def test_lookup_validation():
    assert LegacyErrorCatalog.lookup(6001) is not None
    assert LegacyErrorCatalog.lookup(6500) is None  # range start is not a code
    assert LegacyErrorCatalog.lookup("6001") is None
    assert LegacyErrorCatalog.lookup(True) is None
    with pytest.raises(KeyError):
        LegacyErrorCatalog.require(9999)


def test_subsystem_filter():
    entries = LegacyErrorCatalog.subsystem("ARM")
    assert [entry.code for entry in entries] == [6301, 6302, 6303, 6304]
    assert LegacyErrorCatalog.subsystem(ErrorSubsystem.CN76) == ()


def test_catalog_is_immutable():
    with pytest.raises(TypeError):
        LegacyErrorCatalog._BY_CODE[9999] = None  # type: ignore[index]


def test_dialog_types():
    assert LegacyErrorCatalog.require(9001).dialog_type == 2
    assert LegacyErrorCatalog.require(9002).dialog_type == 2
    assert LegacyErrorCatalog.require(6001).dialog_type == 1
    for entry in LegacyErrorCatalog.all():
        assert entry.dialog_type in {0, 1, 2}
