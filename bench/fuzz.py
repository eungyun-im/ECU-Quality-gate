"""Diagnostic request fuzzer. Seeded, so every failing case can be replayed."""


class DiagFuzzer:
    def __init__(self, client, seed):
        self.client = client
        self.seed = seed

    def random_requests(self, count):
        # TODO: random service ID, length byte and payload
        raise NotImplementedError

    def mutated_requests(self, valid_request, count):
        # TODO: bit flips, truncation, wrong length byte, oversized payload
        raise NotImplementedError

    def run(self, requests):
        # TODO: send each, record no-response and non-negative replies to undefined requests
        raise NotImplementedError
