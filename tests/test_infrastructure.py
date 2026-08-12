from __future__ import annotations

import json
import logging
from pathlib import Path
import tempfile
import unittest

from long_core_gui.infrastructure.config import (
    ApplicationConfig,
    ConfigValidationError,
    InstrumentConfig,
    SerialProfile,
    Subsystem,
)
from long_core_gui.infrastructure.persistence import (
    ConfigCorruptionError,
    load_application_config,
    save_application_config,
    setup_structured_logging,
)
from long_core_gui.infrastructure.protocols import (
    ArmCommands,
    Axis,
    DegaussCommands,
    IrmCommands,
    ProtocolValidationError,
    SampleHandlerCommands,
    SquidCommands,
)
from long_core_gui.infrastructure.serial_transport import (
    DisconnectedTransport,
    PySerialTransport,
    SimulatedSerialTransport,
    TransportDisconnectedError,
    create_transport,
)


class ConfigTests(unittest.TestCase):
    def test_default_config_is_safe_and_has_every_subsystem(self) -> None:
        config = ApplicationConfig()
        self.assertTrue(config.simulation_mode)
        self.assertEqual(set(config.instruments.profiles), set(Subsystem))
        self.assertTrue(all(profile.port is None for profile in config.instruments.profiles.values()))

    def test_config_round_trip(self) -> None:
        profiles = {subsystem: SerialProfile() for subsystem in Subsystem}
        profiles[Subsystem.SQUID] = SerialProfile(
            port="/dev/ttyUSB0", baudrate=19200, read_terminator="\r"
        )
        config = ApplicationConfig(
            simulation_mode=False,
            instruments=InstrumentConfig(profiles=profiles),
        )
        self.assertEqual(ApplicationConfig.from_dict(config.to_dict()), config)

    def test_invalid_serial_and_version_are_rejected(self) -> None:
        with self.assertRaises(ConfigValidationError):
            SerialProfile(baudrate=0)
        with self.assertRaises(ConfigValidationError):
            SerialProfile(parity="invalid")
        with self.assertRaises(ConfigValidationError):
            ApplicationConfig(version=999)


class PersistenceTests(unittest.TestCase):
    def test_atomic_save_creates_backup_and_recovers_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            original = ApplicationConfig(application_name="Original")
            replacement = ApplicationConfig(application_name="Replacement")
            save_application_config(path, original)
            save_application_config(path, replacement)
            self.assertTrue(Path(f"{path}.bak").exists())

            path.write_text("{not-json", encoding="utf-8")
            recovered = load_application_config(path)
            self.assertEqual(recovered.application_name, "Original")
            self.assertTrue(list(path.parent.glob("settings.json.corrupt-*")))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["application_name"], "Original")

    def test_corruption_without_backup_raises_diagnostic_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text("broken", encoding="utf-8")
            with self.assertRaises(ConfigCorruptionError) as context:
                load_application_config(path)
            self.assertIsNotNone(context.exception.quarantine_path)

    def test_structured_logging_is_json_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.log"
            logger_name = f"long_core_gui.test.{id(self)}"
            logger = setup_structured_logging(path, logger_name=logger_name, max_bytes=1024)
            again = setup_structured_logging(path, logger_name=logger_name, max_bytes=1024)
            self.assertIs(logger, again)
            self.assertEqual(len(logger.handlers), 1)
            logger.info("connected", extra={"subsystem": "SQUID"})
            logger.handlers[0].flush()
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(record["message"], "connected")
            self.assertEqual(record["context"]["subsystem"], "SQUID")
            logger.handlers[0].close()
            logger.handlers.clear()


class TransportTests(unittest.TestCase):
    def test_factory_is_simulation_safe_and_frames_commands(self) -> None:
        profile = SerialProfile(write_terminator="\r", read_terminator="\r")
        transport = create_transport(profile)
        self.assertIsInstance(transport, SimulatedSerialTransport)
        transport.queue_response("DONE")
        transport.open()
        self.assertEqual(transport.query("PSS"), "DONE")
        self.assertEqual(transport.writes, (b"PSS\r",))

    def test_disconnected_transport_fails_closed(self) -> None:
        transport = create_transport(SerialProfile(), simulation=False)
        self.assertIsInstance(transport, DisconnectedTransport)
        with self.assertRaises(TransportDisconnectedError):
            transport.open()
        with self.assertRaises(TransportDisconnectedError):
            transport.write("PSS")

    def test_hardware_transport_is_constructed_but_not_opened(self) -> None:
        transport = create_transport(SerialProfile(port="loop://"), simulation=False)
        self.assertIsInstance(transport, PySerialTransport)
        self.assertFalse(transport.is_open)

    def test_command_injection_via_terminator_is_rejected(self) -> None:
        transport = SimulatedSerialTransport(SerialProfile())
        transport.open()
        with self.assertRaises(ValueError):
            transport.write("PSS\rPET")


