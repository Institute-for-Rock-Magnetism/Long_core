# SQUID VI reverse-engineering report

## Result

The nine files in `Labview_source/SQUID` are genuine LabVIEW 8.6 release VIs.
Their RSRC containers retain front-panel resources, block-diagram resources,
compiled i386 code, connector/type descriptors, dependencies, and default data.
The open-source `pylabview` extractor could decode the version, dependencies,
type descriptors, enum labels, and default lookup arrays. Some graphical heaps
remained binary, so the retained LabVIEW HTML/PNG export was used to interpret
the data flow.

This is sufficient for an exact command builder, strict status parser, DAQ
sequence model, and recovered calibration arithmetic. It is not sufficient to
open a serial port safely without current configuration and real reply traces.

## Exact command table

| Operation | All | X | Y | Z |
|---|---|---|---|---|
| Reset counter | `ARC` | `XRC` | `YRC` | `ZRC` |
| Configure filter | `ACF` | `XCF` | `YFC` | `ZCF` |
| Configure range | `ACR` | `XCR` | `YCR` | `ZCR` |
| Configure slew | `ACS` | `XCS` | `YCS` | `ZCS` |
| Configure feedback | `ACL` | `XCL` | `YCL` | `ZCL` |
| Latch analog | `ALD` | `XLD` | `YLD` | `ZLD` |
| Latch counter | `ALC` | `XLC` | `YLC` | `ZLC` |
| Read analog | n/a | `XSD` | `YSD` | `ZSD` |
| Read counter | n/a | `XSC` | `YSC` | `ZSC` |
| Read status | n/a | `XSS` | `YSS` | `ZSS` |

`YFC` is the spelling stored in the original command table. It is not corrected
to `YCF` in the Python port.

Configuration and status commands append one character:

| Selector | Enum value to code |
|---|---|
| Filter | `1 Hz -> 1`, `10 Hz -> T`, `100 Hz -> H`, `Wide band -> W` |
| Range | `1x -> 1`, `10x -> T`, `100x -> H`, `Extended -> E` |
| Slew | `Enable fast -> E`, `Disable fast -> D` |
| Feedback | `Open -> O`, `Close -> C`, `Pulse reset -> P` |
| Status | `All -> A`, `Filter -> F`, `Range -> R`, `Slew -> S`, `Feedback -> L` |

Examples: `XCFT` selects X 10 Hz, `ZCRE` selects extended Z range, `ACLP`
pulses all feedback loops, and `ZSSA` requests complete Z status.

The VI appends carriage return, clears the input buffer before writing, uses a
2000 ms timeout, and reads by carriage-return termination. Reset, configuration,
and latch commands are write-only. Analog, counter, and status commands perform
write/read operations.

Expected reply lengths are 9 bytes for analog, 7 for counter, 12 for complete
status, and 3 for one status category.

## Status parsing and verification

A 12-character complete status response consists of four three-character
segments. Marker/value offsets are:

| Category | Marker offset | Value offset |
|---|---:|---:|
| Filter | 0 | 1 |
| Range | 3 | 4 |
| Slew | 6 | 7 |
| Feedback | 9 | 10 |

The connection probe is always `ZSSA`. The legacy VI verifies only that marker
positions contain `F`, `R`, `S`, and `L`; mismatch produces code `6001`. The
Python parser additionally rejects unknown values and incorrect lengths.

Initialization writes X/Y/Z filter, range, slew, and feedback settings, then
reads complete X/Y/Z status. It compares returned filter, range, and slew values
against requested settings. A mismatch produces code `6002`. The visible legacy
comparison does not include feedback, response, or calibration.

## Connected acquisition sequence

`SQUID DAQ.vi` performs:

```text
ALD
ALC
wait 300 ms
XSC, YSC, ZSC when each axis is in 1x range, with 50 ms delays
ZSD
wait 50 ms
YSD
wait 50 ms
XSD
```

Counter reads are skipped outside 1x range. For each axis:

```text
raw = counter + analog
adjusted = raw - background_meter
moment = adjusted * calibration
```

During background #1 capture, subtraction is bypassed and the new raw values
become the meter offsets. Repeated acquisitions produce calibrated moment arrays
and mean raw values. The loop stops after the requested count or on error.

Background #1 also pulses all feedback loops and waits 4000 ms before DAQ.
Leader, sample, and trailer processing calculates means, standard deviations,
intensity, inclination, declination, rotations, and output rows.

## Recovered configuration structure

Each axis contains response, calibration, filter, range, slew, and feedback.
The archived front-panel defaults show calibrations of `8.21E-5`, `8.34E-5`,
and `4.32E-5` for X/Y/Z. Response defaults are zero even though the setup panel
states that response must be non-zero. These are historical software defaults,
not commissioned machine values.

## Known uncertainties and legacy defects

- `SQUID AC PARSE.vi` conditionally rearranges fixed two-character fields from
  P-prefixed X analog replies. The transformation is reproduced, but its
  numeric/device meaning requires one real raw reply or controller manual.
- Current baud, data bits, parity, stop bits, and calibration remain unknown.
- The driver does not retry failed communications.
- Configuration/reset writes do not read acknowledgements.
- The legacy verification checks markers more weakly than the Python parser.
- A visible filter-cluster update sequence appears shifted by one case. The
  Python code does not reproduce that likely defect.
- Manual reset is only an operator confirmation dialog, not hardware proof.
- The duplicate DAQ and Measure VIs differ at the binary level; their functional
  differences should be inspected in LabVIEW before choosing an authoritative
  version.

## Python implementation

- Exact builders: `long_core_gui/infrastructure/protocols.py`
- Strict parsing and DAQ math: `long_core_gui/infrastructure/squid.py`
- Focused tests: `tests/test_squid.py`

The implementation is transport-independent and performs no serial I/O.
