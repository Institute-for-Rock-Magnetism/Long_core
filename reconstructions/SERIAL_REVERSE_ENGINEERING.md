# Serial layer reverse-engineering report

## Result

The serial layer is a hand-rolled wrapper around the classic LabVIEW 8.6
*serial port* VIs (``Serial Port Init.vi``, ``Serial Port Read.vi``,
``Serial Port Write.vi``) — and the newer initializer additionally drives
NI-VISA (``VISA Configure Serial Port``). Recovered, exact items:

- Per-subsystem dispatch structure and the recoverable port/baud constants.
- The read/write strategy enum set used by `Serial Communication.vi`.
- The per-subsystem port-number semantics of the setup panel (0 = COM1 ...
  8 = COM9).

Not recoverable from this evidence: the exact baud/framing per controller
beyond the 9600 default, and the runtime port assignments (setup values).
See Uncertainties.

## VIs and roles

| VI | Role |
|---|---|
| `Open Serial Driver.vi` | open a port |
| `serpOpen.vi` | (recovered XML only; small wrapper) |
| `Serial Port Init.vi` | legacy parameter set (port, baud, data bits, parity, stop bits) |
| `Serial Port Initializer2.vi` | modern per-subsystem initializer (VISA) |
| `Serial Port Initializer.vi` | older initializer variant |
| `Set Serial Port Parameters.vi` | per-subsystem dispatcher called during full initialization |
| `Serial Communication.vi` | generic write/read with strategy selection |
| `Serial Port Write.vi` | low-level write |
| `Serial Port Read.vi` | low-level read |
| `Bytes At Serial Port.vi` | pending byte count |
| `Serial Port Reset.vi` | port reset |
| `Serial Port Buffer Size.vi` | buffer sizing |
| `Serial Port Data.vi` | global holding the port state cluster |

## Set Serial Port Parameters.vi — dispatch

Case structure on a `Subsystem` enum. Enum labels (from XML, verbatim,
including the legacy misspellings): `ARM`, `Degausser`, `Furnance`, `IRM`,
`Mag Susc`, `Ok`, `SQUIDs`, `Sample Handler`, `idle`, `initialize`.
Each subsystem case wires the port configuration path used at startup;
`Full Intialize System.vi` calls it with per-subsystem port refnums
(terminal names `SQUID Serial Port`, `MS Serial Port`, `DG Serial Port`,
`ARM Serial Port`, `IRM Serial Port`, `FUR Serial Port`).

## Serial Port Initializer2.vi — recovered constants

Per-subsystem case structure (ARM, Sample Handler, SQUIDs, Mag Susc,
Degausser, IRM, Furnance, Default) calling `VISA Configure Serial Port`.
Diagram string constants recovered from the VI XML:

- Ports: `COM1`, `COM2`, `COM3`, `COM4`
- Baud: `9600` (single baud constant; all cases)

The ARM case wires `COM4`. The remaining subsystem-to-port mapping is a
runtime setup value (see Uncertainties).

## Serial Communication.vi — strategy enums

Recovered enum labels (verbatim from XML; `Unitl` is LabVIEW's typo):

| Enum | Labels |
|---|---|
| Event handling | `Add event to list`, `Replace last event`, `Remove last event`, `Remove all events`, `Do nothing` |
| Write/Read mode | `Write Only`, `Read Only`, `Write & Read` |
| Buffer write mode | `No Action`, `Clear Buffer Before Write`, `Clear Buffer After Write` |
| Buffer read mode | `No Action`, `Clear Buffer Before Read` |
| Read termination | `By Time Only`, `Byte Count w/Timeout`, `By String w/Timeout`, `Unitl Buffer Empty w/Timeout`, `Look For Termination String` |
| Auxiliary | `Check For Timeout`, `Start Timer`, `Set Initial State`, `Read From Serial Port`, `Write To Serial Port`, `Number Of Bytes In Buffer`, `Finish` |

Cross-validated with the diagram OCR of `Serial_Communicationd.png`
(Write Only / Clear Buffer Before Write / Read/Write Mode / Port Number
labels). The SQUID driver uses `By String w/Timeout` semantics with a
carriage-return terminator and a 2000 ms timeout, appends `\r`, and clears
the input buffer before writing (per `SQUID_REVERSE_ENGINEERING.md`).

## Setup panel port numbers

From the printed help text in `Full_Intialize_System.vi`: the serial port
number parameter is an integer, `0: COM1 ... 8: COM9` (and legacy LPT
mappings), with platform notes for Sun SPARCstation and Macintosh. One
control per subsystem: SQUID, MS (magnetic susceptibility meter), Degauss,
ARM, IRM, and Furnace subsystems.

## Evidence

- `reconstructions/serial/` — XML extraction and OCR text for all 13 VIs.
- `reconstructions/html_reports/Full_Intialize_System.txt` — init sequence,
  terminal names, port-number help text.
- `vi_prints/dependencies/Serial_Communicationd.png` — diagram OCR.
- `SQUID_REVERSE_ENGINEERING.md` — the SQUID transport behavior above.

## Uncertainties

- Per-subsystem port numbers and framing beyond 9600/8N1 are runtime setup
  values; only the constant set (COM1-COM4) and the ARM → COM4 anchor are in
  the diagram.
- The two initializers (`Serial Port Initializer.vi` vs `Initializer2.vi`)
  differ at the binary level; only `Initializer2` was printable.
- Read terminator defaults per driver (beyond SQUID's `\r` / 2000 ms) need
  per-driver confirmation during the driver reverse engineering.
- `Serial Port Data.vi` is a global; its cluster contents were not printed.

## Python implementation

- Transport primitives (simulation-only): `long_core_gui/infrastructure/serial_transport.py`
- Recovered per-subsystem defaults: `long_core_gui/infrastructure/legacy_settings.py`
  (`SerialPortDefaults`)
