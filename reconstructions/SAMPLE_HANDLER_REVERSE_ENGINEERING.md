# Sample Handler (2G SMC25 track) reverse-engineering report

## Result

The exact 2G SMC25 motion controller command dictionary was recovered from the
enum set of `2G Sample Handler Driver.vi`. Each enum label embeds the byte
form, e.g. `Absolute move - Prrrrrr`. The previous `SampleHandlerCommands`
builders in the codebase used an invented word set (`ACC`, `MOVE ABS`, ...);
they have been **replaced** by this recovered dictionary.

## Exact SMC25 command dictionary

| Enum label (verbatim) | Command | Field |
|---|---|---|
| `Abort - .` | `.` | — |
| `Absolute move - Prrrrrr` | `P` + 6 digits | position |
| `Relative move - Nrrrrrr` | `N` + 6 digits | distance |
| `Acceleration - Azz` | `A` + 2 digits | acceleration |
| `Base rate - Bdddd` | `B` + 4 digits | base rate |
| `Decelaration - D zz` | `D` + 2 digits | deceleration (legacy spelling) |
| `Maximum Speed - Mdddd` | `M` + 4 digits | max speed |
| `Slow jog speed - Jzz` | `J` + 2 digits | jog speed |
| `Hold time - CHn` | `CH` + 1 digit | hold |
| `Home - Hi` | `H` + home position (1/2; `H1` constant seen) | — |
| `Crystal Frequency CX` | `CX` | — |
| `ID - ?` | `?` | — |
| `Go - G` | `G` | — |
| `Go & Wait - GF` | `GF` | — |
| `Poll - %` | `%` | — |
| `Remaining steps - G` | `G` | — |
| `Select/Deselct Axis - @` | `@` + axis | (legacy spelling) |
| `Set position register - Z` | `Z` + value | — |
| `Slew - S` | `S` + direction | — |
| `Stop - Q` | `Q` | — |
| `Input pins - Izz,xx` | `I` + pins | — |
| `Output pins - Ozz,xx` | `O` + pins | — |
| `Wait period - W` | `W` | — |
| `Verify - Vc` | `V` + char | — |

Units enum: `SI` / `CGS`. Direction enum: `CW` / `CCW`.

## Motion state machines

`2G Sample Handler Go To.vi` / `Go To Home.vi` / `Find Home.vi` / `Move to
Load.vi` share the recovered state enums:

- Position references: `#1`, `#2`, `#3`, `Load`, `Home Switch`,
  `Limit Switch`, `Absolute`, `Home & Tray Reference` variants
  (`Left-Hand Home & Left-Hand Tray Reference`, `Left-Hand Home & Right-Hand
  Tray Reference`, `Right-Hand Home & Left-Hand Tray Reference`,
  `Right-Hand Home & Right-Hand Tray Reference`), home switch sides
  (`Left-hand Home Switch`, `Right-hand Home Switch`), limit switch sides,
  and direction `negative` / `positive`.
- `Find Home` outcomes: `Both Switches Open`, `Far Limit Switch Found`,
  `Find Home In Opposite Direction`, `Finished`.
- `Move to Load` steps: `Move`, `Move Done?`, `Poll`, `Finished`,
  `Handle Errors`.
- `Check Load` compares the measured position: `Compare Furnace Load
  Postion`, `Compare Tray Load Postion` (legacy spellings).
- `Set ADV.vi` performs the acceleration/deceleration/velocity setup with
  `Absolute` / `Relative` modes and `SI`/`CGS` units; its diagram strings
  include `A`, `B`, `D`, `M`, `N`, `P` and `+,`/`-,` separators.
- `Scale.vi` (global) converts between steps and centimeters.

Error codes 6501-6512 (catalog) cover the SMC25 ID/range/command errors and
the track/limit-switch failures; the serial timeout is 9001.

## Uncertainties

- The `Vc` verify operand and the `I/O` pin bit semantics need the driver
  diagram at readable resolution or a real trace.
- Position scaling constants (steps per cm) are in `Scale.vi`, whose panel
  default is `1.00` only.

## Evidence

- `reconstructions/sample_handler/` — XML string tables and diagram OCR.
- `vi_prints/dependencies/2G_Sample_Handler_Driverd*.png` — diagram pages.

## Python implementation

- Exact builders: `long_core_gui/infrastructure/protocols.py`
  (`SampleHandlerCommands`)
- Tests: `tests/test_infrastructure.py`
