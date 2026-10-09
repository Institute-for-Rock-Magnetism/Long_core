# Long Core Control

A modern, simulation-first PySide6 rewrite of the Institute for Rock
Magnetism 2G U-Channel Long Core LabVIEW application.

## Desktop workflow

Version 0.3 includes eight pages: Overview, Queue, Run, Plots, Run data,
Instruments, Commissioning, and Logs. The visual system follows
[ASC Oven Control](https://github.com/Institute-for-Rock-Magnetism/ASC_oven_control/blob/main/asc_oven_control/ui/theme.py):
cream canvas, deep teal navigation, orange accents, pill buttons, and rounded
cards, extended with translucent glass panels, diffused color, and soft shadows.
Glass is painted in Qt and works without an OS-specific blur dependency.

1. Add a queue recipe; double-click it or choose **Edit recipe** to change its
   measurement, treatment, sample metadata, orientation, and acquisition settings.
   Duplicate, reorder, import, and export recipes from the queue toolbar.
2. Open **Run** to review the action plan and select the homing policy. Start
   simulation, pause/resume, or abort. Timed pause treatments respect their duration;
   discrete positions and reading counts and continuous reading counts are simulated.
   Acquisition timings, calibrated motion, and treatment physics are not emulated.
3. **Plots** filters sample readings by instrument and sample, showing the latest
   400 readings in acquisition order. Simulation amplitudes use arbitrary units.
4. **Run data** filters durable run snapshots and exports CSV. Runs carry a unique
   ID and timestamps; checkpoints save partial results. Interrupted runs are marked
   after restart. Geographic/tilt directions are calculated when orientation and
   bedding metadata are supplied for SQUID recipes.
5. **Commissioning** preserves serial framing when changing port/baud settings,
   saves configuration across restarts, and executes probes in a background thread.

Queue edits are locked during execution. Closing an active run aborts and waits
for its worker to stop before saving and closing. Corrupt workspace JSON recovers
from its backup while retaining the damaged file as evidence.

## Run

```bash
python -m venv .venv
# Windows
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m long_core_gui
# macOS/Linux: .venv/bin/python -m pip install -e .
#              .venv/bin/python -m long_core_gui
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
no motion, treatment, or high-power commands in the read-only probe plan — and records raw hex/text
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

## Build and previews

```bash
python -m pip install -e ".[packaging]"
python -m PyInstaller LongCoreControl.spec --noconfirm --clean
python tools/preview_ui.py --output .shots
```

Windows output: `dist/Long Core Control/Long Core Control.exe` (distribute the
whole folder). macOS output: `dist/Long Core Control.app`. The spec selects the
appropriate native icon; installed wheels include the UI assets. Windows builds
exclude unrelated ICU DLLs found on PATH so Qt uses its compatible OS library.

For an isolated startup check, set `LONG_CORE_HOME` to a temporary directory,
then run `python -m long_core_gui --smoke-test` (or the packaged executable with
`--smoke-test`). It exits after showing the window. Previews use only simulation
and render every page at 1440 × 900 and 1080 × 700.

## Tests

```bash
python -m pip install -e ".[dev]"
python -m pytest
```
