"""Receives sensor messages, sends BrakeCommand, stores timeout DTCs, serves UDS."""

from ecus.base import VirtualEcu
from ecus.uds_server import UdsServer

DETECT_RANGE_M = 20.0
DEFAULT_THRESHOLD_KPH = 30.0
VIN = b"KMUECUGATE0000001"


class BrakeEcu(VirtualEcu):
    def __init__(self, bus, network, build):
        self.threshold_kph = DEFAULT_THRESHOLD_KPH
        self.dtcs = set()
        self._dtc_of = {
            d["message"]: d["code"] for d in network.diagnostics["dtcs"]
        }
        super().__init__("brake_ecu", bus, network, build)
        self.uds = UdsServer(self, network.diagnostics, build)

    # Application

    def on_timeout(self, message):
        if not self.build.has("SEED-04"):
            self.dtcs.add(self._dtc_of[message.name])

    def tx_values(self, message):
        now = self.bus.now_ms
        fault = any(self.timed_out(m, now) for m in self.rx)
        brake = (
            not fault
            and self.signals.get("speed_kph", 0.0) >= self.threshold_kph
            and self.signals.get("valid", 0) == 1
            and self.signals.get("distance_m", float("inf")) <= DETECT_RANGE_M
        )
        return {"brake_request": int(brake), "fault": int(fault)}

    # Data identifiers

    def read_did(self, did):
        if did == 0xF190:
            return list(VIN)
        if did == 0xF195:
            return self.build.version_bytes
        if did == 0x0101:
            return list(round(self.threshold_kph * 10).to_bytes(2, "big"))
        return None

    def write_did(self, did, data):
        if did == 0x0101:
            self.threshold_kph = int.from_bytes(bytes(data), "big") / 10

    # Bus

    def on_frame(self, frame):
        super().on_frame(frame)
        if frame.can_id == self.uds.request_id:
            response = self.uds.handle(frame.data, frame.ts_ms)
            if response is not None:
                self.bus.send(self.uds.response_id, response, sender=self)

    def step(self, now_ms):
        super().step(now_ms)
        self.uds.tick(now_ms)
