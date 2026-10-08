# Requirements

## Diagnostics

| ID | Requirement | Positive response | Negative response |
|---|---|---|---|
| DIAG-01 | ECU starts in the default session. DiagnosticSessionControl `0x10 03` enters the extended session. | `0x50 03` | NRC `0x12` for an unsupported sub-function |
| DIAG-02 | With no TesterPresent `0x3E` for 5 s (S3 server), the ECU returns to the default session. | n/a | n/a |
| DIAG-03 | ReadDataByIdentifier `0x22` returns the value of a supported DID. | `0x62` + DID + data | NRC `0x31` unknown DID, NRC `0x13` wrong length |
| DIAG-04 | WriteDataByIdentifier `0x2E` is accepted only in the extended session with security unlocked. | `0x6E` + DID | NRC `0x7F` in the default session, NRC `0x33` when locked |
| DIAG-05 | ReadDTCInformation `0x19 02` reports stored DTCs. ClearDiagnosticInformation `0x14` clears them. | `0x59 02` + DTC list, `0x54` | NRC `0x13` wrong length |
| DIAG-06 | ECUReset `0x11 01` resets the ECU. After reset the session is default and security is locked. | `0x51 01` | NRC `0x12` for an unsupported sub-function |

## Network behavior

| ID | Requirement |
|---|---|
| NET-01 | Each periodic message is transmitted within ±10 % of its nominal cycle time. |
| NET-02 | When a subscribed message is missing for more than 3 nominal cycles, the receiving ECU stores a timeout DTC. |
| NET-03 | Every transmitted signal value is inside the range declared in `network/messages.yaml`. |

## Security

| ID | Requirement | Negative response |
|---|---|---|
| SEC-01 | SecurityAccess `0x27`: a wrong key is rejected. After 3 consecutive wrong keys, access is locked for 10 s. | NRC `0x35` wrong key, NRC `0x36` on the third failure, NRC `0x37` during the delay |
| SEC-02 | Write services are rejected while security is locked. | NRC `0x33` |

## Addresses

| Role | CAN ID |
|---|---|
| Tester request | `0x7E0` |
| ECU response | `0x7E8` |
