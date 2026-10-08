"""ISO-TP (ISO 15765-2) endpoint on a bus, using the can-isotp library.

The library does the segmentation: single frames, first frames, consecutive
frames and flow control. This class only connects it to a bus object that
offers send(can_id, data, sender).
"""

from collections import deque

import isotp

# Classic CAN, 8-byte frames, padded. No block size limit and no separation time.
PARAMS = {
    "stmin": 0,
    "blocksize": 0,
    "tx_data_length": 8,
    "tx_data_min_length": 8,
    "tx_padding": 0x00,
    "can_fd": False,
    "max_frame_size": 4095,
    "rx_flowcontrol_timeout": 1000,
    "rx_consecutive_frame_timeout": 1000,
}


class IsoTpEndpoint:
    def __init__(self, bus, txid, rxid, owner):
        self.bus = bus
        self.txid = txid
        self.rxid = rxid
        self.owner = owner
        self.errors = []
        self._rx = deque()
        address = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=txid, rxid=rxid)
        self.layer = isotp.TransportLayerLogic(
            rxfn=self._receive,
            txfn=self._transmit,
            address=address,
            error_handler=self.errors.append,
            params=PARAMS,
        )

    def on_frame(self, frame):
        """Queue a bus frame addressed to this endpoint."""
        if frame.can_id == self.rxid:
            self._rx.append(
                isotp.CanMessage(arbitration_id=frame.can_id, dlc=len(frame.data), data=frame.data)
            )

    def _receive(self, timeout):
        return self._rx.popleft() if self._rx else None

    def _transmit(self, message):
        self.bus.send(message.arbitration_id, bytes(message.data), sender=self.owner)

    def pump(self):
        """Process queued frames and pending transmissions. True when anything happened."""
        stats = self.layer.process()
        return bool(stats.received or stats.sent)

    def send(self, payload):
        self.layer.send(bytes(payload))

    def receive(self):
        """Next complete message as a list of ints, or None."""
        if self.layer.available():
            return list(self.layer.recv())
        return None
