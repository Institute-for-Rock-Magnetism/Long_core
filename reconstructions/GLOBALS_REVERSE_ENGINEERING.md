# System globals reverse-engineering report

## Result

The LabVIEW *global* VIs define the complete runtime configuration schema of
the Long Core system: file paths, serial ports, tray parameters, background
capture, furnace, sample handler, scale, subsystem status, and the offline
treatment defaults. All field names, types, and default values below were
recovered from the printed front panels (`vi_prints/dependencies/*gblp.png`),
the retained HTML report of `File Paths.vi`
(`reconstructions/html_reports/File_Pathsgbl.txt`), and the XML extraction of
the serial initializer (`reconstructions/serial/Serial_Port_Initializer2/`).

These are *software defaults*, not commissioned machine values. The serial port
assignments are recovered diagram constants; the tray/background numbers are
front-panel defaults.

## File Paths.vi (global) — `Global/File Paths.vi`

Fields (in panel order):

| Field | Type | Default |
|---|---|---|
| Application Name | string | — |
| Meas Queue File Path | path | — |
| Meas Queue File Name | string | — |
| Local Hard Drive File Path | path | `C:\Testing` |
| Application Folder File Path | path | — |
| Data File Path | path | — |
| Data File Name | string | — |
| Backup Data File Path | path | — |
| Backup Data File? | bool | — |
| Sample Input File Path | path | — |
| Sample Input File Name | string | — |
| User's Data File Path | path | — |
| User's Data File Name | string | — |
| Use Sample ID | bool | — |
| Datalog File Names #1 | string | — |
| Datalog File Names #2 | string | — |
| Datalog File Names #3 | string | — |
| Datalog Path | path | — |

Revision 33 of the VI is documented in the retained HTML report.

## Serial ports — `Set Up/Set Up Control Serial Ports.vi`, `Serial/Serial Port Initializer2.vi`, `Set Serial Port Parameters.vi`

The setup schema stores one port number per subsystem (0 = COM1 ... 8 = COM9,
per the printed help text). Subsystems: SQUID, MS (Mag Susc), Degauss, ARM, IRM,
Furnace, Sample Handler (TRACK), CN76. `Full Intialize System.vi` calls
`Set Serial Port Parameters.vi` with per-subsystem port refnums.

`Serial Port Initializer2.vi` hard-codes defaults in a per-subsystem case
structure: every subsystem is configured through NI-VISA
(`VISA Configure Serial Port`) at **9600 baud**. Diagram string constants
recovered from the VI XML: `COM1`, `COM2`, `COM3`, `COM4`, `9600`.
The ARM case wires **COM4**. The remaining per-subsystem mapping is a runtime
setup value; only the constant set is recoverable here.

`Degauss Comm Delays.vi` (global) adds a **character delay of 50 ms** for the
degausser link.

## Track Type — `Global/Track Type.vi`

| Field | Notes |
|---|---|
| Track Type | enum: `Standard` / `High Field` |
| DG Type | degausser variant |
| DSS length | — |
| DSS reply | — |
| AF Degauss Timeout | — |

## System Globals — `Global/System Globals.vi`

Boolean status flags: `Track Configured?`, `Valid Parameters?`,
`Valid Data File Path?`, `Valid Back Up Data File Path?`, `Valid Sample Input
File?`, `Abort In Progress?`, `Furnance Configured?` (legacy spelling),
`Auto Save Mode?`, `CW & CCW?`, `Abort Save Data?`, `Disable Password?`,
`Abort?`; plus `Password` (string), `Missing Top` (default **40.00**),
`NRM units` (enum), and the `Discrete Info` cluster.

## Subsystem Status — `Global/Subsystem Status.vi`

Connected flags: `SH?`, `SQUID?`, `MS?`, `DG?`, `ARM?`, `IRM?`, `FUR?`,
`COOL?` (enum `Connected`).

## Tray data — `Global/Tray data.vi`

