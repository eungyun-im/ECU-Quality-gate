"""Assemble the virtual bench: bus, two ECUs, tester and fault injector."""

from dataclasses import dataclass

from bench.bus import VirtualBus
from bench.inject import FaultInjector
from bench.network import Network, load_network
from bench.uds import UdsClient
from ecus.brake_ecu import BrakeEcu
from ecus.build import Build, REFERENCE_BUILD, load_build
from ecus.sensor_ecu import SensorEcu


@dataclass
class Bench:
    build: Build
    network: Network
    bus: VirtualBus
    sensor: SensorEcu
    brake: BrakeEcu
    client: UdsClient
    injector: FaultInjector


def make_bench(build_path=REFERENCE_BUILD):
    build = load_build(build_path)
    network = load_network()
    bus = VirtualBus()
    injector = FaultInjector()
    bus.injector = injector
    # Attach order is step order: the sender steps before the receiver.
    sensor = SensorEcu(bus, network, build)
    brake = BrakeEcu(bus, network, build)
    diagnostics = network.diagnostics
    client = UdsClient(bus, diagnostics["request_id"], diagnostics["response_id"])
    return Bench(build, network, bus, sensor, brake, client, injector)
