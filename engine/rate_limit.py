import asyncio
import os
import time


class AsyncRateLimiter:
    """Simple async rate limiter: at most N requests per minute."""

    def __init__(self, max_requests_per_minute: int = 15):
        self.max_requests_per_minute = max_requests_per_minute
        self.min_interval = (
            60.0 / max_requests_per_minute if max_requests_per_minute > 0 else 0.0
        )
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    @classmethod
    def from_env(cls, env_key: str = "BENCHMARK_MAX_RPM", default: int = 15) -> "AsyncRateLimiter":
        raw = os.getenv(env_key, str(default))
        try:
            rpm = int(raw)
        except ValueError:
            rpm = default
        return cls(max_requests_per_minute=rpm)

    async def acquire(self) -> None:
        if self.min_interval <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            wait = self.min_interval - (now - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = time.monotonic()
