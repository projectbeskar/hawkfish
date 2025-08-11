from __future__ import annotations

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..services.rate_limit import global_rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using token buckets."""
    
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)
        
        # Skip rate limiting for certain endpoints
        if request.url.path in ["/redfish/v1/", "/redfish/v1/metrics"]:
            return await call_next(request)
        
        # Use client IP as rate limit key
        client_ip = request.client.host if request.client else "unknown"
        
        # Check if request is allowed
        allowed, headers = global_rate_limiter.is_allowed(client_ip)
        
        if not allowed:
            # Return 429 Too Many Requests with Redfish error format
            response = Response(
                content='{"error": {"code": "Base.1.0.GeneralError", "message": "Rate limit exceeded", "@Message.ExtendedInfo": [{"MessageId": "Base.1.0.RateLimitExceeded", "Message": "The request rate limit has been exceeded.", "Severity": "Warning"}]}}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    **headers
                }
            )
            return response
        
        # Process request normally
        response = await call_next(request)
        
        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response
