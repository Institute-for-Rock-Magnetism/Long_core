"""Infrastructure primitives for the Long Core control application.

Importing this package is side-effect free: it does not configure logging,
read configuration files, or open serial ports.
"""

from .config import (
    APPLICATION_CONFIG_VERSION,
    INSTRUMENT_CONFIG_VERSION,
    ApplicationConfig,
    ConfigValidationError,
    InstrumentConfig,
    SerialProfile,
    Subsystem,
)
from .persistence import (
    ConfigCorruptionError,
    JsonFormatter,
    atomic_write_json,
    load_application_config,
    save_application_config,
    setup_structured_logging,
)
from .serial_transport import (
    DisconnectedTransport,
    PySerialTransport,
    SerialTransport,
    SimulatedSerialTransport,
    TransportDisconnectedError,
    TransportError,
    create_transport,
)
from .squid import (
    AxisVector,
    SquidCommandStep,
    SquidMeasurement,
    SquidReplyError,
    SquidStatusReply,
    acquisition_plan,
    calculate_measurement,
    normalize_x_analog_reply,
    parse_analog_reply,
    parse_counter_reply,
    parse_status_reply,
    verify_connection_reply,
)

__all__ = [
    "APPLICATION_CONFIG_VERSION",
    "AxisVector",
    "INSTRUMENT_CONFIG_VERSION",
    "ApplicationConfig",
    "ConfigCorruptionError",
    "ConfigValidationError",
    "DisconnectedTransport",
    "InstrumentConfig",
    "JsonFormatter",
    "PySerialTransport",
    "SerialProfile",
    "SerialTransport",
    "SimulatedSerialTransport",
    "SquidCommandStep",
    "SquidMeasurement",
    "SquidReplyError",
    "SquidStatusReply",
    "Subsystem",
    "TransportDisconnectedError",
    "TransportError",
    "atomic_write_json",
    "acquisition_plan",
    "calculate_measurement",
    "create_transport",
    "load_application_config",
    "normalize_x_analog_reply",
    "parse_analog_reply",
    "parse_counter_reply",
    "parse_status_reply",
    "save_application_config",
    "setup_structured_logging",
    "verify_connection_reply",
]
