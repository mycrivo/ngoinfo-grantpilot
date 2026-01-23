import time
from collections import defaultdict, deque
from typing import Deque, Dict


class RateLimiter:
    def __init__(self) -> None:
        self._events: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        window_start = now - window_seconds
        events = self._events[key]
        while events and events[0] < window_start:
            events.popleft()
        if len(events) >= limit:
            return False
        events.append(now)
        return True
