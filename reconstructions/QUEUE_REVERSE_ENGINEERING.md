# Measurement queue reverse-engineering report

## Result

The queue subsystem (`Meas. Q/`, `Set Up/Set Up Measurement Queue.vi`) stores
one queue as a list of `Measurement Queue Line.ctl` clusters. The treatment /
measurement enums, the display strings, and the empirical binary layout of the
`.QUE` files were recovered. Four real queue files exist in the repository
(`Labview_source/Top Level/MEAS QUEUE/`) and were used as ground truth.

## Queue line enums (`Controls/Measurement Queue Line.ctl`)

Recovered verbatim:

- Measurement type: `Magnetic Moment`, `Magnetic Susceptibility`, `None`
- Treatment type: `None`, `Degauss X, Y, & Z`, `Degauss X & Y`, `Degauss Z`,
  `Degauss X, Y, & Z - ARM axial`, `Degauss X, Y, & Z - ARM transverse`,
  `Degauss X & Y - ARM axial`, `Degauss X & Y - ARM transverse`,
  `Degauss  Z - ARM axial`, `Degauss Z - ARM transverse` (double space
  preserved), `ARM axial`, `ARM Transverse`, `IRM`, `Furnance` (legacy
  spelling; the Python domain uses `Furnace`), `Pause`
- Yes/No: `Yes`, `No`
- Units: `0.1`, `1.0`, `S.I.`, `C.S.G.`

These match the `TreatmentType`/`MeasurementType` enums in the Python domain
(`long_core_gui/domain/models.py`).

## Display strings (`Meas Queue Build String.vi`)

The queue editor row text is built with these exact formats:

- `Degauss on axes XYZ at %1d mT || `, `... at %1.1f Gauss || `
- `AF Demag on axes XY at ...`, `AF Demag on axes Z at ...`,
  `AF Demag on Random axes XYZ at ...`
- `Apply an Axial ARM of %1d Gauss and  a Transverse ARM of ...` (legacy
  double space), `Apply an Transverse ARM of ...` (legacy grammar)
- `Apply an IRM of %1d mT || `
- `Heat sample to %1.1f ...`
- `Pause For User's Treatment ||`
- `Average %1d MM per sample`, `Average %1d MS per sample`
- suffix ` -unit SI` / ` -unit CSG`, ` -range: 0.1` / ` -range: 1.0`

## Binary .QUE layout (empirical)

The four repository files are big-endian flattened LabVIEW data. The 96-byte
files (`FEB398.QUE`, `PAUL.QUE`, `NRMDISC.QUE`) share one record layout;
`TEST1.QUE` (196 bytes) holds two records. Verified fields (big-endian):

| Offset | Type | Observed values | Meaning |
|---|---|---|---|
| 0 | I32 | 1 | line marker / record header |
| 4 | DBL | 0.1 (FEB398/PAUL/NRMDISC), 5.0 (TEST1) | treatment value (DG amplitude) |
| 12 | DBL | 0.0 | ARM amplitude |
| 20 | DBL | 0.0 | IRM amplitude |
| 28 | DBL | 1.0 | range/units selector value |
| 36 | I32 | 1 (FEB398/PAUL), 0 (NRMDISC) | measurement mode (Continuous/Discrete) |
| 40 | I32 | 1 | measurement type |
| 44 | I32 | 1 | treatment type |
| 48 | I32 | 1 (FEB/PAUL), 0 (NRMDISC) | treatment flag |
| 52 | I32 | 0 | — |
| 56 | I32 | 0/1 | — |
| 60 | I32 | 0/1 | — |
| 64 | I32 | 0 | — |
| 68 | I32 | 13 (PAUL/TEST1), 14 (FEB398/NRMDISC) | sample/count value |
| 72 | I32 | 0 | — |
| 92 | I32 | 0/1 | trailing flag |

`NRMDISC` (= NRM discrete) is the only file with the discrete-mode marker at
offset 36, consistent with its name.

## Save/load flow

`Meas Queue Save Data.VI` opens a `*.QUE` file dialog (`Enter Measurement
Queue  file name` — double space preserved), writes via `File/Write File.vi`
using the `File Paths.vi` global (`MEAS QUEUE` folder). `Read Measurement
Queue.vi` (File module) loads. The queue editor (`Measurement Queue.vi`) uses
`Item Names` lists, `Enable-Disable.vi`, `Subsystem Status.vi`,
`Bkgnd.vi`, `Furnace Globals.vi`, and `Track Type.vi` to gate available
options.

## Uncertainties

- The exact cluster field order needs the type descriptor bytes (not parsed
  by pylabview for LV 8.6); the empirical table above is anchored by the
  four real files.
- The string fields (sample metadata) are absent from all four files, so
  their offsets are unknown.
- `TEST1.QUE` record framing (2 records + 4-byte prefix) is inferred from
  size alignment.

## Evidence

- `Labview_source/Top Level/MEAS QUEUE/*.QUE` — ground truth files.
- `reconstructions/meas_q/` — XML extraction and OCR for the queue VIs.
- `reconstructions/controls/Measurement_Queue_Line/` — queue line CTL.

## Python implementation

- Queue line model: `long_core_gui/domain/models.py`
  (`QueueStep`, `QueuePlan`)
- Editor display strings: `long_core_gui/ui/pages.py` (`QueuePage`)
