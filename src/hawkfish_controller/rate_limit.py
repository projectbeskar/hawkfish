"""Simple rate limiting middleware."""

import time
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class TokenBucket:
    """Simple token bucket for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
    
    def consume(self) -> bool:
        """Try to consume a token. Returns True if successful."""
        now = time.time()
        # Add tokens based on time passed
        tokens_to_add = (now - self.last_refill) * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using token bucket algorithm."""
    
    def __init__(self, app, requests_per_second: int = 10, burst_size: int = 20):
        super().__init__(app)
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.buckets = defaultdict(lambda: TokenBucket(burst_size, requests_per_second))
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get user from session or use IP
        client_ip = request.client.host if request.client else "unknown"
        return client_ip
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_id = self._get_client_id(request)
        bucket = self.buckets[client_id]
        
        if not bucket.consume():
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "1"}
            )
        
        return await call_next(request)
