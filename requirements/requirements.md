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
| SEC-03 | The seed returned by `0x27 01` differs on every request. A captured seed and key pair does not unlock a later attempt. | NRC `0x35` on replay |
| SEC-04 | ECUReset or a session change does not clear the failed-attempt counter or the lockout delay. | NRC `0x37` during the delay |
| SEC-05 | Under malformed or random diagnostic requests, the ECU keeps responding. Every undefined request gets a negative response and periodic messages keep their cycle time. | Any valid NRC |

## Addresses

| Role | CAN ID |
|---|---|
| Tester request | `0x7E0` |
| ECU response | `0x7E8` |

## Scope of the virtual ECU

The requirements above are verified against a virtual ECU. These choices apply to every test:

- **Transport.** ISO-TP (ISO 15765-2) on classic CAN: 8-byte frames with padding, normal 11-bit addressing, no block size limit, no separation time. Messages longer than 7 bytes are segmented.
- **Server timing.** The session control response carries P2 = 50 ms and P2* = 5000 ms. The ECU answers within the same millisecond, and response pending (NRC `0x78`) is not used.
- **Seed and key.** Seeds are 16 bit. The seed-to-key function is public and simple, because the tests target the access-control state machine and not key strength.
- **Non-volatile data.** The failed-attempt counter, the lockout delay and stored DTCs survive an ECU reset. The session and the unlocked state do not.
- **DTC status.** Stored DTCs are reported with status `0x09` (testFailed and confirmedDTC).
- **Not supported.** suppressPosRspMsgIndicationBit, functional addressing, CAN FD.
