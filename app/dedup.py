from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Hashable


class UpdateDeduplicator:
    def __init__(self, ttl_seconds: float = 900.0, max_entries: int = 10_000, clock=time.monotonic) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._clock = clock
        self._seen: OrderedDict[Hashable, float] = OrderedDict()

    def first_seen(self, update_id: Hashable) -> bool:
        now = self._clock()
        cutoff = now - self.ttl_seconds
        while self._seen:
            oldest_id, timestamp = next(iter(self._seen.items()))
            if timestamp > cutoff:
                break
            self._seen.pop(oldest_id)
        if update_id in self._seen:
            self._seen.move_to_end(update_id)
            return False
        self._seen[update_id] = now
        while len(self._seen) > self.max_entries:
            self._seen.popitem(last=False)
        return True

