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

- **Random**: service ID, length byte and payload drawn at random.
- **Mutation**: start from a valid request and flip bits, truncate, change the length byte, or extend the payload.
- **Oracle**: the ECU answers every request, undefined requests get a negative response, and periodic messages stay within NET-01 while fuzzing runs.
- **Reproducibility**: the fuzzer is seeded. A failing case is stored with its seed and the exact frame, then added to the regression suite as a fixed test.

## Out of scope

Physical debug interfaces (UART, JTAG), firmware extraction, and side-channel analysis. These need hardware and are not modelled by the virtual bench.

## References

ISO 14229-1 (SecurityAccess) · ISO/SAE 21434 · UN Regulation No. 155
