"""Run the virtual ECUs on a real CAN interface, in real time.

    python -m bench.live ecu --interface socketcan --channel vcan0
    python -m bench.live tester --interface socketcan --channel vcan0

The ECU code is the same as on the simulated bench. Only the bus underneath
changes: python-can instead of VirtualBus, wall-clock time instead of ticks.
Any CAN tool can then watch or talk to the ECUs, for example candump or a
standard UDS tester.
"""

import argparse
import threading
import time

import can
import isotp
import udsoncan
from udsoncan.client import Client
from udsoncan.connections import PythonIsoTpConnection

from bench.bus import Frame
from bench.network import load_network
from bench.tester import SECURITY_LEVEL, SW_VERSION_DID, THRESHOLD_DID, VIN_DID, client_config
from ecus.brake_ecu import BrakeEcu
from ecus.build import REFERENCE_BUILD, load_build
from ecus.sensor_ecu import SensorEcu
from protocol.isotp_link import PARAMS


class LiveBus:
    """VirtualBus interface on top of a python-can bus."""

    def __init__(self, can_bus):
        self.can = can_bus
        self.nodes = []
        self.transports = []
        self.trace = []
        self.injector = None
        self.now_ms = 0
        self._start = time.monotonic()

    def attach(self, node):
        self.nodes.append(node)

    def add_transport(self, transport):
        self.transports.append(transport)

    def send(self, can_id, data, sender=None):
        data = bytes(data)
        self.can.send(can.Message(arbitration_id=can_id, data=data, is_extended_id=False))
        self._deliver(Frame(self.now_ms, can_id, data), sender)

    def _deliver(self, frame, sender=None):
        self.trace.append(frame)
        for node in self.nodes:
            if node is not sender:
                node.on_frame(frame)

    def settle(self):
        while any([transport.pump() for transport in self.transports]):
            pass

    def run(self, stop=None, duration_s=None):
        """Serve the bus until stop is set or duration_s has passed."""
        deadline = None if duration_s is None else time.monotonic() + duration_s
        while not (stop and stop.is_set()):
            if deadline is not None and time.monotonic() >= deadline:
                break
            message = self.can.recv(timeout=0.001)
            now_ms = int((time.monotonic() - self._start) * 1000)
            if message is not None and not message.is_error_frame:
                self._deliver(Frame(now_ms, message.arbitration_id, bytes(message.data)))
            if now_ms != self.now_ms:
                self.now_ms = now_ms
                for node in list(self.nodes):
                    node.step(now_ms)
            self.settle()


def start_ecus(can_bus, build_path=REFERENCE_BUILD):
    """Attach the sensor and brake ECUs to a python-can bus. Returns the LiveBus."""
    network = load_network()
    build = load_build(build_path)
    bus = LiveBus(can_bus)
    SensorEcu(bus, network, build)
    BrakeEcu(bus, network, build)
    return bus


def make_live_tester(can_bus, notifier=None):
    """A stock udsoncan client over python-can and can-isotp. Returns (client, notifier)."""
    diagnostics = load_network().diagnostics
    address = isotp.Address(
        isotp.AddressingMode.Normal_11bits,
        txid=diagnostics["request_id"],
        rxid=diagnostics["response_id"],
    )
    notifier = notifier or can.Notifier(can_bus, [])
    stack = isotp.NotifierBasedCanStack(bus=can_bus, notifier=notifier, address=address, params=PARAMS)
    return Client(PythonIsoTpConnection(stack), config=client_config()), notifier


def run_tester_session(client):
    """A short diagnostic session. Returns what was read, for printing or checking."""
    result = {}
    with client:
        result["vin"] = client.read_data_by_identifier(VIN_DID).service_data.values[VIN_DID]
        version = client.read_data_by_identifier(SW_VERSION_DID).service_data.values[SW_VERSION_DID]
        result["sw_version"] = ".".join(str(part) for part in version)
        client.change_session(udsoncan.services.DiagnosticSessionControl.Session.extendedDiagnosticSession)
        client.unlock_security_access(SECURITY_LEVEL)
        client.write_data_by_identifier(THRESHOLD_DID, 350)
        threshold = client.read_data_by_identifier(THRESHOLD_DID).service_data.values[THRESHOLD_DID]
        result["threshold_kph"] = threshold[0] / 10
        dtcs = client.get_dtc_by_status_mask(0xFF).service_data.dtcs
        result["dtcs"] = [f"0x{dtc.id:06X}" for dtc in dtcs]
    return result


def main():
    parser = argparse.ArgumentParser(description="Run the virtual ECUs or a tester on a CAN interface.")
    parser.add_argument("role", choices=["ecu", "tester"])
    parser.add_argument("--interface", default="socketcan")
    parser.add_argument("--channel", default="vcan0")
    parser.add_argument("--build", default=str(REFERENCE_BUILD))
    parser.add_argument("--duration", type=float, default=None, help="seconds to run the ECUs (default: until Ctrl+C)")
    args = parser.parse_args()

    with can.Bus(interface=args.interface, channel=args.channel) as can_bus:
        if args.role == "ecu":
            bus = start_ecus(can_bus, args.build)
            print(f"ECUs running on {args.interface}:{args.channel}. Ctrl+C to stop.")
            try:
                bus.run(stop=threading.Event(), duration_s=args.duration)
            except KeyboardInterrupt:
                pass
        else:
            client, notifier = make_live_tester(can_bus)
            try:
                for key, value in run_tester_session(client).items():
                    print(f"{key}: {value}")
            finally:
                notifier.stop()


if __name__ == "__main__":
    main()
