"""Sends VehicleSpeed and ObstacleDistance. Tests set the values directly."""

from ecus.base import VirtualEcu


class SensorEcu(VirtualEcu):
    def __init__(self, bus, network, build):
        self.speed_kph = 40.0
        self.distance_m = 50.0
        self.valid = 1
        super().__init__("sensor_ecu", bus, network, build)

    def cycle_ms(self, message):
        if message.name == "ObstacleDistance" and self.build.has("SEED-01"):
            return 26
        return message.cycle_ms

    def tx_values(self, message):
        if message.name == "VehicleSpeed":
            return {"speed_kph": self.speed_kph}
        return {"distance_m": self.distance_m, "valid": self.valid}
