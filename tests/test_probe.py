"""Tests for the operator-gated probe harness and legacy setup handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from long_core_gui.infrastructure.config import ConfigValidationError, SerialProfile, Subsystem
from long_core_gui.infrastructure.legacy_setup import (
    SETUP_FILE_NAME, MachineConfig, find_setup_file, store_setup_file,
)
from long_core_gui.infrastructure.probe import (
    PROBE_PLANS, ProbeCapture, ProbeCommandDenied, ProbeSession,
    ProbeStep, allowed_commands,
)
from long_core_gui.infrastructure.serial_transport import (
    SimulatedSerialTransport, TransportError,
)


def _profile(port: str = "COM1") -> SerialProfile:
    return SerialProfile(port=port, baudrate=9600)


class TestProbePlans:
    def test_all_subsystems_have_plans_or_raw_only(self):
        for subsystem in Subsystem:
            commands = allowed_commands(subsystem)
            for command in commands:
                assert command, "allowlist entries must be non-empty"

    def test_plans_are_read_only(self):
        """Guard: probe plans must never contain motion/treatment commands."""
        dangerous = {"P", "N", "G", "DERU", "DERD", "DERC", "DCA", "PET", "PCA", "ARMCF"}
        for subsystem, steps in PROBE_PLANS.items():
            for step in steps:
                assert step.command not in dangerous, (
                    f"{subsystem.value} probe plan contains unsafe command {step.command!r}"
                )

    def test_furnace_has_no_recovered_commands(self):
        assert PROBE_PLANS[Subsystem.FURNACE] == ()
        assert allowed_commands(Subsystem.FURNACE) == frozenset()


class TestProbeSession:
    def test_session_runs_plan_and_captures_bytes(self):
        profile = _profile()
        transport = SimulatedSerialTransport(profile, responses=["FR SL       "])
        session = ProbeSession(Subsystem.SQUID, transport)
        capture = session.run()
        assert capture.subsystem == "SQUID"
        assert len(capture.steps) == 1
        step = capture.steps[0]
        assert step.command == "ZSSA"
        assert step.ok
        assert step.rx_text == "FR SL       "
        assert transport.writes[0] == b"ZSSA\r"
        assert step.rx_bytes == 12

    def test_wrong_reply_length_marks_step_failed(self):
        transport = SimulatedSerialTransport(_profile(), responses=["short"])
        session = ProbeSession(Subsystem.SQUID, transport)
        capture = session.run()
        assert not capture.steps[0].ok
        assert "expected 12 reply bytes" in capture.steps[0].note

    def test_transport_error_is_captured(self):
        class Broken(SimulatedSerialTransport):
            def open(self):
                raise TransportError("port busy")

        session = ProbeSession(Subsystem.MS, Broken(_profile(), responses=[]))
        capture = session.run()
        assert not capture.ok
        assert "port busy" in capture.steps[0].note

    def test_disallowed_command_raises(self):
        transport = SimulatedSerialTransport(_profile())
        session = ProbeSession(Subsystem.SQUID, transport)
        with pytest.raises(ProbeCommandDenied):
            session.run([ProbeStep("evil", "DERU")])

    def test_custom_command_is_recorded_separately(self):
        transport = SimulatedSerialTransport(_profile(), responses=["DONE"])
        session = ProbeSession(Subsystem.FURNACE, transport)
        capture = session.run_custom("PSS")
        assert capture.ok
        assert len(capture.custom) == 1
        assert capture.custom[0].command == "PSS"
        assert capture.custom[0].rx_text == "DONE"

    def test_capture_round_trip(self):
        transport = SimulatedSerialTransport(_profile(port="COM3"), responses=["x"])
        session = ProbeSession(Subsystem.ARM, transport)
        capture = session.run()
        restored = ProbeCapture.from_dict(capture.to_dict())
        assert restored == capture


class TestLegacySetup:
    def test_setup_file_name_verbatim(self):
        assert SETUP_FILE_NAME == "LONG CORE.SET UP"

    def test_find_setup_file(self, tmp_path: Path):
        target = tmp_path / "long core.set up"
        target.write_bytes(b"raw")
        found = find_setup_file(tmp_path)
        assert found is not None
        # macOS APFS is case-insensitive: the exact-name path resolves to the
        # lowercase file, so compare names case-insensitively.
        assert found.name.lower() == SETUP_FILE_NAME.lower()

    def test_find_missing(self, tmp_path: Path):
        assert find_setup_file(tmp_path) is None
        assert find_setup_file(tmp_path / "missing") is None

    def test_store_setup_file(self, tmp_path: Path):
        source = tmp_path / "LONG CORE.SET UP"
        source.write_bytes(b"\x00\x01")
        stored = store_setup_file(source, tmp_path / "workspace")
        assert stored.read_bytes() == b"\x00\x01"
        assert stored.parent.name == "legacy"

    def test_machine_config_port_mapping(self):
        machine = MachineConfig.empty().with_port(Subsystem.SQUID, 3)
        config = machine.to_instrument_config()
        assert config.profile(Subsystem.SQUID).port == "COM4"

    def test_machine_config_rejects_bad_port(self):
        with pytest.raises(ConfigValidationError):
            MachineConfig.empty().with_port(Subsystem.SQUID, 12)

    def test_machine_config_round_trip(self):
        machine = MachineConfig.empty().with_port(Subsystem.TRACK, 0, baudrate=19200)
        restored = MachineConfig.from_dict(machine.to_dict())
        assert restored == machine
