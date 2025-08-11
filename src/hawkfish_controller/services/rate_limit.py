from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float
    last_refill: float
    refill_rate: float  # tokens per second

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if successful."""
        now = time.time()
        
        # Refill tokens based on elapsed time
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        # Try to consume tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False


class RateLimiter:
    """Simple in-memory rate limiter using token buckets."""
    
    def __init__(self):
        self.buckets: dict[str, TokenBucket] = {}
        # Default limits: 100 requests per minute
        self.default_capacity = 100
        self.default_refill_rate = 100 / 60  # tokens per second
    
    def is_allowed(self, key: str, tokens: int = 1) -> tuple[bool, dict[str, Any]]:
        """
        Check if request is allowed for the given key.
        Returns (allowed, headers) tuple.
        """
        # Get or create bucket for this key
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(
                capacity=self.default_capacity,
                tokens=self.default_capacity,
                last_refill=time.time(),
                refill_rate=self.default_refill_rate,
            )
        
        bucket = self.buckets[key]
        allowed = bucket.consume(tokens)
        
        # Calculate rate limit headers
        headers = {
            "X-RateLimit-Limit": str(self.default_capacity),
            "X-RateLimit-Remaining": str(int(bucket.tokens)),
            "X-RateLimit-Reset": str(int(bucket.last_refill + 60)),  # Reset time
        }
        
        if not allowed:
            headers["Retry-After"] = "60"  # Retry after 60 seconds
        
        return allowed, headers


# Global rate limiter instance
global_rate_limiter = RateLimiter()
