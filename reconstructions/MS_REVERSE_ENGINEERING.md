# MS (magnetic susceptibility) reverse-engineering report

## Result

The four VIs in `Labview_source/MS` implement the magnetic susceptibility
meter subsystem. The exact command set, operation enum, purpose enum,
orientation state, manual-interaction flow, and the serial strategy were
recovered. The subsystem reuses `Serial/Serial Communication.vi` with the
`Byte Count w/Timeout` strategy and a 6-byte measurement reply.

## Exact command set (recovered from the VI string table)

`MS Driver.vi` dispatches on an operation enum; the diagram string constants
are single characters:

| Operation | Command | Verified |
|---|---|---|
| Measure | `M` | XML string table |
| Zero | `Z` | XML string table |
| Clear | `C` | XML string table |
| Verify Connection | (see Uncertainties) | — |

Framing: commands go through `Serial Communication.vi` (Write & Read for
Measure, per the diagram), which appends the transport terminator; the
measurement reply is read with `Byte Count w/Timeout` and **6 bytes**
(``Bytes To Read`` constant visible on the diagram).

## Operations and flow (`MS Driver.vi`)

Case structure on the operation enum with labels `Verify Connection`,
`Measure`, `Zero`, `Clear`. Event-list messages (verbatim):

- `Verifying that the Mag Susc meter is connected`
- `Commanding the Mag Susc meter to measure`
- `Commanding the Mag Susc meter to zero`
- `Commanding the Mag Susc meter to clear`

A `Verify Failed (T)` indicator and the error cluster carry failures; the
connection check reports error `6101` (catalog entry: MS did not return the
correct ID string), cross-validating the error catalog.

Units enum (verbatim): `0.1`, `1.0`, `S.I.`, `C.S.G.`. The `0.1` / `1.0`
values are the meter sensitivity/range selections.

## Acquisition (`MS Get Data.vi`, `MS Measure.vi`)

`MS Measure.vi` dispatches on `DAQ Type` with labels `Bkgnd #1`, `Bkgnd #2`,
`Leader`, `Sample`, `Trailer` (plus `N/A`). It uses `Std Deviation and
Variance.vi` (from the LabVIEW analysis palette), the `Measurement Data.ctl`
cluster, `Area`, and `Start Time`. Event messages (verbatim, including the
legacy typo):

- `Measuring background #2`
- `Measuring leader`
- `Measuring sample`
- `Measuring traler`

`MS Get Data.vi` dispatches on `MS mode` (labels `Bkgnd #1`, `Bkgnd #2`,
`Leader`, `Manual`, `Sample`, `Trailer`) with a `Zero MS` action, calls
`Bkgnd.vi` (global), `MS Manual.vi`, `Subsystem Status.vi`, and reports
`Zeroing MS meter` / `Getting MS data from meter`.

## Orientation state (`MS Measure.vi`)

Enum `Flipped: -X -Y` / `Normal: +X +Y` — the sample-handler flip state that
negates X and Y.

## Manual interaction (`MS Manual.vi`)

Front-panel dialog text (verbatim):

- Measure: `Press the Measure button on the Magnetic Susceptibility meter.
  Enter the value below and click DONE.`
- Zero: `Press the Zero button on the Magnetic Susceptibility meter and then
  click DONE.`

The manual mode exists because the meter's front panel can drive operation.

## Evidence

- `reconstructions/ms/` — XML extraction and diagram OCR for all four VIs.
- `vi_prints/dependencies/MS_Driverd*.png` — diagram pages.
- `reconstructions/ERROR_CODES_REVERSE_ENGINEERING.md` — code 6101 anchor.

## Uncertainties

- The exact bytes of `Verify Connection` are not in the recovered string
  table; it likely reuses `Z` or an ID query, but that needs a real reply
  trace or the diagram at higher resolution.
- The 6-byte reply layout (numeric format, sign, exponent) is not
  recoverable from the export; a real reply trace is required before parsing.
- The S.I. ↔ C.S.G. conversion constants in the data math were not printed.

## Python implementation

- Commands and enums: `long_core_gui/infrastructure/ms.py`
- Tests: `tests/test_ms.py`
