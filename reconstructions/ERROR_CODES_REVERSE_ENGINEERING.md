# Error codes reverse-engineering report

## Result

The complete legacy error catalog was recovered from `Global/User Error Codes.vi`
and `Error/Error List.vi`. Descriptions are exact strings extracted from the
VI's DFDS (default data) section via `pylabview`; the numeric codes were
recovered by OCR of the printed front panel (`vi_prints/dependencies/User_Error_Codesgblp.png`),
cross-checked against the printed range table and against the existing SQUID
report (which independently confirms codes `6001` and `6002`).

The catalog is exact for descriptions and structure. Every numeric code except
the ones marked as inferred follows from (a) the printed range table, (b) the
verified row anchors, and (c) row order in the DFDS data. Where inference is
used it is flagged.

## Code ranges

| Subsystem | Range | Cluster name in VI | Verified anchor |
|---|---|---|---|
| DC SQUIDs | 6000 | `DC SQUIDs Errors` | 6001 (panel) + SQUID report |
| MS meter | 6100 | `MS Errors` | 6101 (panel) |
| IRM | 6200 | `IRM 670 Errors` | inferred |
| ARM | 6300 | `ARM 615 Errors` | 6303 (panel) |
| Degauss | 6400 | `Degauss 600 Errors` | 6411 (panel) |
| Sample Handler | 6500 | `Sample Handler 810 Errors` | 6507 (panel) |
| CN76 | 6600 | (no table in the printed panel) | none |
| Furnace (CN7600 controller) | 6700 | `CN76000 Errors` | 6701 (panel) |
| Application | 9000 | `Application Errors` | 9002 (panel) |

The cluster names in the VIs (`Sample Handler 810 Errors`, `Degauss 600 Errors`,
`IRM 670 Errors`, `ARM 615 Errors`) are legacy names and do not match the code
ranges. They are reproduced verbatim below and in the Python port.

## Full catalog

Descriptions are verbatim from the VI, including legacy typos (`swirch`,
`with in`, `recieved`, `susbystem`, `Furnance`). Dialog type: 1 = OK message,
2 = continue or stop, 0 = no dialog.

### DC SQUIDs — 6000

| Code | Dialog | Description |
|---|---|---|
| 6001 | 1 | SQUID DRIVER ERROR. The SQUIDS did not return the correct ID string when prompted. |
| 6002 | 1 | SQUID DRIVER ERROR. The SQUIDS failed to configure according to the user's parameters. |

`6002` is inferred from DFDS order; `6001` matches the `6001` code documented in
`SQUID_REVERSE_ENGINEERING.md` (connection-probe failure).

### MS (magnetic susceptibility meter) — 6100

| Code | Dialog | Description |
|---|---|---|
| 6101 | 1 | MS DRIVER ERROR. The Magnetic Susceptibility did not return the correct ID string when prompted. |

### IRM — 6200

| Code | Dialog | Description |
|---|---|---|
| 6201 | 1 | IRM DRIVER ERROR. The IRM did not return the correct ID string when prompted. |
| 6202 | 1 | IRM TRIGGER TIMEOUT. The IRM Driver failed to return the "DONE" status with in the time limit |

### ARM — 6300

| Code | Dialog | Description |
|---|---|---|
| 6301 | 1 | ARM DRIVER ERROR. The ARM did not return the correct ID string when prompted. |
| 6302 | 1 | ARM IS IN MANUAL MODE! |
| 6303 | 1 | ARM OVER RANGE ERROR! |
| 6304 | 1 | ARM DRIVER ERROR. The ARM failed to configure according to the user's parameters. |

### Degauss — 6400

| Code | Dialog | Description |
|---|---|---|
| 6401 | 1 | Degausser failed to ramp up. |
| 6402 | 1 | Degausser failed to ramp down. |
| 6403 | 1 | Degausser failed to cycle. |
| 6404 | 1 | Failed to set axis and AF field! |
| 6405 | 1 | Failed to set ramp and dwell! |
| 6406 | 1 | Failed to receive "TRACKING" status. |
| 6407 | 1 | Failed to receive "ZERO" status. |
| 6408 | 1 | DEGAUSSER DRIVER ERROR. The Degausser did not return the correct ID string! |
| 6409 | 1 | DEGAUSSER DRIVER ERROR. The DEGAUSSER failed to configure according to the user's parameters. |
| 6410 | 1 | TRACKING ERROR REPORTED BY DEGAUSSER. |
| 6411 | 1 | DEGAUSSER POWER-UP TIME-OUT. The Degausser has exceeded the 30 second power-up time limit. There could be a problem with the sample handler or the tray is moving to slowly. |

