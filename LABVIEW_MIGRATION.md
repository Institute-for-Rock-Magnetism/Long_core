# LabVIEW migration record

## Evidence retained

The printed LabVIEW export (`vi_prints/`) was the initial source for the
reverse engineering and is sufficient to reconstruct the application
architecture, operator workflow, data structures, calculations, queue builder,
and semantic action engine. The machine-readable extraction evidence lives
under `reconstructions/` (module reports, per-VI pylabview XML dumps, and OCR
text of every printed diagram). The original VIs, controls, and queue files
under `Labview_source/` are retained as the ground-truth reference; the
printed export itself, generated National Instruments documentation, and all
installers/executables were removed during the repo slim-down. The printed
pages can be re-exported from a LabVIEW installation to regenerate any
missing artifact with `tools/extract_vi.py`.

Primary reports (see `reconstructions/README.md` for the full index):

- `reconstructions/SQUID_REVERSE_ENGINEERING.md`: top-level interface, SQUID
  driver, event loop, and DAQ math.
- `reconstructions/ERROR_CODES_REVERSE_ENGINEERING.md`: state dispatch and the
  complete legacy error catalog.
- `reconstructions/GLOBALS_REVERSE_ENGINEERING.md`: engine, serial, motion,
  and math configuration schema with historical defaults.
- `reconstructions/SERIAL_REVERSE_ENGINEERING.md`: serial layer (VISA,
  dispatch, defaults).
- `reconstructions/MS_REVERSE_ENGINEERING.md`: MS meter (M/Z/C, enums).
- `reconstructions/SAMPLE_HANDLER_REVERSE_ENGINEERING.md`: 2G SMC25 track
  command dictionary.
- `reconstructions/TREATMENT_DRIVERS_REVERSE_ENGINEERING.md`: degauss, ARM,
  IRM, and furnace drivers.
- `reconstructions/QUEUE_REVERSE_ENGINEERING.md`: measurement queue layout and
  sample/metadata handling.

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

Until those items are available, simulation is the only execution mode that
runs automatically. The **Commissioning** page provides an operator-gated
probe workflow: with `LONG_CORE_HARDWARE=1` it opens real serial ports only
for strictly read-only ID/status/poll commands from the recovered command
tables, and records raw hex/text captures for verifying parsers and framing.
No motion, treatment, or high-power command is ever sent by a probe.