class ProtocolTests(unittest.TestCase):
    def test_irm_commands(self) -> None:
        self.assertEqual(IrmCommands.amplitude(42), "PCA0042")
        self.assertEqual(IrmCommands.trigger(), "PET")
        self.assertEqual(IrmCommands.status(), "PSS")
        self.assertEqual(IrmCommands.attention(), "PCRH")
        with self.assertRaises(ProtocolValidationError):
            IrmCommands.amplitude(10_000)

    def test_degauss_commands_and_ranges(self) -> None:
        self.assertEqual(DegaussCommands.coil(Axis.Y), "DCC2")
        self.assertEqual(DegaussCommands.amplitude(75), "DCA0075")
        self.assertEqual(DegaussCommands.ramp(5), "DCR5")
        self.assertEqual(DegaussCommands.delay(9), "DCD9")
        self.assertEqual(
            [DegaussCommands.ramp_up(), DegaussCommands.ramp_down(),
             DegaussCommands.cycle(), DegaussCommands.status()],
            ["DERU", "DERD", "DERC", "DSS"],
        )
        with self.assertRaises(ProtocolValidationError):
            DegaussCommands.ramp(2)

    def test_arm_commands(self) -> None:
        self.assertEqual(ArmCommands.select_axis("axial"), "ARMCAA")
        self.assertEqual(ArmCommands.select_axis("Transverse"), "ARMCAT")
        self.assertEqual(ArmCommands.configure(), "ARMCF")
        self.assertEqual(ArmCommands.status(), "ARMSS")
        self.assertEqual(ArmCommands.ARM_STATUS_SCAN, "[OF]")
        with self.assertRaises(ProtocolValidationError):
            ArmCommands.select_axis("diagonal")

    def test_sample_handler_motion_and_validation(self) -> None:
        # Recovered SMC25 command dictionary (2G Sample Handler Driver.vi)
        self.assertEqual(SampleHandlerCommands.absolute_move(12.5), "P000012")
        self.assertEqual(SampleHandlerCommands.relative_move(2), "N000002")
        self.assertEqual(SampleHandlerCommands.acceleration(5), "A05")
        self.assertEqual(SampleHandlerCommands.base_rate(500), "B0500")
        self.assertEqual(SampleHandlerCommands.maximum_speed(3000), "M3000")
        self.assertEqual(SampleHandlerCommands.slew(1), "S1")
        self.assertEqual(SampleHandlerCommands.go(), "G")
        self.assertEqual(SampleHandlerCommands.go_and_wait(), "GF")
        self.assertEqual(SampleHandlerCommands.poll(), "%")
        self.assertEqual(SampleHandlerCommands.stop(), "Q")
        self.assertEqual(SampleHandlerCommands.abort(), ".")
        self.assertEqual(SampleHandlerCommands.identify(), "?")
        self.assertEqual(SampleHandlerCommands.home(), "H1")
        self.assertEqual(SampleHandlerCommands.crystal_frequency(), "CX")
        with self.assertRaises(ProtocolValidationError):
            SampleHandlerCommands.slew(0)
        with self.assertRaises(ProtocolValidationError):
            SampleHandlerCommands.absolute_move(-1)

    def test_squid_axis_and_all_axis_commands(self) -> None:
        self.assertEqual(SquidCommands.filter(Axis.ALL, "10hz"), "ACFT")
        self.assertEqual(SquidCommands.range("X", "100x"), "XCRH")
        self.assertEqual(SquidCommands.slew("Y", "fast"), "YCSE")
        self.assertEqual(SquidCommands.feedback("Z", "on"), "ZCLC")
        self.assertEqual(SquidCommands.latch_analog(), "ALD")
        self.assertEqual(SquidCommands.read_counter("X"), "XSC")
        self.assertEqual(SquidCommands.reset_counter(), "ARC")
        self.assertEqual(SquidCommands.status("Z"), "ZSSA")
        self.assertEqual(SquidCommands.verify_connection(), "ZSSA")
        with self.assertRaises(ProtocolValidationError):
            SquidCommands.read_analog(Axis.ALL)


if __name__ == "__main__":
    unittest.main()
