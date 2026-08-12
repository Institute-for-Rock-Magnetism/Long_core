# LabVIEW migration record

## Evidence retained

The print export is useful and sufficient for reconstructing the application
architecture, operator workflow, data structures, calculations, queue builder,
and semantic action engine. The aggregate reports and project-specific diagram
assets remain under `vi_prints`, and the machine-readable extraction evidence
under `reconstructions/` (module reports, per-VI pylabview XML dumps, and OCR
text of every printed diagram; regenerable via `tools/extract_vi.py`). Only
the generated National Instruments `dependencies/vi.lib` documentation was
removed from the active repository; it can be regenerated from a matching
LabVIEW installation.

Primary reports:

- `vi_prints/Long_Core_Control.html`: top-level interface and event loop.
- `vi_prints/dependencies/Case_Control.html`: state dispatch and queue actions.
- `vi_prints/dependencies/File_Pathsgbl.html`: engine, serial, motion, and math.
- `vi_prints/dependencies/SPHCAR.html`: SQUID, MS, DG, ARM, and IRM drivers.
- `vi_prints/dependencies/Full_Intialize_System.html`: setup and verification.
- `vi_prints/dependencies/Save_Yes-No.html`: logging, plotting, and aborts.
- `vi_prints/dependencies/Extract_Input_Data.html`: sample and metadata input.

Module-level reverse-engineering reports live under `reconstructions/`
(SQUID, error codes, globals, serial, MS, sample handler, treatment drivers,
measurement queue).

## Recovered behavior

- Event-driven program-state control with initialization, DAQ, utilities,
  queue editing, plots, sample data, files, furnace loading, and shutdown.
- Continuous and discrete measurement modes.
- Never, every-run, and every-queue homing policies.
- Magnetic moment, magnetic susceptibility, and no-measurement queue steps.
- Degauss, ARM, combined degauss/ARM, IRM, furnace, pause, and no-treatment
  recipes, with before/after measurement ordering.
- Semantic actions for movement, background/leader/sample/trailer DAQ,
  treatment, saving, unloading, and completion.
- Intensity, inclination, declination, specimen/geographic rotation, and tilt
  correction calculations.
- Separate TRACK, SQUID, MS, DG, ARM, IRM, and FURNACE serial profiles.
- Atomic primary/backup persistence and structured diagnostic logging.

## Hardware commissioning boundary

The printouts are not all that is needed for live hardware operation. Before a
hardware adapter can be enabled, supply and independently verify:

1. Runtime LabVIEW INI/setup files and actual serial-port assignments.
2. Exact baud/framing/terminator settings for every controller.
3. Complete command-response documentation and representative raw serial logs.
4. Calibrated positions, track scale, velocities, limits, and homing behavior.
5. SQUID response/calibration values and drift/tray correction reference data.
6. Degauss, ARM, IRM, and furnace limits and physical safety interlocks.
7. Known-good input files and expected output files for regression comparison.
8. A supervised commissioning procedure with emergency-stop validation.

Until those items are available, simulation is the only enabled execution
mode. Protocol builders and pyserial transports are isolated for later adapter
work but are never opened by the GUI.
