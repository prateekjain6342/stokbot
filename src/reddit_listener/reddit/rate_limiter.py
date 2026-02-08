"""Rate limiting for API calls."""

import asyncio
import time
from typing import Optional


class TokenBucketRateLimiter:
    """Token bucket algorithm for rate limiting with burst support."""

    def __init__(self, rate_per_second: float = 1.0, burst: int = 10):
        """Initialize rate limiter.

        Args:
            rate_per_second: Number of requests allowed per second
            burst: Maximum burst capacity (tokens available at once)
        """
        self.rate = rate_per_second
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default 1)
        """
        async with self._lock:
            now = time.monotonic()

            # Add tokens based on time elapsed
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            # If we have enough tokens, consume and return
            if self.tokens >= tokens:
                self.tokens -= tokens
                return

            # Wait for tokens to be available
            wait_time = (tokens - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
            self.tokens = 0
            self.last_update = time.monotonic()