Per measurement system (NRM and MS), default tray parameters:

| Field | Default |
|---|---|
| Valid Tray | false |
| Tray #1/#2/#3 z(t) | `0.00E+0` |
| Measurement Type | `Continuous` |
| Sample interval | **1.00** |
| Leader length | **9.0** |
| Trailer length | **15.0** |
| Delay after move (sec) | **0** |
| Drift Corrected | `No` |
| Tray Corrected | `No` |
| Homing | `No` |

## Background / autosave — `Global/Bkgnd.vi`

Per system (NRM and MS): `Bkg #1` and `Bkg #2` X/Y/Z values (default `0.00E+0`),
their capture times, and the meter offset. Autosave parameters:

| Field | Default / meaning |
|---|---|
| Drift tol type | `0 = % of signal`, `1 = absolute value` |
| Drift tol (%) | 0 |
| Drift tol abs | **4.0E-8** (emu) |
| Remeasure | attempt remeasurement N times |
| Save/Abort | `0 = save and continue`, `1 = abort` |

## Clean Tray — `Global/Clean Tray.vi`

`Tray Cleaning?` flag and `Degauss Level`.

## Furnace — `Global/Furnace Globals.vi`

| Field | Default |
|---|---|
| Furnace Cooling Temp (DegC) | **30.00** |
| Furnace Hold Time (Min) | **0** |
| Furnace Fan Temp (Deg C) | **51.00** |

## Sample Handler — `Global/Sample Handler Globals.vi`

| Field | Notes |
|---|---|
| Home & Tray Ref | reference side |
| Left-Hand Home & Left-Hand Tray Reference | — |
| Home Switch Type | `Home Switch` |
| Homing? | false |
| Next Position (step) | 0 |
| Pos/Neg | `negative` |
| Home Initialized? | false |
| Furnace Home Init? | false |
| Furnace Location | — |

## Offline treatment defaults — `Global/Offline Treatment.vi`

The pause/offline step of the measurement queue: `Measurement` (None),
`DAQs to Average` (Range 0-1), `Units` (`S.I.`), `Treatment`
(`Degauss X, Y, & Z`), `DG Amplitude`, `ARM Amplitude`, `IRM Amplitude`,
`Randomize DG Axis` (`No`), `Temperature`, `Field Dec` (**0**),
`Field Inc` (**90**), `Meas. Series`, `Offline Instrument`, `AF`,
`ARM Acquisition Type`, `Demag of`.

## Evidence

- Printed global panels: `vi_prints/dependencies/*gblp.png` (Scale, Track Type,
  System Globals, Subsystem Status, Tray data, Bkgnd, Clean Tray,
  Degauss Comm Delays, Furnace Globals, Sample Handler Globals,
  Temp Sample Input Data, Offline Treatment, Pause Comment).
- `reconstructions/html_reports/File_Pathsgbl.txt` — File Paths schema.
- `reconstructions/serial/Serial_Port_Initializer2/Serial_Port_Initializer2.xml`
  — VISA dependency and `COM1..COM4` / `9600` diagram constants.
- `reconstructions/html_reports/Full_Intialize_System.txt` — serial port help
  text (0=COM1 ... 8=COM9) and setup panel structure.

## Uncertainties

- Numeric defaults that were blank in the print (datalog names, some paths) are
  not recoverable from this evidence.
- The per-subsystem port assignment (which subsystem used COM2 vs COM3) is a
  runtime setup value; only the constant set (COM1-COM4) and the ARM→COM4
  wiring are in the diagram.
- `Missing Top` (40.00), drift tolerance (4.0E-8), furnace temps (30/51), tray
  geometry (1.00/9.0/15.0) and character delay (50 ms) are historical defaults.

## Python implementation

- Schema with recovered defaults: `long_core_gui/infrastructure/legacy_settings.py`
- Tests: `tests/test_legacy_settings.py`