The DFDS also contains a near-duplicate of the power-up timeout text ("...or you
are moving the core to slowly."). The printed table ends at `6411`, so the
duplicate is excluded from the table (see Uncertainties).

### Sample Handler — 6500

| Code | Dialog | Description |
|---|---|---|
| 6501 | 1 | COMMAND ERROR. Illegal command sent to the 2G Sample Handler. SMC25 error code = 1. Contact 2G and provide them with the information in this error message. |
| 6502 | 1 | RANGE ERROR. An out of range numerical parameter was sent to the 2G Sample Handler. SMC25 error code = 2. Contact 2G and provide them with the information in this error message. |
| 6503 | 1 | INVALID COMMAND ERROR. An illegal command was sent to the 2G Sample Handler was motion was in progress. SMC25 error code = 3. Contact 2G and provide them with the information in this error message. |
| 6504 | 1 | INVALID COMMAND ERROR. This command can only issued from an EEPROM program. SMC25 error code = 4. Contact 2G and provide them with the information in this error message. |
| 6505 | 1 | TRACK ERROR. Motion stopped before the 2G Sample Handler found the limit switch. |
| 6506 | 1 | TRACK ERROR. Expected to encounter the Right-hand limit switch but, Left-hand limit switch was encountered first! (cable cross / bad switch guidance) |
| 6507 | 1 | TRACK ERROR. Expected to encounter the Left-hand limit switch but, Right-hand limit switch was encountered first! (cable cross / bad switch guidance) |
| 6508 | 1 | TRACK ERROR. Both limit switches are open! Make sure that the limit switch cables are connected to the Sample Handler Controller. |
| 6509 | 1 | TRACK ERROR. Motion has stopped but the limit switches have not been engaged. (limit switch bumped / stepping motor failed) |
| 6510 | 1 | TRACK ERROR. A limit swirch was encountered before the Home Switch! (stepping-motor recovery procedure) |
| 6511 | 1 | SAMPLE HANDLER ERROR. The sampler handler did not return the correct ID string when prompted. |
| 6512 | 1 | SAMPLE HANDLER ERROR. The limit switch was encountered before the end of move. |

### Furnace (CN76000 controller) — 6700

| Code | Dialog | Description |
|---|---|---|
| 6701 | 1 | CN76000 ERROR: Undefined command. Command not within acceptable range. |
| 6702 | 1 | CN76000 ERROR: Check sum error on data recieved from host. |
| 6703 | 1 | CN76000 ERROR: Command not performed by instrument. Option may not be enabled, restricted read/write menu. Check message on meter. |
| 6704 | 1 | CN76000 ERROR: Illegal ASCII characters received in command. Instrument only accepts ASCII characters 0-9, A-F and a through f in the data field. |
| 6705 | 1 | CN76000 ERROR: Data field error. Not enough, to many, or improper positioning of characters in data field. |
| 6706 | 1 | CN76000 ERROR: Hardware fault. Return CN76000 to factory. |
| 6707 | 1 | CN76000 ERROR: Check sum error on data recieved from CN7600. |
| 6708 | 1 | CN76000 DRIVER ERROR: The CN7600 did not return the correct ID string when prompted. |

### Application — 9000

| Code | Dialog | Description |
|---|---|---|
| 9001 | 2 | Serial Port timed out waiting for data. |
| 9002 | 2 | "not applicable" state was encountered in the program. This is a programming error. Contact 2G and provide them with the information in this error message. |

The Application table uses dialog type 2 (continue or stop), all others use
type 1 (OK message), per the printed panel.

## Evidence

- `reconstructions/global/User_Error_Codes/User_Error_Codes.xml` — DFDS strings (authoritative).
- `vi_prints/dependencies/User_Error_Codesgblp.png` — printed panel with ranges and code columns.
- `reconstructions/html_reports/File_Pathsgbl.txt` — table structure and dialog-type help text.
- `SQUID_REVERSE_ENGINEERING.md` — independent confirmation of codes 6001/6002.

## Uncertainties

- Codes without a visible anchor row (6201/6202, 6401-6410, 6501-6506,
  6508-6512, 6702-6708, 9001, 6002) are inferred from DFDS row order; the
  inference is anchored by the verified rows (6001, 6101, 6303, 6411, 6507,
  6701, 9002).
- The two "not used"/"no used" CN76000 strings in the DFDS do not appear as
  rows (the visible row 6701 is "Undefined command", the second DFDS entry).
- The Degauss power-up timeout duplicate is excluded (table ends at 6411).
- The 6600 range (CN76 subsystem) has no table in the printed panel; its
  contents are unknown.

## Python implementation

- Catalog: `long_core_gui/infrastructure/error_codes.py`
- Tests: `tests/test_error_codes.py`
