# Long Core Control

A modern, simulation-first PySide6 migration of the Institute for Rock
Magnetism 2G U-Channel Long Core LabVIEW application.

## Run

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/long-core-control
```

The application starts in simulation mode and never opens a physical serial
port. Runtime configuration, queue recovery, results, and rotating JSON logs
are stored in the platform application-data directory. Set `LONG_CORE_HOME` to
use a specific runtime directory.

## Hardware bring-up

Live hardware is operator-gated. Set `LONG_CORE_HARDWARE=1` when starting the
application (or set `hardware_enabled: true` in the application config) to
unlock the **Commissioning** page. It runs strictly read-only probe commands —
ID, status, and poll queries from the recovered per-subsystem command tables;
never motion, treatment, or high-power commands — and records raw hex/text
captures to `probes/`. See
[LABVIEW_MIGRATION.md](LABVIEW_MIGRATION.md) for what must be independently
verified before enabling hardware mode.

## Architecture

- `long_core_gui/domain`: validated queue, sample, action, and vector models.
- `long_core_gui/infrastructure`: versioned configuration, atomic persistence,
  structured logs, serial transports, protocol builders, the recovered legacy
  error catalog (`error_codes.py`), and the recovered LabVIEW settings schema
  (`legacy_settings.py`).
- `long_core_gui/services`: Qt run worker and workspace/result persistence.
- `long_core_gui/ui`: navigation, queue editor, run console, plots, instruments,
  diagnostics, and the visual system.
- `tests`: domain and infrastructure unit tests.
- `Labview_source`: retained 2G LabVIEW source (VIs, controls, queue files) as
  the ground-truth reference. Installers, executables, LLB archives, driver
  sources, and runtime INI files were removed during the repo slim-down.
- `reconstructions`: machine-readable reverse-engineering evidence — module
  reports (`*_REVERSE_ENGINEERING.md`), per-VI extraction notes, and OCR text
  of every printed diagram, produced by `tools/extract_vi.py`.
- `tools`: the evidence extraction pipeline (pylabview XML + tesseract OCR).

## Reverse-engineering status

Recovered to exact-settings level: SQUID command table and DAQ math, MS meter
commands, the 2G SMC25 motion command dictionary, degauss/ARM/IRM command
sets, the complete legacy error catalog (codes + verbatim descriptions), the
system-configuration schema with historical defaults (serial ports, tray and
background parameters, furnace, sample handler), and the serial-layer
architecture (VISA, 9600 baud defaults). Each module has a report under
`reconstructions/`. Hardware remains locked until live values are verified;
see [LABVIEW_MIGRATION.md](LABVIEW_MIGRATION.md).

## Safety status

The software is production-structured and its simulation workflow is usable.
Physical hardware operation is intentionally locked. The LabVIEW print export
does not provide enough evidence to safely infer live port assignments,
terminators, calibrated positions, amplitude/temperature limits, interlocks,
or every expected response. See [LABVIEW_MIGRATION.md](LABVIEW_MIGRATION.md).

## Tests

```bash
.venv/bin/python -m pytest
```
