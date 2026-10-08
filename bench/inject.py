"""Bus-level fault injection: drop, delay, corrupt."""


class FaultInjector:
    def drop(self, can_id, start_ms, duration_ms):
        raise NotImplementedError

    def delay(self, can_id, extra_ms):
        raise NotImplementedError

    def corrupt(self, can_id, byte_index, value):
        raise NotImplementedError
