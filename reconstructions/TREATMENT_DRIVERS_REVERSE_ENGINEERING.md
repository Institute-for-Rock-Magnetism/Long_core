# Treatment drivers reverse-engineering report (Degauss, ARM, IRM, Furnace)

## Result

Exact command strings, operation enums, and state machines for the four
treatment subsystems were recovered from the VI string tables of the driver
VIs. The existing `DegaussCommands` builders in `protocols.py` are confirmed;
ARM commands are newly recovered here.

## Degauss (`Degauss/`)

### Exact command table (`Degausser Driver.vi`)

| Enum label (verbatim) | Command | Notes |
|---|---|---|
| select coil: DCC | `DCC` + axis | coil 1/2/3 (X/Y/Z) |
| set amplitude: DCA | `DCA` + `%04d` | zero-padded 4-digit amplitude |
| set ramp to 1/3/5/7/9: DCRn | `DCR1` `DCR3` `DCR5` `DCR7` `DCR9` | odd ramp values only |
| set delay to 1..9 sec: DCDn | `DCD1` .. `DCD9` | dwell seconds |
| ramp UP: DERU | `DERU` | |
| ramp DOWN: DERD | `DERD` | |
| ramp CYCLE: DERC | `DERC` | |
| send status: DSS | `DSS` | `w/ DSS` / `w/o DSS` variants |
| read DERC/DERU/DERD status | — | status reply reads |

Axis enum: `X-axis`, `Y-axis`, `Z-axis`. Track types: `Standard`,
`High Field`, `Low Field` (and the legacy `Furnance` spelling in shared
enums). Transport: `Serial Communication.vi` (`Write & Read`, `By String
w/Timeout`).

### Power-up state machine (`Degauss Power Up Time Out.vi`)

States (verbatim): `Stand By`, `Ramp Up`, `Ramp Down`, `Tracking`, `Zero`,
`Unknown`. The power-up wait is bounded by the 30-second timeout documented
in error 6411.

### Axis/amplitude sequencing (`Degauss set axis-amp.vi`)

Step enum: `Initialize`, `Verify`, `Verify Connection`, `Set Amp`,
`Set Axis`, `Manual`, `Update Cntl`, `1st Failure`, `2nd Failure`,
`Finished`, `handle Errors` — a two-strike retry policy before reporting
failure.

### Wait loops

- `Degauss Wait On Zero.vi`: sends `Z`, then polls status
  (`Poll`, `Get Status`, `Check For Time Out`, `Update Status`) with
  outcomes `Finished`, `Time Out`, `Time Our Error` (legacy typo),
  `Track Error`, `Abort`, `ERROR`.
- `Degauss Wait On Track.vi`: sends `T`, same polling structure.
- `Degauss Manual Ramp Down.vi` / `Degauss Manual Axis & Amp.vi` /
  `Degauss Manual Ramp Down.vi`: manual front-panel operations.
- `Degauss Comm Delays.vi` (global): 50 ms character delay (see
  `GLOBALS_REVERSE_ENGINEERING.md`).

Reply parsing uses a scan pattern containing `[AC]`; its exact meaning needs
a real reply trace.

## ARM (`ARM/`)

### Exact commands (`ARM Driver.vi`)

| Operation | Command |
|---|---|
| Select axis (axial) | `ARMCAA` |
| Select axis (transverse) | `ARMCAT` |
| Configure | `ARMCF` |
| Status | `ARMSS` |
| Status reply marker | `[OF]` scan pattern |

Enum state: `Axial` / `Transverse`; control `Computer` / `Manual`; status
`Normal` / `Overrange` / `Unknown`; operations `Select Axis`,
`Set amplitude`, `Status`, `Verify Connection`. Error codes 6301-6304
(catalog) cover ID, manual-mode, overrange, and configuration failures.

Sequencing (`ARM Set Axis & Field.vi`): `Set Axis`, `Set Field`,
`Get Status`, `Finished`, `Handel Errors` (legacy typo), `Verify Connection`.
Manual entry (`ARM Manual Axis & Amp.vi`) uses the shared axis enum with
`N/A`.

## IRM (`IRM/`)

Confirmed commands (as previously ported in `protocols.py`):

| Operation | Command |
|---|---|
| Set amplitude | `PCA` + `%04d` |
| Trigger | `PET` |
| Status | `PSS` |
| Attention | `PCRH` |

`IRM Driver.vi` includes a `Look for DONE reply` step (with `IRM Fired.vi`
sending `D` and polling for the DONE reply), and `Verify Connection`.
Error codes 6201/6202 (catalog).

## Furnace (`Furnance/`)

- `CN85 Driver.vi` / `CN85 Control.vi`: controller output states `Off`,
  `Normal`, `High`, `Low` and `Stop` / `idle`; channels `#1`, `#2`, `#3`.
  The CN76000 ASCII error strings are catalog codes 6701-6708.
- `Furnace Motion Utilities.vi`: track motion for furnace positioning:
  `CW`, `CCW`, `GO`, `STOP`, `Home`, `Fast`, `Slow`, `Done`, `stop`.
- `Move To Furnace.vi`: `Load`, `Back`, `STOP`, `poll`, `Done`, `#1-#3`.
- `2G Write to Digital Line.vi` uses the DAQ digital I/O layer;
  `Cooling Control.vi`, `DIO Port Config.vi`, `DIO Port Read.vi`,
  `2G Read from Digital Line.vi` complete the digital interface.
- Globals: `Furnace Globals.vi` (cooling 30 °C, hold 0 min, fan 51 °C),
  `Furnace Motion Utilities`, `Move To Furnace`.

## Uncertainties

- The degausser/ARM status reply byte layouts are not recoverable from the
  print export (scan patterns `[AC]` and `[OF]` are preserved verbatim).
- The CN85 ASCII command set is not in the recovered string tables; the
  controller protocol requires the diagram at readable resolution or a real
  trace.
- The IRM `D` byte in `IRM Fired.vi` is likely the poll character for the
  DONE reply; the reply format needs a trace.

## Evidence

- `reconstructions/degauss/`, `reconstructions/arm/`, `reconstructions/irm/`,
  `reconstructions/furnace/` — XML string tables and diagram OCR.
- `reconstructions/ERROR_CODES_REVERSE_ENGINEERING.md` — code anchors.

## Python implementation

- Command builders: `long_core_gui/infrastructure/protocols.py`
  (`DegaussCommands`, `IrmCommands`, `ArmCommands`)
- Tests: `tests/test_protocols.py` (extended)
