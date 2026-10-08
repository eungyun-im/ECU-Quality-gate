"""Receives sensor messages, sends BrakeCommand, stores timeout DTCs."""

from ecus.base import VirtualEcu


class BrakeEcu(VirtualEcu):
    # TODO: brake decision, receive timeout monitoring
    pass
