"""Tests for the recovered legacy settings schema."""

from __future__ import annotations

import pytest

from long_core_gui.infrastructure.legacy_settings import (
    BackgroundParameters,
    DriftToleranceType,
    FurnaceParameters,
    LegacyFilePaths,
    LegacySettings,
    MeasurementType,
    OfflineTreatmentParameters,
    SampleHandlerParameters,
    SerialPortDefaults,
    SettingsValidationError,
    TrayParameters,
    TrackKind,
)


def test_recovered_defaults():
    settings = LegacySettings()
    # Documented panel defaults
    assert settings.file_paths.local_hard_drive_file_path == r"C:\Testing"
    assert settings.tray.sample_interval == 1.00
    assert settings.tray.leader_length == 9.0
    assert settings.tray.trailer_length == 15.0
    assert settings.tray.measurement_type is MeasurementType.CONTINUOUS
    assert settings.background.drift_tolerance_absolute == 4.0e-8
    assert settings.furnace.cooling_temp_degc == 30.00
    assert settings.furnace.fan_temp_degc == 51.00
    assert settings.sample_handler.home_switch_type == "Home Switch"
    assert settings.offline_treatment.field_dec == 0.0
    assert settings.offline_treatment.field_inc == 90.0
    assert settings.degauss_character_delay_ms == 50
    assert settings.scale == 1.00
    assert settings.track_type is TrackKind.STANDARD


def test_serial_defaults():
    serial = SerialPortDefaults()
    assert serial.recovered_ports == ("COM1", "COM2", "COM3", "COM4")
    assert serial.arm_port == "COM4"
    assert serial.baudrate == 9600
    assert serial.bytesize == 8
    assert serial.parity == "N"
    assert serial.legacy_port_numbers == tuple(range(9))


def test_validation_rejects_bad_values():
    with pytest.raises(SettingsValidationError):
        TrayParameters(sample_interval=-1)
    with pytest.raises(SettingsValidationError):
        TrayParameters(measurement_type="Spiral")
    with pytest.raises(SettingsValidationError):
        LegacyFilePaths(backup_data_file="yes")  # type: ignore[arg-type]
    with pytest.raises(SettingsValidationError):
        FurnaceParameters(cooling_temp_degc="hot")  # type: ignore[arg-type]
    with pytest.raises(SettingsValidationError):
        BackgroundParameters(drift_tolerance_type="7")
    with pytest.raises(SettingsValidationError):
        SampleHandlerParameters(next_position_steps=-5)
    with pytest.raises(SettingsValidationError):
        OfflineTreatmentParameters(daqs_to_average=3)


def test_round_trip_dict():
    settings = LegacySettings()
    restored = LegacySettings.from_dict(settings.to_dict())
    assert restored == settings


def test_from_dict_rejects_unknown_fields():
    with pytest.raises(SettingsValidationError):
        LegacySettings.from_dict({"not_a_field": 1})


def test_defaults_are_historical_not_commissioned():
    """Guard the documented boundary: defaults must not imply live wiring."""
    settings = LegacySettings()
    assert settings.serial.recovered_ports  # constants recovered from the VI
    # No port is "wired" to a subsystem beyond the documented ARM anchor.
    assert settings.serial.arm_port == "COM4"
