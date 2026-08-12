# Reverse-engineering reconstruction index

This folder holds the machine-readable reconstruction evidence for the
LabVIEW → PySide6 migration. Everything here was produced with the open
toolchain in `tools/extract_vi.py` (pylabview XML extraction + tesseract OCR
of the printed diagram/panel exports). The printed exports themselves
(`vi_prints/`) were removed during the repo slim-down; the VIs under
`Labview_source/` remain the ground-truth reference, and the printed pages
can be re-exported from LabVIEW to regenerate any artifact.

## Module reports

| Report | Module | Status |
|---|---|---|
| `SQUID_REVERSE_ENGINEERING.md` (repo root) | SQUID driver | complete (exact commands, parsing, DAQ math) |
| `ERROR_CODES_REVERSE_ENGINEERING.md` | error catalog | complete (all descriptions + codes) |
| `GLOBALS_REVERSE_ENGINEERING.md` | system configuration | complete (schema + defaults) |
| `SERIAL_REVERSE_ENGINEERING.md` | serial layer | complete (dispatch, VISA, defaults) |
| `MS_REVERSE_ENGINEERING.md` | MS meter | complete (M/Z/C commands, enums) |
| `SAMPLE_HANDLER_REVERSE_ENGINEERING.md` | 2G SMC25 track | complete (exact command dictionary) |
| `TREATMENT_DRIVERS_REVERSE_ENGINEERING.md` | Degauss + ARM + IRM + Furnace | complete (commands + state machines) |
| `QUEUE_REVERSE_ENGINEERING.md` | measurement queue | partial (enums + empirical binary layout) |
| Calc/Scan processing | intensity/inclination/declination, rotations, drift/tray correction, leader-trailer | covered by `long_core_gui/domain/calculations.py`; enums cross-validated |

## Raw artifacts per module

- `serial/`, `global/`, `error/`, `setup/`, `ms/`, `degauss/`, `arm/`,
  `irm/`, `furnace/`, `sample_handler/`, `calc/`, `scan/`, `meas_q/`,
  `controls/` — per-VI folders with:
  - `*.xml` — pylabview extraction (enum labels, type descriptors, DFDS
    default data, diagram string constants)
  - `diagram_pageN.txt` — OCR text of each exported block-diagram page
  - `front_panel.txt` — OCR text of the front panel
- `html_reports/` — text conversion of the six LabVIEW HTML exports
  (top-level, case dispatch, SPHCAR, full initialize, save/yes-no,
  extract input data, file paths).

## Regenerating

```bash
python tools/extract_vi.py "Labview_source/<Module>" reconstructions/<module>
```

Requires `pylabview` and `tesseract` (see `pyproject.toml` optional deps),
plus a fresh `vi_prints/dependencies` export of the module's block diagrams
(the shipped prints were removed from the repo). The script is idempotent; it
skips artifacts that already exist.

## Caveats

Defaults recovered from front panels and diagram constants are historical
software values, not commissioned machine settings. See each report's
"Uncertainties" section and `LABVIEW_MIGRATION.md` for the commissioning
boundary.
