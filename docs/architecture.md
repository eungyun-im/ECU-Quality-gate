# Architecture

## Simulated time

The bus owns the clock. Tests advance it explicitly, so a 10 s security lockout or a 5 s session timeout runs in milliseconds and gives the same result on every machine.

## Layers

| Layer | Responsibility |
|---|---|
| `ecus/` | Behavior of each ECU for a given build configuration |
| `bench/` | Bus, tester client, fault injection |
| `analyzer/` | Offline checks on recorded traces |
| `gate/` | Verdict and report |

## Why a virtual bench

The checks are about protocol behavior and timing rules, which do not depend on the physical layer. Keeping everything in one process makes each run deterministic and lets the full gate run in CI on every push.

## Out of scope

Physical-layer faults, ISO-TP multi-frame messages, and timing accuracy of real hardware.
