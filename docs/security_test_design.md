# Security test design

Each security requirement starts from a way the diagnostic interface can be abused. The test asks whether that abuse works on the build under test.

## Attack to test mapping

| Abuse | What an attacker gains | Requirement | Test |
|---|---|---|---|
| Guess the key repeatedly | Unlocked write access | SEC-01 | Three wrong keys, then check the lockout and the delay |
| Write without unlocking | Changed calibration or configuration | SEC-02 | Write in every session and lock state |
| Record one seed and key, replay it later | Unlock without knowing the algorithm | SEC-03 | Compare seeds across requests, replay a captured pair |
| Reset the ECU to get fresh attempts | Unlimited guessing | SEC-04 | Fail twice, reset, fail once, expect the lockout |
| Send malformed requests | Crash, hang, or undefined behavior | SEC-05 | Random and mutated requests, watch responses and bus timing |

## Fuzzing approach

- **Random payloads**: UDS messages of random content, 1 to 40 bytes, sent through ISO-TP. Messages over 7 bytes go out as several frames.
- **Mutation**: start from a valid request and flip bits, truncate, extend, repeat, or swap the service ID.
- **Raw frames**: random CAN frames on the request ID, bypassing ISO-TP. Most are invalid transport frames.
- **Oracle for payloads**: the ECU answers every request, an unsupported service never gets a positive response, and periodic messages stay within NET-01 while fuzzing runs.
- **Oracle for raw frames**: invalid transport frames are rightly ignored, so the check is liveness. After the noise the ECU still answers a single-frame and a multi-frame request.
- **Reproducibility**: the fuzzer is seeded. A failing case is stored with its seed and the exact frame, then added to the regression suite as a fixed test.

## Out of scope

Physical debug interfaces (UART, JTAG), firmware extraction, and side-channel analysis. These need hardware and are not modelled by the virtual bench.

## References

ISO 14229-1 (SecurityAccess) · ISO/SAE 21434 · UN Regulation No. 155
